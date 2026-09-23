"""
Evaluation provider factory.
Model names and endpoint URLs live in app/config/ai_models.py.
"""
from functools import lru_cache
from app.services.evaluation.base import ImageEvaluationProvider
from app.config.settings import settings


@lru_cache(maxsize=4)
def _get_eval_provider(provider_name: str) -> ImageEvaluationProvider:
    # Use rubric vision evaluator whenever a real API key or HF token is present
    if provider_name in ("openai", "huggingface") or \
       settings.image_evaluation_api_key or settings.hf_token:
        from app.services.evaluation.vision_evaluator import RubricVisionEvaluationProvider
        return RubricVisionEvaluationProvider()

    from app.services.evaluation.mock_evaluator import MockImageEvaluationProvider
    return MockImageEvaluationProvider()


def get_image_evaluation_provider() -> ImageEvaluationProvider:
    return _get_eval_provider(settings.ai_provider)
