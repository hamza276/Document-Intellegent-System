import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "Document Intelligence Backend"
    API_V1_STR: str = "/api/v1"
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", ".storage")
    FAISS_INDEX_DIR: str = os.getenv("FAISS_INDEX_DIR", ".storage/faiss_index")
    
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    
    ASYNC_PROCESSING: bool = os.getenv("ASYNC_PROCESSING", "true").lower() == "true"
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))
    
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

os.makedirs(settings.STORAGE_DIR, exist_ok=True)
