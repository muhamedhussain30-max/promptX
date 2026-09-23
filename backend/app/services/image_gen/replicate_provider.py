"""
ReplicateImageGenerationProvider
=================================
Generates images using FLUX.1-schnell via Replicate API.

Replicate API is more reliable than HuggingFace for restricted networks.
Get API token from: https://replicate.com/account/api-tokens

Activated when:  AI_PROVIDER=replicate  in .env
Required env:    REPLICATE_API_TOKEN=r8_...
"""
import asyncio
import base64
import time
import httpx
from app.services.image_gen.base import ImageGenerationProvider, GenerationResult
from app.config.settings import settings
from app.config.logging import logger

_API_URL = "https://api.replicate.com/v1/predictions"
_MODEL_VERSION = "black-forest-labs/flux-schnell"
_TIMEOUT = 60.0


class ReplicateImageGenerationProvider(ImageGenerationProvider):
    
    @property
    def provider_name(self) -> str:
        return "replicate"

    async def generate(self, prompt: str) -> GenerationResult:
        if not settings.replicate_api_token:
            return GenerationResult(
                success=False, image_url=None, image_data=None,
                provider=self.provider_name, model=_MODEL_VERSION, prompt_used=prompt,
                error_message="REPLICATE_API_TOKEN is not set. Get one at https://replicate.com/account/api-tokens",
            )

        start = time.monotonic()
        headers = {
            "Authorization": f"Token {settings.replicate_api_token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "version": "5599ed30703defd1d160a25a63321b4dec97101d98b4674bcc56e41f62f35637",
            "input": {
                "prompt": prompt,
                "num_outputs": 1,
                "aspect_ratio": "1:1",
                "output_format": "png",
                "output_quality": 80,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                # Start prediction
                resp = await client.post(_API_URL, json=payload, headers=headers)
                resp.raise_for_status()
                prediction = resp.json()
                prediction_id = prediction["id"]
                
                # Poll for completion
                get_url = f"{_API_URL}/{prediction_id}"
                max_polls = 30
                for _ in range(max_polls):
                    await asyncio.sleep(2)
                    resp = await client.get(get_url, headers=headers)
                    resp.raise_for_status()
                    prediction = resp.json()
                    
                    if prediction["status"] == "succeeded":
                        image_url = prediction["output"][0]
                        
                        # Download image and convert to base64
                        img_resp = await client.get(image_url)
                        img_resp.raise_for_status()
                        image_bytes = img_resp.content
                        
                        b64 = base64.b64encode(image_bytes).decode("utf-8")
                        data_uri = f"data:image/png;base64,{b64}"
                        
                        elapsed_ms = int((time.monotonic() - start) * 1000)
                        logger.info("replicate_image_generated", model=_MODEL_VERSION, 
                                  prompt_preview=prompt[:60], generation_time_ms=elapsed_ms)
                        
                        return GenerationResult(
                            success=True, image_url=data_uri, image_data=image_bytes,
                            provider=self.provider_name, model=_MODEL_VERSION,
                            prompt_used=prompt, generation_time_ms=elapsed_ms,
                        )
                    
                    elif prediction["status"] == "failed":
                        error = prediction.get("error", "Unknown error")
                        elapsed_ms = int((time.monotonic() - start) * 1000)
                        logger.error("replicate_failed", error=error, time_ms=elapsed_ms)
                        return GenerationResult(
                            success=False, image_url=None, image_data=None,
                            provider=self.provider_name, model=_MODEL_VERSION, prompt_used=prompt,
                            error_message=f"Generation failed: {error}", generation_time_ms=elapsed_ms,
                        )
                
                # Timeout
                elapsed_ms = int((time.monotonic() - start) * 1000)
                return GenerationResult(
                    success=False, image_url=None, image_data=None,
                    provider=self.provider_name, model=_MODEL_VERSION, prompt_used=prompt,
                    error_message="Generation timed out", generation_time_ms=elapsed_ms,
                )

        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.error("replicate_error", error=str(e), time_ms=elapsed_ms)
            return GenerationResult(
                success=False, image_url=None, image_data=None,
                provider=self.provider_name, model=_MODEL_VERSION, prompt_used=prompt,
                error_message=f"Replicate error: {str(e)}", generation_time_ms=elapsed_ms,
            )
