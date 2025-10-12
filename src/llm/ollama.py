from typing import Optional
import ollama

from src.config import LLM_OLLAMA_CONFIG


def get_ollama_async_client() -> Optional[ollama.AsyncClient]:
    host = LLM_OLLAMA_CONFIG.get("api_base_url", "http://localhost:11434")
    try:
        return ollama.AsyncClient(host=host)
    except Exception:
        return None


class OllamaChatStrategy:
    def __init__(self, client: ollama.AsyncClient) -> None:
        self._client = client
        self.model = LLM_OLLAMA_CONFIG.get("model_name", "llama3:8b-instruct")
        self.options = {
            "temperature": LLM_OLLAMA_CONFIG.get("temperature"),
            "num_predict": LLM_OLLAMA_CONFIG.get("num_predict"),
            "format": LLM_OLLAMA_CONFIG.get("format"),
            "top_p": LLM_OLLAMA_CONFIG.get("top_p"),
            "top_k": LLM_OLLAMA_CONFIG.get("top_k"),
        }

    async def chat(self, messages: list[dict]) -> dict:
        return await self._client.chat(model=self.model, messages=messages, options=self.options)


class OllamaGenerateStrategy:
    def __init__(self, client: ollama.AsyncClient) -> None:
        self._client = client
        self.model = LLM_OLLAMA_CONFIG.get("model_name", "llama3:8b-instruct")
        self.options = {
            "temperature": LLM_OLLAMA_CONFIG.get("temperature"),
            "num_predict": LLM_OLLAMA_CONFIG.get("num_predict"),
            "format": LLM_OLLAMA_CONFIG.get("format"),
            "top_p": LLM_OLLAMA_CONFIG.get("top_p"),
            "top_k": LLM_OLLAMA_CONFIG.get("top_k"),
        }

    async def generate(self, prompt: str) -> dict:
        resp = await self._client.generate(model=self.model, prompt=prompt, options=self.options)
        text = (resp or {}).get("response") or (resp or {}).get("message") or ""
        return {"message": {"content": str(text)}}
