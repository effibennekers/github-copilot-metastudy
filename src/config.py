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
        "neural code completion",
    ],
    # Maximum aantal resultaten per zoekterm
    "max_results_per_query": 20,
    # Totaal maximum aantal papers om te processsen (veiligheidsbeperking)
    "total_max_papers": 200,
}

# Database Configuration (PostgreSQL only)
DATABASE_CONFIG = {
    "pg": {"host": "0.0.0.0", "port": 5432, "dbname": "arxiv", "user": "arxiv", "password": "arxiv"}
}

# File Storage Configuration
STORAGE_CONFIG = {
    # Directories die daadwerkelijk gebruikt worden
    "pdf_directory": "data/pdf",
    "markdown_directory": "data/md",
    # Minimum grootte voor geldig markdown bestand
    "min_markdown_size_bytes": 100,
}

# Processing Configuration
PROCESSING_CONFIG = {
    # Rate limiting (VERPLICHT - arXiv Terms of Use)
    "api_rate_limit_seconds": 3,
    "download_rate_limit_seconds": 3,
    # Timeout voor PDF downloads
    "download_timeout_seconds": 60,
}

# Download Workflow Configuration
DOWNLOAD_CONFIG = {
    # Maximaal aantal items om te downloaden in één run
    "max_items": 10,
    # Doelmap voor tarball downloads (relatief aan project root)
    "tarball_directory": "data/tarball",
}

# ==============================================================================
# LOGGING CONFIGURATION
# Python's standaard logging configuratie (logging.config.dictConfig format)
# ==============================================================================
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": (
                "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": "metastudy.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "src": {  # Our package logger
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        }
    },
    "root": {
        "level": "WARNING",  # Only show warnings/errors from other libraries
        "handlers": ["console"],
    },
}

# LLM Configuration (gesplitst: general, ollama, vertex)
LLM_GENERAL_CONFIG = {
    "batch_size": 2,
    # Provider: 'ollama' of 'vertex'
    "provider": "vertex",
}

LLM_OLLAMA_CONFIG = {
    # Modelnaam voor Ollama backend
    "model_name": "gemma3:12b-it-qat",
    "api_base_url": "http://localhost:11434",
    "temperature": 0.1,
    "format": "json",
    "num_predict": 4096,
    "top_p": 0.9,
    "top_k": 40,
    # Concurrency limiet voor Ollama requests (globaal per proces)
    "batch_size": 2,
    # Maximum aantal karakters per chunk voor de LLM converter
    "max_chars_per_chunk": 12000,
}

LLM_VERTEX_CONFIG = {
    # Authenticatie via gcloud ADC (application-default credentials)
    "project": "bennekers",
    "location": "europe-west4",
    # Modelnaam voor Vertex AI backend
    "model_name": "gemini-2.5-flash",
    # Optioneel: API versie configureren
    "api_version": "v1",
    # Tuning opties voor Vertex AI (GenerateContentConfig)
    "temperature": 0.1,
    "top_p": 0.9,
    "top_k": 40,
    # Equivalent aan max tokens voor output
    "max_output_tokens": 4096,
    # Concurrency limiet voor Vertex requests (globaal per proces)
    "batch_size": 4,
    # Maximum aantal karakters per chunk voor de LLM converter
    "max_chars_per_chunk": 20000,
}

# User Interface Configuration
UI_CONFIG = {"show_progress_bars": True, "show_statistics": True}

# Export deze configuraties voor gemakkelijke import
__all__ = [
    "SEARCH_CONFIG",
    "DATABASE_CONFIG",
    "STORAGE_CONFIG",
    "PROCESSING_CONFIG",
    "DOWNLOAD_CONFIG",
    "LOGGING_CONFIG",
    "LLM_GENERAL_CONFIG",
    "LLM_OLLAMA_CONFIG",
    "LLM_VERTEX_CONFIG",
    "UI_CONFIG",
]
