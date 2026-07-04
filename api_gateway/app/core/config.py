from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    VALID_API_KEYS: str
    EDGE_WORKER_URL: str
    MAX_REQUESTS_PER_MINUTE: int = 5
    
    @property
    def api_key_list(self) -> List[str]:
        return [key.strip() for key in self.VALID_API_KEYS.split(",")]

    class Config:
        env_file = ".env"

settings = Settings()