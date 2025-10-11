import asyncio
import logging
import time

from src.database import PaperDatabase
from src.llm import LLMChecker
from src.llm.llm_clients import LLMChatClient
from src.config import LLM_GENERAL_CONFIG


async def _run_labeling_async(labeling_jobs: int = 10) -> dict:
    logger = logging.getLogger(__name__)
    database = PaperDatabase()

    stats = {"processed": 0, "labeled": 0, "skipped_missing": 0, "errors": 0}
    start_ts = time.perf_counter()

    logger.info(
        "🔖 Start labeling vanuit labeling_queue (rij-voor-rij), max jobs=%s", labeling_jobs
    )

    jobs: list[dict] = []
    for _ in range(int(labeling_jobs)):
        job = database.pop_next_labeling_job()
        if not job:
            break
        metadata_id = job.get("metadata_id")
        question_id = job.get("question_id")
        if not metadata_id or not isinstance(question_id, int):
            stats["skipped_missing"] += 1
            continue
        qrow = database.get_question_by_id(int(question_id))
        if not qrow:
            stats["skipped_missing"] += 1
            continue
        prompt: str = qrow["prompt"]
        label_id: int = int(qrow["label_id"])  # type: ignore[assignment]
        ta = database.get_title_and_abstract(str(metadata_id))
        if not ta:
            stats["skipped_missing"] += 1
            continue
        jobs.append(
            {
                "metadata_id": metadata_id,
                "question_id": question_id,
                "label_id": label_id,
                "prompt": prompt,
                "title": ta["title"],
                "abstract": ta["abstract"],
            }
        )

    async with LLMChatClient() as llm_client:
        checker = LLMChecker(llm_client)

        async def _classify_all(jobs_input: list[dict]) -> list[dict]:
            sem = asyncio.Semaphore(int(LLM_GENERAL_CONFIG.get("batch_size", 2)))

            async def _one(j: dict) -> dict:
                async with sem:
                    try:
                        structured = await checker.classify_title_abstract_structured_async(
                            question=j["prompt"], title=j["title"], abstract=j["abstract"]
                        )
                        return {"job": j, "structured": structured, "error": None}
                    except Exception as e:  # pragma: no cover
                        return {"job": j, "structured": None, "error": str(e)}

            tasks = [_one(j) for j in jobs_input]
            return await asyncio.gather(*tasks)

        results: list[dict] = await _classify_all(jobs) if jobs else []

    for res in results:
        j = res["job"]
        if res.get("error") or not isinstance(res.get("structured"), dict):
            stats["errors"] += 1
            continue
        structured = res["structured"]
        stats["processed"] += 1
        counter = f"{stats['processed']:03d}"
        if not bool(structured.get("answer_value")):
            logging.getLogger(__name__).info("%s ❌ %s", counter, j["title"])
            continue
        confidence = structured.get("confidence_score")
        database.upsert_metadata_label(
            metadata_id=j["metadata_id"], label_id=j["label_id"], confidence_score=confidence
        )
        stats["labeled"] += 1
        logging.getLogger(__name__).info("%s ✅ %s", counter, j["title"])

    logging.getLogger(__name__).info(
        "✅ Labeling klaar: processed=%s, labeled=%s, skipped_missing=%s, errors=%s",
        stats["processed"],
        stats["labeled"],
        stats["skipped_missing"],
        stats["errors"],
    )
    elapsed = time.perf_counter() - start_ts
    stats["elapsed_seconds"] = round(elapsed, 3)
    logging.getLogger(__name__).info("⏱️  Totale duur: %.3fs", elapsed)
    return stats


def run_labeling(labeling_jobs: int = 10) -> dict:
    return asyncio.run(_run_labeling_async(labeling_jobs))
