import time
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import httpx

app = FastAPI(title="LLM API Gateway", description="Handles Auth, Rate Limiting, and Edge Proxying")

# ==============================================================================
# 1. CLOUD CONFIGURATION (Zero-Cost Setup)
# ==============================================================================
# This is the secret key users must provide in their headers to access your API
VALID_API_KEYS = {"sk-malhar-dev-778899"} 

# Paste the Cloudflare URL generated on your Mac here
EDGE_WORKER_URL = "https://your-random-url.trycloudflare.com/v1/execute"

# ==============================================================================
# 2. IN-MEMORY RATE LIMITER (Optimized for 1GB RAM Cloud Instances)
# ==============================================================================
# Dictionary to store timestamp arrays for each IP or API key
rate_limit_db = {}
MAX_REQUESTS_PER_MINUTE = 5

def check_rate_limit(api_key: str):
    current_time = time.time()
    
    # Initialize or clean up old requests outside the 60-second window
    if api_key not in rate_limit_db:
        rate_limit_db[api_key] = []
        
    # Filter out timestamps older than 60 seconds
    rate_limit_db[api_key] = [t for t in rate_limit_db[api_key] if current_time - t < 60]
    
    if len(rate_limit_db[api_key]) >= MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Maximum 5 requests per minute.")
        
    # Log the new request timestamp
    rate_limit_db[api_key].append(current_time)

# ==============================================================================
# 3. AUTHENTICATION DEPENDENCY
# ==============================================================================
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    # Check rate limit specifically for this validated key
    check_rate_limit(x_api_key)
    return x_api_key

# ==============================================================================
# 4. REQUEST SCHEMA & EDGE PROXY
# ==============================================================================
class PromptPayload(BaseModel):
    prompt: str
    intent: str
    max_tokens: int = 512

@app.post("/api/v1/generate")
async def generate_response(payload: PromptPayload, api_key: str = Depends(verify_api_key)):
    # Forward the validated request down the Cloudflare tunnel to your Mac
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                EDGE_WORKER_URL,
                json=payload.model_dump(),
                timeout=120.0 # LLMs take time, give the edge node 2 minutes to reply
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503, 
                detail=f"Edge Worker (Mac) is unreachable or offline."
            )
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code, 
                detail="Edge Worker encountered an internal error."
            )

# Execution: uvicorn gateway:app --host 0.0.0.1 --port 8080