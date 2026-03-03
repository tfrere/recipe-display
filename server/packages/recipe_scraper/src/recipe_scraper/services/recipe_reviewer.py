"""
Recipe Reviewer — Pass 3: Adversarial LLM verification.

Compares the structured Recipe JSON against the original source text
to detect discrepancies, missing items, and culinary issues.

The reviewer uses a DIFFERENT model than the structurer (adversarial principle)
and outputs a structured ReviewResult with corrections.

Robustness features (SOTA Feb 2026):
  - Deterministic assertions run BEFORE LLM review (catch obvious bugs cheaply)
  - Retry with Pydantic feedback: validation errors are injected back into the
    prompt so the LLM can self-correct (Instructor/DSPy pattern)
  - Dual-call consensus: 2 independent reviewer calls, only corrections that
    BOTH agree on are kept (cross-call intersection)
  - Time-related metadata corrections are IGNORED — times are computed
    deterministically from the step DAG at enrichment.
"""

import asyncio
import json
import logging
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError

from recipe_scraper.observability import observe, langfuse_context, get_async_openai_class
from recipe_structurer.shared import is_valid_iso8601_duration, parse_iso8601_minutes

AsyncOpenAI = get_async_openai_class()

logger = logging.getLogger(__name__)


# ── Pydantic models for structured review output ────────────────────

class IngredientCorrection(BaseModel):
    """A correction for a specific ingredient."""
    ingredient_id: str = Field(description="ID of the ingredient in the recipe JSON")
    field: str = Field(description="Field to correct: name, name_en, quantity, unit, preparation, category, notes")
    current_value: Optional[str] = None
    suggested_value: str = ""
    reason: str = ""


class StepCorrection(BaseModel):
    """A correction for a specific step."""
    step_id: str = Field(description="ID of the step in the recipe JSON")
    field: str = Field(description="Field to correct: action, duration, temperature, stepType, visualCue")
    current_value: Optional[str] = None
    suggested_value: str = ""
    reason: str = ""


class MissingItem(BaseModel):
    """An item present in the source but missing from the structured recipe."""
    item_type: str = Field(description="'ingredient' or 'step'")
    description: str = ""
    where_in_source: str = ""


class MetadataCorrection(BaseModel):
    """A correction for metadata fields (excluding time fields)."""
    field: str = Field(description="e.g. servings, difficulty, nationality")
    current_value: Optional[str] = None
    suggested_value: str = ""
    reason: str = ""


class ReviewResult(BaseModel):
    """Complete review output from the adversarial LLM."""
    recipe_title: str = Field(description="Title for reference")
    overall_score: int = Field(ge=1, le=10, description="Quality score 1-10 (10 = perfect)")
    summary: str = Field(description="1-2 sentence overall assessment")

    ingredient_corrections: list[IngredientCorrection] = Field(default_factory=list)
    step_corrections: list[StepCorrection] = Field(default_factory=list)
    missing_items: list[MissingItem] = Field(default_factory=list)
    metadata_corrections: list[MetadataCorrection] = Field(default_factory=list)
    culinary_issues: list[str] = Field(
        default_factory=list,
        description="Issues a cook would notice: wrong temps, impossible timings, missing techniques"
    )


class AssertionFailure(BaseModel):
    """A deterministic assertion failure detected before LLM review."""
    category: str = Field(description="assertion category: structural, quantity, format, reference")
    message: str
    severity: str = Field(description="error or warning")


class DeterministicAssertionResult(BaseModel):
    """Result of running deterministic assertions on a recipe."""
    failures: list[AssertionFailure] = Field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.failures if f.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.failures if f.severity == "warning")


# ── Reviewer configuration ──────────────────────────────────────────

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
REVIEWER_MODEL = "deepseek/deepseek-v3.2"

MAX_REVIEW_RETRIES = 2
CONSENSUS_CALLS = 2
CONSENSUS_TEMPERATURE = 0.3


# ── System prompt ───────────────────────────────────────────────────

