"""P19: Structured logging for MCP tools."""

import logging
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"lichess_mcp_{datetime.utcnow().strftime('%Y%m')}.log")

_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)

_logger = logging.getLogger("lichess-mcp")
_logger.setLevel(logging.DEBUG)
_logger.addHandler(_handler)
_logger.propagate = False

# P25: stderr hygiene — no StreamHandler, only FileHandler


def get_logger(name: str) -> logging.Logger:
    return _logger.getChild(name)
