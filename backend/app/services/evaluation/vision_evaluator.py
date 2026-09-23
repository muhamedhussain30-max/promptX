"""
RubricVisionEvaluationProvider
================================
Evaluates the generated image against the hidden challenge criteria using a
vision-language model. The rubric is never sent to the frontend.

Provider selection:
  1. If IMAGE_EVALUATION_API_KEY starts with "sk-" → OpenAI (gpt-4o)
  2. If HF_TOKEN is set → HuggingFace router (Qwen/Qwen2.5-VL-3B-Instruct, free)
  3. Fallback → MockImageEvaluationProvider

Rubric output format (JSON only, temperature=0):
{
  "concepts": [
    {"concept": "...", "result": "yes"|"partial"|"no"},
    ...
  ],
  "subject_score": 0-100,
  "scene_score": 0-100,
  "composition_score": 0-100
}

The evaluation is run VISION_RUNS times (default 2) and the results are averaged
to reduce model variance. JSON is parsed safely with code-fence stripping and one
retry on invalid output.

Security: concept text and rubric prompts are NEVER forwarded to the client.
"""
import json
import re
import time
import asyncio
import httpx
from typing import Optional

from app.services.evaluation.base import (
    ImageEvaluationProvider, EvaluationResult, ObjectScore, ConceptResult
)
from app.config.settings import settings
from app.config.ai_models import (
    VISION_MODEL_FREE, VISION_ROUTER_URL,
    VISION_MODEL_OPENAI, VISION_OPENAI_URL,
    VISION_TEMPERATURE, VISION_MAX_TOKENS, VISION_RUNS,
)
from app.config.logging import logger

# ── System prompt — never reaches the frontend ────────────────────────────────
_SYSTEM = """\
You are a strict image accuracy evaluator for a game.
Given an image and hidden evaluation criteria, assess how well the image matches.
Respond ONLY with valid JSON — no markdown fences, no explanation text.
Schema:
{
  "concepts": [{"concept": "<concept_text>", "result": "yes" | "partial" | "no"}],
  "subject_score": <integer 0-100>,
  "scene_score": <integer 0-100>,
  "composition_score": <integer 0-100>
}
Rules:
- "yes" = clearly visible and accurate
- "partial" = present but unclear, partially visible, or approximately matching
- "no" = absent or wrong
- subject_score: how well the main subject(s) and their action match the target
- scene_score: how well the background / environment matches
- composition_score: overall visual likeness and coherence with the target description
Be strict. A score of 80+ means excellent match. 50-79 means reasonable. Below 50 means poor.
"""


def _build_criteria_text(
    required_objects: list[str],
    required_attributes: list[str],
    required_scene: list[str],
    required_relationships: list[str],
) -> str:
    lines = []
    if required_objects:
        lines.append(f"Required subjects/objects: {', '.join(required_objects)}")
    if required_attributes:
        lines.append(f"Required attributes/details: {', '.join(required_attributes)}")
    if required_scene:
        lines.append(f"Required scene/environment: {', '.join(required_scene)}")
    if required_relationships:
        lines.append(f"Required actions/relationships: {', '.join(required_relationships)}")
    return "\n".join(lines)


def _all_concepts(
    required_objects: list[str],
    required_attributes: list[str],
    required_scene: list[str],
    required_relationships: list[str],
) -> list[tuple[str, str]]:
    """Returns list of (concept_text, player_visible_label)."""
    result = []
    for o in required_objects:
        result.append((o, "Subject"))
    for a in required_attributes:
        result.append((a, "Detail"))
    for s in required_scene:
        result.append((s, "Environment"))
    for r in required_relationships:
        result.append((r, "Action"))
    return result


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if the model wraps its JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _parse_json(raw: str) -> Optional[dict]:
    """Try to parse JSON; return None on failure."""
    try:
        return json.loads(_strip_fences(raw))
    except json.JSONDecodeError:
        # One more try: extract first {...} block
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
        return None


def _detect_invalid_image(image_url: str) -> bool:
    """Heuristic: placehold.co / tiny data URIs are placeholders."""
    if "placehold.co" in image_url:
        return True
    if image_url.startswith("data:image") and len(image_url) < 200:
        return True
    return False


