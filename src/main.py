#!/usr/bin/env python3
"""
GitHub Copilot Metastudy - Hoofdworkflow
Uitgebreide pipeline voor paper downloading, conversie en analyse
"""

import logging
import logging.config
import sys

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


def print_stats(db: PaperDatabase):
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


def search_and_index_papers(db: PaperDatabase, arxiv_client: ArxivClient, logger):
    """STAP 1: Zoek en indexeer papers"""
    logger.info("=== STAP 1: Papers zoeken en indexeren ===")

    # Haal configuratie op
    search_config = SEARCH_CONFIG
    queries = search_config["queries"]
    max_results_per_query = search_config["max_results_per_query"]
    total_max_papers = search_config["total_max_papers"]

    logger.info(
        "Configuratie: %s zoektermen, max %s per query", len(queries), max_results_per_query
    )
    logger.info(f"Totaal maximum papers: {total_max_papers}")

    total_new_papers = 0

    for i, query in enumerate(queries, 1):
        logger.info("[%s/%s] Zoeken met query: '%s'", i, len(queries), query)

        # Check of we het totaal maximum hebben bereikt
        if total_new_papers >= total_max_papers:
            logger.info(f"Maximum aantal papers bereikt ({total_max_papers}), stoppen met zoeken")
            break

        try:
            # Bereken hoeveel papers we nog kunnen ophalen
            remaining_quota = total_max_papers - total_new_papers
            current_max = min(max_results_per_query, remaining_quota)

            papers = arxiv_client.search_papers(query, max_results=current_max)

            new_papers = 0
            for paper in papers:
                if not db.paper_exists(paper["arxiv_id"]):
                    db.insert_paper(paper)
                    new_papers += 1
                    logger.info(
                        f"Nieuw paper toegevoegd: {paper['arxiv_id']} - {paper['title'][:50]}..."
                    )

                    # Check quota again
                    if total_new_papers + new_papers >= total_max_papers:
                        logger.info(f"Maximum papers quota bereikt tijdens verwerking")
                        break

            logger.info(f"Query '{query}': {new_papers} nieuwe papers toegevoegd")
            total_new_papers += new_papers

        except Exception as e:
            logger.error(f"Error in search query '{query}': {e}")
            continue

    logger.info(f"STAP 1 VOLTOOID: Totaal {total_new_papers} nieuwe papers toegevoegd")
    return total_new_papers


def download_pdfs(db: PaperDatabase, arxiv_client: ArxivClient, logger):
    """STAP 2: Download PDFs"""
    logger.info("=== STAP 2: PDFs downloaden ===")

    pending_downloads = db.get_papers_by_status(download_status="PENDING")

    if not pending_downloads:
        logger.info("Geen PDFs om te downloaden")
        return 0

    logger.info(f"Te downloaden PDFs: {len(pending_downloads)}")

    # Ensure PDF directory exists
    pdf_dir = Path(STORAGE_CONFIG["pdf_directory"])
    pdf_dir.mkdir(parents=True, exist_ok=True)

    downloaded_count = 0
    failed_count = 0

    for i, paper in enumerate(pending_downloads, 1):
        logger.info(f"[{i}/{len(pending_downloads)}] Downloading: {paper['arxiv_id']}")

        try:
            # Use ArXiv client's PDF download functionality
            pdf_filename = f"{paper['arxiv_id']}.pdf"
            pdf_path = arxiv_client.download_paper_pdf(
                paper["arxiv_id"], str(pdf_dir), pdf_filename
            )

            if pdf_path:
                db.update_paper_status(
                    paper["arxiv_id"], download_status="DOWNLOADED", pdf_path=pdf_path
                )
                downloaded_count += 1
                logger.info(f"✅ Download successful: {paper['arxiv_id']}")
            else:
                db.update_paper_status(paper["arxiv_id"], download_status="FAILED")
                failed_count += 1
                logger.error(f"❌ Download failed: {paper['arxiv_id']}")

        except Exception as e:
            logger.error(f"❌ Download error for {paper['arxiv_id']}: {e}")
            db.update_paper_status(paper["arxiv_id"], download_status="FAILED")
            failed_count += 1

    logger.info(f"STAP 2 VOLTOOID: {downloaded_count} downloads successful, {failed_count} failed")
    return downloaded_count


