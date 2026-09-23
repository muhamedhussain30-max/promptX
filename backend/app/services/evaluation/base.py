"""
Abstract base class for image-evaluation providers.

EvaluationResult now carries a full rubric breakdown:
  - per_concept_results: list of {concept, label, result: "yes"|"partial"|"no"}
  - subject_score:      0-100  (right subject + action present)
  - scene_score:        0-100  (correct environment/setting)
  - composition_score:  0-100  (overall visual likeness to the target)
  - concept_coverage:   0-100  (% of required concepts present/partial)
  - match_score:        0-100  (50% concept_coverage + 50% avg of three sub-scores)
  - accuracy_total:     0-50   (match_score scaled to the 50-pt component)

These are HIDDEN from players. Players only see the public breakdown dict.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Literal


# kept for backward-compat with scoring_worker / leaderboard code
@dataclass
class ObjectScore:
    name: str
    present: bool
    confidence: float       # 0.0–1.0
    max_points: int
    awarded_points: int


@dataclass
class ConceptResult:
    """Per-concept rubric result — never sent to the frontend."""
    concept: str            # hidden internal concept text
    label: str              # player-visible label e.g. "Subject", "Environment"
    result: Literal["yes", "partial", "no"]

    @property
    def score(self) -> float:
        return {"yes": 1.0, "partial": 0.5, "no": 0.0}[self.result]


@dataclass
class EvaluationResult:
    # ── Backward-compat fields (kept for existing code) ───────────────────────
    object_scores: list[ObjectScore] = field(default_factory=list)
    object_accuracy: float = 0.0
    attribute_accuracy: float = 0.0
    scene_accuracy: float = 0.0
    relationship_accuracy: float = 0.0

    # ── New rubric fields ─────────────────────────────────────────────────────
    per_concept_results: list[ConceptResult] = field(default_factory=list)
    subject_score: int = 0       # 0-100
    scene_score: int = 0         # 0-100
    composition_score: int = 0   # 0-100
    concept_coverage: int = 0    # 0-100  (% concepts matched)
    match_score: int = 0         # 0-100  primary accuracy metric

    # Rolled up to the 50-pt component (match_score / 2)
    accuracy_total: int = 0      # 0-50

    # Provider metadata (never forwarded to players)
    provider: str = "unknown"
    model: Optional[str] = None
    raw_response: Optional[dict] = None
    error_message: Optional[str] = None

    def accuracy_breakdown_dict(self) -> dict:
        """
        Player-visible breakdown — concept text is hidden, only labels are shown.
        """
        return {
            # Rubric sub-scores (0-100 each, shown as bars)
            "subject_score":     self.subject_score,
            "scene_score":       self.scene_score,
            "composition_score": self.composition_score,
            "concept_coverage":  self.concept_coverage,
            "match_score":       self.match_score,
            # Per-concept results: label + result only, concept text hidden
            "concepts": [
                {
                    "label":  cr.label,
                    "result": cr.result,   # "yes" | "partial" | "no"
                }
                for cr in self.per_concept_results
            ],
            # Legacy fields kept for leaderboard / old frontend code
            "object_accuracy":       round(self.object_accuracy, 3),
            "attribute_accuracy":    round(self.attribute_accuracy, 3),
            "scene_accuracy":        round(self.scene_accuracy, 3),
            "relationship_accuracy": round(self.relationship_accuracy, 3),
            "total": self.accuracy_total,
        }


class ImageEvaluationProvider(ABC):

    @abstractmethod
    async def evaluate(
        self,
        image_url: str,
        target_description: str,
        required_objects: list[str],
        required_attributes: list[str],
        required_scene: list[str],
        required_relationships: list[str],
        player_prompt: str = "",
    ) -> EvaluationResult:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...
