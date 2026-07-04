import time
from fastapi import HTTPException, Header, Depends
from app.core.config import settings

rate_limit_db = {}

def check_rate_limit(api_key: str):
    current_time = time.time()
    if api_key not in rate_limit_db:
        rate_limit_db[api_key] = []
        
    rate_limit_db[api_key] = [t for t in rate_limit_db[api_key] if current_time - t < 60]
    
    if len(rate_limit_db[api_key]) >= settings.MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
        
    rate_limit_db[api_key].append(current_time)

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in settings.api_key_list:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    check_rate_limit(x_api_key)
    return x_api_key