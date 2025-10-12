import asyncio
import logging
import time

from src.database import PaperDatabase
from src.llm import LLMChecker
from src.llm.llm_clients import LLMClient


async def _run_labeling_async(labeling_jobs: int = 10) -> dict:
    logger = logging.getLogger(__name__)
    database = PaperDatabase()

    stats = {"processed": 0, "labeled": 0, "skipped_missing": 0, "errors": 0}
    start_ts = time.perf_counter()

    logger.info(
        "🔖 Start labeling vanuit labeling_queue (rij-voor-rij), max jobs=%s", labeling_jobs
    )

    # Jobs worden downstream non-blocking opgehaald en verrijkt

    async with LLMClient() as llm_client:
        checker = LLMChecker(llm_client)

        # Producer: haal jobs uit de queue en verrijk ze non-blocking
        async def fetch_jobs_from_queue(limit: int) -> list[dict]:
            fetched: list[dict] = []
            for _ in range(int(limit)):
                job = await asyncio.to_thread(database.pop_next_labeling_job)
                if not job:
                    break
                fetched.append(job)
            return fetched

        async def enrich_stream(jobs_input: list[dict]):

            async def _enrich(j: dict):
                metadata_id = j.get("metadata_id")
                question_id = j.get("question_id")
                if not metadata_id or not isinstance(question_id, int):
                    stats["skipped_missing"] += 1
                    return None
                qrow = await asyncio.to_thread(database.get_question_by_id, int(question_id))
                if not qrow:
                    stats["skipped_missing"] += 1
                    return None
                ta = await asyncio.to_thread(database.get_title_and_abstract, str(metadata_id))
                if not ta:
                    stats["skipped_missing"] += 1
                    return None
                return {
                    "metadata_id": metadata_id,
                    "question_id": question_id,
                    "label_id": int(qrow["label_id"]),
                    "prompt": qrow["prompt"],
                    "title": ta["title"],
                    "abstract": ta["abstract"],
                }

            tasks = [asyncio.create_task(_enrich(j)) for j in jobs_input]
            for fut in asyncio.as_completed(tasks):
                res = await fut
                if res:
                    yield res

        # Consumer: classificeer verrijkte jobs en verwerk direct resultaten
        enriched_queue: asyncio.Queue = asyncio.Queue()

        async def producer():
            raw_jobs = await fetch_jobs_from_queue(labeling_jobs)
            async for ej in enrich_stream(raw_jobs):
                await enriched_queue.put(ej)
            await enriched_queue.put(None)  # sentinel

        async def consumer():
            classify_tasks: set[asyncio.Task] = set()

            async def classify_and_handle(j: dict):
                try:
                    structured = await checker.classify_title_abstract_structured_async(
                        question=j["prompt"], title=j["title"], abstract=j["abstract"]
                    )
                    error = None
                except Exception as e:  # pragma: no cover
                    structured, error = None, str(e)

                if error or not isinstance(structured, dict):
                    stats["errors"] += 1
                    return

                stats["processed"] += 1
                counter = f"{stats['processed']:03d}"
                if not bool(structured.get("answer_value")):
                    logging.getLogger(__name__).info("%s ❌ %s", counter, j["title"])
                    return

                confidence = structured.get("confidence_score")
                await asyncio.to_thread(
                    database.upsert_metadata_label,
                    j["metadata_id"],
                    j["label_id"],
                    confidence,
                )
                stats["labeled"] += 1
                logging.getLogger(__name__).info("%s ✅ %s", counter, j["title"])

            while True:
                item = await enriched_queue.get()
                if item is None:
                    break
                t = asyncio.create_task(classify_and_handle(item))
                classify_tasks.add(t)
                t.add_done_callback(lambda _t: classify_tasks.discard(_t))

            if classify_tasks:
                await asyncio.gather(*classify_tasks)

        await asyncio.gather(producer(), consumer())

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
