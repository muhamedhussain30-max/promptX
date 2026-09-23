"""
Scoring Engine
==============
Anti-gaming formula (spec §5):

  final = 0.60 * match  +  (match/100) * (0.15*creativity_100 + 0.15*speed_100 + 0.10*efficiency_100)
  if match < 20: final is capped at 20

Where:
  match         = image match score  0-100  (50% concept coverage + 50% avg of 3 vision sub-scores)
  creativity_100 = creativity        0-100
  speed_100      = speed             0-100
  efficiency_100 = efficiency        0-100

Compliance (forbidden-word check) is a hard gate: if prompt had forbidden words the
submission was rejected before reaching scoring, but we keep it as a 20-pt indicator
to show in the breakdown (always 20 here — 0 means the submission should never have
arrived, so we give it a small base floor).

Stored in the existing Score columns:
  accuracy   ← match_score  (0-50, match/2)
  compliance ← 20 always (prompt already server-validated)
  creativity ← creativity_100 / 10  (0-10, for display)
  speed      ← speed_100 / 10       (0-10)
  efficiency ← efficiency_100 / 10  (0-10)
  total      ← final (0-100)        ← this is the ACTUAL ranking score

  accuracy_breakdown ← full rubric dict including new sub-scores
"""
import re
import math
from typing import Optional

from app.models.submission import Submission
from app.models.challenge import Challenge
from app.services.evaluation.factory import get_image_evaluation_provider
from app.config.logging import logger


# ─────────────────────────────────────────────────────────────────────────────
# Speed  (0-100, continuous exponential decay)
# ─────────────────────────────────────────────────────────────────────────────

def _speed_score_100(submission_time_ms: Optional[int], round_duration: int) -> int:
    """
    Smooth speed score 0-100 using exponential decay over round duration.
    Fully proportional to any duration — 30s, 60s, 600s, 3600s all scale correctly.

        score = 100 * e^(-4 * pct)   where pct = elapsed / duration

    pct=0%   → 100
    pct=5%   → 82
    pct=10%  → 67
    pct=20%  → 45
    pct=35%  → 25
    pct=50%  → 14
    pct=75%  → 5
    pct=100% → 2  (just squeezed in before deadline)
    >100%    → 0  (too late)
    """
    if submission_time_ms is None:
        return 0
    seconds = submission_time_ms / 1000.0
    if seconds > round_duration:
        return 0
    pct = max(0.0, min(1.0, seconds / max(round_duration, 1)))
    raw = 100.0 * math.exp(-4.0 * pct)
    return max(0, min(100, round(raw)))


# ─────────────────────────────────────────────────────────────────────────────
# Creativity  (0-100 heuristic)
# ─────────────────────────────────────────────────────────────────────────────

def _creativity_score_100(raw_prompt: str, forbidden_words: list[str], target_description: str) -> int:
    """
    Measures how *indirectly* the prompt describes the target.

    Rewards:
    - Avoiding all "obvious" non-forbidden target words (near-synonym substitution penalised)
    - Vocabulary richness (varied, descriptive language)
    - Adequate descriptive length (saturates at 20 words)

    Penalises:
    - Directly copying non-forbidden target words (lazy near-paraphrase)
    - Very repetitive prompts
    - Very short prompts (< 5 words)
    """
    if not raw_prompt.strip():
        return 0

    stop_words = {
        "a", "an", "the", "at", "in", "on", "of", "and", "or", "is",
        "with", "for", "to", "from", "by", "its", "it", "as", "are",
        "was", "has", "have", "had", "but", "their", "while", "that", "this",
    }

    prompt_lower = raw_prompt.lower()
    target_words = set(re.findall(r"[a-z]+", target_description.lower()))
    forbidden_lower = {fw.lower() for fw in forbidden_words}

    # "Obvious" = non-forbidden, non-stop words from the target
    target_meaningful = target_words - forbidden_lower - stop_words

    prompt_words = set(re.findall(r"[a-z]+", prompt_lower))

    # Indirectness: fraction of obvious target words the prompt avoids
    avoidance = (
        1.0 - len(prompt_words & target_meaningful) / max(len(target_meaningful), 1)
        if target_meaningful else 1.0
    )

    # Vocabulary richness
    all_words = re.findall(r"[a-z]+", prompt_lower)
    richness = len(set(all_words)) / max(len(all_words), 1)

    # Descriptiveness (saturates at 20 words)
    descriptiveness = min(1.0, len(all_words) / 20.0)

    raw = (avoidance * 0.50 + richness * 0.30 + descriptiveness * 0.20) * 100
    return max(0, min(100, round(raw)))


# ─────────────────────────────────────────────────────────────────────────────
# Efficiency  (0-100 heuristic)
# ─────────────────────────────────────────────────────────────────────────────

def _efficiency_score_100(raw_prompt: str) -> int:
    """
    Rewards the ideal word-count band (15-40 words) and low repetition.
    Very short or padded prompts score lower.
    """
    words = re.findall(r"[a-z]+", raw_prompt.lower())
    word_count = len(words)
    if word_count == 0:
        return 0

    # Bell-curve length score: peak at 15-40 words
    if word_count < 5:
        length_score = 0.10
    elif word_count < 10:
        length_score = 0.45
    elif word_count < 15:
        length_score = 0.80
    elif word_count <= 40:
        length_score = 1.00
    elif word_count <= 60:
        length_score = 0.80
    elif word_count <= 100:
        length_score = 0.55
    else:
        length_score = 0.30

    unique_ratio = len(set(words)) / word_count
    repetition_score = min(1.0, unique_ratio * 1.1)

    raw = (length_score * 0.55 + repetition_score * 0.45) * 100
    return max(0, min(100, round(raw)))


# ─────────────────────────────────────────────────────────────────────────────
# Anti-gaming final formula
# ─────────────────────────────────────────────────────────────────────────────

def _final_score(match: int, creativity: int, speed: int, efficiency: int) -> int:
    """
    Anti-gaming formula (spec §5):

        final = 0.60*match + (match/100) * (0.15*creativity + 0.15*speed + 0.10*efficiency)

    - Speed, creativity, efficiency only contribute IN PROPORTION to accuracy.
    - A fast but wrong image can never score high.
    - If match < 20, final is capped at 20.
    """
    bonus_weight = match / 100.0
    bonus = bonus_weight * (0.15 * creativity + 0.15 * speed + 0.10 * efficiency)
    raw = 0.60 * match + bonus
    final = max(0, min(100, round(raw)))
    if match < 20:
        final = min(final, 20)
    return final


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

async def score_submission(
    submission: Submission,
    challenge: Challenge,
    round_duration: int,
) -> dict:
    """
    Compute all scoring components and return a breakdown dict.

    Return dict keys (backward-compatible with scoring_worker.py):
      accuracy       — match_score / 2  (0-50, for Score.accuracy column)
      compliance     — 20 (always — prompt already server-validated)
      creativity     — creativity_100 / 10  (0-10, for display)
      speed          — speed_100 / 10        (0-10)
      efficiency     — efficiency_100 / 10   (0-10)
      total          — final_score (0-100)   ← the actual anti-gaming score
      accuracy_breakdown — full rubric dict including new sub-scores

    New keys (for the enhanced ResultsPage):
      match_score       — 0-100
      subject_score     — 0-100
      scene_score       — 0-100
      composition_score — 0-100
      concept_coverage  — 0-100
      creativity_100    — 0-100
      speed_100         — 0-100
      efficiency_100    — 0-100
    """
    # ── 1. Image match via evaluator ──────────────────────────────────────────
    match_score = 0
    subject_score = 0
    scene_score = 0
    composition_score = 0
    concept_coverage = 0
    accuracy_breakdown: dict = {}

    if submission.image_url and submission.generation_completed:
        evaluator = get_image_evaluation_provider()
        try:
            eval_result = await evaluator.evaluate(
                image_url=submission.image_url,
                target_description=challenge.target_description,
                required_objects=challenge.required_objects,
                required_attributes=challenge.required_attributes,
                required_scene=challenge.required_scene,
                required_relationships=challenge.required_relationships,
                player_prompt=submission.raw_prompt,
            )
            match_score       = eval_result.match_score
            subject_score     = eval_result.subject_score
            scene_score       = eval_result.scene_score
            composition_score = eval_result.composition_score
            concept_coverage  = eval_result.concept_coverage
            accuracy_breakdown = eval_result.accuracy_breakdown_dict()
        except Exception as e:
            logger.error("evaluation_error", submission_id=submission.id, error=str(e))

    # ── 2. Speed (0-100) ──────────────────────────────────────────────────────
    speed_100 = _speed_score_100(submission.submission_time_ms, round_duration)

    # ── 3. Creativity (0-100) ─────────────────────────────────────────────────
    creativity_100 = _creativity_score_100(
        submission.raw_prompt,
        challenge.forbidden_words,
        challenge.target_description,
    )

    # ── 4. Efficiency (0-100) ─────────────────────────────────────────────────
    efficiency_100 = _efficiency_score_100(submission.raw_prompt)

    # ── 5. Anti-gaming final score (0-100) ────────────────────────────────────
    final = _final_score(match_score, creativity_100, speed_100, efficiency_100)

    logger.info(
        "score_computed",
        submission_id=submission.id,
        match=match_score,
        creativity=creativity_100,
        speed=speed_100,
        efficiency=efficiency_100,
        final=final,
    )

    return {
        # Backward-compat keys used by scoring_worker.py → Score model columns
        "accuracy":   match_score // 2,   # 0-50  (match scaled to old column range)
        "compliance": 20,                 # always 20 — server already validated
        "creativity": creativity_100 // 10,
        "speed":      speed_100 // 10,
        "efficiency": efficiency_100 // 10,
        "total":      final,              # 0-100, the anti-gaming final score

        # Full rubric (stored in accuracy_breakdown JSON)
        "accuracy_breakdown": {
            **accuracy_breakdown,
            "match_score":       match_score,
            "subject_score":     subject_score,
            "scene_score":       scene_score,
            "composition_score": composition_score,
            "concept_coverage":  concept_coverage,
            "creativity_100":    creativity_100,
            "speed_100":         speed_100,
            "efficiency_100":    efficiency_100,
            "final_score":       final,
        },

        # Convenience flat keys for the WebSocket score event
        "match_score":       match_score,
        "subject_score":     subject_score,
        "scene_score":       scene_score,
        "composition_score": composition_score,
        "concept_coverage":  concept_coverage,
        "creativity_100":    creativity_100,
        "speed_100":         speed_100,
        "efficiency_100":    efficiency_100,
    }
