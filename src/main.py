#!/usr/bin/env python3
"""
GitHub Copilot Metastudy - Hoofdworkflow
Uitgebreide pipeline voor paper downloading, conversie en analyse
"""

import logging
import logging.config
import sys
import asyncio
from pathlib import Path

# Import from package modules
from src.database import PaperDatabase
from src.arxiv_client import ArxivClient
from src.llm import LLMChecker
from src.conversion import pdf_naar_md
from src.config import (
    SEARCH_CONFIG,
    DATABASE_CONFIG,
    STORAGE_CONFIG,
    LOGGING_CONFIG,
    LLM_CONFIG,
    UI_CONFIG,
)
from importlib import import_module


def print_stats():
    """Print database statistieken"""
    db = PaperDatabase()
    # Tabel-aantallen ophalen
    table_counts: dict[str, int] = {}

    with db._connect() as conn:
        cur = conn.cursor()
        for table in ["metadata", "papers", "labels", "questions", "metadata_labels", "labeling_queue"]:
            try:
                cur.execute(f"SELECT COUNT(1) AS count FROM {table}")
                row = cur.fetchone()
                table_counts[table] = row["count"] if row else 0
            except Exception:
                table_counts[table] = 0

    print("\n" + "=" * 60)
    print("DATABASE STATISTIEKEN")
    print("=" * 60)
    print("Tabellen (aantal rijen):")
    for tbl in ["metadata", "papers", "labels", "questions", "metadata_labels", "labeling_queue"]:
        print(f"  {tbl}: {table_counts.get(tbl, 0)}")


def run_metadata_import(
    max_records: int | None = None,
    batch_size: int = 1000,
) -> int:
    """Importeer metadata JSON in de database na validatie tegen het schema.

    Default paden:
    - data/metadata/arxiv-metadata-oai-snapshot.json
    - data/metadataschema.json
    """
    # Zorg dat logging is geconfigureerd
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)

    project_root = Path(__file__).resolve().parent.parent
    json_path = str(Path(project_root / "data" / "metadata" / "arxiv-metadata-oai-snapshot.json"))
    schema_path = str(Path(project_root / "data" / "metadataschema.json"))

    # Gebruik importlib om module met naam 'import' te laden
    db_import = import_module("src.database.import")

    logger.info("📥 Metadata import start")
    logger.info(f"  - JSON: {json_path}")
    logger.info(f"  - Schema: {schema_path}")

    count = db_import.import_metadata(
        json_path=json_path, schema_path=schema_path, max_records=max_records, batch_size=batch_size
    )
    logger.info(f"✅ Metadata import voltooid: {count} records toegevoegd")
    return count


def run_paper_preparation(batch_size: int | None = None, limit: int | None = None) -> int:
    """Maak paper records aan op basis van bestaande metadata records.

    Roept `prepare_paper_from_metadata` aan uit `src.database.import`.
    """
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)

    db_import = import_module("src.database.import")

    kwargs = {}
    if batch_size is not None:
        kwargs["batch_size"] = int(batch_size)
    if limit is not None:
        kwargs["limit"] = int(limit)

    logger.info("🧩 Paper preparation from metadata start")
    created = db_import.prepare_paper_from_metadata(**kwargs)
    logger.info("✅ Paper preparation voltooid: %s records aangemaakt", created)
    return created


def import_labels_questions() -> int:
    """Seed labels en questions vanuit data/labels.json."""
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)

    db_import = import_module("src.database.import")
    project_root = Path(__file__).resolve().parent.parent
    labels_path = str(Path(project_root / "data" / "labels.json"))

    logger.info("🌱 Importing labels/questions start")
    logger.info(f"  - Labels: {labels_path}")

    added = db_import.import_labels_questions(labels_path=labels_path)
    logger.info(f"✅ Import voltooid: {added} items toegevoegd/gededupliceerd")
    return added


def run_labeling(labeling_jobs: int = 10) -> dict:
    """Verwerk labeling jobs rij-voor-rij vanuit labeling_queue.

    - Geen parameters nodig; neemt volgende job uit de queue totdat leeg.
    - LLM-calls zijn sequentieel per rij.
    - Retourneert een statistieken-dict.
    """
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)

    database = PaperDatabase()
    checker = LLMChecker()

    stats = {
        "processed": 0,
        "labeled": 0,
        "skipped_missing": 0,
        "errors": 0,
    }

    logger.info(
        "🔖 Start labeling vanuit labeling_queue (rij-voor-rij), max jobs=%s",
        labeling_jobs,
    )

    # Verzamel tot 'labeling_jobs' items uit de queue en bereid inputs voor
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

    # Run LLM-calls async met bounded concurrency
    async def _classify_all(jobs_input: list[dict]) -> list[dict]:
        sem = asyncio.Semaphore(int(LLM_CONFIG.get("batch_size", 2)))

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

    results: list[dict] = asyncio.run(_classify_all(jobs)) if jobs else []

    # Verwerk resultaten sequentieel (DB upserts)
    for res in results:
        j = res["job"]
        if res.get("error") or not isinstance(res.get("structured"), dict):
            stats["errors"] += 1
            continue
        structured = res["structured"]
        stats["processed"] += 1
        counter = f"{stats['processed']:03d}"
        if not bool(structured.get("answer_value")):
            logger.info("%s ❌ %s", counter, j["title"])
            continue
        confidence = structured.get("confidence_score")
        database.upsert_metadata_label(
            metadata_id=j["metadata_id"], label_id=j["label_id"], confidence_score=confidence
        )
        stats["labeled"] += 1
        logger.info("%s ✅ %s", counter, j["title"]) 

    logger.info(
        "✅ Labeling klaar: processed=%s, labeled=%s, skipped_missing=%s, errors=%s",
        stats["processed"],
        stats["labeled"],
        stats["skipped_missing"],
        stats["errors"],
    )


def list_questions() -> list[str]:
    """Retourneer leesbare regels: "id: <id>, name: <name>, label: <label_name>"""
    logging.config.dictConfig(LOGGING_CONFIG)
    db = PaperDatabase()
    rows = db.list_questions()
    return [f"id: {r['id']}, name: {r['name']}, label: {r['label_name']}" for r in rows]


def run_prepare_metadata_labeling(question_id: int, date_after: str = "2025-09-01") -> int:
    """Vul labeling_queue met (metadata_id, question_id) voor metadata na date_after."""
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)
    if not isinstance(question_id, int) or question_id <= 0:
        raise ValueError("question_id moet een positief integer zijn")
    db = PaperDatabase()
    logger.info(
        "🔧 prepare_metadata_labeling start: question_id=%s, date_after=%s",
        question_id,
        date_after,
    )
    enqueued = db.prepare_metadata_labeling(question_id=question_id, date_after=date_after)
    logger.info("✅ labeling_queue gevuld: %s items", enqueued)
    return enqueued

def main():
    """Hoofd workflow voor metastudy"""
    # Setup logging first
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)

    logger.info("🚀 GitHub Copilot Metastudy - Pipeline Start")
    logger.info("=" * 70)

    # Eenvoudige CLI-hook voor labeling vanuit queue: python -m src.main label
    if len(sys.argv) >= 2 and sys.argv[1] == "label":
        res = run_labeling()
        print(res)
        return


if __name__ == "__main__":
    main()
