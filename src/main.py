#!/usr/bin/env python3
"""
GitHub Copilot Metastudy - Hoofdworkflow
Uitgebreide pipeline voor paper downloading, conversie en analyse
"""

import logging
import logging.config
import sys
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
        for table in ["metadata", "papers", "labels", "questions", "metadata_labels"]:
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
    for tbl in ["metadata", "papers", "labels", "questions", "metadata_labels"]:
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


def run_labeling(
    question_id: int,
    *,
    limit: int | None = None,
    offset: int = 0,
    batch_size: int = 500,
    db: PaperDatabase | None = None,
    llm: LLMChecker | None = None,
) -> dict:
    """Label alle metadata voor een gegeven question.

    - Bestaande metadata_labels voor dit label worden overgeslagen (resume-vriendelijk).
    - LLM-calls gebeuren sequentieel.
    - Resultaat is een klein statistieken-dict.
    """
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)

    if not isinstance(question_id, int) or question_id <= 0:
        raise ValueError("question_id moet een positief integer zijn")

    database = db or PaperDatabase()
    checker = llm or LLMChecker()

    # 1) Haal vraag + label
    qrow = database.get_question_by_id(question_id)
    if not qrow:
        raise ValueError(f"question_id niet gevonden: {question_id}")
    prompt: str = qrow["prompt"]
    label_id: int = int(qrow["label_id"])  # type: ignore[assignment]

    # 2) Bepaal al-gelabelde metadata_ids voor dit label
    already_labeled_ids = set(database.get_metadata_ids_by_label(label_id))

    logger.info(
        "🔖 Start labeling: question_id=%s, label_id=%s, limit=%s, offset=%s, batch_size=%s",
        question_id,
        label_id,
        limit,
        offset,
        batch_size,
    )

    stats = {
        "question_id": question_id,
        "label_id": label_id,
        "processed": 0,
        "skipped_existing": 0,
        "labeled": 0,
        "errors": 0,
    }

    # 3) Itereer metadata in batches
    for batch in database.iter_metadata_records(offset=offset, limit=limit, batch_size=batch_size):
        logger.info("Batch ontvangen: %s records", len(batch))
        for record in batch:
            metadata_id = record.get("id")
            if not metadata_id:
                continue
            if metadata_id in already_labeled_ids:
                stats["skipped_existing"] += 1
                continue

            try:
                mdl = checker.classify_record_to_metadata_label(
                    question=prompt, metadata_record=record, label_id=label_id
                )
                stats["processed"] += 1
                if not bool(mdl.get("_applicable")):
                    continue
                confidence = mdl.get("confidence_score")
                database.upsert_metadata_label(
                    metadata_id=metadata_id, label_id=label_id, confidence_score=confidence
                )
                stats["labeled"] += 1
            except Exception as exc:
                logger.warning("Labeling fout voor %s: %s", metadata_id, exc)
                stats["errors"] += 1

    logger.info(
        "✅ Labeling klaar: processed=%s, labeled=%s, skipped_existing=%s, errors=%s",
        stats["processed"],
        stats["labeled"],
        stats["skipped_existing"],
        stats["errors"],
    )
    return stats


def list_questions() -> list[str]:
    """Retourneer leesbare regels: "id: <id>, name: <name>, label: <label_name>"""
    logging.config.dictConfig(LOGGING_CONFIG)
    db = PaperDatabase()
    rows = db.list_questions()
    return [f"id: {r['id']}, name: {r['name']}, label: {r['label_name']}" for r in rows]

def main():
    """Hoofd workflow voor metastudy"""
    # Setup logging first
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)

    logger.info("🚀 GitHub Copilot Metastudy - Pipeline Start")
    logger.info("=" * 70)

    # Eenvoudige CLI-hook voor labeling: python -m src.main label <question_id> [limit] [offset] [batch]
    if len(sys.argv) >= 3 and sys.argv[1] == "label":
        try:
            qid = int(sys.argv[2])
        except Exception:
            raise SystemExit("Gebruik: python -m src.main label <question_id> [limit] [offset] [batch]")
        lim = int(sys.argv[3]) if len(sys.argv) >= 4 and sys.argv[3].isdigit() else None
        off = int(sys.argv[4]) if len(sys.argv) >= 5 and sys.argv[4].isdigit() else 0
        bsz = int(sys.argv[5]) if len(sys.argv) >= 6 and sys.argv[5].isdigit() else 500
        res = run_labeling(qid, limit=lim, offset=off, batch_size=bsz)
        print(res)
        return


if __name__ == "__main__":
    main()
