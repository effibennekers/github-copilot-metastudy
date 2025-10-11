from typing import Optional, Any
import asyncio
import ollama
from google.genai import Client as VertexClient
from google.genai import types as genai_types

from src.config import LLM_GENERAL_CONFIG, LLM_OLLAMA_CONFIG, LLM_VERTEX_CONFIG


def get_vertex_genai_sync_client() -> VertexClient:
    """Maakt de synchrone (niet-gesloten) VertexClient aan."""
    project_id = LLM_VERTEX_CONFIG.get("project", "bennekers")
    location = LLM_VERTEX_CONFIG.get("location", "europe-west4")
    api_version = LLM_VERTEX_CONFIG.get("api_version")

    http_options = genai_types.HttpOptions(api_version=api_version) if api_version else None

    client_kwargs = {"vertexai": True, "project": project_id, "location": location}
    if http_options is not None:
        client_kwargs["http_options"] = http_options

    # Retourneer de synchrone client. De .aio (async) interface wordt later gesloten.
    return VertexClient(**client_kwargs)


def get_ollama_async_client() -> Optional[ollama.AsyncClient]:
    host = LLM_OLLAMA_CONFIG.get("api_base_url", "http://localhost:11434")
    try:
        return ollama.AsyncClient(host=host)
    except Exception:
        return None


def get_vertex_genai_async_client() -> Any:
    project_id = LLM_VERTEX_CONFIG.get("project", "bennekers")
    location = LLM_VERTEX_CONFIG.get("location", "europe-west4")
    api_version = LLM_VERTEX_CONFIG.get("api_version")
    http_options = genai_types.HttpOptions(api_version=api_version) if api_version else None
    client_kwargs = {"vertexai": True, "project": project_id, "location": location}
    if http_options is not None:
        client_kwargs["http_options"] = http_options
    client = VertexClient(**client_kwargs)
    return client.aio


class LLMChatClient:
    """Uniforme chat-client (Strategy Pattern) die als async context manager fungeert."""

    def __init__(self) -> None:
        self._provider = str(LLM_GENERAL_CONFIG.get("provider", "ollama")).strip().lower()
        self._client: Optional[Any] = (
            None  # De concrete client (VertexClient of ollama.AsyncClient)
        )
        self._strategy: Optional[Any] = None

    async def __aenter__(self) -> "LLMChatClient":
        """Initialiseert de client en strategie asynchroon. Zorgt voor robuuste client creatie."""
        if self._provider == "vertex":
            try:
                # 1. Maak de synchrone client aan
                self._client = get_vertex_genai_sync_client()
                # 2. Gebruik de .aio interface in de strategie
                self._strategy = _VertexChatStrategy(self._client.aio)
            except Exception as e:
                # Vang fouten op bij client creatie (bijv. config fouten)
                raise RuntimeError(f"Vertex AI Client kon niet worden geïnitialiseerd: {e}")

        else:  # ollama
            host = LLM_OLLAMA_CONFIG.get("api_base_url", "http://localhost:11434")
            try:
                # 1. Maak de Ollama client aan
                self._client = ollama.AsyncClient(host=host)
                # 2. (Optioneel, maar goed gebruik) Vraag de client om zijn aenter uit te voeren
                # if hasattr(self._client, '__aenter__'):
                #     await self._client.__aenter__() # Ollama's client heeft dit niet expliciet nodig maar kan geen kwaad

                self._strategy = _OllamaChatStrategy(self._client)
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
        if self._strategy is None:
            # Zorgt ervoor dat de client altijd met 'async with' moet worden gebruikt
            raise RuntimeError(
                "LLMChatClient moet worden gebruikt met 'async with' om te initialiseren"
            )
        return await self._strategy.chat(messages)


class _OllamaChatStrategy:
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


class _VertexChatStrategy:
    def __init__(self, aclient: Any) -> None:
        self._aclient = aclient
        self.model = LLM_VERTEX_CONFIG.get("model_name", "gemini-2.5-flash")
        self.config = genai_types.GenerateContentConfig(
            temperature=LLM_VERTEX_CONFIG.get("temperature"),
            top_p=LLM_VERTEX_CONFIG.get("top_p"),
            top_k=LLM_VERTEX_CONFIG.get("top_k"),
            max_output_tokens=LLM_VERTEX_CONFIG.get("max_output_tokens"),
        )

    async def chat(self, messages: list[dict]) -> dict:
        system_instructions = []
        final_messages = []

        # 1. Voorverwerking van de berichten om de 'system' rol te verwijderen
        for m in messages:
            role = m.get('role', 'user').strip().lower()
            content = m.get('content', '')
            
            if role == 'system':
                # Verzamel alle system instructies
                system_instructions.append(content)
            elif role in ('user', 'model'):
                # Accepteer geldige rollen
                final_messages.append(m)
            # Negeer andere ongeldige rollen

        # 2. Voeg de system instructies toe aan het eerste 'user' bericht
        if system_instructions:
            full_system_prompt = "\n\n".join(system_instructions) + "\n\n"
            
            # Zoek het eerste 'user' bericht om de instructies aan toe te voegen
            if final_messages and final_messages[0]['role'] == 'user':
                final_messages[0]['content'] = full_system_prompt + final_messages[0]['content']
            elif final_messages:
                 # Als de conversatie begint met 'model' (ongebruikelijk), voeg dan de system instructie als eerste 'user' toe
                 final_messages.insert(0, {'role': 'user', 'content': full_system_prompt})
            else:
                 # Als er alleen system berichten waren, maak een user message aan
                 final_messages.append({'role': 'user', 'content': full_system_prompt})


        # 3. Bouw de officiële Contents lijst (alleen 'user' en 'model' rollen)
        contents_list = [
            genai_types.Content(
                role=m['role'],
                parts=[genai_types.Part(text=m['content'])]
            )
            for m in final_messages
        ]
        response = await self._aclient.models.generate_content(
            model=self.model,
            contents=contents_list,
            config=self.config,
        )
        text = getattr(response, "text", None) or getattr(response, "output_text", None)
        if text is None:
            text = ""
        return {"message": {"content": str(text)}}
