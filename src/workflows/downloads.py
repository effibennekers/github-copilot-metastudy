import logging
import os
import re
import tarfile
import shutil
from pathlib import Path

from src.config import DOWNLOAD_CONFIG
from src.database import PaperDatabase
from src.arxiv_client import ArxivClient


def run_downloads(limit: int | None = None) -> dict:
    """Verwerk tot 'limit' items uit download_queue en download tarballs.

    - Schrijft naar DOWNLOAD_CONFIG['tarball_directory']
    - Update status naar COMPLETED of FAILED
    """
    logger = logging.getLogger(__name__)
    db = PaperDatabase()
    client = ArxivClient()

    max_items = int(limit) if isinstance(limit, int) and limit > 0 else int(
        DOWNLOAD_CONFIG.get("max_items", 50)
    )
    tarball_dir = Path(DOWNLOAD_CONFIG.get("tarball_directory", "data/tarball"))
    tarball_dir.mkdir(parents=True, exist_ok=True)

    pending_ids = db.get_pending_downloads(max_items)

    stats = {
        "requested": max_items,
        "attempted": 0,
        "completed": 0,
        "failed": 0,
    }

    if not pending_ids:
        logger.info("Geen pending downloads gevonden.")
        return stats

    # Helpers
    def _extract_and_copy_main_tex(tarball_path: str, aid: str) -> None:
        extracted_base = tarball_dir / "extracted"
        extracted_dir = extracted_base / aid
        extracted_dir.mkdir(parents=True, exist_ok=True)

        def _is_within_directory(directory: str, target: str) -> bool:
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
            return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

        def _safe_extract(tar: tarfile.TarFile, path: str) -> None:
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not _is_within_directory(path, member_path):
                    raise Exception("Blocked path traversal in tar file")
            tar.extractall(path)

        with tarfile.open(tarball_path, "r:*") as tf:
            _safe_extract(tf, str(extracted_dir))

        largest_tex: Path | None = None
        largest_size = -1
        for root, _dirs, files in os.walk(extracted_dir):
            for fname in files:
                if fname.lower().endswith(".tex"):
                    fpath = Path(root) / fname
                    try:
                        size = fpath.stat().st_size
                    except Exception:
                        continue
                    if size > largest_size:
                        largest_size = size
                        largest_tex = fpath

        if largest_tex is not None:
            tex_out_dir = Path("data") / "tex"
            tex_out_dir.mkdir(parents=True, exist_ok=True)
            dest = tex_out_dir / f"{aid}.tex"
            shutil.copy2(str(largest_tex), str(dest))
            logger.info("📄 Extracted main TEX: %s -> %s", largest_tex, dest)
        else:
            logger.warning("⚠️  Geen .tex-bestanden gevonden na extractie voor %s", aid)

        # Opruimen uitgepakte content, tarball blijft staan
        try:
            shutil.rmtree(extracted_dir)
            logger.info("🧹 Removed extracted directory: %s", extracted_dir)
        except Exception as cleanup_err:  # pragma: no cover
            logger.warning("Kon extracted directory niet verwijderen (%s): %s", extracted_dir, cleanup_err)

    def _parse_version(aid: str) -> int:
        m = re.search(r"v(\d+)$", aid)
        return int(m.group(1)) if m else 1

    def _prev_version(aid: str) -> str | None:
        m = re.search(r"^(.*)v(\d+)$", aid)
        if not m:
            return None
        base, ver = m.group(1), int(m.group(2))
        if ver <= 1:
            return None
        return f"{base}v{ver-1}"

    # Chain of Responsibility onderdelen
    class Handler:
        def __init__(self, next_handler: "Handler | None" = None):
            self._next = next_handler

        def set_next(self, next_handler: "Handler") -> "Handler":
            self._next = next_handler
            return next_handler

        def handle(self, aid: str) -> bool:
            if self._next:
                return self._next.handle(aid)
            return False

    class TarballHandler(Handler):
        def handle(self, aid: str) -> bool:
            try:
                tarball_path = client.download_paper_source(arxiv_id=aid, dirpath=str(tarball_dir))
                _extract_and_copy_main_tex(tarball_path, aid)
                return True
            except Exception as e:  # pragma: no cover
                logger.info("Tarball download mislukt voor %s: %s", aid, e)
                return super().handle(aid)

    class PdfHandler(Handler):
        def handle(self, aid: str) -> bool:
            try:
                pdf_dir = Path("data") / "pdf"
                pdf_dir.mkdir(parents=True, exist_ok=True)
                _ = client.download_paper_pdf(arxiv_id=aid, dirpath=str(pdf_dir))
                logger.info("📄 PDF downloaded for %s", aid)
                return True
            except Exception as e:  # pragma: no cover
                logger.info("PDF download mislukt voor %s: %s", aid, e)
                return super().handle(aid)

    class PrevVersionTarballHandler(Handler):
        def handle(self, aid: str) -> bool:
            prev = _prev_version(aid)
            if not prev:
                return super().handle(aid)
            try:
                tarball_path = client.download_paper_source(arxiv_id=prev, dirpath=str(tarball_dir))
                _extract_and_copy_main_tex(tarball_path, prev)
                logger.info("✅ Tarball gedownload van eerdere versie %s voor %s", prev, aid)
                return True
            except Exception as e:  # pragma: no cover
                logger.info("Tarball vorige versie mislukt voor %s (%s): %s", aid, prev, e)
                return super().handle(aid)

    class PrevVersionPdfHandler(Handler):
        def handle(self, aid: str) -> bool:
            prev = _prev_version(aid)
            if not prev:
                return super().handle(aid)
            try:
                pdf_dir = Path("data") / "pdf"
                pdf_dir.mkdir(parents=True, exist_ok=True)
                _ = client.download_paper_pdf(arxiv_id=prev, dirpath=str(pdf_dir))
                logger.info("✅ PDF gedownload van eerdere versie %s voor %s", prev, aid)
                return True
            except Exception as e:  # pragma: no cover
                logger.info("PDF vorige versie mislukt voor %s (%s): %s", aid, prev, e)
                return super().handle(aid)

    for arxiv_id in pending_ids:
        stats["attempted"] += 1
        try:
            # 1) Vind bestaande tarball of download indien nodig
            existing = next(
                (p for p in tarball_dir.iterdir() if p.is_file() and p.name.startswith(arxiv_id)),
                None,
            )
            if existing is not None:
                logger.info("📦 Tarball bestaat al voor %s: %s — overslaan en markeren als COMPLETED", arxiv_id, existing)
                db.set_download_status(arxiv_id, "COMPLETED")
                stats["completed"] += 1
                logger.info("✅ Download COMPLETED (reused): %s", arxiv_id)
                continue
            # Chain opbouwen: tarball -> pdf -> prev tarball -> prev pdf
            chain = TarballHandler( PdfHandler( PrevVersionTarballHandler( PrevVersionPdfHandler() ) ) )
            success = chain.handle(arxiv_id)

            if success:
                db.set_download_status(arxiv_id, "COMPLETED")
                stats["completed"] += 1
                logger.info("✅ Download COMPLETED (chain): %s", arxiv_id)
            else:
                raise RuntimeError("Geen downloadvariant geslaagd")
        except Exception as e:  # pragma: no cover
            logger.error("❌ Download FAILED: %s (%s)", arxiv_id, e)
            try:
                db.set_download_status(arxiv_id, "FAILED")
            except Exception:
                logger.exception("Kon status niet bijwerken voor %s", arxiv_id)
            stats["failed"] += 1

    return stats


