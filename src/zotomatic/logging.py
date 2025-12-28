# src/zotomatic/logging.py
import logging
import sys


def get_logger(name: str = "zotomatic", verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        if verbose:
            handler = logging.StreamHandler(sys.stderr)
            fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            handler.setFormatter(logging.Formatter(fmt))
        else:
            handler = logging.NullHandler()
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    return logger
