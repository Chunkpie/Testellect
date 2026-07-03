from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./database/app.db"
    JWT_SECRET_KEY: str = "change-me-in-production-use-a-real-secret"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "qwen2.5:1.5b"
    OLLAMA_FALLBACK_MODELS: list[str] = []
    OLLAMA_TIMEOUT: int = 300
    OLLAMA_NUM_THREAD: int = 8
    OLLAMA_TEMPERATURE: float = 0.1
    OLLAMA_BATCH_SIZE: int = 5
    CHROMA_BASE_URL: str = "http://chromadb:8001"
    FILE_STORAGE_PATH: str = "/data/storage"
    BACKUP_PATH: str = "/data/backups"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost", "http://localhost:80", "http://localhost:8000"]
    UPLOAD_DIR: str = "uploads"
    REPORTS_DIR: str = "reports"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
