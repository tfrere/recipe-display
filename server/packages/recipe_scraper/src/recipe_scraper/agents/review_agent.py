"""
Review Agent — Standalone recipe quality auditor.

Sends the original source text and structured JSON to an LLM and gets
a detailed scorecard rating fidelity across 5 axes (total /100).

This agent is read-only: it NEVER modifies recipe files.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from recipe_scraper.observability import get_async_openai_class

from .models import AxisScore, ReviewScorecard, ReviewReport

AsyncOpenAI = get_async_openai_class()

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
REVIEWER_MODEL = "google/gemini-2.5-flash"

# ── System prompt ────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert culinary recipe auditor. Your job is to SCORE how faithfully
a structured recipe JSON represents its original source text.

You must evaluate 5 axes and assign points for each. Be precise and fair.

## Barème

### 1. Ingredient Completeness (/30)
- 30/30: Every source ingredient is in the JSON, no phantom ingredients
- 20-29: 1-2 minor omissions (garnish, optional ingredient)
- 10-19: Missing a key ingredient or has phantom ingredients
- 0-9:   Multiple key ingredients missing

### 2. Quantity & Unit Accuracy (/25)
- 25/25: All quantities and units exactly match the source
- 18-24: 1-2 minor discrepancies (rounding, equivalent units)
- 10-17: Several wrong quantities or units
- 0-9:   Systematic quantity errors
Note: French-to-English unit TRANSLATION (cuillère → tbsp) is CORRECT BY DESIGN — do NOT penalize it.

### 3. Step Completeness (/25)
- 25/25: All source steps present, correct order, durations & temperatures captured
- 18-24: 1-2 minor steps missing or merged (still cookable)
- 10-17: Missing important steps or wrong order
- 0-9:   Major steps missing, recipe not reproducible

### 4. DAG Semantic Coherence (/10)
- 10/10: Every uses/produces relationship makes culinary sense
- 7-9:   Minor oddities (ingredient used in unexpected step)
- 4-6:   Some relationships don't make culinary sense
- 0-3:   DAG is semantically broken

### 5. Metadata Quality (/10)
- 10/10: Title, servings, difficulty, recipe type all correct
- 7-9:   1 minor metadata error
- 4-6:   Multiple metadata errors
- 0-3:   Metadata is mostly wrong
Note: DO NOT evaluate time metadata (totalTime, prepTime, etc.) — these are computed from the DAG, not from the source.

## Rules

- Be SPECIFIC: quote the source text when pointing out issues
- List each issue found in the "issues" array of the relevant axis
- The "details" field should explain your reasoning for the score
- If the source text is ambiguous, give benefit of the doubt
- Return ONLY a JSON object matching the schema below, no markdown fences

## Output Schema

{schema_example}
"""

# ── Schema example for the prompt ────────────────────────────────────

_SCHEMA_EXAMPLE = ReviewScorecard(
    recipe_title="Example Recipe",
    ingredient_completeness=AxisScore(
        axis="ingredient_completeness",
        score=28,
        max_score=30,
        details="All ingredients present. Minor: garnish parsley not listed.",
        issues=["Optional garnish parsley mentioned in step 5 but not in ingredients"],
    ),
    quantity_accuracy=AxisScore(
        axis="quantity_accuracy",
        score=25,
        max_score=25,
        details="All quantities match perfectly.",
        issues=[],
    ),
    step_completeness=AxisScore(
        axis="step_completeness",
        score=22,
        max_score=25,
        details="All steps present. Resting time not captured as a separate step.",
        issues=["Source says 'let rest 10min' between steps 3 and 4, not captured"],
    ),
    dag_semantic_coherence=AxisScore(
        axis="dag_semantic_coherence",
        score=10,
        max_score=10,
        details="DAG relationships are logical and culinary-sound.",
        issues=[],
    ),
    metadata_quality=AxisScore(
        axis="metadata_quality",
        score=9,
        max_score=10,
        details="All correct except difficulty could be 'easy' instead of 'medium'.",
        issues=["Source suggests easy recipe but difficulty is 'medium'"],
    ),
    summary="Faithful transcription with minor omissions. Score: 94/100.",
).model_dump()


# ── Agent ────────────────────────────────────────────────────────────


class ReviewAgent:
    """Standalone recipe quality auditor.

    Sends originalText + structured JSON to an LLM and returns a ReviewScorecard.
    Read-only: never modifies recipe files.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or REVIEWER_MODEL
        if not self.api_key:
            logger.warning("No OPENROUTER_API_KEY — review agent will be disabled")
            self._client = None
        else:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=OPENROUTER_BASE_URL,
            )

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def review(self, recipe_data: Dict[str, Any]) -> ReviewReport:
        """Review a single recipe and return a ReviewReport.

        Args:
            recipe_data: Full recipe dict (must contain 'originalText' and 'metadata').

        Returns:
            ReviewReport with scorecard or error.
        """
        metadata = recipe_data.get("metadata", {})
        slug = metadata.get("slug", "unknown")
        title = metadata.get("title", "Untitled")

        if not self.is_available:
            return ReviewReport(
                slug=slug, title=title,
                error="Review agent disabled (no OPENROUTER_API_KEY)",
            )

        original_text = recipe_data.get("originalText", "")
        if not original_text:
            return ReviewReport(
                slug=slug, title=title,
                error="No originalText in recipe — cannot review fidelity",
            )

        logger.info(f"[ReviewAgent] Reviewing: {title}")

        # Build compact recipe JSON (relevant fields only)
        recipe_summary = {
            "metadata": {
                k: v for k, v in metadata.items()
                if k in (
                    "title", "description", "servings", "difficulty",
                    "recipeType", "nationality", "notes",
                )
            },
            "ingredients": recipe_data.get("ingredients", []),
            "steps": [
                {k: v for k, v in s.items() if k in (
                    "id", "action", "uses", "requires", "produces",
                    "duration", "temperature", "isPassive", "stepType",
                    "visualCue", "subRecipe",
                )}
                for s in recipe_data.get("steps", [])
            ],
            "tools": recipe_data.get("tools", []),
            "finalState": recipe_data.get("finalState", ""),
        }
        recipe_json = json.dumps(recipe_summary, indent=2, ensure_ascii=False)

        source_text_truncated = original_text[:8000]

        system_prompt = SYSTEM_PROMPT.replace(
            "{schema_example}",
            json.dumps(_SCHEMA_EXAMPLE, indent=2),
        )

        user_prompt = f"""## ORIGINAL SOURCE TEXT

{source_text_truncated}

---

## STRUCTURED RECIPE (JSON)

{recipe_json}

---

Score this structured recipe against the source text using the barème above.
Return ONLY a JSON object matching the ReviewScorecard schema."""

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
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
            scorecard = ReviewScorecard(**review_data)

            logger.info(
                f"[ReviewAgent] {title}: {scorecard.total_score}/{scorecard.total_max} "
                f"({scorecard.score_10}/10)"
            )

            return ReviewReport(slug=slug, title=title, scorecard=scorecard)

        except Exception as e:
            logger.error(f"[ReviewAgent] Failed for '{title}': {e}")
            return ReviewReport(slug=slug, title=title, error=str(e))
