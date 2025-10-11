import logging
import os
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
            else:
                tarball_path = client.download_paper_source(
                    arxiv_id=arxiv_id, dirpath=str(tarball_dir)
                )

            # 2) Extract tarball naar data/tarball/extracted/<arxiv_id>/
            extracted_base = tarball_dir / "extracted"
            extracted_dir = extracted_base / arxiv_id
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

            # 3) Zoek grootste .tex file en kopieer naar data/tex/<arxiv_id>.tex
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
                dest = tex_out_dir / f"{arxiv_id}.tex"
                shutil.copy2(str(largest_tex), str(dest))
                logger.info("📄 Extracted main TEX: %s -> %s", largest_tex, dest)
            else:
                logger.warning("⚠️  Geen .tex-bestanden gevonden na extractie voor %s", arxiv_id)

            # 4) Opruimen: verwijder uitgepakte directory (tarball blijft staan)
            try:
                shutil.rmtree(extracted_dir)
                logger.info("🧹 Removed extracted directory: %s", extracted_dir)
            except Exception as cleanup_err:  # pragma: no cover
                logger.warning("Kon extracted directory niet verwijderen (%s): %s", extracted_dir, cleanup_err)

            # 5) Markeer als completed
            db.set_download_status(arxiv_id, "COMPLETED")
            stats["completed"] += 1
            logger.info("✅ Download COMPLETED: %s", arxiv_id)
        except Exception as e:  # pragma: no cover
            logger.error("❌ Download FAILED: %s (%s)", arxiv_id, e)
            try:
                db.set_download_status(arxiv_id, "FAILED")
            except Exception:
                logger.exception("Kon status niet bijwerken voor %s", arxiv_id)
            stats["failed"] += 1

    return stats


