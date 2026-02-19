"""
Recipe Reviewer — Pass 3: Adversarial LLM verification.

Compares the structured Recipe JSON against the original source text
to detect discrepancies, missing items, and culinary issues.

The reviewer uses a DIFFERENT model than the structurer (adversarial principle)
and outputs a structured ReviewResult with corrections.

Note: time-related metadata corrections are IGNORED — times are now computed
deterministically from the step DAG at enrichment.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from recipe_scraper.observability import observe, get_async_openai_class

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


# ── Reviewer configuration ──────────────────────────────────────────

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Use a DIFFERENT model than the pipeline (adversarial = different "brain")
# Gemini Flash: fast, cheap ($0.30/$2.50 per 1M), excellent reasoning
REVIEWER_MODEL = "google/gemini-2.5-flash"


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
- Wrong servings count
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


class RecipeReviewer:
    """
    Adversarial reviewer that compares structured recipes against source text.
    
    Uses a different LLM model than the recipe structurer to provide
    independent verification (adversarial principle).
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

    @observe(name="pass3_review")
    async def review(
        self,
        recipe_data: Dict[str, Any],
        source_text: str,
        source_url: Optional[str] = None,
    ) -> Optional[ReviewResult]:
        """
        Review a structured recipe against its original source text.

        Args:
            recipe_data: The structured recipe dict
            source_text: Original text of the recipe (from scraping)
            source_url: URL of the source (for context in the prompt)

        Returns:
            ReviewResult with corrections, or None if review fails
        """
        if not self.is_available:
            logger.warning("Reviewer not available (no API key)")
            return None

        title = recipe_data.get("metadata", {}).get("title", "Unknown")
        logger.info(f"[Pass 3] Reviewing recipe: {title}")

        # Build compact recipe JSON for the reviewer (relevant fields only)
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

        # Truncate source text to stay within context window.
        # Gemini 2.5 Flash has a 1M token context; 24K chars ≈ 6-8K tokens,
        # leaving plenty of room for the recipe JSON + system prompt.
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

        try:
            response = await self._client.chat.completions.create(
                model=REVIEWER_MODEL,
                messages=[
                    {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4096,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content

            # Strip markdown code fences if present
            if raw.strip().startswith("```"):
                raw = raw.strip()
                first_newline = raw.index("\n")
                raw = raw[first_newline + 1:]
                if raw.rstrip().endswith("```"):
                    raw = raw.rstrip()[:-3].rstrip()

            review_data = json.loads(raw)
            review = ReviewResult(**review_data)

            total_issues = (
                len(review.ingredient_corrections)
                + len(review.step_corrections)
                + len(review.missing_items)
                + len(review.metadata_corrections)
                + len(review.culinary_issues)
            )

            logger.info(
                f"[Pass 3] Review complete for '{title}': "
                f"score={review.overall_score}/10, issues={total_issues}"
            )

            return review

        except Exception as e:
            logger.error(f"[Pass 3] Review failed for '{title}': {e}")
            return None

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
                        f"for field '{field}' — keeping as string"
                    )
                    return value
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
