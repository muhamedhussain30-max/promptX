"""
Image generation provider factory.
Model names live in app/config/ai_models.py — never here.
"""
from functools import lru_cache
from app.services.image_gen.base import ImageGenerationProvider
from app.config.settings import settings


@lru_cache(maxsize=4)
def _get_provider(provider_name: str) -> ImageGenerationProvider:
    if provider_name == "replicate":
        from app.services.image_gen.replicate_provider import ReplicateImageGenerationProvider
        return ReplicateImageGenerationProvider()
    
    if provider_name == "gemini":
        from app.services.image_gen.gemini_provider import GeminiNanoBananaImageGenerationProvider
        return GeminiNanoBananaImageGenerationProvider()

    if provider_name == "nanobanana":
        from app.services.image_gen.nanobanana_provider import NanoBananaImageGenerationProvider
        return NanoBananaImageGenerationProvider()

    if provider_name == "huggingface":
        # Use direct HTTP implementation to bypass api-inference.huggingface.co DNS blocking
        from app.services.image_gen.huggingface_direct import HuggingFaceDirectImageGenerationProvider
        return HuggingFaceDirectImageGenerationProvider()

    if provider_name == "openai":
        from app.services.image_gen.openai_provider import OpenAIImageGenerationProvider
        return OpenAIImageGenerationProvider()

    from app.services.image_gen.mock_provider import MockImageGenerationProvider
    return MockImageGenerationProvider()


def get_image_generation_provider() -> ImageGenerationProvider:
    """Return the provider configured in AI_PROVIDER env var."""
    return _get_provider(settings.ai_provider)