class RubricVisionEvaluationProvider(ImageEvaluationProvider):

    @property
    def provider_name(self) -> str:
        return "rubric-vision"

    # ── Provider / auth selection ─────────────────────────────────────────────

    def _endpoint_and_key(self) -> tuple[str, str, str]:
        """Returns (base_url, api_key, model_id)."""
        eval_key = settings.image_evaluation_api_key
        if eval_key.startswith("sk-"):
            return VISION_OPENAI_URL, eval_key, VISION_MODEL_OPENAI
        hf = settings.hf_token
        if hf:
            return VISION_ROUTER_URL, hf, VISION_MODEL_FREE
        return "", "", ""

    # ── Single evaluation run ────────────────────────────────────────────────

    async def _single_run(
        self,
        image_url: str,
        criteria_text: str,
        concepts: list[tuple[str, str]],
        base_url: str,
        api_key: str,
        model: str,
    ) -> Optional[dict]:
        """Call the vision model once and parse the JSON rubric."""
        concept_list = "\n".join(
            f"  - \"{c}\"" for c, _ in concepts
        )
        user_text = (
            f"Evaluate this image.\n\n"
            f"Target criteria:\n{criteria_text}\n\n"
            f"Evaluate EACH of the following concepts and classify as yes/partial/no:\n"
            f"{concept_list}\n\n"
            f"Also give subject_score, scene_score, composition_score (0-100 each)."
        )

        payload = {
            "model":       model,
            "temperature": VISION_TEMPERATURE,
            "max_tokens":  VISION_MAX_TOKENS,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url":    image_url,
                                "detail": "low",
                            },
                        },
                    ],
                },
            ],
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

            raw_content = data["choices"][0]["message"]["content"]
            parsed = _parse_json(raw_content)

            if parsed is None:
                logger.warning("vision_json_parse_failed", raw=raw_content[:200])
                # One retry with explicit reminder
                payload["messages"].append({"role": "assistant", "content": raw_content})
                payload["messages"].append({"role": "user",
                    "content": "Your previous response was not valid JSON. Reply ONLY with the JSON object."})
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp2 = await client.post(
                        f"{base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                    resp2.raise_for_status()
                    parsed = _parse_json(resp2.json()["choices"][0]["message"]["content"])

            return parsed

        except Exception as e:
            logger.error("vision_api_error", model=model, error=str(e))
            return None

    # ── Main evaluate method ─────────────────────────────────────────────────

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

        # Reject obvious placeholder images — Image Match = 0
        if _detect_invalid_image(image_url):
            logger.info("vision_invalid_image_detected", url=image_url[:80])
            return self._zero_result("Invalid or placeholder image")

        base_url, api_key, model = self._endpoint_and_key()
        if not api_key:
            # No credentials → fall back to mock
            from app.services.evaluation.mock_evaluator import MockImageEvaluationProvider
            return await MockImageEvaluationProvider().evaluate(
                image_url, target_description,
                required_objects, required_attributes,
                required_scene, required_relationships,
                player_prompt=player_prompt,
            )

        concepts = _all_concepts(required_objects, required_attributes, required_scene, required_relationships)
        criteria_text = _build_criteria_text(required_objects, required_attributes, required_scene, required_relationships)

        start = time.monotonic()

        # Run VISION_RUNS times concurrently, average results
        tasks = [
            self._single_run(image_url, criteria_text, concepts, base_url, api_key, model)
            for _ in range(VISION_RUNS)
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        valid = [r for r in raw_results if isinstance(r, dict) and r is not None]

        if not valid:
            logger.error("vision_all_runs_failed", model=model)
            from app.services.evaluation.mock_evaluator import MockImageEvaluationProvider
            fallback = await MockImageEvaluationProvider().evaluate(
                image_url, target_description,
                required_objects, required_attributes,
                required_scene, required_relationships,
                player_prompt=player_prompt,
            )
            fallback.error_message = "Vision API failed on all runs; mock scores used"
            return fallback

        # ── Average scores across runs ────────────────────────────────────────
        # Per-concept: majority vote
        concept_tally: dict[str, list[str]] = {c: [] for c, _ in concepts}
        for run in valid:
            for item in run.get("concepts", []):
                cname = item.get("concept", "")
                if cname in concept_tally:
                    concept_tally[cname].append(item.get("result", "no"))

        per_concept: list[ConceptResult] = []
        concept_scores_f: list[float] = []
        for (ctext, clabel) in concepts:
            votes = concept_tally.get(ctext, [])
            # Convert to numeric, average, then back to label
            numeric = [{"yes": 1.0, "partial": 0.5, "no": 0.0}.get(v, 0.0) for v in votes]
            avg = sum(numeric) / max(len(numeric), 1)
            if avg >= 0.75:
                result_label = "yes"
            elif avg >= 0.35:
                result_label = "partial"
            else:
                result_label = "no"
            per_concept.append(ConceptResult(concept=ctext, label=clabel, result=result_label))
            concept_scores_f.append(avg)

        concept_coverage = max(0, min(100, round(
            sum(concept_scores_f) / max(len(concept_scores_f), 1) * 100
        )))

        def _avg_field(field: str) -> int:
            vals = [r.get(field, 0) for r in valid if isinstance(r.get(field), (int, float))]
            return max(0, min(100, round(sum(vals) / max(len(vals), 1))))

        subject_score     = _avg_field("subject_score")
        scene_score       = _avg_field("scene_score")
        composition_score = _avg_field("composition_score")

        sub_avg    = (subject_score + scene_score + composition_score) / 3
        match_score = max(0, min(100, round(0.50 * concept_coverage + 0.50 * sub_avg)))
        accuracy_total = match_score // 2

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # ── Legacy ObjectScore list ───────────────────────────────────────────
        obj_scores: list[ObjectScore] = []
        n = max(len(required_objects), 1)
        per_pts = 25 // n
        for obj in required_objects:
            cr = next((c for c in per_concept if c.concept == obj), None)
            cov = {"yes": 1.0, "partial": 0.5, "no": 0.0}.get(cr.result if cr else "no", 0.0)
            obj_scores.append(ObjectScore(
                name=obj,
                present=cov >= 0.5,
                confidence=cov,
                max_points=per_pts,
                awarded_points=int(per_pts * cov),
            ))

        logger.info(
            "vision_eval_complete",
            model=model,
            runs=len(valid),
            match=match_score,
            concept_cov=concept_coverage,
            subject=subject_score,
            scene=scene_score,
            composition=composition_score,
            time_ms=elapsed_ms,
        )

        return EvaluationResult(
            object_scores=obj_scores,
            object_accuracy=subject_score / 100,
            attribute_accuracy=composition_score / 100,
            scene_accuracy=scene_score / 100,
            relationship_accuracy=concept_coverage / 100,
            per_concept_results=per_concept,
            subject_score=subject_score,
            scene_score=scene_score,
            composition_score=composition_score,
            concept_coverage=concept_coverage,
            match_score=match_score,
            accuracy_total=accuracy_total,
            provider=self.provider_name,
            model=model,
        )

    @staticmethod
    def _zero_result(msg: str) -> EvaluationResult:
        return EvaluationResult(
            match_score=0,
            accuracy_total=0,
            error_message=msg,
            provider="rubric-vision",
        )
