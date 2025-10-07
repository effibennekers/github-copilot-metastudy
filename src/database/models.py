"""
Database module voor GitHub Copilot Metastudy
Beheert SQLite database voor paper metadata en status tracking
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Import configuratie
from ..config import DATABASE_CONFIG, STORAGE_CONFIG
from ..logging import get_logger

class PaperDatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DATABASE_CONFIG['db_path']
        self.logger = get_logger(__name__)
        
        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.init_database()
    
    def init_database(self):
        """Initialiseer database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    arxiv_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    abstract TEXT,
                    authors TEXT,  -- JSON array van auteurs
                    published_date TEXT,
                    url TEXT,
                    pdf_url TEXT,
                    pdf_path TEXT,
                    md_path TEXT,
                    download_status TEXT DEFAULT 'PENDING',  -- PENDING, DOWNLOADED, FAILED
                    llm_check_status TEXT DEFAULT 'PENDING', -- PENDING, CLEAN, FIXED, FAILED
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_download_status ON papers(download_status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_status ON papers(llm_check_status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON papers(created_at)")
            
            conn.commit()
            
        self.logger.info(f"Database initialized: {self.db_path}")
    
    def paper_exists(self, arxiv_id: str) -> bool:
        """Check of paper al in database staat"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM papers WHERE arxiv_id = ?", 
                (arxiv_id,)
            )
            return cursor.fetchone() is not None
    
    def insert_paper(self, paper_data: Dict) -> None:
        """Voeg nieuw paper toe aan database"""
        # Convert authors list to JSON string
        authors_json = json.dumps(paper_data.get('authors', []))
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO papers (
                    arxiv_id, title, abstract, authors, published_date, 
                    url, pdf_url, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_data['arxiv_id'],
                paper_data['title'],
                paper_data.get('abstract', ''),
                authors_json,
                paper_data.get('published_date', ''),
                paper_data.get('url', ''),
                paper_data.get('pdf_url', ''),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            conn.commit()
            
        self.logger.info(f"Paper inserted: {paper_data['arxiv_id']}")
    
    def get_papers_by_status(self, download_status: str = None, 
                           llm_status: str = None) -> List[Dict]:
        """Haal papers op op basis van status"""
        query = "SELECT * FROM papers WHERE 1=1"
        params = []
        
        if download_status:
            query += " AND download_status = ?"
            params.append(download_status)
            
        if llm_status:
            query += " AND llm_check_status = ?"
            params.append(llm_status)
        
        query += " ORDER BY created_at DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # Return rows as dicts
            cursor = conn.execute(query, params)
            
            papers = []
            for row in cursor.fetchall():
                paper = dict(row)
                # Convert authors JSON back to list
                if paper['authors']:
                    paper['authors'] = json.loads(paper['authors'])
                papers.append(paper)
                
            return papers
    
    def update_paper_status(self, arxiv_id: str, **kwargs) -> None:
        """Update paper status en timestamps"""
        # Always update the updated_at timestamp
        kwargs['updated_at'] = datetime.now().isoformat()
        
        # Build UPDATE query dynamically
        set_clauses = []
        params = []
        
        for field, value in kwargs.items():
            set_clauses.append(f"{field} = ?")
            params.append(value)
        
        params.append(arxiv_id)  # For WHERE clause
        
        query = f"UPDATE papers SET {', '.join(set_clauses)} WHERE arxiv_id = ?"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query, params)
            conn.commit()
            
        self.logger.info(f"Paper updated: {arxiv_id} - {kwargs}")
    
    def get_statistics(self) -> Dict:
        """Haal database statistieken op"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total papers
            cursor = conn.execute("SELECT COUNT(*) FROM papers")
            stats['total_papers'] = cursor.fetchone()[0]
            
            # Download status breakdown
            cursor = conn.execute("""
                SELECT download_status, COUNT(*) 
                FROM papers 
                GROUP BY download_status
            """)
            stats['download_status'] = dict(cursor.fetchall())
            
            # LLM status breakdown
            cursor = conn.execute("""
                SELECT llm_check_status, COUNT(*) 
                FROM papers 
                GROUP BY llm_check_status
            """)
            stats['llm_status'] = dict(cursor.fetchall())
            
            return stats
    
    def get_paper_by_id(self, arxiv_id: str) -> Optional[Dict]:
        """Haal specifiek paper op via arxiv_id"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM papers WHERE arxiv_id = ?", 
                (arxiv_id,)
            )
            
            row = cursor.fetchone()
            if row:
                paper = dict(row)
                if paper['authors']:
                    paper['authors'] = json.loads(paper['authors'])
                return paper
            
            return None
