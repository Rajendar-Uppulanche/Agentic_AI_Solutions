"""
Vertex AI client — genuinely different from llm/client.py and llm/gemini_client.py.

Those two use a static API key that never changes, so they build ONE client object
at import time and reuse it forever. Vertex AI uses a service account instead: you
exchange the service account's credentials for a short-lived access token (~1 hour),
and that token expires. So instead of one static `client`, this file exposes a
function — get_client() — that returns a client built with a fresh, valid token
every time it's called. Call it right before each request, not once at startup.

⚠️ Not live-tested — no real service account file was available in this environment
while building this. The endpoint shape and auth flow follow Google's documented
Vertex AI OpenAI-compatibility layer; verify against the real credentials.
"""
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from openai import AsyncOpenAI

from config import settings

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

_credentials = None
if settings.vertex_service_account_path:
    _credentials = service_account.Credentials.from_service_account_file(
        settings.vertex_service_account_path, scopes=_SCOPES
    )


def _get_access_token() -> str:
    """Returns a valid bearer token, refreshing it first if it's expired or unset."""
    if _credentials is None:
        return "not-configured"   # lets the app start even before VERTEX_SERVICE_ACCOUNT_PATH is set
    if not _credentials.valid:
        _credentials.refresh(Request())
    return _credentials.token


def get_client() -> AsyncOpenAI:
    """Build a client with a fresh token. Call this per-request, not once at import."""
    if not settings.vertex_project_id:
        raise RuntimeError("VERTEX_PROJECT_ID is not set in .env")

    base_url = (
        f"https://{settings.vertex_region}-aiplatform.googleapis.com/v1beta1/"
        f"projects/{settings.vertex_project_id}/locations/{settings.vertex_region}/endpoints/openapi"
    )
    return AsyncOpenAI(api_key=_get_access_token(), base_url=base_url)
