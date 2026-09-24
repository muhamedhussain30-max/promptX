"""
HuggingFace Direct HTTP Provider
=================================
Makes direct HTTP requests to HuggingFace Inference API
Bypasses SDK to avoid version/endpoint issues
"""
import asyncio
import base64
import io
import time
import httpx
from PIL import Image

from app.services.image_gen.base import ImageGenerationProvider, GenerationResult
from app.config.ai_models import (
    IMAGE_GEN_MODEL,
    IMAGE_GEN_WIDTH, IMAGE_GEN_HEIGHT,
    IMAGE_GEN_STEPS, IMAGE_GEN_GUIDANCE,
)
from app.config.settings import settings
from app.config.logging import logger


class HuggingFaceDirectProvider(ImageGenerationProvider):
    """
    Direct HTTP client for HuggingFace Inference API
    Works with any model that supports text-to-image
    """

    @property
    def provider_name(self) -> str:
        return "huggingface-direct"

    async def generate(self, prompt: str) -> GenerationResult:
        if not settings.hf_token:
            return GenerationResult(
                success=False,
                image_url=None,
                image_data=None,
                provider=self.provider_name,
                model=IMAGE_GEN_MODEL,
                prompt_used=prompt,
                error_message="HF_TOKEN is not set",
            )

        start = time.monotonic()

        try:
            # Use direct HTTP API call
            image_bytes = await self._call_api(prompt)
            
            elapsed_ms = int((time.monotonic() - start) * 1000)

            # Convert to base64 data URI
            b64 = base64.b64encode(image_bytes).decode("utf-8")
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
                image_data=image_bytes,
                provider=self.provider_name,
                model=IMAGE_GEN_MODEL,
                prompt_used=prompt,
                generation_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            error_str = str(e)

            if "429" in error_str or "rate limit" in error_str.lower():
                msg = "Rate limit reached — please wait a moment and try again."
            elif "timeout" in error_str.lower() or "timed out" in error_str.lower():
                msg = "Image generation timed out — the model is busy, try again shortly."
            elif "503" in error_str:
                msg = "Model is loading, please try again in a moment."
            else:
                msg = f"Generation failed: {error_str}"

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

    async def _call_api(self, prompt: str) -> bytes:
        """Make direct HTTP request to HuggingFace Inference API"""
        
        # Correct HuggingFace Inference API endpoint
        api_url = f"https://api-inference.huggingface.co/models/{IMAGE_GEN_MODEL}"
        
        headers = {
            "Authorization": f"Bearer {settings.hf_token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "width": IMAGE_GEN_WIDTH,
                "height": IMAGE_GEN_HEIGHT,
                "num_inference_steps": IMAGE_GEN_STEPS,
                "guidance_scale": IMAGE_GEN_GUIDANCE,
            }
        }
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                api_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                return response.content
            elif response.status_code == 503:
                # Model is loading, wait and retry once
                import asyncio
                logger.info("model_loading", model=IMAGE_GEN_MODEL)
                await asyncio.sleep(20)
                
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    return response.content
            
            # API call failed
            error_text = response.text[:500]
            raise Exception(
                f"API returned {response.status_code}: {error_text}"
            )
