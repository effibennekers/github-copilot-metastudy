"""
Database module voor GitHub Copilot Metastudy
Beheert SQLite database voor paper metadata en status tracking
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Import configuratie
from src.config import DATABASE_CONFIG, STORAGE_CONFIG

class PaperDatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DATABASE_CONFIG['db_path']
        self.logger = logging.getLogger(__name__)
        
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
                    categories TEXT,  -- JSON array van categorieën
                    published_date TEXT,
                    updated_date TEXT,  -- Laatste update datum
                    url TEXT,
                    pdf_url TEXT,
                    doi TEXT,  -- DOI indien beschikbaar
                    journal_ref TEXT,  -- Journal reference
                    comment TEXT,  -- Paper comment
                    pdf_path TEXT,
                    md_path TEXT,
                    download_status TEXT DEFAULT 'PENDING',  -- PENDING, DOWNLOADED, FAILED
                    llm_check_status TEXT DEFAULT 'PENDING', -- PENDING, CLEAN, FIXED, FAILED
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create metadata table based on metadataschema.json
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    id TEXT PRIMARY KEY,  -- arXiv ID (e.g., "2510.01576v1")
                    submitter TEXT,  -- Can be null
                    authors TEXT NOT NULL,  -- Author names as string
                    title TEXT NOT NULL,  -- Paper title
                    comments TEXT,  -- Optional comments (can be null)
                    journal_ref TEXT,  -- Journal reference (can be null)  
                    doi TEXT,  -- DOI (can be null)
                    report_no TEXT,  -- Report number (can be null)
                    categories TEXT NOT NULL,  -- Categories as string
                    license TEXT,  -- License (can be null)
                    abstract TEXT NOT NULL,  -- Paper abstract
                    versions TEXT NOT NULL,  -- JSON array of versions (minified)
                    update_date TEXT NOT NULL,  -- Last update date
                    authors_parsed TEXT NOT NULL,  -- JSON array of parsed authors (minified)
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_download_status ON papers(download_status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_status ON papers(llm_check_status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON papers(created_at)")
            
            # Create indexes for metadata table
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metadata_categories ON metadata(categories)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metadata_update_date ON metadata(update_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metadata_doi ON metadata(doi)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metadata_created_at ON metadata(created_at)")
            
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
        # Convert arrays to JSON strings
        authors_json = json.dumps(paper_data.get('authors', []))
        categories_json = json.dumps(paper_data.get('categories', []))
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO papers (
                    arxiv_id, title, abstract, authors, categories, published_date, 
                    updated_date, url, pdf_url, doi, journal_ref, comment, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_data['arxiv_id'],
                paper_data['title'],
                paper_data.get('abstract', ''),
                authors_json,
                categories_json,
                paper_data.get('published_date', ''),
                paper_data.get('updated_date'),
                paper_data.get('url', ''),
                paper_data.get('pdf_url', ''),
                paper_data.get('doi'),
                paper_data.get('journal_ref'),
                paper_data.get('comment'),
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
                # Convert JSON fields back to Python objects
                if paper['authors']:
                    paper['authors'] = json.loads(paper['authors'])
                if paper.get('categories'):
                    paper['categories'] = json.loads(paper['categories'])
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
                # Parse JSON fields
                if paper['authors']:
                    paper['authors'] = json.loads(paper['authors'])
                if paper.get('categories'):
                    paper['categories'] = json.loads(paper['categories'])
                return paper
            
            return None
    
    def search_papers_by_category(self, category: str) -> List[Dict]:
        """Zoek papers op basis van categorie"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM papers WHERE categories LIKE ?",
                (f'%{category}%',)
            )
            papers = []
            for row in cursor.fetchall():
                paper = dict(row)
                if paper['authors']:
                    paper['authors'] = json.loads(paper['authors'])
                if paper.get('categories'):
                    paper['categories'] = json.loads(paper['categories'])
                papers.append(paper)
            return papers
    
    def get_papers_with_doi(self) -> List[Dict]:
        """Haal papers op die een DOI hebben"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM papers WHERE doi IS NOT NULL AND doi != ''"
            )
            papers = []
            for row in cursor.fetchall():
                paper = dict(row)
                if paper['authors']:
                    paper['authors'] = json.loads(paper['authors'])
                if paper.get('categories'):
                    paper['categories'] = json.loads(paper['categories'])
                papers.append(paper)
            return papers
    
    def metadata_exists(self, metadata_id: str) -> bool:
        """Check of metadata record al in database staat"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM metadata WHERE id = ?", 
                (metadata_id,)
            )
            return cursor.fetchone() is not None
    
    def insert_metadata(self, metadata_record: Dict) -> None:
        """Voeg nieuw metadata record toe aan database"""
        # Convert arrays to minified JSON strings
        versions_json = json.dumps(metadata_record.get('versions', []), separators=(',', ':'))
        authors_parsed_json = json.dumps(metadata_record.get('authors_parsed', []), separators=(',', ':'))
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO metadata (
                    id, submitter, authors, title, comments, journal_ref, doi, report_no,
                    categories, license, abstract, versions, update_date, authors_parsed,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata_record['id'],
                metadata_record.get('submitter'),  # Can be null
                metadata_record['authors'],
                metadata_record['title'],
                metadata_record.get('comments'),  # Can be null
                metadata_record.get('journal-ref'),  # Can be null (note hyphen)
                metadata_record.get('doi'),  # Can be null
                metadata_record.get('report-no'),  # Can be null (note hyphen)
                metadata_record['categories'],
                metadata_record.get('license'),  # Can be null
                metadata_record['abstract'],
                versions_json,
                metadata_record['update_date'],
                authors_parsed_json,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            conn.commit()
            
        self.logger.info(f"Metadata inserted: {metadata_record['id']}")
    
    def get_metadata_by_id(self, metadata_id: str) -> Optional[Dict]:
        """Haal specifiek metadata record op via id"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM metadata WHERE id = ?", 
                (metadata_id,)
            )
            
            row = cursor.fetchone()
            if row:
                metadata = dict(row)
                # Parse JSON fields back to Python objects
                if metadata['versions']:
                    metadata['versions'] = json.loads(metadata['versions'])
                if metadata['authors_parsed']:
                    metadata['authors_parsed'] = json.loads(metadata['authors_parsed'])
                return metadata
            
            return None
    
    def get_metadata_by_category(self, category: str) -> List[Dict]:
        """Zoek metadata records op basis van categorie"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM metadata WHERE categories LIKE ? ORDER BY update_date DESC",
                (f'%{category}%',)
            )
            records = []
            for row in cursor.fetchall():
                metadata = dict(row)
                # Parse JSON fields back to Python objects
                if metadata['versions']:
                    metadata['versions'] = json.loads(metadata['versions'])
                if metadata['authors_parsed']:
                    metadata['authors_parsed'] = json.loads(metadata['authors_parsed'])
                records.append(metadata)
            return records
    
    def get_metadata_statistics(self) -> Dict:
        """Haal metadata statistieken op"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Total metadata records
            cursor = conn.execute("SELECT COUNT(*) FROM metadata")
            stats['total_metadata'] = cursor.fetchone()[0]
            
            # Records with DOI
            cursor = conn.execute("SELECT COUNT(*) FROM metadata WHERE doi IS NOT NULL AND doi != ''")
            stats['with_doi'] = cursor.fetchone()[0]
            
            # Records without submitter
            cursor = conn.execute("SELECT COUNT(*) FROM metadata WHERE submitter IS NULL")
            stats['null_submitter'] = cursor.fetchone()[0]
            
            # Most common categories (top 10)
            cursor = conn.execute("""
                SELECT categories, COUNT(*) as count 
                FROM metadata 
                GROUP BY categories 
                ORDER BY count DESC 
                LIMIT 10
            """)
            stats['top_categories'] = dict(cursor.fetchall())
            
            return stats
    
    def search_metadata_by_title(self, title_search: str) -> List[Dict]:
        """Zoek metadata records op basis van titel"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM metadata WHERE title LIKE ? ORDER BY update_date DESC",
                (f'%{title_search}%',)
            )
            records = []
            for row in cursor.fetchall():
                metadata = dict(row)
                # Parse JSON fields back to Python objects  
                if metadata['versions']:
                    metadata['versions'] = json.loads(metadata['versions'])
                if metadata['authors_parsed']:
                    metadata['authors_parsed'] = json.loads(metadata['authors_parsed'])
                records.append(metadata)
            return records
