import asyncio
import os
import sys

# Ensure backend folder is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.services.ai_pipeline.client_factory import get_ai_client

async def verify():
    print("Testing get_ai_client() resolution...")
    client = get_ai_client()
    print(f"Resolved client type: {type(client).__name__}")
    
    if type(client).__name__ != "OllamaClient":
        print("ERROR: Factory did not return OllamaClient. Monkeypatch or config failed.")
        sys.exit(1)
        
    print("Testing offline inference with Ollama...")
    try:
        # Assuming generate signature from standard OllamaClient
        response = await client.generate("Why is the sky blue? Answer in 1 sentence.", model="llama3.2")
        print(f"SUCCESS: Received response from local Ollama: {response}")
    except Exception as e:
        print(f"ERROR: Local inference failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(verify())
