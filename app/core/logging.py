"""
Logging configuration for HushMonitor.

Sets up structured JSON logging with:
- File output to logs/app.log
- Console output for warnings/errors
- JSON format for easy parsing
"""

import logging
import sys
from pathlib import Path

from pythonjsonlogger import jsonlogger


def setup_logging() -> logging.Logger:
    """
    Configure structured JSON logging.
    
    - INFO+ logs go to logs/app.log
    - WARNING+ logs go to stderr (console)
    - JSON format with timestamp, level, event, context
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers = []
    
    # JSON formatter
    formatter = jsonlogger.JsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s",
        rename_fields={"levelname": "level", "name": "logger"},
        timestamp=True
    )
    
    # Handler 1: File output
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    file_handler = logging.FileHandler(log_dir / "app.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler 2: Console (WARNING+ only)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Reduce verbosity of external libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with specific name."""
    return logging.getLogger(name)
