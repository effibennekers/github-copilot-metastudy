#!/usr/bin/env python3
"""
GitHub Copilot Metastudy - Hoofdworkflow
Uitgebreide pipeline voor paper downloading, conversie en analyse
"""

import sys
from pathlib import Path

# Import from package modules
from .database import PaperDatabase
from .arxiv import ArxivClient
from .pdf import PDFProcessor
from .logging import setup_logging, get_logger
from .config import (
    SEARCH_CONFIG, 
    DATABASE_CONFIG, 
    STORAGE_CONFIG, 
    PROCESSING_CONFIG, 
    UI_CONFIG
)

def print_stats(db: PaperDatabase):
    """Print database statistieken"""
    stats = db.get_statistics()
    
    if not UI_CONFIG.get('show_statistics', True):
        return
    
    print("\n" + "="*60)
    print("DATABASE STATISTIEKEN")
    print("="*60)
    print(f"Totaal papers: {stats['total_papers']}")
    
    print("\nDownload Status:")
    for status, count in stats.get('download_status', {}).items():
        print(f"  {status}: {count}")
    
    print("\nLLM Check Status:")
    for status, count in stats.get('llm_status', {}).items():
        print(f"  {status}: {count}")
    print("="*60)

def search_and_index_papers(db: PaperDatabase, arxiv_client: ArxivClient, logger):
    """STAP 1: Zoek en indexeer papers"""
    logger.info("=== STAP 1: Papers zoeken en indexeren ===")
    
    # Haal configuratie op
    search_config = SEARCH_CONFIG
    queries = search_config['queries']
    max_results_per_query = search_config['max_results_per_query']
    total_max_papers = search_config['total_max_papers']
    
    logger.info(f"Configuratie: {len(queries)} zoektermen, max {max_results_per_query} per query")
    logger.info(f"Totaal maximum papers: {total_max_papers}")
    
    total_new_papers = 0
    
    for i, query in enumerate(queries, 1):
        logger.info(f"[{i}/{len(queries)}] Zoeken met query: '{query}'")
        
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
                if not db.paper_exists(paper['arxiv_id']):
                    db.insert_paper(paper)
                    new_papers += 1
                    logger.info(f"Nieuw paper toegevoegd: {paper['arxiv_id']} - {paper['title'][:50]}...")
                    
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

def download_pdfs(db: PaperDatabase, pdf_processor: PDFProcessor, logger):
    """STAP 2: Download PDFs"""
    logger.info("=== STAP 2: PDFs downloaden ===")
    
    pending_downloads = db.get_papers_by_status(download_status='PENDING')
    
    if not pending_downloads:
        logger.info("Geen PDFs om te downloaden")
        return 0
    
    logger.info(f"Te downloaden PDFs: {len(pending_downloads)}")
    
    downloaded_count = 0
    failed_count = 0
    
    for i, paper in enumerate(pending_downloads, 1):
        logger.info(f"[{i}/{len(pending_downloads)}] Downloading: {paper['arxiv_id']}")
        
        try:
            pdf_path = pdf_processor.download_pdf(
                paper['arxiv_id'], 
                paper['pdf_url']
            )
            
            if pdf_path:
                db.update_paper_status(
                    paper['arxiv_id'],
                    download_status='DOWNLOADED',
                    pdf_path=pdf_path
                )
                downloaded_count += 1
                logger.info(f"✅ Download successful: {paper['arxiv_id']}")
            else:
                db.update_paper_status(
                    paper['arxiv_id'],
                    download_status='FAILED'
                )
                failed_count += 1
                logger.error(f"❌ Download failed: {paper['arxiv_id']}")
                
        except Exception as e:
            logger.error(f"❌ Download error for {paper['arxiv_id']}: {e}")
            db.update_paper_status(
                paper['arxiv_id'],
                download_status='FAILED'
            )
            failed_count += 1
    
    logger.info(f"STAP 2 VOLTOOID: {downloaded_count} downloads successful, {failed_count} failed")
    return downloaded_count

def convert_to_markdown(db: PaperDatabase, pdf_processor: PDFProcessor, logger):
    """STAP 3: Convert naar Markdown"""
    logger.info("=== STAP 3: PDF naar Markdown conversie ===")
    
    downloaded_papers = db.get_papers_by_status(download_status='DOWNLOADED')
    
    # Filter papers that don't have markdown yet
    to_convert = [p for p in downloaded_papers if not p['md_path']]
    
    if not to_convert:
        logger.info("Geen PDFs om te converteren")
        return 0
    
    logger.info(f"Te converteren PDFs: {len(to_convert)}")
    
    converted_count = 0
    
    for i, paper in enumerate(to_convert, 1):
        logger.info(f"[{i}/{len(to_convert)}] Converting: {paper['arxiv_id']}")
        
        try:
            md_path = pdf_processor.pdf_to_markdown(
                paper['pdf_path'], 
                paper['arxiv_id']
            )
            
            if md_path:
                db.update_paper_status(
                    paper['arxiv_id'],
                    md_path=md_path
                )
                converted_count += 1
                logger.info(f"✅ Conversion successful: {paper['arxiv_id']}")
            else:
                logger.error(f"❌ Conversion failed: {paper['arxiv_id']}")
                
        except Exception as e:
            logger.error(f"❌ Conversion error for {paper['arxiv_id']}: {e}")
    
    logger.info(f"STAP 3 VOLTOOID: {converted_count} conversions successful")
    return converted_count

def main():
    """Hoofd workflow voor metastudy"""
    # Setup logging first
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("🚀 GitHub Copilot Metastudy - Pipeline Start")
    logger.info("=" * 70)
    
    # Log configuratie
    search_config = SEARCH_CONFIG
    logger.info(f"Configuratie geladen:")
    logger.info(f"  - Zoektermen: {len(search_config['queries'])}")
    logger.info(f"  - Max per query: {search_config['max_results_per_query']}")
    logger.info(f"  - Totaal max: {search_config['total_max_papers']}")
    logger.info(f"  - Database: {DATABASE_CONFIG['db_path']}")
    logger.info(f"  - PDF directory: {STORAGE_CONFIG['pdf_directory']}")
    logger.info(f"  - Markdown directory: {STORAGE_CONFIG['markdown_directory']}")
    
    try:
        # Initialize components met configuratie
        logger.info("Initializing components...")
        db = PaperDatabase(DATABASE_CONFIG['db_path'])
        arxiv_client = ArxivClient()
        pdf_processor = PDFProcessor(
            STORAGE_CONFIG['pdf_directory'], 
            STORAGE_CONFIG['markdown_directory']
        )
        
        logger.info("✅ All components initialized successfully")
        
        # Show initial stats
        if UI_CONFIG.get('show_statistics', True):
            print_stats(db)
        
        # STAP 1: Zoek en indexeer papers
        new_papers = search_and_index_papers(db, arxiv_client, logger)
        
        # STAP 2: Download PDFs
        downloads = download_pdfs(db, pdf_processor, logger)
        
        # STAP 3: Convert naar Markdown
        conversions = convert_to_markdown(db, pdf_processor, logger)
        
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
            print("="*60)
        
        logger.info("🎉 Pipeline completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