REVIEWER_SYSTEM_PROMPT = """You are an expert culinary recipe reviewer and quality auditor.

Your job is to compare a STRUCTURED RECIPE (JSON) against its ORIGINAL SOURCE TEXT and find every discrepancy, error, or missing element.

Think like a professional chef reviewing a junior cook's recipe transcription. Be thorough but fair.

## What to check

### 1. INGREDIENTS (compare source list vs JSON ingredients)
- Missing ingredients (in source but not in JSON)
- Extra ingredients (in JSON but not in source)
- Wrong quantities (e.g., source says "2 cups" but JSON has quantity=1)
- Wrong names (misspelled, wrong ingredient entirely)
- Missing or wrong preparation states (e.g., source says "diced" but JSON has no preparation)
- Missing notes (substitution suggestions from the source that should be in the notes field)

### 2. STEPS (compare source instructions vs JSON steps)
- Missing steps (source instruction not captured)
- Wrong order
- Missing temperatures or cooking times on individual steps
- Aberrant step durations (e.g., 2 hours for sautéing onions, 2 minutes for braising)

### 3. METADATA
- Wrong servings count. NOTE: servings MUST always be a positive integer. Never suggest "null", "varies", or a range like "4-6". If the source says "serves 4-6", suggest "4" (lower bound). If unclear, estimate from ingredients.
- Wrong difficulty

### 4. CULINARY SANITY
- Temperatures that seem wrong (e.g., 170°F instead of 170°C, or unrealistic values)
- Ingredient quantities that seem off for the number of servings
- Techniques that don't match the recipe type

## Rules
- DO NOT flag unit translations as errors — our pipeline normalizes all units to English (tbsp, tsp, clove, etc.) BY DESIGN
- DO NOT flag time metadata (prepTime, cookTime, totalTime) — these are computed from the step DAG, not from the source
- Only flag REAL issues — not style preferences
- If the source is ambiguous, note it but don't count it as an error
- Be specific: quote the source text when pointing out discrepancies
- All field values in corrections must be STRINGS (convert numbers to strings if needed)

## Output
Return a JSON object matching the ReviewResult schema exactly."""


# ── Build the schema example ────────────────────────────────────────

_SCHEMA_EXAMPLE = ReviewResult(
    recipe_title="Example Recipe",
    overall_score=8,
    summary="Good transcription with 2 minor issues.",
    ingredient_corrections=[
        IngredientCorrection(
            ingredient_id="olive_oil",
            field="quantity",
            current_value="1",
            suggested_value="2",
            reason="Source says '2 tablespoons olive oil'"
        )
    ],
    step_corrections=[],
    missing_items=[],
    metadata_corrections=[],
    culinary_issues=[],
).model_dump()


# ═══════════════════════════════════════════════════════════════════════
# Deterministic assertions (P0) — run BEFORE LLM reviewer
# ═══════════════════════════════════════════════════════════════════════

