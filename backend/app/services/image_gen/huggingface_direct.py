"""
HuggingFaceDirectImageGenerationProvider
=========================================
Direct HTTP implementation that bypasses api-inference.huggingface.co DNS blocking.

Uses the main domain endpoint: https://huggingface.co/api/inference/models/{model}
This works when corporate firewalls or DNS filters block the api-inference subdomain.

API endpoint: POST https://huggingface.co/api/inference/models/black-forest-labs/FLUX.1-schnell
Headers: Authorization: Bearer {HF_TOKEN}
Body: {"inputs": prompt, "parameters": {...}}
Returns: Binary PNG image data

Activated when:  AI_PROVIDER=huggingface  in .env
Required env:    HF_TOKEN=hf_...
"""
import asyncio
import base64
import io
import time
import httpx
from PIL import Image
from app.services.image_gen.base import ImageGenerationProvider, GenerationResult
from app.config.ai_models import (
    IMAGE_GEN_MODEL, IMAGE_GEN_WIDTH, IMAGE_GEN_HEIGHT,
    IMAGE_GEN_STEPS, IMAGE_GEN_GUIDANCE,
)
from app.config.settings import settings
from app.config.logging import logger

# Use main domain instead of blocked api-inference subdomain
_ENDPOINT_TEMPLATE = "https://huggingface.co/api/inference/models/{model}"
_TIMEOUT = 60.0


class HuggingFaceDirectImageGenerationProvider(ImageGenerationProvider):
    """Direct HTTP calls to HuggingFace — bypasses DNS-blocked subdomain."""

    @property
    def provider_name(self) -> str:
        return "huggingface-direct"

    async def generate(self, prompt: str) -> GenerationResult:
        if not settings.hf_token:
            return GenerationResult(
                success=False, image_url=None, image_data=None,
                provider=self.provider_name, model=IMAGE_GEN_MODEL, prompt_used=prompt,
                error_message="HF_TOKEN is not set. Add to .env: HF_TOKEN=hf_...",
            )

        start = time.monotonic()
        endpoint = _ENDPOINT_TEMPLATE.format(model=IMAGE_GEN_MODEL)

        headers = {"Authorization": f"Bearer {settings.hf_token}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "width": IMAGE_GEN_WIDTH,
                "height": IMAGE_GEN_HEIGHT,
                "num_inference_steps": IMAGE_GEN_STEPS,
                "guidance_scale": IMAGE_GEN_GUIDANCE,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)

            if resp.status_code == 429:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                logger.warning("hf_rate_limit", time_ms=elapsed_ms)
                return GenerationResult(
                    success=False, image_url=None, image_data=None,
                    provider=self.provider_name, model=IMAGE_GEN_MODEL, prompt_used=prompt,
                    error_message="Rate limit reached — wait a moment and try again.",
                    generation_time_ms=elapsed_ms,
                )

            if resp.status_code == 503:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                logger.warning("hf_model_loading", time_ms=elapsed_ms)
                return GenerationResult(
                    success=False, image_url=None, image_data=None,
                    provider=self.provider_name, model=IMAGE_GEN_MODEL, prompt_used=prompt,
                    error_message="Model is loading — this takes 20-30s on first request, try again.",
                    generation_time_ms=elapsed_ms,
                )

            resp.raise_for_status()
            
            # Response is binary PNG data
            image_bytes = resp.content
            elapsed_ms = int((time.monotonic() - start) * 1000)

            # Validate it's actually an image
            try:
                Image.open(io.BytesIO(image_bytes)).verify()
            except Exception as e:
                logger.error("hf_invalid_image", error=str(e))
                return GenerationResult(
                    success=False, image_url=None, image_data=None,
                    provider=self.provider_name, model=IMAGE_GEN_MODEL, prompt_used=prompt,
                    error_message=f"Invalid image response: {str(e)}",
                    generation_time_ms=elapsed_ms,
                )

            # Convert to base64 data URI
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            data_uri = f"data:image/png;base64,{b64}"

            logger.info(
                "hf_direct_image_generated",
                model=IMAGE_GEN_MODEL,
                prompt_preview=prompt[:60],
                generation_time_ms=elapsed_ms,
                size_kb=len(image_bytes) // 1024,
            )

            return GenerationResult(
                success=True,
                image_url=data_uri,
                image_data=image_bytes,
                provider=self.provider_name,
                model=IMAGE_GEN_MODEL,
                prompt_used=prompt,
                generation_time_ms=elapsed_ms,
            )

        except httpx.TimeoutException:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.error("hf_timeout", time_ms=elapsed_ms)
            return GenerationResult(
                success=False, image_url=None, image_data=None,
                provider=self.provider_name, model=IMAGE_GEN_MODEL, prompt_used=prompt,
                error_message="Generation timed out — model may be cold starting, try again.",
                generation_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.error("hf_error", error=str(e), time_ms=elapsed_ms)
            return GenerationResult(
                success=False, image_url=None, image_data=None,
                provider=self.provider_name, model=IMAGE_GEN_MODEL, prompt_used=prompt,
                error_message=f"Generation failed: {str(e)}",
                generation_time_ms=elapsed_ms,
            )
