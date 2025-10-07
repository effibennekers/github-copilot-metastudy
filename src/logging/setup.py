"""
Logging setup en configuratie module
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from ..config import LOGGING_CONFIG


def setup_logging(config: Optional[dict] = None) -> None:
    """
    Setup logging configuratie uit config
    
    Args:
        config: Optional logging config dict, gebruikt LOGGING_CONFIG als None
    """
    log_config = config or LOGGING_CONFIG
    
    # Create formatters
    formatter = logging.Formatter(
        log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # Setup handlers
    handlers = []
    
    # Console handler
    if log_config.get('console_enabled', True):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    # File handler with rotation
    if log_config.get('file_enabled', True):
        file_path = log_config.get('file_path', 'metastudy.log')
        max_bytes = log_config.get('max_file_size_mb', 10) * 1024 * 1024
        backup_count = log_config.get('backup_count', 5)
        
        # Ensure log directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_config.get('level', 'INFO')),
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    # Log successful setup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={log_config.get('level', 'INFO')}, "
                f"console={log_config.get('console_enabled', True)}, "
                f"file={log_config.get('file_enabled', True)}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with consistent naming
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def set_log_level(level: str) -> None:
    """
    Dynamically change the log level for all loggers
    
    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Update root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Update all handlers  
    for handler in root_logger.handlers:
        handler.setLevel(log_level)
    
    logger = get_logger(__name__)
    logger.info(f"Log level changed to: {level.upper()}")


def add_file_handler(file_path: str, level: str = "INFO") -> None:
    """
    Add an additional file handler for specific logging needs
    
    Args:
        file_path: Path to log file
        level: Log level for this handler
    """
    # Ensure directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Create handler
    handler = logging.FileHandler(file_path, encoding='utf-8')
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Set formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    
    logger = get_logger(__name__)
    logger.info(f"Added file handler: {file_path} (level: {level})")


def configure_module_logger(module_name: str, level: str = None) -> logging.Logger:
    """
    Configure a specific module logger with optional level override
    
    Args:
        module_name: Name of the module
        level: Optional log level override for this module
        
    Returns:
        Configured logger for the module
    """
    logger = get_logger(module_name)
    
    if level:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        logger.info(f"Module logger '{module_name}' configured with level: {level}")
    
    return logger