def run_deterministic_assertions(recipe_data: Dict[str, Any]) -> DeterministicAssertionResult:
    """Run code-based assertions on a structured recipe.

    These checks are fast, deterministic, and free (no LLM call).
    They catch structural bugs that the LLM reviewer shouldn't waste
    tokens on: missing IDs, negative quantities, duplicate IDs,
    broken step→ingredient references, and invalid ISO 8601 durations.
    """
    failures: list[AssertionFailure] = []

    ingredients = recipe_data.get("ingredients", [])
    steps = recipe_data.get("steps", [])
    metadata = recipe_data.get("metadata", {})

    # ── Structural: recipe must have ingredients and steps ────────
    if not ingredients:
        failures.append(AssertionFailure(
            category="structural", severity="error",
            message="Recipe has no ingredients",
        ))
    if not steps:
        failures.append(AssertionFailure(
            category="structural", severity="error",
            message="Recipe has no steps",
        ))

    # ── Structural: no duplicate ingredient IDs ──────────────────
    ing_ids = [ing.get("id") for ing in ingredients if ing.get("id")]
    dupes = [iid for iid, count in Counter(ing_ids).items() if count > 1]
    for dup in dupes:
        failures.append(AssertionFailure(
            category="structural", severity="error",
            message=f"Duplicate ingredient ID: '{dup}'",
        ))

    # ── Structural: no duplicate step IDs ────────────────────────
    step_ids = [s.get("id") for s in steps if s.get("id")]
    step_dupes = [sid for sid, count in Counter(step_ids).items() if count > 1]
    for dup in step_dupes:
        failures.append(AssertionFailure(
            category="structural", severity="error",
            message=f"Duplicate step ID: '{dup}'",
        ))

    # ── Quantity: ingredient quantities must be positive when set ─
    for ing in ingredients:
        qty = ing.get("quantity")
        if qty is not None:
            try:
                val = float(qty)
                if val <= 0:
                    failures.append(AssertionFailure(
                        category="quantity", severity="error",
                        message=f"Ingredient '{ing.get('id')}' has non-positive quantity: {qty}",
                    ))
            except (ValueError, TypeError):
                pass  # non-numeric quantity (e.g. "to taste") is fine

    # ── Format: step durations should be valid ISO 8601 if set ───
    for step in steps:
        dur = step.get("duration")
        if dur and isinstance(dur, str) and not is_valid_iso8601_duration(dur):
            failures.append(AssertionFailure(
                category="format", severity="warning",
                message=f"Step '{step.get('id')}' has non-ISO-8601 duration: '{dur}'",
            ))

    # ── Duration: catch missing and aberrant step durations ────────
    _DURATION_BOUNDS = {
        "prep":    (0, 120),
        "combine": (0, 30),
        "cook":    (1, 180),
        "rest":    (1, 1440),
        "serve":   (0, 30),
    }

    for step in steps:
        dur = step.get("duration")
        step_type = step.get("stepType", "")

        if not dur or not isinstance(dur, str):
            failures.append(AssertionFailure(
                category="duration", severity="warning",
                message=f"Step '{step.get('id')}' has no duration",
            ))
            continue

        total_min = parse_iso8601_minutes(dur)
        if total_min is None:
            continue

        if step_type in _DURATION_BOUNDS:
            lo, hi = _DURATION_BOUNDS[step_type]
            if total_min > hi:
                failures.append(AssertionFailure(
                    category="duration", severity="warning",
                    message=(
                        f"Step '{step.get('id')}' ({step_type}) has duration "
                        f"{dur} ({total_min:.0f}min) — exceeds typical max "
                        f"of {hi}min for {step_type} steps"
                    ),
                ))

    # ── Reference: step 'uses' should reference ingredients or step produces ──
    ing_id_set = set(ing_ids)
    produces_set = set()
    for step in steps:
        prod = step.get("produces")
        if isinstance(prod, str) and prod:
            produces_set.add(prod)
        elif isinstance(prod, list):
            produces_set.update(p for p in prod if isinstance(p, str))

    valid_refs = ing_id_set | produces_set
    for step in steps:
        for ref in step.get("uses", []):
            ref_id = ref if isinstance(ref, str) else ref.get("ingredientId", "")
            if ref_id and ref_id not in valid_refs:
                failures.append(AssertionFailure(
                    category="reference", severity="warning",
                    message=f"Step '{step.get('id')}' references unknown ID '{ref_id}'",
                ))

    # ── Metadata: servings must be a positive integer ───────────
    servings = metadata.get("servings")
    if servings is not None:
        try:
            s = int(servings)
            if s <= 0:
                failures.append(AssertionFailure(
                    category="quantity", severity="error",
                    message=f"Servings is non-positive: {servings}",
                ))
            elif s > 100:
                failures.append(AssertionFailure(
                    category="quantity", severity="warning",
                    message=f"Servings suspiciously high: {servings}",
                ))
        except (ValueError, TypeError):
            failures.append(AssertionFailure(
                category="quantity", severity="error",
                message=f"Servings is not a valid integer: '{servings}' (type={type(servings).__name__})",
            ))

    result = DeterministicAssertionResult(failures=failures)
    if result.failures:
        logger.info(
            f"[Pass 3 Assertions] {result.error_count} errors, "
            f"{result.warning_count} warnings"
        )
    return result


# ═══════════════════════════════════════════════════════════════════════
# Consensus logic (P1) — intersect corrections from N reviewer calls
# ═══════════════════════════════════════════════════════════════════════

def _correction_key(corr: BaseModel) -> str:
    """Build a hashable key to match corrections across reviewer calls."""
    if isinstance(corr, IngredientCorrection):
        return f"ing:{corr.ingredient_id}:{corr.field}"
    if isinstance(corr, StepCorrection):
        return f"step:{corr.step_id}:{corr.field}"
    if isinstance(corr, MetadataCorrection):
        return f"meta:{corr.field}"
    if isinstance(corr, MissingItem):
        return f"missing:{corr.item_type}:{corr.description[:60]}"
    return str(corr)


