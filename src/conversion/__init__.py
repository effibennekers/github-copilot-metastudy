"""
Conversion module voor het converteren van bestanden en beheren van tarballs.
"""

from .converter import (
    tex_naar_md,
    html_naar_md,
    pak_tarball_uit,
    verwijder_uitgepakte_tarball
)

__all__ = [
    'tex_naar_md',
    'html_naar_md', 
    'pak_tarball_uit',
    'verwijder_uitgepakte_tarball'
]
