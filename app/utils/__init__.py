"""
Structured logging utility for the backend.
Replaces print() statements with proper logging.
"""
import logging
import sys
from datetime import datetime


# Configure root logger
def setup_logger(name: str = "barbersync", level: int = logging.INFO) -> logging.Logger:
    """Create and configure a logger instance."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(level)
        
        # Console handler with formatting
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        # Format: [2024-01-15 10:30:45] [INFO] [module] message
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


# Default logger instance
logger = setup_logger()


def log_info(message: str, module: str = None):
    """Log an info message."""
    if module:
        setup_logger(module).info(message)
    else:
        logger.info(message)


def log_error(message: str, error: Exception = None, module: str = None):
    """Log an error message with optional exception details."""
    log = setup_logger(module) if module else logger
    if error:
        log.error(f"{message}: {str(error)}")
    else:
        log.error(message)


def log_warning(message: str, module: str = None):
    """Log a warning message."""
    if module:
        setup_logger(module).warning(message)
    else:
        logger.warning(message)


def log_debug(message: str, module: str = None):
    """Log a debug message."""
    if module:
        setup_logger(module).debug(message)
    else:
        logger.debug(message)
