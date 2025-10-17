import logging
import sys
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Get a logger instance with the specified name."""
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger
