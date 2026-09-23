"""
MockImageEvaluationProvider
============================
Evaluates the player's PROMPT semantically against the challenge criteria.
This is the correct proxy in mock mode: a good prompt produces a good image,
so semantic coverage of the prompt is the best available signal.

Scoring:
  concept_coverage  — what fraction of required concepts are described (0-100)
  subject_score     — how well the main subject + action is covered (0-100)
  scene_score       — how well the environment/setting is covered (0-100)
  composition_score — an estimate of overall coherence (0-100)
  match_score       — 50% concept_coverage + 50% avg(subject, scene, composition) (0-100)
  accuracy_total    — match_score // 2  (0-50, backward-compat column)

Scores are deterministic per (prompt, challenge) pair — same inputs, same output.
Small jitter makes leaderboards feel natural without being random.
"""
import re
import math
import hashlib
import asyncio
from typing import Optional

from app.services.evaluation.base import (
    ImageEvaluationProvider, EvaluationResult, ObjectScore, ConceptResult
)
from app.config.settings import settings
from app.config.logging import logger


# ── Synonym map ───────────────────────────────────────────────────────────────
_SYNONYMS: dict[str, list[str]] = {
    "bear":           ["grizzly", "brown animal", "woodland creature", "large mammal",
                       "furry beast", "wild animal", "forest animal", "mammal"],
    "cat":            ["feline", "kitten", "kitty", "tabby", "furry animal"],
    "dog":            ["canine", "hound", "puppy", "pup", "pooch"],
    "elephant":       ["pachyderm", "tusked animal", "large grey animal",
                       "tusks", "proboscis", "trunk"],
    "lion":           ["feline", "mane", "big cat", "predator", "pride"],
    "fox":            ["canine", "cunning animal", "red animal", "bushy tail",
                       "orange animal", "woodland animal", "red fur"],
    "penguin":        ["flightless bird", "black white bird", "arctic bird", "tuxedo bird"],
    "monkey":         ["primate", "ape", "simian"],
    "dragon":         ["beast", "winged beast", "reptile", "mythical creature", "scaled creature"],
    "mermaid":        ["sea creature", "half fish", "underwater being", "aquatic figure"],
    "astronaut":      ["space suit", "cosmonaut", "spacesuit", "space traveller", "suited figure"],
    "samurai":        ["warrior", "armoured fighter", "japanese fighter", "sword wielder", "katana"],
    "viking":         ["norse warrior", "norseman", "warrior", "longship sailor", "norse"],
    "alien":          ["extraterrestrial", "otherworldly being", "space creature"],
    "wizard":         ["sorcerer", "mage", "magician", "enchanter", "robed figure", "spell caster"],
    "chef":           ["cook", "culinary artist", "kitchen worker"],
    "robot":          ["android", "mechanical figure", "machine", "automaton", "artificial being"],
    "construction":   ["building site", "worksite", "site", "scaffolding", "crane", "machinery"],
    "hat":            ["headgear", "cap", "helmet", "headwear", "hard hat"],
    "piano":          ["keyboard", "keys", "instrument", "grand piano"],
    "bicycle":        ["bike", "two-wheeled", "cycling", "pedal"],
    "car":            ["automobile", "vehicle", "motor", "vintage car", "auto"],
    "library":        ["books", "shelves", "bookshelves", "reading room", "study", "archives"],
    "river":          ["water", "stream", "brook", "flowing water", "waterway"],
    "coffee":         ["mug", "cup", "brew", "hot drink", "beverage"],
    "pizza":          ["pie", "dough", "toppings", "circular food"],
    "castle":         ["fortress", "stronghold", "tower", "battlement", "medieval structure"],
    "spaceship":      ["spacecraft", "rocket", "vessel", "ship", "ufo", "saucer", "capsule"],
    "desert":         ["sand", "arid", "dune", "dry landscape", "wasteland"],
    "portrait":       ["painting", "canvas", "artwork", "picture"],
    "detective":      ["investigator", "sleuth", "inspector",
                       "magnifying glass", "trench coat", "clues", "mystery"],
    "village":        ["town", "settlement", "houses", "buildings", "community"],
    "supermarket":    ["store", "shop", "grocery", "market", "aisle", "shelves", "cart"],
    "cherry blossom": ["sakura", "pink flowers", "spring flowers", "petals", "flowering tree"],
    "ice":            ["frozen", "arctic", "glacier", "iceberg", "frost", "cold", "polar"],
    "wearing":        ["dressed in", "clad in", "donning", "sporting", "clothed in"],
    "driving":        ["behind the wheel", "at the wheel", "operating", "steering"],
    "riding":         ["atop", "mounted on", "pedalling", "seated on"],
    "sleeping":       ["asleep", "slumbering", "resting", "napping", "curled up"],
    "cooking":        ["preparing food", "making food", "culinary", "stirring", "frying"],
    "painting":       ["creating art", "brushing", "canvas work", "depicting"],
    "playing":        ["performing", "playing music", "pressing keys", "strumming"],
    "reading":        ["studying", "perusing", "looking at pages", "book in hand"],
    "drinking":       ["sipping", "quaffing", "consuming liquid", "holding a cup"],
    "sailing":        ["navigating", "at sea", "on water", "aboard", "seafaring"],
    "shopping":       ["browsing", "buying", "in a shop", "cart", "aisle"],
    "standing":       ["upright", "erect", "posed", "positioned"],
    "examining":      ["inspecting", "studying", "looking closely", "investigating"],
}

_STOP_WORDS = {
    "a", "an", "the", "at", "in", "on", "of", "and", "or", "is", "it",
    "its", "as", "are", "with", "for", "to", "from", "by", "while",
    "that", "this", "be", "was", "has", "have", "had", "but", "their",
}


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOP_WORDS]


def _ngrams(tok: list[str], n: int) -> set[str]:
    return {" ".join(tok[i:i+n]) for i in range(len(tok)-n+1)}


def _concept_coverage(prompt: str, concept: str) -> float:
    """
    Return 0.0–1.0 coverage of a concept in the prompt.

    Tiers:
      1.0  — exact word/phrase or direct synonym
      0.7  — prefix match (5+ chars, e.g. "construct" covers "construction")
      0.4  — indirect hint (shared char set)
    """
    p_lower = prompt.lower()
    p_tok = _tokens(p_lower)
    p_uni = set(p_tok)
    p_bi  = _ngrams(p_tok, 2)
    p_tri = _ngrams(p_tok, 3)

    c_lower = concept.lower()
    c_tok = _tokens(c_lower)

    # ── Tier 1: exact ────────────────────────────────────────────────────────
    if c_lower in p_lower:
        return 1.0
    if c_tok and " ".join(c_tok) in p_bi | p_tri:
        return 1.0
    if any(t in p_uni for t in c_tok if len(t) > 3):
        return 0.95

    # ── Tier 1b: synonyms ────────────────────────────────────────────────────
    syns: list[str] = []
    for ct in c_tok:
        syns.extend(_SYNONYMS.get(ct, []))
    syns.extend(_SYNONYMS.get(c_lower, []))
    for syn in syns:
        if syn in p_lower:
            return 1.0
        syn_tok = syn.split()
        if len(syn_tok) == 1 and syn_tok[0] in p_uni:
            return 1.0
        if len(syn_tok) == 2 and " ".join(syn_tok) in p_bi:
            return 1.0

    # ── Tier 2: prefix match ─────────────────────────────────────────────────
    for ct in c_tok:
        if len(ct) >= 5 and any(t.startswith(ct[:5]) for t in p_tok):
            return 0.7

    # ── Tier 3: indirect hint ────────────────────────────────────────────────
    for ct in c_tok:
        if len(ct) >= 5:
            if any(abs(len(t) - len(ct)) <= 2 and
                   sum(1 for a, b in zip(t, ct) if a == b) >= 4
                   for t in p_tok if len(t) >= 4):
                return 0.4

    return 0.0


def _jitter(seed: str, magnitude: float = 0.06) -> float:
    """Deterministic jitter in [-magnitude, +magnitude]."""
    h = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
    return (h % 10000 / 10000.0 * 2 - 1) * magnitude


