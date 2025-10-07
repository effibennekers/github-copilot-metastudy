# GitHub Copilot Metastudy - Implementatie Stappenplan

## Overzicht 📋

Dit stappenplan implementeert een robuust system voor het downloaden, converteren en analyseren van arXiv papers voor de GitHub Copilot metastudie.

## Fase 1: Database & Infrastructuur Setup 🗄️

### Stap 1.1: SQLite Database Schema
```sql
CREATE TABLE papers (
    arxiv_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT,
    authors TEXT,  -- JSON array van auteurs
    published_date TEXT,
    url TEXT,
    pdf_path TEXT,
    md_path TEXT,
    download_status TEXT DEFAULT 'PENDING',  -- PENDING, DOWNLOADED, FAILED
    llm_check_status TEXT DEFAULT 'PENDING', -- PENDING, CLEAN, FIXED, FAILED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_download_status ON papers(download_status);
CREATE INDEX idx_llm_status ON papers(llm_check_status);
```

### Stap 1.2: Directory Structuur
```
github-copilot-metastudy/
├── data/                      # Data opslag (NIET in git)
│   ├── papers.db              # SQLite database
│   ├── pdf/                   # Gedownloade PDF bestanden
│   └── md/                    # Geconverteerde Markdown bestanden
├── metastudy/
│   ├── src/
│   │   ├── database.py        # Database operaties
│   │   ├── arxiv_client.py    # ArXiv API wrapper
│   │   ├── pdf_processor.py   # PDF download & conversie
│   │   ├── llm_checker.py     # LLM kwaliteitscontrole
│   │   └── cli.py             # Command-line interface
│   ├── main.py                # Hoofd applicatie
│   └── requirements.txt
├── .gitignore                 # Bevat data/ exclusion
└── README.md
```

## Fase 2: Core Components Implementatie 🔧

### Stap 2.1: Database Module (`database.py`)
```python
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class PaperDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialiseer database schema"""
        # Schema creation met proper indexes
    
    def paper_exists(self, arxiv_id: str) -> bool:
        """Check of paper al in database staat"""
    
    def insert_paper(self, paper_data: Dict) -> None:
        """Voeg nieuw paper toe aan database"""
    
    def get_papers_by_status(self, download_status: str = None, 
                           llm_status: str = None) -> List[Dict]:
        """Haal papers op op basis van status"""
    
    def update_paper_status(self, arxiv_id: str, **kwargs) -> None:
        """Update paper status en timestamps"""
```

### Stap 2.2: ArXiv Client (`arxiv_client.py`)
```python
import arxiv
import time
import logging
from typing import List, Dict

class ArxivClient:
    def __init__(self):
        self.client = arxiv.Client()
        self.logger = logging.getLogger(__name__)
    
    def search_papers(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Zoek papers met rate limiting compliance
        VERPLICHT: 3 seconden tussen requests
        """
        self.logger.info(f"Zoeken naar papers: {query}")
        
        # RATE LIMITING: 3 seconden wachten
        time.sleep(3)
        
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        papers = []
        for result in self.client.results(search):
            paper_data = {
                'arxiv_id': result.entry_id.split('/')[-1],
                'title': result.title,
                'abstract': result.summary,
                'authors': [author.name for author in result.authors],
                'published_date': result.published.isoformat(),
                'url': result.entry_id,
                'pdf_url': result.pdf_url
            }
            papers.append(paper_data)
        
        return papers
```

