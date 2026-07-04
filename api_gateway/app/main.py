from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="LLM API Gateway", description="Production Hybrid Edge Orchestrator")

app.include_router(router, prefix="/api/v1")