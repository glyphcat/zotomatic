from __future__ import annotations

import logging

from zotomatic.logging import get_logger


def test_get_logger_non_verbose_adds_null_handler() -> None:
    logger = get_logger("zotomatic.test.null", verbose=False)
    assert logger.handlers
    assert isinstance(logger.handlers[0], logging.NullHandler)
    assert logger.propagate is False


def test_get_logger_verbose_adds_stream_handler() -> None:
    logger = get_logger("zotomatic.test.stream", verbose=True)
    assert logger.handlers
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert logger.level == logging.DEBUG
