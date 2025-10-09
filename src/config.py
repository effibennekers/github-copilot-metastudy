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
    "total_max_papers": 200
}

# Database Configuration  
DATABASE_CONFIG = {
    "db_path": "data/papers.db"
}

# File Storage Configuration
STORAGE_CONFIG = {
    # Directories die daadwerkelijk gebruikt worden
    "pdf_directory": "data/pdf",
    "markdown_directory": "data/md",
    
    # Minimum grootte voor geldig markdown bestand
    "min_markdown_size_bytes": 100
}

# Processing Configuration
PROCESSING_CONFIG = {
    # Rate limiting (VERPLICHT - arXiv Terms of Use)
    "api_rate_limit_seconds": 3,
    "download_rate_limit_seconds": 3,
    
    # Timeout voor PDF downloads
    "download_timeout_seconds": 60
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
    "enabled": True,
    "model_name": "llama3.2",
    "ollama_api_base_url": "http://localhost:11434",
    "temperature": 0.1,
    "batch_size": 5,
    "batch_delay_seconds": 10,
    
    # Quality check prompt template
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

Antwoord ALLEEN met de gecorrigeerde Markdown, geen extra uitleg of commentaar."""
}

# User Interface Configuration
UI_CONFIG = {
    "show_progress_bars": True,
    "show_statistics": True
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
