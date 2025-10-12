import asyncio
import logging
from typing import List, Iterator
from src.config import LLM_GENERAL_CONFIG, LLM_OLLAMA_CONFIG, LLM_VERTEX_CONFIG

from src.llm.llm_clients import LLMClient

logger = logging.getLogger(__name__)


SYSTEM_INSTRUCTIONS = (
    "You are an expert converter of complex, potentially broken, scientific LaTeX documents into clean, correct Markdown. Your single highest priority is to ensure **ABSOLUTELY ALL TEXTUAL CONTENT IS RETAINED**.\n"
    "Output Rules:\n"
    "1. **Markdown ONLY:** Return only the converted Markdown text. No preamble, explanation, title, or YAML metadata.\n"
    "2. **Math:** Preserve all mathematical formulas **EXACTLY** as they appear in the LaTeX source, enclosed in single dollar signs ($...$) or double dollar signs ($$...$$).\n"
    "3. **Content Rescue:** For unknown or broken LaTeX environments (e.g., \\begin{wrapfigure}, \\lstlisting, or custom macros), **remove the \\begin and \\end tags** but preserve the **CONTENT** as plain text.\n"
    "4. **Structure:** Use standard Markdown headings (#, ##, ###) for section hierarchy, and convert lists and tables to their best, cleanest Markdown equivalent.\n"
    "5. **Content Fusion & Cleanup:** Do not simply delete reviewer comments. You must perform an intelligent merge operation:\n"
    "    a. **INTEGRATE** the content of corrective commands (e.g., \\correction{...}, \\fix{...}) into the main text, overwriting or replacing the previous text if the command suggests a definitive change.\n"
    "    b. **REMOVE** purely editorial, housekeeping, or querying commands (e.g., \\todo{}, \\note{}, \\check{}).\n"
    "    c. Neutralize all other remaining LaTeX commands that do not translate to Markdown or Math.\n"
    "6. **Code Blocks:** Convert code environments or \\lstlisting-like blocks into correct, fenced Markdown code blocks (e.g., ```language ... ```).\n"
)


def _chunk_text(text: str, max_chars: int) -> Iterator[str]:
    if len(text) <= max_chars:
        yield text
        return
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # Probeer netjes op een paragraafgrens te knippen
        cut = text.rfind("\n\n", start, end)
        if cut == -1 or cut <= start + int(max_chars * 0.85):
            cut = end
        yield text[start:cut]
        start = cut


async def build_markdown_from_latex_async(latex: str, *, max_chars_per_chunk: int = 20000) -> str:
    # Bepaal provider-specifieke chunkgrootte uit config indien niet expliciet overschreven
    provider = str(LLM_GENERAL_CONFIG.get("provider", "ollama")).strip().lower()
    if provider == "vertex":
        cfg_val = LLM_VERTEX_CONFIG.get("max_chars_per_chunk")
    else:
        cfg_val = LLM_OLLAMA_CONFIG.get("max_chars_per_chunk")
    if isinstance(cfg_val, int) and cfg_val > 0:
        max_chars_per_chunk = cfg_val
    async with LLMClient() as client:
        tasks = [
            client.generate(f"{SYSTEM_INSTRUCTIONS}\n\n{chunk}")
            for chunk in _chunk_text(latex, max_chars_per_chunk)
        ]
        responses = await asyncio.gather(*tasks)

    parts: List[str] = []
    for resp in responses:
        content = (resp or {}).get("message", {}).get("content", "")
        parts.append(content.strip())
    return "\n\n".join(p for p in parts if p)


def build_markdown_from_latex(latex: str, *, max_chars_per_chunk: int = 20000) -> str:
    # Laat async variant provider-config lezen; geef eventueel een override mee
    return asyncio.run(
        build_markdown_from_latex_async(latex, max_chars_per_chunk=max_chars_per_chunk)
    )
