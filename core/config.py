"""
Configuration and cache management for ROM Librarian
"""

import json
import os
from .constants import CONFIG_FILE, HASH_CACHE_FILE
from .logging_setup import logger


def load_config():
    """Load configuration from file"""
    defaults = {"theme": "light"}
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded configuration from {CONFIG_FILE}")
                return {**defaults, **config}
        else:
            logger.debug(f"No config file found, using defaults")
    except Exception as e:
        logger.error(f"Failed to load config from {CONFIG_FILE}: {e}")
    return defaults


def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.debug(f"Saved configuration to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Failed to save config to {CONFIG_FILE}: {e}")


def load_hash_cache():
    """Load hash cache from file"""
    try:
        if os.path.exists(HASH_CACHE_FILE):
            with open(HASH_CACHE_FILE, 'r') as f:
                cache = json.load(f)
                logger.info(f"Loaded hash cache with {len(cache)} entries from {HASH_CACHE_FILE}")
                return cache
        else:
            logger.debug("No hash cache file found, starting fresh")
    except Exception as e:
        logger.error(f"Failed to load hash cache from {HASH_CACHE_FILE}: {e}")
    return {}


def save_hash_cache(cache):
    """Save hash cache to file"""
    try:
        with open(HASH_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
        logger.debug(f"Saved hash cache with {len(cache)} entries to {HASH_CACHE_FILE}")
    except Exception as e:
        logger.error(f"Failed to save hash cache to {HASH_CACHE_FILE}: {e}")
