# Vertex AI Setup — Do This on Your Company Machine

> This code (including this template) is safe to keep in the repo — it has **no real secrets** in it.
> The real service account file goes **outside** the project folder, on the company machine only.

---

## Step 1 — get the real service account JSON from your TL

It'll look like this shape (these are placeholder values — yours will have real ones):

```json
{
  "type": "service_account",
  "project_id": "your-project-id-here",
  "private_key_id": "your-private-key-id-here",
  "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_REAL_PRIVATE_KEY_CONTENT_HERE\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account@your-project-id-here.iam.gserviceaccount.com",
  "client_id": "your-client-id-here",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project-id-here.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
```

## Step 2 — save it OUTSIDE the project folder

On the company machine, save the real file **somewhere that is not inside `agentic_app\`** — e.g.:
```
C:\Users\<you>\secrets\vertex-service-account.json
```
This matters because it means even if you `git add .` carelessly, this file physically isn't there to be added. Never save it inside the repo folder, even if `.gitignore` should catch it — outside is the real safety net.

## Step 3 — point `.env` at it

In `agentic_app\.env` on the company machine, uncomment and fill in:
```
VERTEX_SERVICE_ACCOUNT_PATH=C:\Users\<you>\secrets\vertex-service-account.json
VERTEX_PROJECT_ID=<the project_id value from the JSON file>
VERTEX_REGION=us-central1
```
Same pattern as the Gemini key — one `.env` edit, no code changes.

## Step 4 — install the one new dependency

```bash
pip install -r requirements.txt
```
(This pulls in `google-auth`, which the other three providers didn't need.)

## Step 5 — test it

```bash
python -m uvicorn app_fastapi:app --reload --port 8000
```
Then POST to `/triage-vertex` with a real alert. If `VERTEX_PROJECT_ID` or the file path is wrong, you'll get a clear error message (not a crash) telling you exactly what's missing — see `agents/triage_agent_vertex.py` / `llm/vertex_client.py` if you need to debug further.

---

## Reminder

- Never commit the real `vertex-service-account.json` (or whatever you name it)
- `.gitignore` in this project already blocks `*.json` and `*vertexAI*` as a safety net — but don't rely on that alone, keep the real file outside the repo folder entirely (Step 2)
