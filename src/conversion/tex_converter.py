"""TeX -> Markdown conversie via pre-processing + Pandoc Lua-filter."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def tex_naar_md(arxiv_id: str) -> str:
    tex_dir = Path("data") / "tex"
    md_dir = Path("data") / "md"
    md_dir.mkdir(parents=True, exist_ok=True)

    tex_path = tex_dir / f"{arxiv_id}.tex"
    md_path = md_dir / f"{arxiv_id}.md"

    if not tex_path.exists():
        raise FileNotFoundError(f"TeX bronbestand niet gevonden: {tex_path}")

    cmd = [
        "pandoc",
        "--from=latex",
        "--to=markdown_strict",
        "--wrap=none",
        "--output",
        str(md_path),
        tex_path,
    ]

    try:
        logger.info("Pandoc TeX->MD: %s -> %s", tex_path, md_path)
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            logger.debug("Pandoc stdout: %s", result.stdout)
        if result.stderr:
            logger.debug("Pandoc stderr: %s", result.stderr)
        return str(md_path)
    except FileNotFoundError as e:
        logger.error("Pandoc niet gevonden: %s", e)
        raise
    except subprocess.CalledProcessError as e:
        logger.warning(
            "Pandoc conversie gefaald (exit %s): %s — probeer LLM fallback",
            e.returncode,
            e.stderr,
        )
        # LLM fallback: gebruik de originele TeX-inhoud als input
        try:
            from src.llm.llm_converter import build_markdown_from_latex

            latex_content = tex_path.read_text(encoding="utf-8", errors="ignore")
            md_content = build_markdown_from_latex(latex_content)
            md_path.write_text(md_content, encoding="utf-8")
            logger.info("LLM fallback voltooid voor %s", tex_path)
            return str(md_path)
        except Exception as le:  # pragma: no cover
            logger.error("LLM fallback gefaald: %s", le)
            raise
