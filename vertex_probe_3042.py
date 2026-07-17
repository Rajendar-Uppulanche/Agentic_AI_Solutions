"""
Diagnostic script — finds which (region, model) combo your Vertex service account
can actually use. Run it from the agentic_app folder:

    python vertex_probe.py

It reads VERTEX_SERVICE_ACCOUNT_PATH and VERTEX_PROJECT_ID from .env, then tries
a small matrix of regions x models and prints which ones work. Put the winning
combo into .env as VERTEX_REGION and VERTEX_MODEL, then delete this file.
"""
import asyncio
import itertools

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from openai import AsyncOpenAI

from config import settings

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# 'global' is where Google now serves many newer Gemini models on Vertex —
# it uses a different hostname (no region prefix), handled in base_url() below.
REGIONS = ["us-central1", "global", "us-east1", "us-east4", "europe-west1"]

MODELS = [
    "google/gemini-2.0-flash-001",
    "google/gemini-2.0-flash",
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    "google/gemini-1.5-flash-002",
]


def get_token() -> str:
    creds = service_account.Credentials.from_service_account_file(
        settings.vertex_service_account_path, scopes=SCOPES
    )
    creds.refresh(Request())
    return creds.token


def base_url(region: str) -> str:
    host = "aiplatform.googleapis.com" if region == "global" else f"{region}-aiplatform.googleapis.com"
    return f"https://{host}/v1beta1/projects/{settings.vertex_project_id}/locations/{region}/endpoints/openapi"


async def probe(region: str, model: str, token: str) -> tuple[bool, str]:
    client = AsyncOpenAI(api_key=token, base_url=base_url(region))
    try:
        r = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
        )
        return True, f"WORKS   region={region:<14} model={model:<32} -> {r.choices[0].message.content!r}"
    except Exception as e:
        short = str(e).replace("\n", " ")[:100]
        return False, f"fails   region={region:<14} model={model:<32} -> {short}"


async def main():
    if not settings.vertex_service_account_path:
        print("ERROR: VERTEX_SERVICE_ACCOUNT_PATH is not set in .env")
        return
    if not settings.vertex_project_id:
        print("ERROR: VERTEX_PROJECT_ID is not set in .env")
        return

    print(f"project : {settings.vertex_project_id}")
    print(f"sa file : {settings.vertex_service_account_path}\n")

    try:
        token = get_token()
    except Exception as e:
        print(f"ERROR getting token from service account file: {e}")
        return
    print("token   : acquired OK\n")
    print(f"Trying {len(REGIONS) * len(MODELS)} combinations...\n")

    winners = []
    for region, model in itertools.product(REGIONS, MODELS):
        ok, line = await probe(region, model, token)
        print(line)
        if ok:
            winners.append((region, model))

    print("\n" + "=" * 70)
    if winners:
        print("WORKING COMBOS FOUND — put one of these in your .env:\n")
        for region, model in winners:
            print(f"    VERTEX_REGION={region}")
            print(f"    VERTEX_MODEL={model}\n")
    else:
        print("No combo worked. Likely causes:")
        print("  - The Vertex AI API isn't enabled on this project")
        print("  - The service account lacks the 'Vertex AI User' IAM role")
        print("  - Your org restricts which models/regions this project can use")
        print("Ask your TL which region + model the project is actually provisioned for.")


if __name__ == "__main__":
    asyncio.run(main())
