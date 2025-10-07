#!/usr/bin/env python3
"""
GitHub Copilot Metastudy - Main Entry Point
Uitgebreide pipeline voor paper downloading, conversie en analyse
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import main function from the package
from src.main import main

if __name__ == "__main__":
    main()
