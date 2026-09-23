"""
HuggingFaceImageGenerationProvider
===================================
Generates images using FLUX.1-schnell via the HuggingFace Inference Providers API.

API used:
  huggingface_hub.InferenceClient.text_to_image()
  Docs: https://huggingface.co/docs/inference-providers/en/guides/first-api-call
  Returns: PIL.Image object

The image is converted to a base64 data URI (data:image/png;base64,...)
so it can be stored and served without a separate file host.

Activated when:  AI_PROVIDER=huggingface  in .env
Required env:    HF_TOKEN=hf_...          (HuggingFace user access token)

Error handling:
  - 429 Too Many Requests → clear retry message, success=False
  - Timeout (>30s)        → clear retry message, success=False
  - Any other error       → logged, success=False
"""
import asyncio
import base64
import io
import time
from typing import Optional

from app.services.image_gen.base import ImageGenerationProvider, GenerationResult
from app.config.ai_models import (
    IMAGE_GEN_MODEL, IMAGE_GEN_PROVIDER,
    IMAGE_GEN_WIDTH, IMAGE_GEN_HEIGHT,
    IMAGE_GEN_STEPS, IMAGE_GEN_GUIDANCE,
)
from app.config.settings import settings
from app.config.logging import logger


class HuggingFaceImageGenerationProvider(ImageGenerationProvider):
    """
    Calls FLUX.1-schnell through HuggingFace Inference Providers.
    Returns a base64 data URI so no external URL is needed.
    """

    @property
    def provider_name(self) -> str:
        return "huggingface-flux"

    async def generate(self, prompt: str) -> GenerationResult:
        if not settings.hf_token:
            return GenerationResult(
                success=False,
                image_url=None,
                image_data=None,
                provider=self.provider_name,
                model=IMAGE_GEN_MODEL,
                prompt_used=prompt,
                error_message=(
                    "HF_TOKEN is not set. "
                    "Add your HuggingFace token to .env: HF_TOKEN=hf_..."
                ),
            )

        start = time.monotonic()

        try:
            # Run the synchronous HF client in a thread pool so we don't block the event loop
            image = await asyncio.get_event_loop().run_in_executor(
                None,
                self._generate_sync,
                prompt,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            error_str = str(e)

            if "429" in error_str or "rate limit" in error_str.lower():
                msg = "Rate limit reached — please wait a moment and try again."
            elif "timeout" in error_str.lower() or "timed out" in error_str.lower():
                msg = "Image generation timed out — the model is busy, try again shortly."
            else:
                msg = f"Image generation failed: {error_str}"

            logger.error("hf_generation_error", error=error_str, time_ms=elapsed_ms)
            return GenerationResult(
                success=False,
                image_url=None,
                image_data=None,
                provider=self.provider_name,
                model=IMAGE_GEN_MODEL,
                prompt_used=prompt,
                error_message=msg,
                generation_time_ms=elapsed_ms,
            )

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Convert PIL Image → PNG bytes → base64 data URI
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        data_uri = f"data:image/png;base64,{b64}"

        logger.info(
            "hf_image_generated",
            model=IMAGE_GEN_MODEL,
            prompt_preview=prompt[:60],
            generation_time_ms=elapsed_ms,
        )

        return GenerationResult(
            success=True,
            image_url=data_uri,
            image_data=buf.getvalue(),
            provider=self.provider_name,
            model=IMAGE_GEN_MODEL,
            prompt_used=prompt,
            generation_time_ms=elapsed_ms,
        )

    def _generate_sync(self, prompt: str):
        """Synchronous generation call — runs in thread pool."""
        from huggingface_hub import InferenceClient

        client = InferenceClient(
            api_key=settings.hf_token,
        )
        return client.text_to_image(
            prompt,
            model=IMAGE_GEN_MODEL,
            provider="auto",  # Let HF select the best available provider
            width=IMAGE_GEN_WIDTH,
            height=IMAGE_GEN_HEIGHT,
            num_inference_steps=IMAGE_GEN_STEPS,
            guidance_scale=IMAGE_GEN_GUIDANCE,
        )
