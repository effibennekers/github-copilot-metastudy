from typing import Any
from google.genai import Client as VertexClient
from google.genai import types as genai_types

from src.config import LLM_VERTEX_CONFIG


def get_vertex_genai_sync_client() -> VertexClient:
    project_id = LLM_VERTEX_CONFIG.get("project", "bennekers")
    location = LLM_VERTEX_CONFIG.get("location", "europe-west4")
    api_version = LLM_VERTEX_CONFIG.get("api_version")
    http_options = genai_types.HttpOptions(api_version=api_version) if api_version else None
    client_kwargs = {"vertexai": True, "project": project_id, "location": location}
    if http_options is not None:
        client_kwargs["http_options"] = http_options
    return VertexClient(**client_kwargs)


class VertexChatStrategy:
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
        for m in messages:
            role = m.get("role", "user").strip().lower()
            content = m.get("content", "")
            if role == "system":
                system_instructions.append(content)
            elif role in ("user", "model"):
                final_messages.append(m)

        if system_instructions:
            full_system_prompt = "\n\n".join(system_instructions) + "\n\n"
            if final_messages and final_messages[0]["role"] == "user":
                final_messages[0]["content"] = full_system_prompt + final_messages[0]["content"]
            elif final_messages:
                final_messages.insert(0, {"role": "user", "content": full_system_prompt})
            else:
                final_messages.append({"role": "user", "content": full_system_prompt})

        contents_list = [
            genai_types.Content(role=m["role"], parts=[genai_types.Part(text=m["content"])])
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


class VertexGenerateStrategy:
    def __init__(self, aclient: Any) -> None:
        self._aclient = aclient
        self.model = LLM_VERTEX_CONFIG.get("model_name", "gemini-2.5-flash")
        self.config = genai_types.GenerateContentConfig(
            temperature=LLM_VERTEX_CONFIG.get("temperature"),
            top_p=LLM_VERTEX_CONFIG.get("top_p"),
            top_k=LLM_VERTEX_CONFIG.get("top_k"),
            max_output_tokens=LLM_VERTEX_CONFIG.get("max_output_tokens"),
        )

    async def generate(self, prompt: str) -> dict:
        contents_list = [
            genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=prompt)],
            )
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
