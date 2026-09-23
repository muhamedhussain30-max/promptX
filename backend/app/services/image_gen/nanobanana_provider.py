"""
NanoBananaImageGenerationProvider
===================================
Generates images using the Nano Banana API.

API docs: https://docs.nananobanana.com/en/api

Endpoint:  POST https://www.nananobanana.com/api/v1/generate
Auth:      Authorization: Bearer nb_your_api_key_here
Mode:      "sync" — waits for completion, returns imageUrls directly.
           No polling needed → faster than queue-based providers.

Response:
  {
    "data": {
      "outputImageUrls": ["https://..."],
      "processingStatus": "completed",
      "creditsUsed": 1
    }
  }

Error handling:
  429 concurrency limit → retry once after Retry-After header (default 5s)
  402 insufficient credits → clear message
  any timeout / error → GenerationResult(success=False, error_message=...)

Activated when:  AI_PROVIDER=nanobanana  in .env
Required env:    NANOBANANA_API_KEY=nb_...
"""
import asyncio
import base64
import time
import httpx
from app.services.image_gen.base import ImageGenerationProvider, GenerationResult
from app.config.settings import settings
from app.config.logging import logger

_BASE_URL = "https://www.nananobanana.com/api/v1"
_MODEL    = "nano-banana"
_TIMEOUT  = 120.0   # sync mode waits; give it up to 2 minutes


class NanoBananaImageGenerationProvider(ImageGenerationProvider):

    @property
    def provider_name(self) -> str:
        return "nanobanana"

    async def generate(self, prompt: str) -> GenerationResult:
        if not settings.nanobanana_api_key:
            return GenerationResult(
                success=False,
                image_url=None,
                image_data=None,
                provider=self.provider_name,
                model=_MODEL,
                prompt_used=prompt,
                error_message=(
                    "NANOBANANA_API_KEY is not set. "
                    "Add it to .env: NANOBANANA_API_KEY=nb_..."
                ),
            )

        start = time.monotonic()

        payload = {
            "prompt":        prompt,
            "selectedModel": _MODEL,
            "mode":          "sync",   # wait for result — simplest integration
            "quantity":      1,
        }
        headers = {
            "Authorization": f"Bearer {settings.nanobanana_api_key}",
            "Content-Type":  "application/json",
        }

        for attempt in range(2):   # one retry on 429
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    resp = await client.post(
                        f"{_BASE_URL}/generate",
                        json=payload,
                        headers=headers,
                    )

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "5"))
                    if attempt == 0:
                        logger.warning("nanobanana_rate_limit", retry_after=retry_after)
                        await asyncio.sleep(retry_after)
                        continue
                    return GenerationResult(
                        success=False,
                        image_url=None,
                        image_data=None,
                        provider=self.provider_name,
                        model=_MODEL,
                        prompt_used=prompt,
                        error_message="Rate limit reached — please wait a moment and try again.",
                    )

                if resp.status_code == 402:
                    return GenerationResult(
                        success=False,
                        image_url=None,
                        image_data=None,
                        provider=self.provider_name,
                        model=_MODEL,
                        prompt_used=prompt,
                        error_message="Insufficient Nano Banana credits. Top up at nananobanana.com.",
                    )

                resp.raise_for_status()
                data = resp.json()

                urls: list[str] = (
                    data.get("data", {}).get("outputImageUrls")
                    or data.get("data", {}).get("imageUrls")
                    or []
                )
                if not urls:
                    return GenerationResult(
                        success=False,
                        image_url=None,
                        image_data=None,
                        provider=self.provider_name,
                        model=_MODEL,
                        prompt_used=prompt,
                        error_message=f"No image URL in response: {str(data)[:200]}",
                    )

                elapsed_ms = int((time.monotonic() - start) * 1000)
                image_url = urls[0]

                logger.info(
                    "nanobanana_image_generated",
                    prompt_preview=prompt[:60],
                    image_url=image_url,
                    generation_time_ms=elapsed_ms,
                )

                return GenerationResult(
                    success=True,
                    image_url=image_url,
                    image_data=None,
                    provider=self.provider_name,
                    model=_MODEL,
                    prompt_used=prompt,
                    generation_time_ms=elapsed_ms,
                )

            except httpx.TimeoutException:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                logger.error("nanobanana_timeout", time_ms=elapsed_ms)
                return GenerationResult(
                    success=False,
                    image_url=None,
                    image_data=None,
                    provider=self.provider_name,
                    model=_MODEL,
                    prompt_used=prompt,
                    error_message="Image generation timed out — try again.",
                    generation_time_ms=elapsed_ms,
                )
            except Exception as e:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                logger.error("nanobanana_error", error=str(e), time_ms=elapsed_ms)
                return GenerationResult(
                    success=False,
                    image_url=None,
                    image_data=None,
                    provider=self.provider_name,
                    model=_MODEL,
                    prompt_used=prompt,
                    error_message=f"Generation failed: {str(e)}",
                    generation_time_ms=elapsed_ms,
                )

        # Should never reach here
        return GenerationResult(
            success=False, image_url=None, image_data=None,
            provider=self.provider_name, model=_MODEL, prompt_used=prompt,
            error_message="Unexpected error after retries",
        )
