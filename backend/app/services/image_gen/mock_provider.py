"""
MockImageGenerationProvider — returns placeholder images that display the prompt text.

Uses placehold.co (a free placeholder image service) to return images that
actually show text from the prompt. This makes testing meaningful:
  - You can see which prompt generated which image
  - Images are visually distinct per prompt
  - No API key needed

In development, set AI_PROVIDER=mock in .env
"""
import asyncio
import hashlib
import time
from urllib.parse import quote
from app.services.image_gen.base import ImageGenerationProvider, GenerationResult
from app.config.settings import settings
from app.config.logging import logger

# Colour pairs (background/text) cycled by prompt hash for visual variety
_COLOUR_PAIRS = [
    ("1a1a2e", "e94560"),
    ("16213e", "0f3460"),
    ("0f3460", "e94560"),
    ("1b1b2f", "f5a623"),
    ("2c2c54", "ff793f"),
    ("2d132c", "ee4540"),
    ("1a1a2e", "533483"),
    ("162447", "e43f5a"),
]


def _prompt_to_colours(prompt: str) -> tuple[str, str]:
    h = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:4], 16)
    return _COLOUR_PAIRS[h % len(_COLOUR_PAIRS)]


def _truncate_for_url(text: str, max_chars: int = 60) -> str:
    """Truncate prompt to fit in a URL-safe placeholder label."""
    words = text.split()
    result = []
    total = 0
    for w in words:
        if total + len(w) + 1 > max_chars:
            break
        result.append(w)
        total += len(w) + 1
    short = " ".join(result)
    if len(short) < len(text):
        short += "..."
    return short


class MockImageGenerationProvider(ImageGenerationProvider):
    """
    Simulates image generation with a configurable delay.
    Returns a placehold.co URL that renders the first few words of the prompt
    as visible text, making it easy to verify prompt→image mapping during tests.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    async def generate(self, prompt: str) -> GenerationResult:
        start = time.monotonic()

        # Simulate API latency
        delay = settings.mock_generation_delay
        if delay > 0:
            await asyncio.sleep(delay)

        bg, fg = _prompt_to_colours(prompt)
        label = _truncate_for_url(prompt)
        # placehold.co format: /WxH/bg/fg?text=...&font=montserrat
        encoded = quote(label, safe="")
        image_url = (
            f"https://placehold.co/512x512/{bg}/{fg}"
            f"?text={encoded}&font=montserrat"
        )

        elapsed_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "mock_image_generated",
            prompt_preview=prompt[:60],
            image_url=image_url,
            generation_time_ms=elapsed_ms,
        )

        return GenerationResult(
            success=True,
            image_url=image_url,
            image_data=None,
            provider=self.provider_name,
            model="mock-v1",
            prompt_used=prompt,
            generation_time_ms=elapsed_ms,
        )