def merge_reviews_by_consensus(reviews: list[ReviewResult]) -> ReviewResult:
    """Keep only corrections that appear in ALL reviews (intersection).

    For scalar fields (score, summary), take the conservative values:
    score = min, summary from the lowest-scoring review.
    Culinary issues are kept if they appear in >= half of the reviews.
    """
    if len(reviews) == 1:
        return reviews[0]

    n = len(reviews)

    # ── Ingredient corrections: keep only if ALL reviewers flagged ─
    ing_counts: Dict[str, list[IngredientCorrection]] = {}
    for r in reviews:
        for c in r.ingredient_corrections:
            key = _correction_key(c)
            ing_counts.setdefault(key, []).append(c)
    consensus_ing = [cs[0] for cs in ing_counts.values() if len(cs) >= n]

    # ── Step corrections ─────────────────────────────────────────
    step_counts: Dict[str, list[StepCorrection]] = {}
    for r in reviews:
        for c in r.step_corrections:
            key = _correction_key(c)
            step_counts.setdefault(key, []).append(c)
    consensus_step = [cs[0] for cs in step_counts.values() if len(cs) >= n]

    # ── Missing items ────────────────────────────────────────────
    missing_counts: Dict[str, list[MissingItem]] = {}
    for r in reviews:
        for m in r.missing_items:
            key = _correction_key(m)
            missing_counts.setdefault(key, []).append(m)
    consensus_missing = [ms[0] for ms in missing_counts.values() if len(ms) >= n]

    # ── Metadata corrections ─────────────────────────────────────
    meta_counts: Dict[str, list[MetadataCorrection]] = {}
    for r in reviews:
        for c in r.metadata_corrections:
            key = _correction_key(c)
            meta_counts.setdefault(key, []).append(c)
    consensus_meta = [cs[0] for cs in meta_counts.values() if len(cs) >= n]

    # ── Culinary issues: keep if >= half reviewers mention it ─────
    issue_counts: Dict[str, int] = {}
    for r in reviews:
        for issue in r.culinary_issues:
            normalized = issue.strip().lower()[:80]
            issue_counts[normalized] = issue_counts.get(normalized, 0) + 1
    all_issues = []
    for r in reviews:
        for issue in r.culinary_issues:
            if issue.strip().lower()[:80] in issue_counts:
                if issue_counts[issue.strip().lower()[:80]] >= (n / 2):
                    if issue not in all_issues:
                        all_issues.append(issue)

    # ── Score: conservative (min) ────────────────────────────────
    min_review = min(reviews, key=lambda r: r.overall_score)

    total_before = sum(
        len(r.ingredient_corrections) + len(r.step_corrections)
        + len(r.missing_items) + len(r.metadata_corrections)
        for r in reviews
    ) / n
    total_after = (
        len(consensus_ing) + len(consensus_step)
        + len(consensus_missing) + len(consensus_meta)
    )
    logger.info(
        f"[Pass 3 Consensus] {n} reviews merged: "
        f"avg {total_before:.0f} corrections → {total_after} consensus corrections"
    )

    return ReviewResult(
        recipe_title=min_review.recipe_title,
        overall_score=min_review.overall_score,
        summary=min_review.summary,
        ingredient_corrections=consensus_ing,
        step_corrections=consensus_step,
        missing_items=consensus_missing,
        metadata_corrections=consensus_meta,
        culinary_issues=all_issues,
    )


# ═══════════════════════════════════════════════════════════════════════
# Main reviewer class
# ═══════════════════════════════════════════════════════════════════════

class RecipeReviewer:
    """
    Adversarial reviewer that compares structured recipes against source text.

    Uses a different LLM model than the recipe structurer to provide
    independent verification (adversarial principle).

    Robustness features:
      - Deterministic pre-assertions (structural, quantity, format, reference)
      - Retry with Pydantic validation feedback (max 2 retries)
      - Dual-call consensus (only keeps corrections both calls agree on)
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.warning("No OPENROUTER_API_KEY — reviewer will be disabled")
            self._client = None
        else:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=OPENROUTER_BASE_URL,
            )

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def _build_messages(
        self,
        recipe_json: str,
        source_text: str,
        source_url: Optional[str],
        validation_error: Optional[str] = None,
    ) -> list[dict]:
        """Build the chat messages for a review call.

        If validation_error is set, it is appended as a follow-up message
        so the LLM can self-correct (Instructor retry pattern).
        """
        source_text_truncated = source_text[:24000]

        user_prompt = f"""## ORIGINAL SOURCE TEXT{f' (from {source_url})' if source_url else ''}

