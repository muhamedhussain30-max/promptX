"""
AI model name configuration — change model IDs here, nowhere else.

Image generation:
  FLUX.1-schnell  — fast, free-tier on HuggingFace Inference Providers (fal-ai / replicate)
  FLUX.1-dev      — higher quality, slower, non-commercial license

Vision scoring:
  Qwen/Qwen2.5-VL-3B-Instruct — free via HuggingFace router (OpenAI-compat endpoint)
  Fallback: gpt-4o via openai if IMAGE_EVALUATION_API_KEY starts with "sk-"

All keys are read from .env — never hardcoded here.
"""

# ── Image generation ──────────────────────────────────────────────────────────
# Using Stable Diffusion v1.4 - reliable on free HuggingFace Inference API
IMAGE_GEN_MODEL    = "CompVis/stable-diffusion-v1-4"
IMAGE_GEN_PROVIDER = "auto"
IMAGE_GEN_WIDTH    = 512
IMAGE_GEN_HEIGHT   = 512
IMAGE_GEN_STEPS    = 25
IMAGE_GEN_GUIDANCE = 7.5

# ── Vision evaluation ─────────────────────────────────────────────────────────
# HuggingFace router — free tier (Qwen2.5-VL-3B is available serverless)
VISION_MODEL_FREE  = "Qwen/Qwen2.5-VL-3B-Instruct"
VISION_ROUTER_URL  = "https://router.huggingface.co/v1"

# OpenAI fallback — used when IMAGE_EVALUATION_API_KEY starts with "sk-"
VISION_MODEL_OPENAI = "gpt-4o"
VISION_OPENAI_URL   = "https://api.openai.com/v1"

# Scoring parameters
VISION_TEMPERATURE = 0       # must be deterministic
VISION_MAX_TOKENS  = 600     # enough for JSON rubric output
VISION_RUNS        = 2       # run evaluation twice, average results
