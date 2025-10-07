"""
GitHub Copilot Metastudy Package
Onderzoek naar AI-ondersteunde programmering via arXiv papers
"""

from src.database import PaperDatabase
from src.arxiv_client import ArxivClient
from src.pdf import PDFProcessor

__version__ = "1.0.0"
__author__ = "GitHub Copilot Metastudy Project"

__all__ = [
    'PaperDatabase',
    'ArxivClient', 
    'PDFProcessor'
]
