"""
Conversion module voor het converteren van bestanden.
"""

from .tex_converter import tex_naar_md
from .pdf_converter import pdf_naar_md

__all__ = [
    "tex_naar_md",
    "pdf_naar_md",
]
