"""
ArXiv API Client voor GitHub Copilot Metastudy
Wrapper rond de officiële arxiv.py client met rate limiting compliance
"""

import arxiv
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime

# Import configuratie
from src.config import PROCESSING_CONFIG

class ArxivClient:
    def __init__(self):
        # Gebruik de officiële arxiv client met optimized settings
        self.client = arxiv.Client(
            page_size=100,  # Verhoog page size voor efficiëntie
            delay_seconds=3.0,  # Ingebouwde rate limiting (arXiv compliant)
            num_retries=2  # Retry logic
        )
        self.logger = logging.getLogger(__name__)
        
        # Load processing configuration
        self.processing_config = PROCESSING_CONFIG
        self.rate_limit = self.processing_config['api_rate_limit_seconds']
        
        self.logger.info(f"ArXiv Client initialized with {self.rate_limit}s rate limiting")
        self.logger.info("Using official arxiv.py client with built-in rate limiting")
    
    def search_papers(self, query: str, max_results: int = 50, sort_by: str = "submittedDate") -> List[Dict]:
        """
        Zoek papers met de officiële arxiv client
        
        Args:
            query: Zoekquery (support arXiv query syntax)
            max_results: Maximum aantal resultaten
            sort_by: Sortering ("submittedDate", "lastUpdatedDate", "relevance")
        """
        self.logger.info(f"Zoeken naar papers: '{query}' (max: {max_results}, sort: {sort_by})")
        
        try:
            # Map sort_by string naar arxiv SortCriterion
            sort_criterion_map = {
                "submittedDate": arxiv.SortCriterion.SubmittedDate,
                "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
                "relevance": arxiv.SortCriterion.Relevance
            }
            
            sort_criterion = sort_criterion_map.get(sort_by, arxiv.SortCriterion.SubmittedDate)
            
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=sort_criterion
            )
            
            papers = []
            result_count = 0
            
            # De client heeft ingebouwde rate limiting, dus geen handmatige sleep nodig
            for result in self.client.results(search):
                # Extract arxiv_id from entry_id URL
                arxiv_id = result.entry_id.split('/')[-1]
                
                paper_data = {
                    'arxiv_id': arxiv_id,
                    'title': result.title.strip(),
                    'abstract': result.summary.strip(),
                    'authors': [author.name for author in result.authors],
                    'categories': result.categories,  # Toegevoegd: categorieën
                    'published_date': result.published.isoformat(),
                    'updated_date': result.updated.isoformat() if result.updated else None,  # Toegevoegd
                    'url': result.entry_id,
                    'pdf_url': result.pdf_url,
                    'doi': result.doi,  # Toegevoegd: DOI indien beschikbaar
                    'journal_ref': result.journal_ref,  # Toegevoegd: journal reference
                    'comment': result.comment  # Toegevoegd: paper comment
                }
                papers.append(paper_data)
                result_count += 1
                
                # Log progress every 10 papers
                if result_count % 10 == 0:
                    self.logger.info(f"Verwerkt {result_count} papers...")
            
            self.logger.info(f"Totaal gevonden papers: {len(papers)}")
            return papers
            
        except Exception as e:
            self.logger.error(f"ArXiv search failed: {e}")
            raise
    
    def search_by_ids(self, arxiv_ids: List[str]) -> List[Dict]:
        """
        Zoek papers op basis van arXiv IDs
        
        Args:
            arxiv_ids: List van arXiv IDs (bijv. ["2023.12345v1", "2023.12346v1"])
        """
        self.logger.info(f"Zoeken papers by IDs: {len(arxiv_ids)} IDs")
        
        try:
            search = arxiv.Search(id_list=arxiv_ids)
            
            papers = []
            for result in self.client.results(search):
                arxiv_id = result.entry_id.split('/')[-1]
                
                paper_data = {
                    'arxiv_id': arxiv_id,
                    'title': result.title.strip(),
                    'abstract': result.summary.strip(),
                    'authors': [author.name for author in result.authors],
                    'categories': result.categories,
                    'published_date': result.published.isoformat(),
                    'updated_date': result.updated.isoformat() if result.updated else None,
                    'url': result.entry_id,
                    'pdf_url': result.pdf_url,
                    'doi': result.doi,
                    'journal_ref': result.journal_ref,
                    'comment': result.comment
                }
                papers.append(paper_data)
            
            self.logger.info(f"Gevonden papers by ID: {len(papers)}")
            return papers
            
        except Exception as e:
            self.logger.error(f"ArXiv search by IDs failed: {e}")
            raise
    
    def download_paper_source(self, arxiv_id: str, dirpath: str, filename: Optional[str] = None) -> str:
        """
        Download de source (.tar.gz) van een paper
        
        Args:
            arxiv_id: ArXiv ID
            dirpath: Directory om naar te downloaden
            filename: Optionele custom filename
            
        Returns:
            Pad naar gedownload bestand
        """
        try:
            # Zoek de paper eerst
            search = arxiv.Search(id_list=[arxiv_id])
            paper = next(self.client.results(search))
            
            # Download source met de ingebouwde functie
            if filename:
                filepath = paper.download_source(dirpath=dirpath, filename=filename)
            else:
                filepath = paper.download_source(dirpath=dirpath)
            
            self.logger.info(f"Source downloaded: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to download source for {arxiv_id}: {e}")
            raise
    
    def download_paper_pdf(self, arxiv_id: str, dirpath: str, filename: Optional[str] = None) -> str:
        """
        Download de PDF van een paper
        
        Args:
            arxiv_id: ArXiv ID
            dirpath: Directory om naar te downloaden
            filename: Optionele custom filename
            
        Returns:
            Pad naar gedownload bestand
        """
        try:
            # Zoek de paper eerst
            search = arxiv.Search(id_list=[arxiv_id])
            paper = next(self.client.results(search))
            
            # Download PDF met de ingebouwde functie
            if filename:
                filepath = paper.download_pdf(dirpath=dirpath, filename=filename)
            else:
                filepath = paper.download_pdf(dirpath=dirpath)
            
            self.logger.info(f"PDF downloaded: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to download PDF for {arxiv_id}: {e}")
            raise
    
