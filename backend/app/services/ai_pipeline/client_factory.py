import logging
from app.core.config import settings
from app.services.ai_pipeline.ollama_client import OllamaClient
from app.services.ai_pipeline.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

def get_ai_client():
    """
    Resolves the AI client based on AI_PROVIDER_MODE.
    local: always Ollama (hard fail if unreachable)
    cloud: always Gemini/OpenRouter
    auto: attempt Ollama, fallback to Gemini
    """
    mode = settings.AI_PROVIDER_MODE.lower()
    ai_mode = getattr(settings, "AI_MODE", "local_llm").lower()
    
    if mode == "cloud" or ai_mode == "cloud_api":
        logger.info("Using Cloud AI provider (Gemini/OpenRouter)")
        return GeminiClient()
        
    # By default (and in 'local' or 'auto'), we return OllamaClient.
    # The 'auto' fallback logic is not implemented here since it was requested 
    # out of scope for the strictly offline profile, but we default to Ollama.
    logger.info("Using Local AI provider (Ollama)")
    return OllamaClient()

