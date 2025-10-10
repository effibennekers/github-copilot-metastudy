"""
LLM Checker voor GitHub Copilot Metastudy
Gebruikt Ollama voor binaire classificatie op basis van titel en abstract.
"""

import json
import ollama
import logging
from typing import Optional, Tuple, Dict, Any  # noqa: F401
from datetime import datetime

# Import configuratie
from src.config import LLM_CONFIG


class LLMChecker:
    def __init__(self):
        self.config = LLM_CONFIG
        self.ollama_url = self.config.get("ollama_api_base_url", "http://localhost:11434")
        self.model_name = self.config.get("model_name", "llama3:8b-instruct")
        self.logger = logging.getLogger(__name__)

        # Check if LLM is enabled
        if not self.config.get("enabled", False):
            self.logger.info("LLM checker is disabled in configuration")
        else:
            self.logger.info(
                f"LLM Checker initialized: {self.ollama_url} with model {self.model_name}"
            )

    def is_enabled(self) -> bool:
        """Check if LLM functionality is enabled"""
        return self.config.get("enabled", False)

    def _build_messages(self, question: str, title: str, abstract: str) -> list[dict]:
        system_msg = (
            "You are an extremely strict and efficient binary classification agent. "
            "Your task is to analyze the provided TEXT to answer the given QUESTION. "
            "You **MUST** respond in strict JSON format. "
            "No extra text, explanation, introduction, or markdown is allowed. "
            "The JSON schema is: {\"answer\": true|false, \"confidence\": number}. "
            "The 'confidence' must be a floating-point number between 0.00 and 1.00, "
            "reflecting the certainty of your 'answer'. "
            "**Respond directly and ONLY with the JSON output.**"
        )
        user_msg = f"QUESTION: {question}\n\nTITLE: {title}\n\nABSTRACT: {abstract}"
        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

    # Sync chat verwijderd; gebruik uitsluitend _chat_async

    async def _chat_async(self, messages: list[dict]) -> str:
        client = ollama.AsyncClient(host=self.ollama_url)
        response = await client.chat(
            model=self.model_name,
            messages=messages,
            options={
                "temperature": self.config.get("temperature", 0.1),
                "num_predict": self.config.get("num_predict", 64),
                "format": self.config.get("format", "json"),
                "top_p": self.config.get("top_p", 0.9),
                "top_k": self.config.get("top_k", 40),
            },
        )
        return ((response or {}).get("message") or {}).get("content", "").strip()

    def _parse_answer(self, text: str) -> Optional[bool]:
        # Probeer strikt JSON met veld 'answer' te lezen
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return self._coerce_answer_bool(obj.get("answer"))
        except Exception:
            pass
        # Fallback: herken losse of ingesloten true/false patronen
        embedded = self._contains_true_false(text)
        if embedded is not None:
            return embedded
        # Laatste poging: direct coerce van gehele string
        return self._coerce_answer_bool(text)

    def _parse_structured(self, text: str) -> Tuple[Optional[bool], Optional[float]]:
        """Parseer JSON met velden {answer: bool|str, confidence: number}.

        Retourneert (answer_bool|None, confidence|None) waarbij confidence in [0,1] is geschaald.
        """
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                ans_val = self._coerce_answer_bool(obj.get("answer"))
                conf_val = self._coerce_confidence(
                    obj.get("confidence") if "confidence" in obj else obj.get("confidence_score")
                )
                return ans_val, conf_val
        except Exception:
            pass

        # Fallback op enkel answer parsing
        return self._parse_answer(text), None

    # ============================
    # DRY helpers
    # ============================

    def _coerce_answer_bool(self, value: Any) -> Optional[bool]:
        if isinstance(value, bool):
            return bool(value)
        if isinstance(value, str):
            low = value.strip().lower()
            if low in ("true", "yes", "ja"):  # taal-agnostisch
                return True
            if low in ("false", "no", "nee"):
                return False
        return None

    def _contains_true_false(self, text: str) -> Optional[bool]:
        low = (text or "").strip().lower()
        if '"answer": true' in low or "\ntrue\n" in low or low == "true":
            return True
        if '"answer": false' in low or "\nfalse\n" in low or low == "false":
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
        return {"answer_value": None, "confidence_score": None, "llm_model": self.model_name}

    def _extract_title_abstract(self, metadata_record: dict) -> Tuple[str, str]:
        title = (metadata_record or {}).get("title") or ""
        abstract = (metadata_record or {}).get("abstract") or ""
        return title, abstract

    # Sync classificatie verwijderd; gebruik uitsluitend async variant

    async def classify_title_abstract_structured_async(
        self, question: str, title: str, abstract: str
    ) -> Dict[str, object]:
        """Async variant van classify_title_abstract_structured."""
        result = self._default_structured()
        if not self.is_enabled():
            self.logger.info("LLM checker disabled; returning default structured result")
            result["answer_value"] = False
            return result

        if not title or not abstract or not question:
            self.logger.warning(
                "Missing question/title/abstract; returning default structured result"
            )
            result["answer_value"] = False
            return result

        try:
            messages = self._build_messages(question=question, title=title, abstract=abstract)
            self.logger.info(messages)
            content = await self._chat_async(messages)
            ans, conf = self._parse_structured(content)
            self.logger.info("Answer: %s, Confidence: %s", ans, conf)
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

    # Sync convenience verwijderd

    # Sync convenience verwijderd

    # Sync convenience verwijderd

    # =====================================
    # metadata_labels record helpers (DB schema)
    # =====================================

    # Sync helper verwijderd

    # Sync helper verwijderd
