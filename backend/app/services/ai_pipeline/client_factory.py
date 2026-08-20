import logging
from app.core.config import settings
from app.services.ai_pipeline.ollama_client import OllamaClient
from app.services.ai_pipeline.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

def get_ai_client(ai_provider: str | None = None):
    """
    Resolves the AI client based on AI_PROVIDER_MODE or an explicit override.
    """
    if ai_provider == "gemini":
        logger.info("Using Cloud AI provider (Gemini) [Explicit Override]")
        return GeminiClient()
    elif ai_provider == "local":
        logger.info("Using Local AI provider (Ollama) [Explicit Override]")
        return OllamaClient()

    mode = settings.AI_PROVIDER_MODE.lower()
    ai_mode = getattr(settings, "AI_MODE", "local_llm").lower()
    
    if mode == "auto":
        import os
        import subprocess
        
        # 1. Check if running in Docker with GPU flag passed
        if os.environ.get("OLLAMA_HAS_GPU", "").lower() == "true":
            logger.info("dGPU indicated via environment (Docker). Using Local AI provider (Ollama) automatically.")
            return OllamaClient()
            
        # 2. Check natively for NVIDIA GPU (e.g., when running backend locally)
        try:
            subprocess.run(["nvidia-smi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            logger.info("dGPU detected (NVIDIA). Using Local AI provider (Ollama) automatically.")
            return OllamaClient()
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.info("No dGPU detected. Falling back to Cloud AI provider (Gemini).")
            return GeminiClient()

    if mode == "cloud" or ai_mode == "cloud_api":
        logger.info("Using Cloud AI provider (Gemini/OpenRouter)")
        return GeminiClient()
        
    logger.info("Using Local AI provider (Ollama)")
    return OllamaClient()

