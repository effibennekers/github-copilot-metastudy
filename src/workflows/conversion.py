import logging
from pathlib import Path

from src.conversion.tex_converter import tex_naar_md
from src.conversion.pdf_converter import pdf_naar_md


def convert_to_md() -> dict:
    """Converteer alle beschikbare bronnen naar Markdown.

    - Bronmappen:
      - data/tex/<arxiv_id>.tex
      - data/pdf/<arxiv_id>.pdf
    - Doelmap: data/md/<arxiv_id>.md

    Regels:
    - Sla over als doelbestand al bestaat
    - Verwerk eerst TeX, daarna PDF (PDF wordt overgeslagen als TeX al is geconverteerd)
    """
    logger = logging.getLogger(__name__)

    tex_dir = Path("data") / "tex"
    pdf_dir = Path("data") / "pdf"
    md_dir = Path("data") / "md"
    md_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "tex_found": 0,
        "pdf_found": 0,
        "converted_tex": 0,
        "converted_pdf": 0,
        "skipped_existing": 0,
        "errors": 0,
    }

    produced_ids: set[str] = set()

    # 1) TeX -> MD
    if tex_dir.exists():
        for tex_path in sorted(tex_dir.glob("*.tex")):
            arxiv_id = tex_path.stem
            stats["tex_found"] += 1
            md_path = md_dir / f"{arxiv_id}.md"
            if md_path.exists():
                stats["skipped_existing"] += 1
                produced_ids.add(arxiv_id)
                continue
            try:
                tex_naar_md(arxiv_id)
                produced_ids.add(arxiv_id)
                stats["converted_tex"] += 1
                logger.info("✅ TeX -> MD: %s", arxiv_id)
            except Exception as e:  # pragma: no cover
                stats["errors"] += 1
                logger.error("❌ TeX conversie mislukt voor %s: %s", arxiv_id, e)

    # 2) PDF -> MD (alleen als er nog geen MD is geproduceerd)
    if pdf_dir.exists():
        for pdf_path in sorted(pdf_dir.glob("*.pdf")):
            arxiv_id = pdf_path.stem
            stats["pdf_found"] += 1
            if arxiv_id in produced_ids:
                continue
            md_path = md_dir / f"{arxiv_id}.md"
            if md_path.exists():
                stats["skipped_existing"] += 1
                continue
            try:
                pdf_naar_md(arxiv_id)
                stats["converted_pdf"] += 1
                logger.info("✅ PDF -> MD: %s", arxiv_id)
            except Exception as e:  # pragma: no cover
                stats["errors"] += 1
                logger.error("❌ PDF conversie mislukt voor %s: %s", arxiv_id, e)

    return stats


# pre_process_latex is verplaatst naar src/conversion/pandoc_converter.py
