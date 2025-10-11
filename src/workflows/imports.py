import logging
from pathlib import Path
from importlib import import_module

logger = logging.getLogger(__name__)


def run_metadata_import(max_records: int | None = None, batch_size: int = 1000) -> int:
    project_root = Path(__file__).resolve().parents[2]
    json_path = str(project_root / "data" / "metadata" / "arxiv-metadata-oai-snapshot.json")
    schema_path = str(project_root / "data" / "metadataschema.json")

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
    db_import = import_module("src.database.import")
    project_root = Path(__file__).resolve().parents[2]
    labels_path = str(project_root / "data" / "labels.json")
    logger.info("🌱 Importing labels/questions start")
    logger.info(f"  - Labels: {labels_path}")
    added = db_import.import_labels_questions(labels_path=labels_path)
    logger.info(f"✅ Import voltooid: {added} items toegevoegd/gededupliceerd")
    return added
