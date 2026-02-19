"""Pydantic models for agent reports."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Review Agent Models ──────────────────────────────────────────────


class AxisScore(BaseModel):
    """Score for a single evaluation axis."""

    axis: str = Field(description="Name of the evaluation axis")
    score: float = Field(ge=0, description="Points awarded")
    max_score: float = Field(gt=0, description="Maximum possible points")
    details: str = Field(default="", description="Explanation for the score")
    issues: List[str] = Field(
        default_factory=list,
        description="Specific issues found on this axis",
    )


class ReviewScorecard(BaseModel):
    """Structured scorecard returned by the LLM reviewer.

    Barème:
        - ingredient_completeness: /30
        - quantity_accuracy:       /25
        - step_completeness:       /25
        - dag_semantic_coherence:  /10
        - metadata_quality:        /10
        Total:                     /100
    """

    recipe_title: str = Field(description="Title for reference")

    ingredient_completeness: AxisScore = Field(
        description="All source ingredients present, no phantoms (max 30)"
    )
    quantity_accuracy: AxisScore = Field(
        description="Quantities and units match the source text (max 25)"
    )
    step_completeness: AxisScore = Field(
        description="All source steps present, correct order, durations and temperatures captured (max 25)"
    )
    dag_semantic_coherence: AxisScore = Field(
        description="uses/produces make culinary sense (max 10)"
    )
    metadata_quality: AxisScore = Field(
        description="Title, servings, difficulty, recipe type are correct (max 10)"
    )

    summary: str = Field(description="1-3 sentence overall assessment")

    @property
    def total_score(self) -> float:
        """Sum of all axis scores."""
        return (
            self.ingredient_completeness.score
            + self.quantity_accuracy.score
            + self.step_completeness.score
            + self.dag_semantic_coherence.score
            + self.metadata_quality.score
        )

    @property
    def total_max(self) -> float:
        """Sum of all max scores (should be 100)."""
        return (
            self.ingredient_completeness.max_score
            + self.quantity_accuracy.max_score
            + self.step_completeness.max_score
            + self.dag_semantic_coherence.max_score
            + self.metadata_quality.max_score
        )

    @property
    def score_10(self) -> float:
        """Score converted to a /10 scale."""
        if self.total_max == 0:
            return 0
        return round(self.total_score / self.total_max * 10, 1)


class ReviewReport(BaseModel):
    """Full report for a single recipe review."""

    slug: str
    title: str
    scorecard: Optional[ReviewScorecard] = None
    error: Optional[str] = None

    @property
    def score_10(self) -> Optional[float]:
        if self.scorecard:
            return self.scorecard.score_10
        return None


# ── Nutrition Agent Models ───────────────────────────────────────────


class IngredientNutritionDetail(BaseModel):
    """Per-ingredient nutrition comparison."""

    name_en: str
    matched_in_ref: bool = False
    our_kcal_100g: Optional[float] = None
    ref_kcal_100g: Optional[float] = None
    deviation_pct: Optional[float] = None


class NutritionComparison(BaseModel):
    """Macro comparison between computed and reference values."""

    calories: float = 0
    protein: float = 0
    fat: float = 0
    carbs: float = 0
    fiber: float = 0


class NutritionIssue(BaseModel):
    """A flagged nutrition issue."""

    severity: str = Field(description="'warning' or 'error'")
    field: str = Field(description="e.g. 'calories', 'protein'")
    detail: str = ""


class NutritionReport(BaseModel):
    """Full report for a single recipe nutrition validation."""

    slug: str
    title: str
    computed: Optional[NutritionComparison] = None
    reference: Optional[NutritionComparison] = None
    deviation_pct: Optional[NutritionComparison] = None
    issues: List[NutritionIssue] = Field(default_factory=list)
    ingredient_details: List[IngredientNutritionDetail] = Field(default_factory=list)
    verdict: str = Field(default="unknown", description="'pass', 'warning', 'fail', 'unknown'")
    error: Optional[str] = None
