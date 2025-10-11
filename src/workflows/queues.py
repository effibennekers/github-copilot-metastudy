import logging
from src.database import PaperDatabase

logger = logging.getLogger(__name__)


def run_prepare_metadata_labeling(question_id: int, date_after: str = "2025-09-01") -> int:
    if not isinstance(question_id, int) or question_id <= 0:
        raise ValueError("question_id moet een positief integer zijn")
    db = PaperDatabase()
    logger.info(
        "🔧 prepare_metadata_labeling start: question_id=%s, date_after=%s", question_id, date_after
    )
    enqueued = db.prepare_metadata_labeling(question_id=question_id, date_after=date_after)
    logger.info("✅ labeling_queue gevuld: %s items", enqueued)
    return enqueued


def run_prepare_paper_download(label_id: int) -> int:
    if not isinstance(label_id, int) or label_id <= 0:
        raise ValueError("label_id moet een positief integer zijn")
    db = PaperDatabase()
    logger.info("🔧 prepare_paper_download start: label_id=%s", label_id)
    enqueued = db.prepare_paper_download(label_id=label_id)
    logger.info("✅ download_queue gevuld: %s items", enqueued)
    return enqueued
