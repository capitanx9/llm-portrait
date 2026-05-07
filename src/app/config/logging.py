"""Project-wide logging setup.

Bootstraps loguru as the single sink for everything that calls into the
stdlib `logging` module — Django, DRF, Channels, Celery, daphne, gunicorn.
The module is imported once from `manage.py`, `wsgi.py` and `asgi.py` so
the redirection happens before any of those frameworks emit their first
log record.

In dev (`LOG_FORMAT=human`, the default) loguru prints colored, human
readable lines with module:line and bound context. In prod
(`LOG_FORMAT=json`) every record is serialized as JSON so log aggregators
can parse it.

Per-request context (request id, user) is attached by the request-id
middleware via `logger.contextualize(...)`; the format strings below
include `extra[request_id]` so the value shows up in every line emitted
during that request.
"""

from __future__ import annotations

import logging
import os
import sys
from types import FrameType
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from loguru import Record

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.environ.get("LOG_FORMAT", "human").lower()

_HUMAN_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<magenta>request_id={extra[request_id]}</magenta> | "
    "<level>{message}</level>"
)


class InterceptHandler(logging.Handler):
    """Forward every stdlib `logging` record to loguru.

    Django, DRF, Channels, daphne, celery and gunicorn all log through
    `logging.getLogger(...)`. Installing this as the root handler makes
    them all appear in loguru's single stream with consistent formatting
    instead of three different log shapes mixed together.
    """

    def emit(self, record: logging.LogRecord) -> None:
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Walk the stack until we leave the logging module so the loguru
        # frame info points at the real caller, not at the handler itself.
        frame: FrameType | None = sys._getframe(6)
        depth = 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _patch_extra(record: Record) -> None:
    """Make {extra[request_id]} safe even outside a request scope.

    Without this, log calls that happen at startup (or in tasks that
    don't bind a request id) would crash the formatter with KeyError.
    """
    record["extra"].setdefault("request_id", "-")


def configure_logging() -> None:
    """Idempotent: install the loguru sink and route stdlib logging into it."""
    # Loguru ships with one default stderr handler; remove it so we install
    # exactly the sinks we want and don't double-print.
    logger.remove()

    logger.configure(patcher=_patch_extra)

    if LOG_FORMAT == "json":
        # serialize=True asks loguru to dump each record as a JSON object,
        # which is what production log shippers want.
        logger.add(sys.stdout, level=LOG_LEVEL, serialize=True, backtrace=False)
    else:
        logger.add(
            sys.stdout,
            level=LOG_LEVEL,
            format=_HUMAN_FORMAT,
            colorize=True,
            backtrace=False,
        )

    # Replace stdlib root handler so every framework logger funnels here.
    # Each library's named logger (django, daphne, celery, ...) propagates
    # up to root by default; with the InterceptHandler installed at the
    # root they all end up in loguru without per-logger configuration.
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Some loggers attach their own handlers on first use (notably daphne's
    # runserver access logger and channels). Without clearing those, every
    # access line shows up twice — once via loguru, once via the library's
    # original stream handler. Strip the handlers and force propagation so
    # the message reaches root once.
    for name in (
        "daphne",
        "daphne.server",
        "daphne.management.commands.runserver",
        "daphne.http_protocol",
        "daphne.ws_protocol",
        "channels",
        "channels.server",
    ):
        named_logger = logging.getLogger(name)
        named_logger.handlers = []
        named_logger.propagate = True
