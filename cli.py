#!/usr/bin/env python3
"""
Command Line Interface voor GitHub Copilot Metastudy
Maakt het mogelijk om stappen afzonderlijk uit te voeren
"""

import sys
import argparse
import logging
import logging.config
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.database import PaperDatabase
from src.arxiv_client import ArxivClient
from src.pdf import PDFProcessor
from src.llm import LLMChecker
from src.config import (
    SEARCH_CONFIG, 
    DATABASE_CONFIG, 
    STORAGE_CONFIG, 
    PROCESSING_CONFIG, 
    LOGGING_CONFIG,
    LLM_CONFIG,
    UI_CONFIG
)
from src.main import (
    print_stats,
    search_and_index_papers,
    download_pdfs,
    convert_to_markdown,
    llm_quality_check
)


def setup_logging():
    """Setup logging configuratie"""
    logging.config.dictConfig(LOGGING_CONFIG)
    return logging.getLogger(__name__)


def initialize_components():
    """Initialize alle pipeline components"""
    logger = setup_logging()
    
    logger.info("Initializing components...")
    db = PaperDatabase(DATABASE_CONFIG['db_path'])
    arxiv_client = ArxivClient()
    pdf_processor = PDFProcessor(
        STORAGE_CONFIG['pdf_directory'], 
        STORAGE_CONFIG['markdown_directory']
    )
    llm_checker = LLMChecker()
    
    logger.info("✅ All components initialized successfully")
    return db, arxiv_client, pdf_processor, llm_checker, logger


def cmd_status(args):
    """Show database statistics"""
    db, _, _, _, logger = initialize_components()
    
    logger.info("📊 Database Status")
    print_stats(db)


def cmd_search(args):
    """Run paper search and indexing step"""
    db, arxiv_client, _, _, logger = initialize_components()
    
    logger.info("🔍 Starting paper search and indexing...")
    new_papers = search_and_index_papers(db, arxiv_client, logger)
    
    print(f"\n✅ Search completed: {new_papers} nieuwe papers toegevoegd")
    if UI_CONFIG.get('show_statistics', True):
        print_stats(db)


def cmd_download(args):
    """Run PDF download step"""
    db, _, pdf_processor, _, logger = initialize_components()
    
    logger.info("⬇️ Starting PDF downloads...")
    downloads = download_pdfs(db, pdf_processor, logger)
    
    print(f"\n✅ Downloads completed: {downloads} PDFs gedownload")
    if UI_CONFIG.get('show_statistics', True):
        print_stats(db)


def cmd_convert(args):
    """Run PDF to Markdown conversion step"""
    db, _, pdf_processor, _, logger = initialize_components()
    
    logger.info("📝 Starting PDF to Markdown conversion...")
    conversions = convert_to_markdown(db, pdf_processor, logger)
    
    print(f"\n✅ Conversions completed: {conversions} bestanden geconverteerd")
    if UI_CONFIG.get('show_statistics', True):
        print_stats(db)


def cmd_llm(args):
    """Run LLM quality check step"""
    db, _, _, llm_checker, logger = initialize_components()
    
    logger.info("🤖 Starting LLM quality check...")
    llm_fixes = llm_quality_check(db, llm_checker, logger)
    
    print(f"\n✅ LLM check completed: {llm_fixes} papers processed")
    if UI_CONFIG.get('show_statistics', True):
        print_stats(db)


def cmd_pipeline(args):
    """Run complete pipeline"""
    db, arxiv_client, pdf_processor, llm_checker, logger = initialize_components()
    
    logger.info("🚀 GitHub Copilot Metastudy - Pipeline Start")
    logger.info("=" * 70)
    logger.info("Configuratie geladen:")
    logger.info(f"  - Zoektermen: {len(SEARCH_CONFIG['search_queries'])}")
    logger.info(f"  - Max per query: {SEARCH_CONFIG['max_results_per_query']}")
    logger.info(f"  - Totaal max: {SEARCH_CONFIG['total_max_papers']}")
    logger.info(f"  - Database: {DATABASE_CONFIG['db_path']}")
    logger.info(f"  - PDF directory: {STORAGE_CONFIG['pdf_directory']}")
    logger.info(f"  - Markdown directory: {STORAGE_CONFIG['markdown_directory']}")
    
    # Show initial stats
    if UI_CONFIG.get('show_statistics', True):
        print_stats(db)
    
    # Run all steps
    new_papers = search_and_index_papers(db, arxiv_client, logger)
    downloads = download_pdfs(db, pdf_processor, logger)
    conversions = convert_to_markdown(db, pdf_processor, logger)
    llm_fixes = llm_quality_check(db, llm_checker, logger)
    
    # Final statistics
    if UI_CONFIG.get('show_statistics', True):
        print_stats(db)
    
    # Summary
    if UI_CONFIG.get('show_progress_bars', True):
        print("\n" + "="*60)
        print("PIPELINE SUMMARY")
        print("="*60)
        print(f"🔍 Nieuwe papers gevonden: {new_papers}")
        print(f"⬇️  PDFs gedownload: {downloads}")
        print(f"📝 Markdown conversies: {conversions}")
        print(f"🤖 LLM kwaliteitscontroles: {llm_fixes}")
        print("="*60)
    
    logger.info("🎉 Pipeline completed successfully!")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='GitHub Copilot Metastudy Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status     # Show database statistics
  %(prog)s search     # Search and index new papers
  %(prog)s download   # Download PDFs for indexed papers
  %(prog)s convert    # Convert PDFs to Markdown
  %(prog)s llm        # Run LLM quality check on Markdown
  %(prog)s pipeline   # Run complete pipeline (all steps)
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show database statistics')
    status_parser.set_defaults(func=cmd_status)
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search and index papers from arXiv')
    search_parser.set_defaults(func=cmd_search)
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download PDFs for indexed papers')
    download_parser.set_defaults(func=cmd_download)
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert PDFs to Markdown')
    convert_parser.set_defaults(func=cmd_convert)
    
    # LLM command
    llm_parser = subparsers.add_parser('llm', help='Run LLM quality check on Markdown files')
    llm_parser.set_defaults(func=cmd_llm)
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Run complete pipeline (all steps)')
    pipeline_parser.set_defaults(func=cmd_pipeline)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
