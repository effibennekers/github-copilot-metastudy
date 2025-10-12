from typing import Optional, Any, Callable, Awaitable
import asyncio

from src.config import LLM_GENERAL_CONFIG, LLM_OLLAMA_CONFIG, LLM_VERTEX_CONFIG
from src.llm.ollama import get_ollama_async_client, OllamaChatStrategy, OllamaGenerateStrategy
from src.llm.vertex import get_vertex_genai_sync_client, VertexChatStrategy, VertexGenerateStrategy


class LLMClient:
    """Uniforme LLM-client (Strategy Pattern) die als async context manager fungeert."""

    def __init__(self) -> None:
        self._provider = str(LLM_GENERAL_CONFIG.get("provider", "ollama")).strip().lower()
        self._client: Optional[Any] = (
            None  # De concrete client (VertexClient of ollama.AsyncClient)
        )
        self._chat_strategy: Optional[Any] = None
        self._generate_strategy: Optional[Any] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def __aenter__(self) -> "LLMClient":
        """Initialiseert de client en strategie asynchroon. Zorgt voor robuuste client creatie."""
        
        if self._provider == "vertex":
            try:
                # 1. Maak de synchrone client aan
                self._client = get_vertex_genai_sync_client()
                # 2. Gebruik de .aio interface in de strategie
                self._chat_strategy = VertexChatStrategy(self._client.aio)
                self._generate_strategy = VertexGenerateStrategy(self._client.aio)
                self._semaphore = _GlobalSemaphoreRegistry.get_semaphore(self._provider, int(LLM_VERTEX_CONFIG.get("batch_size", 2)))
            except Exception as e:
                # Vang fouten op bij client creatie (bijv. config fouten)
                raise RuntimeError(f"Vertex AI Client kon niet worden geïnitialiseerd: {e}")

        else:  # ollama
            try:
                self._client = get_ollama_async_client()
                if self._client is None:
                    raise RuntimeError("Ollama AsyncClient kon niet worden aangemaakt (None)")

                self._chat_strategy = OllamaChatStrategy(self._client)
                self._generate_strategy = OllamaGenerateStrategy(self._client)
                self._semaphore = _GlobalSemaphoreRegistry.get_semaphore(self._provider, int(LLM_OLLAMA_CONFIG.get("batch_size", 2)))
            except Exception as e:
                raise RuntimeError(f"Ollama AsyncClient kon niet worden geïnitialiseerd: {e}")
        
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """Sluit de client en alle netwerkverbindingen correct af."""
        if self._client:
            # 1. Sluit de Vertex AI client. De .aio interface heeft een close() methode
            if self._provider == "vertex":
                # Gebruik asyncio.gather om te wachten op de asynchrone sluiting
                await asyncio.gather(self._client.aio.aclose())

            # 2. Sluit de Ollama client. Deze heeft een awaitable close() methode.
            elif self._provider == "ollama" and hasattr(self._client, "close"):
                # Wacht tot de Ollama client de verbindingen heeft gesloten
                await self._client.close()
                # Optioneel: als er een aexit methode is, roep die aan
                if hasattr(self._client, "__aexit__"):
                    await self._client.__aexit__(exc_type, exc_value, traceback)

    async def chat(self, messages: list[dict]) -> dict:
        """Voert de chat-aanroep uit via de geselecteerde strategie."""
        if self._chat_strategy is None:
            # Zorgt ervoor dat de client altijd met 'async with' moet worden gebruikt
            raise RuntimeError(
                "LLMClient moet worden gebruikt met 'async with' om te initialiseren"
            )
        return await self._run_with_limit(lambda: self._chat_strategy.chat(messages))

    async def generate(self, prompt: str) -> dict:
        """Voert de generate-aanroep uit via de geselecteerde strategie (prompt-only)."""
        if not hasattr(self, "_generate_strategy") or self._generate_strategy is None:
            raise RuntimeError(
                "LLMClient moet worden gebruikt met 'async with' om te initialiseren"
            )
        return await self._run_with_limit(lambda: self._generate_strategy.generate(prompt))

    async def _run_with_limit(self, call: Callable[[], Awaitable[Any]]) -> Any:
        if self._semaphore is None:
            return await call()
        await self._semaphore.acquire()
        try:
            return await call()
        finally:
            self._semaphore.release()


class _GlobalSemaphoreRegistry:
    # key: (provider, loop_id) -> semaphore
    _semaphores: dict[tuple[str, int], asyncio.Semaphore] = {}

    @classmethod
    def get_semaphore(cls, provider: str, capacity: int) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        key = (provider, id(loop))
        sem = cls._semaphores.get(key)
        if sem is None or (hasattr(sem, "_value") and sem._value != capacity):  # type: ignore[attr-defined]
            cls._semaphores[key] = asyncio.Semaphore(int(max(1, capacity)))
        return cls._semaphores[key]

 
