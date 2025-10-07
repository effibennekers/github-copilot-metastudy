"""
Configuratie voor GitHub Copilot Metastudy
Alle aanpasbare parameters voor het systeem
"""

# ArXiv Search Configuration
SEARCH_CONFIG = {
    # Zoektermen voor verschillende aspecten van AI-assisted programming
    "queries": [
        "GitHub Copilot",
        "AI code generation", 
        "programming assistant AI",
        "automated code completion",
        "copilot programming",
        "AI pair programming",
        "code completion AI",
        "intelligent code assistance",
        "LLM code generation",
        "neural code completion"
    ],
    
    # Maximum aantal resultaten per zoekterm
    "max_results_per_query": 20,
    
    # Totaal maximum aantal papers om te processsen (veiligheidsbeperking)
    "total_max_papers": 200,
    
    # ArXiv sorteer criteria
    "sort_by": "submittedDate",  # submittedDate, lastUpdatedDate, relevance
    
    # Filter op datum (optioneel)
    "date_filter": {
        "enabled": False,
        "start_date": "2020-01-01",  # YYYY-MM-DD format
        "end_date": None  # None voor huidige datum
    }
}

# Database Configuration  
DATABASE_CONFIG = {
    "db_path": "data/papers.db",
    "backup_enabled": True,
    "backup_frequency": "daily"  # daily, weekly, monthly
}

# File Storage Configuration
STORAGE_CONFIG = {
    "pdf_directory": "data/pdf",
    "markdown_directory": "data/md", 
    "backup_directory": "data/backups",
    
    # Bestandsgroottes
    "max_pdf_size_mb": 50,  # Maximum PDF grootte in MB
    "min_pdf_size_kb": 1,   # Minimum PDF grootte in KB (filter voor lege bestanden)
    "min_markdown_size_bytes": 100  # Minimum Markdown grootte in bytes
}

# Processing Configuration
PROCESSING_CONFIG = {
    # Rate limiting (VERPLICHT - arXiv Terms of Use)
    "api_rate_limit_seconds": 3,
    "download_rate_limit_seconds": 3,
    
    # Retry configuratie
    "max_retries": 3,
    "retry_delay_seconds": 5,
    
    # Timeout configuratie  
    "api_timeout_seconds": 30,
    "download_timeout_seconds": 60,
    "conversion_timeout_seconds": 120,
    
    # Conversion preferences
    "prefer_pandoc": True,  # Probeer pandoc eerst, fallback naar pdfplumber
    "pandoc_options": ["--wrap=none", "--extract-media=."],
    
    # Parallel processing (LET OP: Rate limiting moet gerespecteerd worden!)
    "max_concurrent_downloads": 1,  # MOET 1 blijven voor arXiv compliance
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_enabled": True,
    "file_path": "metastudy.log",
    "console_enabled": True,
    "max_file_size_mb": 10,
    "backup_count": 5
}

# LLM Configuration (Optioneel - voor toekomstige uitbreiding)
LLM_CONFIG = {
    "enabled": False,
    "provider": "ollama",  # ollama, openai, anthropic
    "model": "llama3.2",
    "api_url": "http://localhost:11434",
    "timeout_seconds": 120,
    "max_retries": 2,
    
    # Quality check prompts
    "quality_check_prompt": """
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
""".strip()
}

# User Interface Configuration
UI_CONFIG = {
    "show_progress_bars": True,
    "show_statistics": True,
    "colored_output": True,
    "verbose_logging": False
}

# Export deze configuraties voor gemakkelijke import
__all__ = [
    'SEARCH_CONFIG',
    'DATABASE_CONFIG', 
    'STORAGE_CONFIG',
    'PROCESSING_CONFIG',
    'LOGGING_CONFIG',
    'LLM_CONFIG',
    'UI_CONFIG'
]
