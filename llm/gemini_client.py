from openai import AsyncOpenAI

from config import settings

# Google's Gemini API exposes an OpenAI-compatible endpoint, so the same
# AsyncOpenAI class from llm/client.py works here too — just pointed at
# Google's base_url with a Gemini key instead of an OpenAI key.
#
# Falls back to a placeholder if GEMINI_API_KEY isn't set in .env yet, so
# just importing this module doesn't crash the whole app before the real key
# is added — a real call will fail with a clear auth error instead.
client = AsyncOpenAI(
    api_key=settings.gemini_api_key or "not-set-yet",
    base_url=settings.gemini_base_url,
)
