"""PDF -> Markdown conversie met pdfplumber."""

import logging
from pathlib import Path
import pdfplumber

logger = logging.getLogger(__name__)


def pdf_naar_md(arxiv_id: str) -> str:
    pdf_dir = Path("data") / "pdf"
    md_dir = Path("data") / "md"
    md_dir.mkdir(parents=True, exist_ok=True)

    input_path = pdf_dir / f"{arxiv_id}.pdf"
    output_path = md_dir / f"{arxiv_id}.md"

    if not input_path.exists():
        raise FileNotFoundError(f"PDF bronbestand niet gevonden: {input_path}")

    logger.info("Converteer PDF naar MD: %s -> %s", input_path, output_path)
    parts: list[str] = []
    with pdfplumber.open(str(input_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            txt = page.extract_text() or ""
            if txt:
                parts.append(txt.strip())
            else:
                logger.debug("Lege/ongeparseerde pagina: %s (%s)", page_num, input_path)

    content = "\n\n".join(parts).strip()
    output_path.write_text(content, encoding="utf-8")
    return str(output_path)
