"""
GitHub Copilot Metastudy Package
Onderzoek naar AI-ondersteunde programmering via arXiv papers
"""

from .database import PaperDatabase
from .arxiv import ArxivClient
from .pdf import PDFProcessor

__version__ = "1.0.0"
__author__ = "GitHub Copilot Metastudy Project"

__all__ = [
    'PaperDatabase',
    'ArxivClient', 
    'PDFProcessor'
]
