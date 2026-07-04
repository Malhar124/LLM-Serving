import httpx
from fastapi import HTTPException
from app.core.config import settings

async def forward_to_edge(payload: dict):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.EDGE_WORKER_URL,
                json=payload,
                timeout=120.0 
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Edge Worker unreachable.")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail="Edge Worker error.")