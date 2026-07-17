import logging

from fastapi import FastAPI

from api_fastapi.routes import router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SOC Triage Agent (FastAPI)", version="1.0.0")
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
