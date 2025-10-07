"""
PDF Processor voor GitHub Copilot Metastudy
Handles PDF download en conversie naar Markdown
"""

import requests
import time
import subprocess
import logging
from pathlib import Path
from typing import Optional
import hashlib

# Import configuratie
import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import STORAGE_CONFIG, PROCESSING_CONFIG

class PDFProcessor:
    def __init__(self, pdf_dir: str = None, md_dir: str = None):
        self.pdf_dir = Path(pdf_dir or STORAGE_CONFIG['pdf_directory'])
        self.md_dir = Path(md_dir or STORAGE_CONFIG['markdown_directory'])
        self.logger = logging.getLogger(__name__)
        self.last_download_time = 0
        
        # Load processing configuration
        self.processing_config = PROCESSING_CONFIG
        self.storage_config = STORAGE_CONFIG
        
        # Ensure directories exist
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.md_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"PDF Processor initialized - PDF: {self.pdf_dir}, MD: {self.md_dir}")
        self.logger.info(f"Rate limiting: {self.processing_config['download_rate_limit_seconds']}s between downloads")
    
    def _enforce_download_rate_limit(self):
        """
        VERPLICHTE RATE LIMITING: configureerbare seconden tussen downloads
        Bron: https://info.arxiv.org/help/api/tou.html
        """
        rate_limit = self.processing_config['download_rate_limit_seconds']
        current_time = time.time()
        time_since_last = current_time - self.last_download_time
        
        if time_since_last < rate_limit:
            sleep_time = rate_limit - time_since_last
            self.logger.info(f"Download rate limiting: wachten {sleep_time:.1f} seconden")
            time.sleep(sleep_time)
        
        self.last_download_time = time.time()
    
    def download_pdf(self, arxiv_id: str, pdf_url: str) -> Optional[str]:
        """
        Download PDF met rate limiting compliance
        VERPLICHT: 3 seconden tussen downloads
        """
        pdf_path = self.pdf_dir / f"{arxiv_id}.pdf"
        
        # Check if PDF already exists
        if pdf_path.exists():
            file_size = pdf_path.stat().st_size
            min_size = self.storage_config['min_pdf_size_kb'] * 1024
            max_size = self.storage_config['max_pdf_size_mb'] * 1024 * 1024
            
            if min_size <= file_size <= max_size:
                self.logger.info(f"PDF already exists: {pdf_path} ({file_size} bytes)")
                return str(pdf_path)
            else:
                self.logger.warning(f"Existing PDF size invalid ({file_size} bytes), re-downloading: {pdf_path}")
                pdf_path.unlink()  # Remove invalid file
        
        try:
            # VERPLICHTE RATE LIMITING
            self._enforce_download_rate_limit()
            
            self.logger.info(f"Downloading PDF: {arxiv_id} from {pdf_url}")
            
            # Download with proper headers and timeout
            headers = {
                'User-Agent': 'GitHub-Copilot-Metastudy/1.0 (research paper analysis)'
            }
            
            timeout = self.processing_config['download_timeout_seconds']
            response = requests.get(pdf_url, headers=headers, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Check if response is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type:
                self.logger.error(f"Response is not a PDF: {content_type}")
                return None
            
            # Write PDF to file
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Verify file was written and has reasonable size
            min_size = self.storage_config['min_pdf_size_kb'] * 1024
            max_size = self.storage_config['max_pdf_size_mb'] * 1024 * 1024
            
            if pdf_path.exists() and min_size <= pdf_path.stat().st_size <= max_size:
                self.logger.info(f"PDF downloaded successfully: {pdf_path} ({pdf_path.stat().st_size} bytes)")
                return str(pdf_path)
            else:
                size = pdf_path.stat().st_size if pdf_path.exists() else 0
                self.logger.error(f"PDF download failed or invalid size: {pdf_path} ({size} bytes)")
                if pdf_path.exists():
                    pdf_path.unlink()
                return None
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error downloading PDF {arxiv_id}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error downloading PDF {arxiv_id}: {e}")
            return None
    
    def pdf_to_markdown(self, pdf_path: str, arxiv_id: str) -> Optional[str]:
        """Convert PDF to Markdown using pandoc"""
        md_path = self.md_dir / f"{arxiv_id}.md" 
        
        # Check if Markdown already exists
        if md_path.exists():
            file_size = md_path.stat().st_size
            min_size = self.storage_config['min_markdown_size_bytes']
            
            if file_size >= min_size:
                self.logger.info(f"Markdown already exists: {md_path} ({file_size} bytes)")
                return str(md_path)
            else:
                self.logger.warning(f"Existing markdown too small, reconverting: {md_path}")
                md_path.unlink()
        
        # Check if source PDF exists
        if not Path(pdf_path).exists():
            self.logger.error(f"Source PDF not found: {pdf_path}")
            return None
        
        try:
            self.logger.info(f"Converting PDF to Markdown: {arxiv_id}")
            
            # Try pandoc first if preferred and available
            if self.processing_config.get('prefer_pandoc', True) and self._has_pandoc():
                return self._convert_with_pandoc(pdf_path, md_path, arxiv_id)
            else:
                # Fallback to pdfplumber
                self.logger.warning("Using pdfplumber for conversion")
                return self._convert_with_pdfplumber(pdf_path, md_path, arxiv_id)
                
        except Exception as e:
            self.logger.error(f"PDF to Markdown conversion failed for {arxiv_id}: {e}")
            return None
    
    def _has_pandoc(self) -> bool:
        """Check if pandoc is available"""
        try:
            result = subprocess.run(['pandoc', '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _convert_with_pandoc(self, pdf_path: str, md_path: Path, arxiv_id: str) -> Optional[str]:
        """Convert PDF using pandoc"""
        try:
            # Get pandoc options from config
            pandoc_options = self.processing_config.get('pandoc_options', ["--wrap=none", "--extract-media=."])
            
            cmd = ['pandoc', pdf_path, '-o', str(md_path)] + pandoc_options + ['-t', 'markdown']
            
            timeout = self.processing_config['conversion_timeout_seconds']
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=timeout)
            
            if result.returncode == 0 and md_path.exists():
                file_size = md_path.stat().st_size
                self.logger.info(f"Pandoc conversion successful: {md_path} ({file_size} bytes)")
                return str(md_path)
            else:
                self.logger.error(f"Pandoc conversion failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Pandoc conversion timeout for {arxiv_id}")
            return None
        except Exception as e:
            self.logger.error(f"Pandoc conversion error: {e}")
            return None
    
    def _convert_with_pdfplumber(self, pdf_path: str, md_path: Path, arxiv_id: str) -> Optional[str]:
        """Fallback conversion using pdfplumber"""
        try:
            import pdfplumber
            
            with pdfplumber.open(pdf_path) as pdf:
                text_content = []
                
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        text_content.append(f"## Page {page_num + 1}\n\n{text}\n\n")
                
                if text_content:
                    markdown_content = f"# {arxiv_id}\n\n" + "".join(text_content)
                    
                    with open(md_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                    
                    file_size = md_path.stat().st_size
                    self.logger.info(f"PDFPlumber conversion successful: {md_path} ({file_size} bytes)")
                    return str(md_path)
                else:
                    self.logger.error(f"No text extracted from PDF: {arxiv_id}")
                    return None
                    
        except ImportError:
            self.logger.error("pdfplumber not available - install with: pip install pdfplumber")
            return None
        except Exception as e:
            self.logger.error(f"PDFPlumber conversion error: {e}")
            return None
    
    def get_file_info(self, file_path: str) -> dict:
        """Get information about a file"""
        path = Path(file_path)
        
        if not path.exists():
            return {'exists': False}
        
        stat = path.stat()
        
        # Calculate file hash for integrity checking
        with open(path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        return {
            'exists': True,
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'hash': file_hash
        }
    
    def cleanup_failed_files(self):
        """Remove files that are too small or corrupted"""
        cleaned = 0
        
        # Clean PDFs that don't meet size requirements
        min_pdf_size = self.storage_config['min_pdf_size_kb'] * 1024
        max_pdf_size = self.storage_config['max_pdf_size_mb'] * 1024 * 1024
        
        for pdf_file in self.pdf_dir.glob("*.pdf"):
            size = pdf_file.stat().st_size
            if not (min_pdf_size <= size <= max_pdf_size):
                self.logger.info(f"Removing invalid PDF: {pdf_file} ({size} bytes)")
                pdf_file.unlink()
                cleaned += 1
        
        # Clean Markdown files that are too small
        min_md_size = self.storage_config['min_markdown_size_bytes']
        for md_file in self.md_dir.glob("*.md"):
            if md_file.stat().st_size < min_md_size:
                self.logger.info(f"Removing small Markdown: {md_file}")
                md_file.unlink()
                cleaned += 1
        
        self.logger.info(f"Cleanup completed: {cleaned} files removed")
