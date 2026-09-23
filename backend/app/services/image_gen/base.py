"""
Abstract base class for all image-generation providers.
Any provider (mock, OpenAI DALL-E, Stability AI, Replicate, etc.) must implement this.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class GenerationResult:
    success: bool
    image_url: Optional[str]        # URL or base64 data URI
    image_data: Optional[bytes]     # Raw bytes if available
    provider: str
    model: Optional[str]
    prompt_used: str
    error_message: Optional[str] = None
    generation_time_ms: Optional[int] = None


class ImageGenerationProvider(ABC):
    """Interface every image-generation backend must satisfy."""

    @abstractmethod
    async def generate(self, prompt: str) -> GenerationResult:
        """Generate an image from a text prompt. Returns a GenerationResult."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name shown in logs."""
        ...
