#!/usr/bin/env python3
"""Initialize database tables."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.storage import init_db
from apps.common import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")