class MockImageEvaluationProvider(ImageEvaluationProvider):

    @property
    def provider_name(self) -> str:
        return "mock"

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
        await asyncio.sleep(settings.mock_generation_delay * 0.2)

        # Use the player's prompt as the evaluation text
        eval_text = player_prompt.strip() if player_prompt.strip() else target_description

        # ── Concept coverage ──────────────────────────────────────────────────
        all_concepts: list[tuple[str, str]] = []   # (concept_text, label)
        for obj in required_objects:
            all_concepts.append((obj, "Subject"))
        for attr in required_attributes:
            all_concepts.append((attr, "Detail"))
        for scene in required_scene:
            all_concepts.append((scene, "Environment"))
        for rel in required_relationships:
            all_concepts.append((rel, "Action"))

        per_concept: list[ConceptResult] = []
        concept_scores: list[float] = []

        for concept_text, label in all_concepts:
            cov = _concept_coverage(eval_text, concept_text)
            cov = max(0.0, min(1.0, cov + _jitter(f"{eval_text}:{concept_text}")))
            if cov >= 0.75:
                result = "yes"
            elif cov >= 0.35:
                result = "partial"
            else:
                result = "no"
            per_concept.append(ConceptResult(concept=concept_text, label=label, result=result))
            concept_scores.append(ConceptResult(concept=concept_text, label=label, result=result).score)

        concept_coverage_f = (sum(concept_scores) / max(len(concept_scores), 1))
        concept_coverage_pct = max(0, min(100, round(concept_coverage_f * 100)))

        # ── Subject score ─────────────────────────────────────────────────────
        subj_raw = (
            sum(_concept_coverage(eval_text, o) for o in required_objects) /
            max(len(required_objects), 1)
        ) if required_objects else 1.0
        subject_score = max(0, min(100, round(
            (subj_raw + _jitter(f"{eval_text}:subject", 0.08)) * 100
        )))

        # ── Scene score ───────────────────────────────────────────────────────
        scene_raw = (
            sum(_concept_coverage(eval_text, s) for s in required_scene) /
            max(len(required_scene), 1)
        ) if required_scene else 1.0
        scene_score = max(0, min(100, round(
            (scene_raw + _jitter(f"{eval_text}:scene", 0.08)) * 100
        )))

        # ── Composition score (relationships + attributes) ────────────────────
        rel_raw = (
            sum(_concept_coverage(eval_text, r) for r in required_relationships) /
            max(len(required_relationships), 1)
        ) if required_relationships else 1.0
        attr_raw = (
            sum(_concept_coverage(eval_text, a) for a in required_attributes) /
            max(len(required_attributes), 1)
        ) if required_attributes else 1.0
        comp_raw = (rel_raw * 0.6 + attr_raw * 0.4)
        composition_score = max(0, min(100, round(
            (comp_raw + _jitter(f"{eval_text}:comp", 0.08)) * 100
        )))

        # ── Match score ───────────────────────────────────────────────────────
        sub_avg = (subject_score + scene_score + composition_score) / 3
        match_score = max(0, min(100, round(
            0.50 * concept_coverage_pct + 0.50 * sub_avg
        )))
        accuracy_total = match_score // 2  # 0-50

        # ── Legacy ObjectScore list (backward compat) ─────────────────────────
        obj_scores: list[ObjectScore] = []
        n = max(len(required_objects), 1)
        per_pts = 25 // n
        for obj in required_objects:
            cov = _concept_coverage(eval_text, obj)
            present = cov >= 0.35
            obj_scores.append(ObjectScore(
                name=obj,
                present=present,
                confidence=round(cov, 3),
                max_points=per_pts,
                awarded_points=int(per_pts * cov) if present else 0,
            ))

        obj_acc  = subject_score / 100
        attr_acc = composition_score / 100
        sc_acc   = scene_score / 100
        rel_acc  = (sum(ConceptResult(c, "Action", "yes" if _concept_coverage(eval_text, c) >= 0.75
                        else "partial" if _concept_coverage(eval_text, c) >= 0.35 else "no").score
                        for c in required_relationships) / max(len(required_relationships), 1)
                    ) if required_relationships else 1.0

        logger.info(
            "mock_eval_complete",
            match=match_score,
            concept_cov=concept_coverage_pct,
            subject=subject_score,
            scene=scene_score,
            composition=composition_score,
            accuracy_total=accuracy_total,
            prompt_preview=eval_text[:60],
        )

        result_obj = EvaluationResult(
            object_scores=obj_scores,
            object_accuracy=round(obj_acc, 3),
            attribute_accuracy=round(attr_acc, 3),
            scene_accuracy=round(sc_acc, 3),
            relationship_accuracy=round(rel_acc, 3),
            per_concept_results=per_concept,
            subject_score=subject_score,
            scene_score=scene_score,
            composition_score=composition_score,
            concept_coverage=concept_coverage_pct,
            match_score=match_score,
            accuracy_total=accuracy_total,
            provider=self.provider_name,
            model="mock-semantic-v3",
        )
        return result_obj