{source_text_truncated}

---

## STRUCTURED RECIPE (JSON)

{recipe_json}

---

Review this structured recipe against the source text. Find all discrepancies.

You MUST return a JSON object with EXACTLY this structure (example):

{json.dumps(_SCHEMA_EXAMPLE, indent=2)}

Required fields: recipe_title, overall_score (1-10), summary, ingredient_corrections, step_corrections, missing_items, metadata_corrections, culinary_issues.
All values in correction objects must be STRINGS.
Return ONLY the JSON object, no markdown fences."""

        messages = [
            {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        if validation_error:
            messages.append({
                "role": "assistant",
                "content": "(previous attempt had validation errors)",
            })
            messages.append({
                "role": "user",
                "content": (
                    "Your previous response failed Pydantic validation:\n\n"
                    f"```\n{validation_error}\n```\n\n"
                    "Please fix these errors and return a corrected JSON object."
                ),
            })

        return messages

    def _strip_fences(self, raw: str) -> str:
        """Strip markdown code fences from LLM output."""
        text = raw.strip()
        if text.startswith("```"):
            first_newline = text.index("\n")
            text = text[first_newline + 1:]
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3].rstrip()
        return text

    async def _single_review_call(
        self,
        recipe_json: str,
        source_text: str,
        source_url: Optional[str],
        temperature: float = 0.1,
    ) -> Optional[ReviewResult]:
        """Execute a single review call with retry-on-validation-error.

        On Pydantic validation failure, the error is injected back into
        the conversation and the LLM retries (up to MAX_REVIEW_RETRIES).
        """
        validation_error: Optional[str] = None

        for attempt in range(1 + MAX_REVIEW_RETRIES):
            try:
                messages = self._build_messages(
                    recipe_json, source_text, source_url, validation_error,
                )
                response = await self._client.chat.completions.create(
                    model=REVIEWER_MODEL,
                    messages=messages,
                    max_tokens=4096,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )

                raw = self._strip_fences(response.choices[0].message.content)
                review_data = json.loads(raw)
                review = ReviewResult(**review_data)

                if attempt > 0:
                    logger.info(f"[Pass 3] Retry {attempt} succeeded")

                return review

            except (json.JSONDecodeError, ValidationError) as e:
                validation_error = str(e)
                if attempt < MAX_REVIEW_RETRIES:
                    logger.warning(
                        f"[Pass 3] Attempt {attempt + 1} validation failed, "
                        f"retrying with feedback: {validation_error[:200]}"
                    )
                else:
                    logger.error(
                        f"[Pass 3] All {1 + MAX_REVIEW_RETRIES} attempts failed: "
                        f"{validation_error[:200]}"
                    )
            except Exception as e:
                logger.error(f"[Pass 3] Review call failed: {e}")
                return None

        return None

    @observe(name="pass3_review")
    async def review(
        self,
        recipe_data: Dict[str, Any],
        source_text: str,
        source_url: Optional[str] = None,
    ) -> Tuple[Optional[ReviewResult], DeterministicAssertionResult]:
        """
        Review a structured recipe against its original source text.

        Runs deterministic assertions first, then dual LLM reviewer calls
        with consensus merging.

        Returns:
            Tuple of (ReviewResult or None, DeterministicAssertionResult)
        """
        # ── Phase 1: Deterministic assertions (free, instant) ─────
        assertions = run_deterministic_assertions(recipe_data)

        if not self.is_available:
            logger.warning("Reviewer not available (no API key)")
            return None, assertions

        title = recipe_data.get("metadata", {}).get("title", "Unknown")
        logger.info(f"[Pass 3] Reviewing recipe: {title}")

        # Build compact recipe JSON for the reviewer
        recipe_summary = {
            "metadata": {
                k: v for k, v in recipe_data.get("metadata", {}).items()
                if k in ("title", "description", "servings", "difficulty",
                         "recipeType", "nationality", "notes")
            },
            "ingredients": recipe_data.get("ingredients", []),
            "steps": [
                {k: v for k, v in s.items()
                 if k in ("id", "action", "uses", "requires", "produces",
                          "duration", "temperature", "isPassive", "stepType",
                          "visualCue", "subRecipe")}
                for s in recipe_data.get("steps", [])
            ],
            "tools": recipe_data.get("tools", []),
        }
        recipe_json = json.dumps(recipe_summary, indent=2, ensure_ascii=False)

        # ── Phase 2: Dual LLM reviewer calls (consensus) ─────────
        calls = [
            self._single_review_call(
                recipe_json, source_text, source_url,
                temperature=CONSENSUS_TEMPERATURE,
            )
            for _ in range(CONSENSUS_CALLS)
        ]
        results = await asyncio.gather(*calls, return_exceptions=True)

        reviews = [
            r for r in results
            if isinstance(r, ReviewResult)
        ]

        if not reviews:
            logger.error(f"[Pass 3] All reviewer calls failed for '{title}'")
            return None, assertions

        # ── Phase 3: Consensus merge ─────────────────────────────
        review = merge_reviews_by_consensus(reviews)

        total_issues = (
            len(review.ingredient_corrections)
            + len(review.step_corrections)
            + len(review.missing_items)
            + len(review.metadata_corrections)
            + len(review.culinary_issues)
        )

        logger.info(
            f"[Pass 3] Review complete for '{title}': "
            f"score={review.overall_score}/10, "
            f"consensus_issues={total_issues}, "
            f"assertions={assertions.error_count}err/{assertions.warning_count}warn"
        )

        # ── Langfuse observation-level scoring ───────────────────
        langfuse_context.score_current_span(
            name="pass3_review_score", value=float(review.overall_score),
        )
        langfuse_context.score_current_span(
            name="pass3_consensus_issues", value=float(total_issues),
        )
        langfuse_context.score_current_span(
            name="pass3_assertion_errors", value=float(assertions.error_count),
        )

        return review, assertions

    @staticmethod
    def apply_corrections(
        recipe_data: Dict[str, Any],
        review: ReviewResult,
    ) -> Dict[str, Any]:
        """
        Apply the corrections from an adversarial review to the recipe data.

        Only applies corrections where `current_value` matches the actual value
        in the recipe (safety check to avoid stale patches).

        Handles:
        - ingredient_corrections: patch fields on matching ingredient
        - step_corrections: patch fields on matching step
        - metadata_corrections: patch metadata fields (excluding time fields)
        - missing_items: logged as warnings (not auto-added)
        - culinary_issues: logged as warnings (not auto-fixable)

        Returns:
            The mutated recipe_data dict with corrections applied.
        """
        applied = 0
        skipped = 0
        title = recipe_data.get("metadata", {}).get("title", "?")

        # ── Helper: coerce to comparable string ──────────────────────
        def _to_str(val: Any) -> str:
            if val is None:
                return ""
            return str(val).strip()

        def _coerce_value(field: str, value: str, original: Any) -> Any:
            """Coerce the suggested string value to match the original type.
            
            Handles range strings like '4-5' for numeric fields by taking
            the midpoint (4.5).
            """
            if original is None:
                return value or None
            if isinstance(original, (int, float)):
                try:
                    return type(original)(value)
                except (ValueError, TypeError):
                    # Handle range strings like "4-5" → midpoint
                    if "-" in value:
                        parts = value.split("-")
                        if len(parts) == 2:
                            try:
                                lo, hi = float(parts[0].strip()), float(parts[1].strip())
                                midpoint = (lo + hi) / 2
                                logger.info(
                                    f"[Pass 3 Apply] Range '{value}' → midpoint {midpoint}"
                                )
                                return type(original)(midpoint)
                            except (ValueError, TypeError):
                                pass
                    logger.warning(
                        f"[Pass 3 Apply] Cannot coerce '{value}' to {type(original).__name__} "
                        f"for field '{field}' — keeping original value"
                    )
                    return original
            return value

        # ── 1. Ingredient corrections ────────────────────────────────
        ingredients_by_id = {
            ing["id"]: ing for ing in recipe_data.get("ingredients", [])
        }
        for corr in review.ingredient_corrections:
            ing = ingredients_by_id.get(corr.ingredient_id)
            if not ing:
                logger.warning(
                    f"[Pass 3 Apply] Ingredient '{corr.ingredient_id}' not found — skipping"
                )
                skipped += 1
                continue

            actual = _to_str(ing.get(corr.field))
            expected = _to_str(corr.current_value)

            # Safety: verify current value matches (empty expected = new field)
            if expected and actual != expected:
                logger.warning(
                    f"[Pass 3 Apply] Ingredient '{corr.ingredient_id}'.{corr.field}: "
                    f"expected '{expected}' but found '{actual}' — skipping"
                )
                skipped += 1
                continue

            new_value = _coerce_value(corr.field, corr.suggested_value, ing.get(corr.field))
            ing[corr.field] = new_value
            applied += 1
            logger.info(
                f"[Pass 3 Apply] Ingredient '{corr.ingredient_id}'.{corr.field}: "
                f"'{actual}' → '{corr.suggested_value}' ({corr.reason})"
            )

        # ── 2. Step corrections ──────────────────────────────────────
        steps_by_id = {
            step["id"]: step for step in recipe_data.get("steps", [])
        }
        for corr in review.step_corrections:
            step = steps_by_id.get(corr.step_id)
            if not step:
                logger.warning(
                    f"[Pass 3 Apply] Step '{corr.step_id}' not found — skipping"
                )
                skipped += 1
                continue

            actual = _to_str(step.get(corr.field))
            expected = _to_str(corr.current_value)

            if expected and actual != expected:
                logger.warning(
                    f"[Pass 3 Apply] Step '{corr.step_id}'.{corr.field}: "
                    f"expected '{expected}' but found '{actual}' — skipping"
                )
                skipped += 1
                continue

            new_value = _coerce_value(corr.field, corr.suggested_value, step.get(corr.field))
            step[corr.field] = new_value
            applied += 1
            logger.info(
                f"[Pass 3 Apply] Step '{corr.step_id}'.{corr.field}: "
                f"'{actual}' → '{corr.suggested_value}' ({corr.reason})"
            )

        # ── 3. Metadata corrections (skip time fields) ───────────────
        TIME_FIELDS = {"prepTime", "cookTime", "totalTime", "prepTimeMinutes",
                       "cookTimeMinutes", "totalTimeMinutes"}
        metadata = recipe_data.get("metadata", {})
        for corr in review.metadata_corrections:
            if corr.field in TIME_FIELDS:
                logger.debug(
                    f"[Pass 3 Apply] Skipping time metadata '{corr.field}' (computed from DAG)"
                )
                continue

            actual = _to_str(metadata.get(corr.field))
            expected = _to_str(corr.current_value)

            if expected and actual != expected:
                logger.warning(
                    f"[Pass 3 Apply] Metadata '{corr.field}': "
                    f"expected '{expected}' but found '{actual}' — skipping"
                )
                skipped += 1
                continue

            new_value = _coerce_value(corr.field, corr.suggested_value, metadata.get(corr.field))
            metadata[corr.field] = new_value
            applied += 1
            logger.info(
                f"[Pass 3 Apply] Metadata '{corr.field}': "
                f"'{actual}' → '{corr.suggested_value}' ({corr.reason})"
            )

        # ── 4. Missing items (warn only) ─────────────────────────────
        for item in review.missing_items:
            logger.warning(
                f"[Pass 3 Apply] Missing {item.item_type}: {item.description} "
                f"(found in source: {item.where_in_source})"
            )

        # ── 5. Culinary issues (warn only) ───────────────────────────
        for issue in review.culinary_issues:
            logger.warning(f"[Pass 3 Apply] Culinary issue: {issue}")

        # ── Summary ──────────────────────────────────────────────────
        recipe_data["metadata"]["reviewCorrectionsApplied"] = applied
        recipe_data["metadata"]["reviewCorrectionsSkipped"] = skipped
        logger.info(
            f"[Pass 3 Apply] '{title}': {applied} corrections applied, "
            f"{skipped} skipped, {len(review.missing_items)} missing items, "
            f"{len(review.culinary_issues)} culinary warnings"
        )

        return recipe_data