def convert_to_markdown(db: PaperDatabase, logger):
    """STAP 3: Convert naar Markdown"""
    logger.info("=== STAP 3: PDF naar Markdown conversie ===")

    downloaded_papers = db.get_papers_by_status(download_status="DOWNLOADED")

    # Filter papers that don't have markdown yet
    to_convert = [p for p in downloaded_papers if not p["md_path"]]

    if not to_convert:
        logger.info("Geen PDFs om te converteren")
        return 0

    logger.info(f"Te converteren PDFs: {len(to_convert)}")

    # Ensure markdown directory exists
    md_dir = Path(STORAGE_CONFIG["markdown_directory"])
    md_dir.mkdir(parents=True, exist_ok=True)

    converted_count = 0

    for i, paper in enumerate(to_convert, 1):
        logger.info(f"[{i}/{len(to_convert)}] Converting: {paper['arxiv_id']}")

        try:
            # Use conversion module for PDF to Markdown conversion
            md_path = pdf_naar_md(
                pdf_path=paper["pdf_path"],
                paper_id=paper["arxiv_id"],
                output_dir=str(md_dir),
                min_size_bytes=STORAGE_CONFIG["min_markdown_size_bytes"],
            )

            if md_path:
                db.update_paper_status(paper["arxiv_id"], md_path=md_path)
                converted_count += 1
                logger.info(f"✅ Conversion successful: {paper['arxiv_id']}")
            else:
                logger.error(f"❌ Conversion failed: {paper['arxiv_id']}")

        except Exception as e:
            logger.error(f"❌ Conversion error for {paper['arxiv_id']}: {e}")

    logger.info(f"STAP 3 VOLTOOID: {converted_count} conversions successful")
    return converted_count


def llm_quality_check(db: PaperDatabase, llm_checker: LLMChecker, logger) -> int:
    """Stap 4: LLM Kwaliteitscontrole van Markdown bestanden"""
    logger.info("=== STAP 4: LLM Kwaliteitscontrole ===")

    if not llm_checker.is_enabled():
        logger.info("LLM kwaliteitscontrole is uitgeschakeld in configuratie")
        return 0

    # Check Ollama availability
    if not llm_checker.check_ollama_availability():
        logger.warning("Ollama server niet beschikbaar, LLM stap wordt overgeslagen")
        return 0

    # Get papers that need LLM quality check
    papers_to_check = db.get_papers_by_status(download_status="DOWNLOADED", llm_status="PENDING")

    if not papers_to_check:
        logger.info("Geen papers voor LLM kwaliteitscontrole")
        return 0

    logger.info(f"Te controleren papers: {len(papers_to_check)}")

    # Process papers in batches
    batch_size = LLM_CONFIG.get("batch_size", 5)
    batch_delay = LLM_CONFIG.get("batch_delay_seconds", 10)

    processed_count = 0
    fixed_count = 0
    failed_count = 0

    for i in range(0, len(papers_to_check), batch_size):
        batch = papers_to_check[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(papers_to_check) + batch_size - 1) // batch_size

        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} papers)")

        for j, paper in enumerate(batch):
            arxiv_id = paper["arxiv_id"]
            md_path = paper.get("md_path")

            if not md_path or not Path(md_path).exists():
                logger.warning(f"No markdown file found for {arxiv_id}")
                db.update_paper(arxiv_id, {"llm_check_status": "FAILED"})
                failed_count += 1
                continue

            try:
                logger.info(f"[{i+j+1}/{len(papers_to_check)}] LLM check: {arxiv_id}")

                # Read markdown content
                with open(md_path, "r", encoding="utf-8") as f:
                    md_content = f.read()

                # Process with LLM
                improved_content, status = llm_checker.check_and_fix_markdown(md_content, arxiv_id)

                # Save improved version if fixed
                if status == "FIXED":
                    # Create backup first
                    backup_path = Path(md_path).with_suffix(".md.backup")
                    with open(backup_path, "w", encoding="utf-8") as f:
                        f.write(md_content)

                    # Save improved version
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(improved_content)

                    logger.info(f"✅ Improved and saved: {arxiv_id}")
                    fixed_count += 1
                elif status == "CLEAN":
                    logger.info(f"✅ Already clean: {arxiv_id}")
                else:  # FAILED
                    logger.warning(f"❌ LLM check failed: {arxiv_id}")
                    failed_count += 1

                # Update database
                db.update_paper(arxiv_id, {"llm_check_status": status})
                processed_count += 1

            except Exception as e:
                logger.error(f"Error processing {arxiv_id}: {e}")
                db.update_paper(arxiv_id, {"llm_check_status": "FAILED"})
                failed_count += 1

        # Delay between batches (except for the last batch)
        if i + batch_size < len(papers_to_check):
            logger.info("Waiting %ss before next batch...", batch_delay)
            import time

            time.sleep(batch_delay)

    logger.info(f"STAP 4 VOLTOOID: {processed_count} papers processed")
    logger.info(f"  - Fixed: {fixed_count}")
    logger.info(f"  - Clean: {processed_count - fixed_count - failed_count}")
    logger.info(f"  - Failed: {failed_count}")

    return processed_count


