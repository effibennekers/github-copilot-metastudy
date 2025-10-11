import logging
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
            client.download_paper_source(arxiv_id=arxiv_id, dirpath=str(tarball_dir))
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


