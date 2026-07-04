from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.security import verify_api_key
from app.services.llm_client import forward_to_edge

router = APIRouter()

class PromptPayload(BaseModel):
    prompt: str
    intent: str
    max_tokens: int = 512

@router.post("/generate")
async def generate_response(payload: PromptPayload, api_key: str = Depends(verify_api_key)):
    # The route handler is now clean and purely orchestrates the flow
    return await forward_to_edge(payload.model_dump())