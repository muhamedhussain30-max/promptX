"""
GeminiNanoBananaImageGenerationProvider
=========================================
Generates images using Google Gemini Nano Banana (gemini-3.1-flash-image).

API docs: https://ai.google.dev/gemini-api/docs/image-generation

Endpoint:  POST https://generativelanguage.googleapis.com/v1beta/interactions
Auth:      x-goog-api-key header
Model:     gemini-3.1-flash-image  (Nano Banana 2 — best speed/quality balance)
           gemini-3.1-flash-lite-image  (Nano Banana 2 Lite — fastest, cheapest)

Response: interaction.output_image.data  → base64-encoded PNG

The image is returned as a base64 data URI so it can be stored and served
without a separate file host, same as the HuggingFace provider.

Activated when:  AI_PROVIDER=gemini  in .env
Required env:    GEMINI_API_KEY=AIza...
"""
import asyncio
import base64
import time
import httpx
from app.services.image_gen.base import ImageGenerationProvider, GenerationResult
from app.config.settings import settings
from app.config.logging import logger

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
_MODEL    = "gemini-3.1-flash-image"
_TIMEOUT  = 90.0   # Nano Banana 2 typically responds in 5-20 seconds


class GeminiNanoBananaImageGenerationProvider(ImageGenerationProvider):

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate(self, prompt: str) -> GenerationResult:
        if not settings.gemini_api_key:
            return GenerationResult(
                success=False,
                image_url=None,
                image_data=None,
                provider=self.provider_name,
                model=_MODEL,
                prompt_used=prompt,
                error_message=(
                    "GEMINI_API_KEY is not set. "
                    "Get a free key at https://aistudio.google.com/apikey "
                    "then add to .env: GEMINI_API_KEY=AIza..."
                ),
            )

        start = time.monotonic()

        payload = {
            "model": _MODEL,
            "input": prompt,
            "response_format": {
                "type": "image",
                "aspect_ratio": "1:1",
                "image_size": "1K",   # 1024x1024 — fast and good quality
            },
        }
        headers = {
            "x-goog-api-key": settings.gemini_api_key,
            "Content-Type":   "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(_ENDPOINT, json=payload, headers=headers)

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "10"))
                logger.warning("gemini_rate_limit", retry_after=retry_after)
                # One automatic retry after the wait
                await asyncio.sleep(retry_after)
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    resp = await client.post(_ENDPOINT, json=payload, headers=headers)

            if resp.status_code == 400:
                body = resp.json()
                err = body.get("error", {}).get("message", str(body))
                return GenerationResult(
                    success=False, image_url=None, image_data=None,
                    provider=self.provider_name, model=_MODEL, prompt_used=prompt,
                    error_message=f"Bad request: {err}",
                )

            resp.raise_for_status()
            data = resp.json()

            # Extract base64 image from response
            # Primary path: interaction.output_image.data (convenience property)
            output_image = data.get("output_image") or data.get("outputImage")
            if output_image:
                b64 = output_image.get("data") or output_image.get("imageData", "")
            else:
                # Fallback: iterate steps → model_output → image content block
                b64 = None
                for step in data.get("steps", []):
                    if step.get("type") == "model_output":
                        for block in step.get("content", []):
                            if block.get("type") == "image":
                                b64 = block.get("data", "")
                                break
                    if b64:
                        break

            if not b64:
                logger.error("gemini_no_image_in_response", response_keys=list(data.keys()))
                return GenerationResult(
                    success=False, image_url=None, image_data=None,
                    provider=self.provider_name, model=_MODEL, prompt_used=prompt,
                    error_message="No image data in Gemini response",
                )

            # Build data URI
            data_uri = f"data:image/png;base64,{b64}"
            elapsed_ms = int((time.monotonic() - start) * 1000)

            logger.info(
                "gemini_image_generated",
                model=_MODEL,
                prompt_preview=prompt[:60],
                generation_time_ms=elapsed_ms,
            )

            return GenerationResult(
                success=True,
                image_url=data_uri,
                image_data=base64.b64decode(b64),
                provider=self.provider_name,
                model=_MODEL,
                prompt_used=prompt,
                generation_time_ms=elapsed_ms,
            )

        except httpx.TimeoutException:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.error("gemini_timeout", time_ms=elapsed_ms)
            return GenerationResult(
                success=False, image_url=None, image_data=None,
                provider=self.provider_name, model=_MODEL, prompt_used=prompt,
                error_message="Gemini image generation timed out — try again.",
                generation_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.error("gemini_error", error=str(e), time_ms=elapsed_ms)
            return GenerationResult(
                success=False, image_url=None, image_data=None,
                provider=self.provider_name, model=_MODEL, prompt_used=prompt,
                error_message=f"Gemini generation failed: {str(e)}",
                generation_time_ms=elapsed_ms,
            )
