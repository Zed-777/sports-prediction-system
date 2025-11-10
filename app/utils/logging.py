"""
Logging configuration and utilities
"""

import json
import logging
import logging.config
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """

    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_entry['correlation_id'] = getattr(record, 'correlation_id', None)

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(level: str = 'INFO', config: Optional[Dict[str, Any]] = None):
    """
    Set up logging configuration for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        config: Logging configuration dictionary
    """
    if config is None:
        config = {}

    # Ensure logs directory exists
    logs_dir = Path(config.get('location', 'logs'))
    logs_dir.mkdir(exist_ok=True)

    # Determine if we should use JSON formatting
    use_json = config.get('format', 'json') == 'json'

    # Create formatters
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # Create handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # File handler
    file_handler = logging.FileHandler(
        logs_dir / 'sports_prediction.log',
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    handlers.append(file_handler)

    # Error file handler
    error_handler = logging.FileHandler(
        logs_dir / 'sports_prediction_errors.log',
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    handlers.append(error_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        force=True
    )

    # Set up correlation ID context
    if config.get('correlation_ids', True):
        setup_correlation_id_filter()


def setup_correlation_id_filter():
    """
    Set up correlation ID filter for request tracing
    """
    # Simplified implementation without thread locals
    pass


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set correlation ID for the current context
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """
    Get current correlation ID
    """
    return None


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    """
    return logging.getLogger(name)
