from typing import Optional
from pydantic import BaseModel


class ConceptResultOut(BaseModel):
    """Player-visible per-concept result. The 'concept' text is hidden; only label shown."""
    label: str                         # "Subject" | "Detail" | "Environment" | "Action"
    result: str                        # "yes" | "partial" | "no"


class AccuracyBreakdownOut(BaseModel):
    """Player-visible rubric breakdown embedded in ScoreBreakdown."""
    match_score:       int             # 0-100 primary image-match score
    subject_score:     int             # 0-100
    scene_score:       int             # 0-100
    composition_score: int             # 0-100
    concept_coverage:  int             # 0-100 fraction of concepts matched
    concepts:          list[ConceptResultOut] = []

    model_config = {"from_attributes": True}


class ScoreBreakdown(BaseModel):
    # ── Anti-gaming final score (0-100) — the actual ranking value ────────────
    total:          int                # final anti-gaming score 0-100

    # ── Component scores shown in the breakdown UI ────────────────────────────
    match_score:       int = 0        # 0-100  image match (renamed from accuracy*2)
    creativity_100:    int = 0        # 0-100
    speed_100:         int = 0        # 0-100
    efficiency_100:    int = 0        # 0-100

    # ── Legacy 0-10 columns (kept for leaderboard sort) ──────────────────────
    accuracy:    int = 0              # match_score//2  (0-50, for DB column compat)
    compliance:  int = 20             # always 20
    creativity:  int = 0              # creativity_100//10  (0-10)
    speed:       int = 0              # speed_100//10       (0-10)
    efficiency:  int = 0              # efficiency_100//10  (0-10)

    # ── Rubric detail ─────────────────────────────────────────────────────────
    accuracy_breakdown: Optional[dict] = None   # full dict including concepts list
    image_url:          Optional[str] = None    # the generated image to display
    raw_prompt:         Optional[str] = None    # prompt used

    # One-line explanation shown to the player
    explanation: Optional[str] = None

    model_config = {"from_attributes": True}

    @property
    def explanation_text(self) -> str:
        """Generate a one-line result explanation."""
        m = self.match_score
        if m >= 80:
            base = "Excellent image match!"
        elif m >= 60:
            base = "Good image match."
        elif m >= 40:
            base = "Partial match — some elements missing."
        elif m >= 20:
            base = "Weak match — key elements not visible."
        else:
            base = "Image didn't match the target."

        if self.total < 20 and m < 20:
            return f"{base} Score capped at 20 (match too low)."
        return base


class LeaderboardEntryOut(BaseModel):
    rank: int
    player_id: str
    display_name: str
    round_score: int
    cumulative_score: int
    is_advanced: Optional[bool]
    accuracy: int
    speed: int

    model_config = {"from_attributes": True}


class LeaderboardOut(BaseModel):
    game_id: str
    round_number: int
    entries: list[LeaderboardEntryOut]