def run_metadata_import(
    json_path: str = None,
    schema_path: str = None,
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
    default_json = project_root / "data" / "metadata" / "arxiv-metadata-oai-snapshot.json"
    default_schema = project_root / "data" / "metadataschema.json"

    json_path = str(default_json if json_path is None else Path(json_path))
    schema_path = str(default_schema if schema_path is None else Path(schema_path))

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


def main():
    """Hoofd workflow voor metastudy"""
    # Setup logging first
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)

    logger.info("🚀 GitHub Copilot Metastudy - Pipeline Start")
    logger.info("=" * 70)

    # Log configuratie
    search_config = SEARCH_CONFIG
    logger.info("Configuratie geladen:")
    logger.info(f"  - Zoektermen: {len(search_config['queries'])}")
    logger.info(f"  - Max per query: {search_config['max_results_per_query']}")
    logger.info(f"  - Totaal max: {search_config['total_max_papers']}")
    logger.info(
        f"  - Database: postgresql://{DATABASE_CONFIG['pg']['user']}@{DATABASE_CONFIG['pg']['host']}:{DATABASE_CONFIG['pg']['port']}/{DATABASE_CONFIG['pg']['dbname']}"
    )
    logger.info(f"  - PDF directory: {STORAGE_CONFIG['pdf_directory']}")
    logger.info(f"  - Markdown directory: {STORAGE_CONFIG['markdown_directory']}")

    try:
        # Initialize components met configuratie
        logger.info("Initializing components...")
        db = PaperDatabase()
        arxiv_client = ArxivClient()
        llm_checker = LLMChecker()

        logger.info("✅ All components initialized successfully")

        # Show initial stats
        if UI_CONFIG.get("show_statistics", True):
            print_stats(db)

        # STAP 1: Zoek en indexeer papers
        new_papers = search_and_index_papers(db, arxiv_client, logger)

        # STAP 2: Download PDFs
        downloads = download_pdfs(db, arxiv_client, logger)

        # STAP 3: Convert naar Markdown
        conversions = convert_to_markdown(db, logger)

        # STAP 4: LLM Kwaliteitscontrole
        llm_fixes = llm_quality_check(db, llm_checker, logger)

        # Final statistics
        if UI_CONFIG.get("show_statistics", True):
            print_stats(db)

        # Summary
        if UI_CONFIG.get("show_progress_bars", True):
            print("\n" + "=" * 60)
            print("PIPELINE SUMMARY")
            print("=" * 60)
            print(f"🔍 Nieuwe papers gevonden: {new_papers}")
            print(f"⬇️  PDFs gedownload: {downloads}")
            print(f"📝 Markdown conversies: {conversions}")
            print(f"🤖 LLM kwaliteitscontroles: {llm_fixes}")
            print("=" * 60)

        logger.info("🎉 Pipeline completed successfully!")

    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
