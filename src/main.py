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
    db = PaperDatabase()
    """Print database statistieken"""
    stats = db.get_statistics()

    if not UI_CONFIG.get("show_statistics", True):
        return

    print("\n" + "=" * 60)
    print("DATABASE STATISTIEKEN")
    print("=" * 60)
    print(f"Totaal papers: {stats['total_papers']}")

    print("\nDownload Status:")
    for status, count in stats.get("download_status", {}).items():
        print(f"  {status}: {count}")

    print("\nLLM Check Status:")
    for status, count in stats.get("llm_status", {}).items():
        print(f"  {status}: {count}")
    print("=" * 60)


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


def run_paper_preparation(
    batch_size: int | None = None, limit: int | None = None, db_path: str | None = None
) -> int:
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
    if db_path is not None:
        kwargs["db_path"] = db_path

    logger.info("🧩 Paper preparation from metadata start")
    created = db_import.prepare_paper_from_metadata(**kwargs)
    logger.info("✅ Paper preparation voltooid: %s records aangemaakt", created)
    return created


def main():
    """Hoofd workflow voor metastudy"""
    # Setup logging first
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)

    logger.info("🚀 GitHub Copilot Metastudy - Pipeline Start")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
