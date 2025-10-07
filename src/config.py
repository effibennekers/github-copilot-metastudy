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
    "max_retries": 2,
    "retry_delay_seconds": 5,
    
    # Timeout configuratie  
    "api_timeout_seconds": 30,
    "download_timeout_seconds": 60,
    "conversion_timeout_seconds": 120, # Timeout voor PDF naar Markdown conversie
    
    # Parallel processing (LET OP: Rate limiting moet gerespecteerd worden!)
    "max_concurrent_downloads": 1,  # MOET 1 blijven voor arXiv compliance
}

# ==============================================================================
# LOGGING CONFIGURATION
# Python's standaard logging configuratie (logging.config.dictConfig format)
# ==============================================================================
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'filename': 'metastudy.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf-8'
        }
    },
    'loggers': {
        'src': {  # Our package logger
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False
        }
    },
    'root': {
        'level': 'WARNING',  # Only show warnings/errors from other libraries
        'handlers': ['console']
    }
}

# LLM Configuration (voor kwaliteitscontrole en analyse)
LLM_CONFIG = {
    "enabled": False,                 # Schakel LLM kwaliteitscontrole in/uit
    "provider": "ollama",             # ollama, openai, anthropic
    "model_name": "llama3.2",         # Naam van het te gebruiken model
    "ollama_api_base_url": "http://localhost:11434", # Ollama API endpoint
    "timeout_seconds": 120,           # Timeout voor LLM requests
    "max_retries": 2,                 # Max aantal pogingen bij failures
    "retry_delay_seconds": 5,         # Wachttijd tussen pogingen
    
    # Processing settings
    "max_tokens": 4000,               # Max tokens voor LLM response
    "temperature": 0.1,               # Creativiteit van de LLM (laag voor consistentie)
    "batch_size": 5,                  # Aantal papers per batch
    "batch_delay_seconds": 10,        # Wachttijd tussen batches
    
    # Quality check prompts
    "prompt_template": """Je bent een expert in het controleren van academische papers die zijn geconverteerd van PDF naar Markdown.

Controleer de volgende Markdown tekst op:
1. Verkeerde koppen (# ## ###) - zorg dat ze logisch genest zijn
2. Gebroken tabellen - herstel tabel formatting
3. Foute lijstopmaak - corrigeer genummerde en bullet lists
4. Referentie formatting - zorg voor correcte [1], [2] notatie
5. Figuur/tabel captions - herstel "Figure 1:", "Table 2:" formatting
6. Paragraaf structuur - voeg ontbrekende line breaks toe
7. Code blocks - zorg voor correcte ``` formatting
8. Mathematical formulas - behoud LaTeX notatie waar mogelijk

BELANGRIJKE REGELS:
- Behoud ALLE originele inhoud en betekenis
- Verander GEEN wetenschappelijke termen of concepten
- Voeg GEEN nieuwe informatie toe
- Focus alleen op Markdown opmaak verbetering
- Als de tekst al goed geformatteerd is, verander dan niets

Antwoord ALLEEN met de gecorrigeerde Markdown, geen extra uitleg of commentaar.""",
    
    # Analysis prompts voor verschillende aspecten
    "summary_prompt": "Maak een korte samenvatting van deze paper in het Nederlands:",
    "keyword_extraction_prompt": "Extraheer de belangrijkste keywords uit deze paper:",
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
