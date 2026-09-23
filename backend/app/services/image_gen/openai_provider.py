"""
OpenAI DALL-E image-generation provider.
Activated when AI_PROVIDER=openai in .env
Requires: IMAGE_GENERATION_API_KEY=sk-...
"""
import time
import httpx
from app.services.image_gen.base import ImageGenerationProvider, GenerationResult
from app.config.settings import settings
from app.config.logging import logger

_DALLE_ENDPOINT = "https://api.openai.com/v1/images/generations"
_MODEL = "dall-e-3"
_SIZE = "1024x1024"
_QUALITY = "standard"


class OpenAIImageGenerationProvider(ImageGenerationProvider):

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate(self, prompt: str) -> GenerationResult:
        if not settings.image_generation_api_key:
            return GenerationResult(
                success=False,
                image_url=None,
                image_data=None,
                provider=self.provider_name,
                model=_MODEL,
                prompt_used=prompt,
                error_message="IMAGE_GENERATION_API_KEY not set",
            )

        start = time.monotonic()
        headers = {
            "Authorization": f"Bearer {settings.image_generation_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": _MODEL,
            "prompt": prompt,
            "n": 1,
            "size": _SIZE,
            "quality": _QUALITY,
            "response_format": "url",
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(_DALLE_ENDPOINT, json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            image_url: str = data["data"][0]["url"]
            elapsed_ms = int((time.monotonic() - start) * 1000)

            logger.info("openai_image_generated", model=_MODEL, time_ms=elapsed_ms)

            return GenerationResult(
                success=True,
                image_url=image_url,
                image_data=None,
                provider=self.provider_name,
                model=_MODEL,
                prompt_used=prompt,
                generation_time_ms=elapsed_ms,
            )

        except Exception as e:
            logger.error("openai_generation_error", error=str(e))
            return GenerationResult(
                success=False,
                image_url=None,
                image_data=None,
                provider=self.provider_name,
                model=_MODEL,
                prompt_used=prompt,
                error_message=str(e),
            )