### Stap 2.3: PDF Processor (`pdf_processor.py`)
```python
import requests
import time
import subprocess
import logging
from pathlib import Path
from typing import Optional

class PDFProcessor:
    def __init__(self, pdf_dir: str = "data/pdf", md_dir: str = "data/md"):
        self.pdf_dir = Path(pdf_dir)
        self.md_dir = Path(md_dir)
        self.logger = logging.getLogger(__name__)
        
        # Ensure directories exist
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.md_dir.mkdir(parents=True, exist_ok=True)
    
    def download_pdf(self, arxiv_id: str, pdf_url: str) -> Optional[str]:
        """
        Download PDF met rate limiting
        VERPLICHT: 3 seconden tussen downloads
        """
        pdf_path = self.pdf_dir / f"{arxiv_id}.pdf"
        
        if pdf_path.exists():
            self.logger.info(f"PDF already exists: {pdf_path}")
            return str(pdf_path)
        
        try:
            # RATE LIMITING: 3 seconden wachten
            time.sleep(3)
            
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            
            self.logger.info(f"Downloaded PDF: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            self.logger.error(f"Failed to download PDF {arxiv_id}: {e}")
            return None
    
    def pdf_to_markdown(self, pdf_path: str, arxiv_id: str) -> Optional[str]:
        """Convert PDF to Markdown using pandoc"""
        md_path = self.md_dir / f"{arxiv_id}.md"
        
        if md_path.exists():
            self.logger.info(f"Markdown already exists: {md_path}")
            return str(md_path)
        
        try:
            # Use pandoc for PDF to Markdown conversion
            cmd = [
                'pandoc',
                pdf_path,
                '-o', str(md_path),
                '--wrap=none',
                '--extract-media=.',
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Converted to Markdown: {md_path}")
                return str(md_path)
            else:
                self.logger.error(f"Pandoc conversion failed: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"PDF to Markdown conversion failed: {e}")
            return None
```

## Fase 3: LLM Integratie & Quality Control 🤖

### Stap 3.1: LLM Checker (`llm_checker.py`)
```python
import requests
import json
import logging
from typing import Optional

class LLMChecker:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.logger = logging.getLogger(__name__)
    
    def check_and_fix_markdown(self, md_content: str, arxiv_id: str) -> tuple[str, str]:
        """
        Check en verbeter Markdown met lokale LLM
        Returns: (improved_content, status)
        """
        prompt = """
        Je bent een expert in het controleren van academische papers die zijn geconverteerd van PDF naar Markdown.
        
        Controleer de volgende Markdown tekst op:
        1. Verkeerde koppen (# ## ###)
        2. Gebroken tabellen
        3. Foute lijstopmaak
        4. Referentie formatting
        5. Figuur/tabel captions
        
        Corrigeer de opmaak waar nodig en behoud alle originele inhoud.
        Antwoord ALLEEN met de gecorrigeerde Markdown, geen extra uitleg.
        
        TEKST:
        """ + md_content
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama3.2",  # of ander beschikbaar model
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                improved_content = result.get('response', '')
                
                if len(improved_content) > len(md_content) * 0.8:  # Sanity check
                    return improved_content, 'FIXED'
                else:
                    self.logger.warning(f"LLM response too short for {arxiv_id}")
                    return md_content, 'CLEAN'
            else:
                self.logger.error(f"LLM API error: {response.status_code}")
                return md_content, 'FAILED'
                
        except Exception as e:
            self.logger.error(f"LLM check failed for {arxiv_id}: {e}")
            return md_content, 'FAILED'
```

## Fase 4: Workflow Orchestration 🎯

