#!/usr/bin/env python3
"""
GitHub Copilot Metastudy - Run Script
Entry point voor het uitvoeren van de metastudy pipeline
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import and run main function
if __name__ == "__main__":
    from src.main import main
    main()
