"""
Recipe Reviewer — Adversarial LLM experiment.

Takes a structured RecipeV2 JSON + the original source URL,
re-scrapes the source text, and asks a "culinary expert" LLM
to produce a structured list of corrections (like a git diff).

Usage:
    cd server && poetry run python ../experiments/test_recipe_reviewer.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

# ─── Load env ────────────────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parent.parent / "server" / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Use a DIFFERENT model than the pipeline (adversarial = different "brain")
REVIEWER_MODEL = "anthropic/claude-sonnet-4"


# ─── Pydantic models for structured review output ────────────────────

class IngredientCorrection(BaseModel):
    """A correction for a specific ingredient."""
    ingredient_id: str = Field(description="ID of the ingredient in the recipe JSON")
    field: str = Field(description="Field to correct: 'name', 'name_en', 'quantity', 'unit', 'preparation', 'category'")
    current_value: Optional[str] = Field(description="Current value in the JSON")
    suggested_value: str = Field(description="Corrected value")
    reason: str = Field(description="Brief explanation of why this is wrong")


class StepCorrection(BaseModel):
    """A correction for a specific step."""
    step_id: str = Field(description="ID of the step in the recipe JSON")
    field: str = Field(description="Field to correct: 'action', 'uses', 'produces', 'time', 'temperature'")
    current_value: Optional[str] = Field(description="Current value in the JSON")
    suggested_value: str = Field(description="Corrected value")
    reason: str = Field(description="Brief explanation")


class MissingItem(BaseModel):
    """An item present in the source but missing from the structured recipe."""
    item_type: str = Field(description="'ingredient' or 'step'")
    description: str = Field(description="What's missing, from the source text")
    where_in_source: str = Field(description="Quote from the source text")


class MetadataCorrection(BaseModel):
    """A correction for metadata fields."""
    field: str = Field(description="e.g. 'servings', 'totalTime', 'difficulty'")
    current_value: Optional[str] = None
    suggested_value: str = ""
    reason: str = ""


class ReviewResult(BaseModel):
    """Complete review output from the adversarial LLM."""
    recipe_title: str = Field(description="Title for reference")
    overall_score: int = Field(description="Quality score 1-10 (10 = perfect)")
    summary: str = Field(description="1-2 sentence overall assessment")

    ingredient_corrections: list[IngredientCorrection] = Field(default_factory=list)
    step_corrections: list[StepCorrection] = Field(default_factory=list)
    missing_items: list[MissingItem] = Field(default_factory=list)
    metadata_corrections: list[MetadataCorrection] = Field(default_factory=list)

    # Culinary sanity checks
    culinary_issues: list[str] = Field(
        default_factory=list,
        description="Issues a cook would notice: wrong temps, impossible timings, missing techniques, etc."
    )


# ─── System prompt ───────────────────────────────────────────────────

REVIEWER_SYSTEM_PROMPT = """You are an expert culinary recipe reviewer and quality auditor.

Your job is to compare a STRUCTURED RECIPE (JSON) against its ORIGINAL SOURCE TEXT and find every discrepancy, error, or missing element.

Think like a professional chef reviewing a junior cook's recipe transcription. Be thorough but fair.

## What to check

### 1. INGREDIENTS (compare source list vs JSON ingredients)
- Missing ingredients (in source but not in JSON)
- Extra ingredients (in JSON but not in source)
- Wrong quantities (e.g., source says "2 cups" but JSON has quantity=1)
- Wrong units (e.g., source says "tablespoons" but JSON has "tsp")
- Wrong names (misspelled, wrong ingredient entirely)
- Missing or wrong preparation states (e.g., source says "diced" but JSON has no preparation)