### Stap 4.1: Main Workflow (`main.py` update)
```python
#!/usr/bin/env python3
"""
GitHub Copilot Metastudy - Hoofdworkflow
"""

import logging
from pathlib import Path
from src.database import PaperDatabase
from src.arxiv_client import ArxivClient
from src.pdf_processor import PDFProcessor
from src.llm_checker import LLMChecker

def setup_logging():
    """Setup logging configuratie"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('metastudy.log'),
            logging.StreamHandler()
        ]
    )

def main():
    """Hoofd workflow voor metastudy"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Initialize components
    db = PaperDatabase('data/papers.db')
    arxiv_client = ArxivClient()
    pdf_processor = PDFProcessor()  # Uses default data/pdf and data/md
    llm_checker = LLMChecker()
    
    # STAP 1: Zoek en indexeer papers
    logger.info("=== STAP 1: Papers zoeken en indexeren ===")
    query = "GitHub Copilot OR AI code generation OR programming assistant"
    papers = arxiv_client.search_papers(query, max_results=100)
    
    new_papers = 0
    for paper in papers:
        if not db.paper_exists(paper['arxiv_id']):
            db.insert_paper(paper)
            new_papers += 1
            logger.info(f"Nieuw paper toegevoegd: {paper['arxiv_id']}")
    
    logger.info(f"Totaal nieuwe papers: {new_papers}")
    
    # STAP 2: Download PDFs
    logger.info("=== STAP 2: PDFs downloaden ===")
    pending_downloads = db.get_papers_by_status(download_status='PENDING')
    
    for paper in pending_downloads:
        pdf_path = pdf_processor.download_pdf(
            paper['arxiv_id'], 
            paper['url'].replace('abs', 'pdf') + '.pdf'
        )
        
        if pdf_path:
            db.update_paper_status(
                paper['arxiv_id'],
                download_status='DOWNLOADED',
                pdf_path=pdf_path
            )
        else:
            db.update_paper_status(
                paper['arxiv_id'],
                download_status='FAILED'
            )
    
    # STAP 3: Convert naar Markdown
    logger.info("=== STAP 3: PDF naar Markdown conversie ===")
    downloaded_papers = db.get_papers_by_status(download_status='DOWNLOADED')
    
    for paper in downloaded_papers:
        if paper['md_path'] is None:  # Nog niet geconverteerd
            md_path = pdf_processor.pdf_to_markdown(
                paper['pdf_path'], 
                paper['arxiv_id']
            )
            
            if md_path:
                db.update_paper_status(
                    paper['arxiv_id'],
                    md_path=md_path
                )
    
    # STAP 4: LLM Kwaliteitscontrole
    logger.info("=== STAP 4: LLM Kwaliteitscontrole ===")
    markdown_papers = db.get_papers_by_status(
        download_status='DOWNLOADED',
        llm_status='PENDING'
    )
    
    for paper in markdown_papers:
        if paper['md_path']:
            with open(paper['md_path'], 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            improved_content, status = llm_checker.check_and_fix_markdown(
                md_content, paper['arxiv_id']
            )
            
            # Save improved version
            if status == 'FIXED':
                with open(paper['md_path'], 'w', encoding='utf-8') as f:
                    f.write(improved_content)
            
            db.update_paper_status(
                paper['arxiv_id'],
                llm_check_status=status
            )
    
    logger.info("=== Workflow voltooid ===")

if __name__ == "__main__":
    main()
```

## Fase 5: Dependencies & Testing 🧪

### Stap 5.1: Requirements Update
```txt
# Core dependencies
arxiv==2.2.0
requests>=2.28.0
sqlite3  # Standaard library

# PDF Processing
pdfplumber>=2.0.0  # Fallback voor pandoc

# Development dependencies
pytest>=7.0.0
black>=22.0.0
flake8>=4.0.0
```

### Stap 5.2: Command-Line Interface
```python
# cli.py
import click
from main import main

@click.group()
def cli():
    """GitHub Copilot Metastudy CLI"""
    pass

@cli.command()
@click.option('--query', default="GitHub Copilot OR AI code generation")
@click.option('--max-results', default=50)
def search(query, max_results):
    """Zoek en download nieuwe papers"""
    # Implementation

@cli.command()
def status():
    """Toon database status"""
    # Implementation

@cli.command()
def process():
    """Draai volledige workflow"""
    main()

if __name__ == '__main__':
    cli()
```

## Uitvoering Plan 🚀

1. **Start met Fase 1**: Database setup en directory structuur
2. **Implementeer Fase 2**: Core components één voor één
3. **Test elke component** individueel voor betrouwbaarheid
4. **Integreer Fase 3**: LLM functionaliteit (optioneel voor MVP)
5. **Bouw Fase 4**: Complete workflow orchestration
6. **Finaliseer Fase 5**: CLI en testing

**Geschatte tijdsduur**: 3-5 dagen voor complete implementatie.

**Kritieke aandachtspunten**:
- ✅ Rate limiting (3 seconden) bij elke arXiv API call
- ✅ Robuuste error handling voor netwerk issues
- ✅ Database integrity met unieke arxiv_id constraints
- ✅ Logging voor debugging en monitoring
