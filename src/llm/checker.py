"""
LLM Checker voor GitHub Copilot Metastudy
Gebruikt Ollama voor binaire classificatie op basis van titel en abstract.
"""

from datetime import datetime
import json
import logging
from typing import Any, Dict, Optional, Tuple
import re

import ollama
from src.llm.llm_clients import LLMClient

from src.config import LLM_GENERAL_CONFIG, LLM_OLLAMA_CONFIG, LLM_VERTEX_CONFIG


class LLMChecker:
    def __init__(self, llm_client: LLMClient) -> None:
        provider = str(LLM_GENERAL_CONFIG.get("provider", "ollama")).strip().lower()
        if provider == "vertex":
            self.model_name = LLM_VERTEX_CONFIG.get("model_name", "gemini-2.5-flash")
        else:
            self.model_name = LLM_OLLAMA_CONFIG.get("model_name", "llama3:8b-instruct")
        self.logger = logging.getLogger(__name__)
        # Reuse a single AsyncClient instance voor gekozen provider
        provider = str(LLM_GENERAL_CONFIG.get("provider", "ollama")).strip().lower()
        self.async_client = llm_client
        self.logger.info(f"LLM Checker initialized: provider={provider}, model={self.model_name}")

    def _build_messages(self, question: str, title: str, abstract: str) -> list[dict]:
        system_msg = (
            "You are an extremely strict and efficient binary classification agent. "
            "Your task is to analyze the provided TEXT to answer the given QUESTION. "
            "You **MUST** respond in strict JSON format. "
            "No extra text, explanation, introduction, or markdown is allowed. "
            'The JSON schema is: {"answer": true|false, "confidence": number}. '
            "The 'confidence' must be a floating-point number between 0.00 and 1.00, "
            "reflecting the certainty of your 'answer'. "
            "**Respond directly and ONLY with the JSON output.**"
        )
        user_msg = f"QUESTION: {question}\n\nTITLE: {title}\n\nABSTRACT: {abstract}"
        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

    async def _chat_async(self, messages: list[dict]) -> str:
        if self.async_client is None:
            raise RuntimeError("AsyncClient is niet geïnitialiseerd")
        response = await self.async_client.chat(messages=messages)
        return ((response or {}).get("message") or {}).get("content", "").strip()

    def _strip_code_fences(self, text: str) -> str:
        if not text:
            return text
        s = text.strip()
        # Match ```json\n...\n``` of ```\n...\n```
        m = re.match(r"^```[a-zA-Z0-9]*\s*\n([\s\S]*?)\n```\s*$", s)
        if m:
            return m.group(1).strip()
        return s

    def _parse_structured(self, text: str) -> Tuple[Optional[bool], Optional[float]]:
        """Parseer JSON met velden {answer: bool|str, confidence: number}.

        Retourneert (answer_bool|None, confidence|None) waarbij confidence in [0,1] is geschaald.
        """
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                ans_val = self._coerce_answer_bool(obj.get("answer"))
                conf_val = self._coerce_confidence(obj.get("confidence"))
                return ans_val, conf_val
        except Exception:
            return None, None

    def _coerce_answer_bool(self, value: Any) -> Optional[bool]:
        if isinstance(value, bool):
            return bool(value)
        if isinstance(value, str):
            low = value.strip().lower()
            if low in ("true", "yes"):
                return True
            if low in ("false", "no"):
                return False
        return None

    def _coerce_confidence(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            conf = float(value)
        except Exception:
            return None
        if conf > 1.0 and conf <= 100.0:
            conf = conf / 100.0
        conf = max(0.0, min(1.0, conf))
        return conf

    def _default_structured(self) -> Dict[str, object]:
        return {"answer_value": None, "confidence_score": None}

    # Sync classificatie verwijderd; gebruik uitsluitend async
    async def classify_title_abstract_structured_async(
        self, question: str, title: str, abstract: str
    ) -> Dict[str, object]:
        """Async variant van classify_title_abstract_structured."""
        result = self._default_structured()

        if not title or not abstract or not question:
            self.logger.warning(
                "Missing question/title/abstract; returning default structured result"
            )
            result["answer_value"] = False
            return result

        try:
            messages = self._build_messages(question=question, title=title, abstract=abstract)
            content = await self._chat_async(messages)
            sanitized = self._strip_code_fences(content)
            ans, conf = self._parse_structured(sanitized)
            if ans is None:
                self.logger.warning("Unclear LLM response (async); defaulting answer to False")
                ans = False
            result["answer_value"] = bool(ans)
            result["confidence_score"] = conf
            return result
        except Exception as exc:
            self.logger.error("LLM async classification failed: %s", exc)
            result["answer_value"] = False
            return result