### 2. STEPS (compare source instructions vs JSON steps)
- Missing steps (source instruction not captured)
- Wrong order
- Missing temperatures or cooking times
- Wrong "uses" references (step claims to use an ingredient it doesn't)
- Missing "uses" (step should reference an ingredient but doesn't)

### 3. METADATA
- Wrong servings count
- Wrong total time
- Missing or wrong difficulty

### 4. CULINARY SANITY
- Temperatures that seem wrong (e.g., 170°F instead of 170°C)
- Cooking times that seem unreasonable
- Techniques that don't match the recipe type
- Ingredient quantities that seem off for the number of servings

## Rules
- Only flag REAL issues — not style preferences
- If the source is ambiguous, note it but don't count it as an error
- Be specific: quote the source text when pointing out discrepancies
- For each correction, explain WHY it matters

## Output
Return a JSON object matching the ReviewResult schema exactly."""


# ─── Scrape source text ──────────────────────────────────────────────

async def scrape_source_text(url: str) -> str:
    """Simple scrape of the source URL to get raw text."""
    import httpx
    from bs4 import BeautifulSoup

    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) RecipeReviewer/1.0"
        })
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove script/style/nav
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    # Get text from the main content area
    main = soup.find("main") or soup.find("article") or soup.find("div", class_="content") or soup
    text = main.get_text(separator="\n", strip=True)

    # Clean up excessive whitespace
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return "\n".join(lines)


# ─── Review a recipe ─────────────────────────────────────────────────

async def review_recipe(recipe_path: Path) -> ReviewResult:
    """Review a single recipe file against its source."""
    with open(recipe_path) as f:
        recipe_data = json.load(f)

    title = recipe_data.get("metadata", {}).get("title", "Unknown")
    source_url = recipe_data.get("metadata", {}).get("sourceUrl")

    print(f"\n{'='*70}")
    print(f"  Reviewing: {title}")
    print(f"  Source: {source_url}")
    print(f"{'='*70}")

    # Scrape source
    if not source_url:
        print("  ⚠ No sourceUrl — skipping")
        return None

    print("  Scraping source text...")
    try:
        source_text = await scrape_source_text(source_url)
        print(f"  Got {len(source_text)} chars of source text")
    except Exception as e:
        print(f"  ✗ Failed to scrape: {e}")
        return None

    # Prepare recipe JSON (compact, relevant fields only)
    recipe_summary = {
        "metadata": recipe_data.get("metadata", {}),
        "ingredients": recipe_data.get("ingredients", []),
        "steps": [
            {k: v for k, v in s.items() if k in ("id", "action", "uses", "requires", "produces", "time", "temperature", "isPassive")}
            for s in recipe_data.get("steps", [])
        ],
        "tools": recipe_data.get("tools", []),
    }

    recipe_json = json.dumps(recipe_summary, indent=2, ensure_ascii=False)

    # Call reviewer LLM
    print(f"  Asking {REVIEWER_MODEL} to review...")

    client = AsyncOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )

    # Build the exact schema example for the LLM
    schema_example = ReviewResult(
        recipe_title="Example",
        overall_score=7,
        summary="Good overall but 3 issues found.",
        ingredient_corrections=[
            IngredientCorrection(
                ingredient_id="olive_oil",
                field="quantity",
                current_value="1.0",
                suggested_value="2.0",
                reason="Source says '2 tablespoons olive oil'"
            )
        ],
        step_corrections=[],
        missing_items=[
            MissingItem(
                item_type="ingredient",
                description="Fresh parsley for garnish",
                where_in_source="Garnish with fresh parsley"
            )
        ],
        metadata_corrections=[],
        culinary_issues=["170°F seems too low for grilling — likely should be 170°C"],
    ).model_dump()

    user_prompt = f"""## ORIGINAL SOURCE TEXT (scraped from {source_url})

{source_text[:6000]}

---

## STRUCTURED RECIPE (JSON)

{recipe_json}

---

Review this structured recipe against the source text. Find all discrepancies.

You MUST return a JSON object with EXACTLY this structure (example):

{json.dumps(schema_example, indent=2)}

Required fields: recipe_title, overall_score (1-10), summary, ingredient_corrections, step_corrections, missing_items, metadata_corrections, culinary_issues.

Return ONLY the JSON object, no markdown fences."""

    response = await client.chat.completions.create(
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
        # Remove opening fence (```json or ```)
        first_newline = raw.index("\n")
        raw = raw[first_newline + 1:]
        # Remove closing fence
        if raw.rstrip().endswith("```"):
            raw = raw.rstrip()[:-3].rstrip()

    try:
        review_data = json.loads(raw)
        review = ReviewResult(**review_data)
    except Exception as e:
        print(f"  ✗ Failed to parse review: {e}")
        print(f"  Raw (first 800 chars): {raw[:800]}")
        return None

    return review


# ─── Pretty print results ────────────────────────────────────────────

def print_review(review: ReviewResult):
    """Pretty-print a review result."""
    score_bar = "█" * review.overall_score + "░" * (10 - review.overall_score)
    print(f"\n  Score: [{score_bar}] {review.overall_score}/10")
    print(f"  {review.summary}")

    if review.ingredient_corrections:
        print(f"\n  🔧 INGREDIENT CORRECTIONS ({len(review.ingredient_corrections)}):")
        for c in review.ingredient_corrections:
            print(f"    • [{c.ingredient_id}].{c.field}: \"{c.current_value}\" → \"{c.suggested_value}\"")
            print(f"      Reason: {c.reason}")

    if review.step_corrections:
        print(f"\n  🔧 STEP CORRECTIONS ({len(review.step_corrections)}):")
        for c in review.step_corrections:
            print(f"    • [{c.step_id}].{c.field}: \"{c.current_value}\" → \"{c.suggested_value}\"")
            print(f"      Reason: {c.reason}")

    if review.missing_items:
        print(f"\n  ❌ MISSING ITEMS ({len(review.missing_items)}):")
        for m in review.missing_items:
            print(f"    • [{m.item_type}] {m.description}")
            print(f"      Source: \"{m.where_in_source}\"")

    if review.metadata_corrections:
        print(f"\n  📝 METADATA CORRECTIONS ({len(review.metadata_corrections)}):")
        for c in review.metadata_corrections:
            print(f"    • {c.field}: \"{c.current_value}\" → \"{c.suggested_value}\" — {c.reason}")

    if review.culinary_issues:
        print(f"\n  👨‍🍳 CULINARY ISSUES ({len(review.culinary_issues)}):")
        for issue in review.culinary_issues:
            print(f"    • {issue}")

    total_issues = (
        len(review.ingredient_corrections)
        + len(review.step_corrections)
        + len(review.missing_items)
        + len(review.metadata_corrections)
        + len(review.culinary_issues)
    )
    print(f"\n  Total issues found: {total_issues}")


# ─── Main ─────────────────────────────────────────────────────────────

async def main():
    recipes_dir = Path(__file__).resolve().parent.parent / "server" / "data" / "recipes"
    recipe_files = sorted(recipes_dir.glob("*.recipe.json"))

    if not recipe_files:
        print("No recipe files found!")
        return

    print(f"Found {len(recipe_files)} recipes to review\n")

    all_reviews = []
    for recipe_path in recipe_files:
        review = await review_recipe(recipe_path)
        if review:
            print_review(review)
            all_reviews.append(review)

    # Summary
    if all_reviews:
        print(f"\n{'='*70}")
        print(f"  SUMMARY: {len(all_reviews)} recipes reviewed")
        print(f"{'='*70}")
        avg_score = sum(r.overall_score for r in all_reviews) / len(all_reviews)
        total_corrections = sum(
            len(r.ingredient_corrections) + len(r.step_corrections)
            + len(r.missing_items) + len(r.metadata_corrections)
            + len(r.culinary_issues)
            for r in all_reviews
        )
        print(f"  Average score: {avg_score:.1f}/10")
        print(f"  Total issues: {total_corrections}")
        print(f"  Issues per recipe: {total_corrections / len(all_reviews):.1f}")

        # Save raw results
        output_path = Path(__file__).resolve().parent / "review_results.json"
        with open(output_path, "w") as f:
            json.dump(
                [r.model_dump() for r in all_reviews],
                f, indent=2, ensure_ascii=False,
            )
        print(f"\n  Raw results saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
