"""
Logging configuration for ROM Librarian
"""

import os
import logging
from logging.handlers import RotatingFileHandler

# Log file location
LOG_FILE = os.path.join(os.path.expanduser("~"), ".rom_librarian.log")


def setup_logging():
    """Setup application logging with file and console handlers"""
    logger = logging.getLogger('ROMLibrarian')
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # File handler - rotating log file (10MB max, keep 3 backups)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not setup log file: {e}")

    # Console handler - only show INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


# Initialize logger
logger = setup_logging()
