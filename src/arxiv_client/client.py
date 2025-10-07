"""
ArXiv API Client voor GitHub Copilot Metastudy
Implementeert rate limiting compliance volgens arXiv Terms of Use
"""

import arxiv
import time
import logging
from typing import List, Dict
from datetime import datetime

# Import configuratie
from src.config import PROCESSING_CONFIG

class ArxivClient:
    def __init__(self):
        self.client = arxiv.Client()
        self.logger = logging.getLogger(__name__)
        self.last_request_time = 0
        
        # Load processing configuration
        self.processing_config = PROCESSING_CONFIG
        self.rate_limit = self.processing_config['api_rate_limit_seconds']
        
        self.logger.info(f"ArXiv Client initialized with {self.rate_limit}s rate limiting")
    
    def _enforce_rate_limit(self):
        """
        VERPLICHTE RATE LIMITING: configureerbare seconden tussen requests
        Bron: https://info.arxiv.org/help/api/tou.html
        """
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last
            self.logger.info(f"Rate limiting: wachten {sleep_time:.1f} seconden")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search_papers(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Zoek papers met rate limiting compliance
        """
        self.logger.info(f"Zoeken naar papers: '{query}' (max: {max_results})")
        
        # VERPLICHTE RATE LIMITING
        self._enforce_rate_limit()
        
        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )
            
            papers = []
            result_count = 0
            
            for result in self.client.results(search):
                # Extract arxiv_id from entry_id URL
                arxiv_id = result.entry_id.split('/')[-1]
                
                paper_data = {
                    'arxiv_id': arxiv_id,
                    'title': result.title.strip(),
                    'abstract': result.summary.strip(),
                    'authors': [author.name for author in result.authors],
                    'published_date': result.published.isoformat(),
                    'url': result.entry_id,
                    'pdf_url': result.pdf_url
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
    
