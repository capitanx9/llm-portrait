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
middleware via `logger.contextualize(...)`; the human format always
prints `request_id=...`, and any extra fields bound on a specific log
call (`logger.info(..., room=..., user=...)`) are auto-rendered as
`key=value` pairs by `_human_format` without listing them up front.
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

_HUMAN_BASE = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<magenta>request_id={extra[request_id]}</magenta>"
)


def _human_format(record: Record) -> str:
    """Build the human-format template, including any user-bound extras.

    Loguru's static format string can only render extras whose keys are
    listed up front (`{extra[room]}` etc.). That worked for the fixed
    `request_id` field, but every other `logger.bind(...)` field
    (room/user/length/method/status/duration_ms — anything we attach to
    a structured event) ended up invisible in the human-format log,
    visible only in `LOG_FORMAT=json`.

    Using a `format=` callable lets us inspect `record["extra"]` and
    generate a `key=value` suffix for whichever extras this particular
    record carries. The output is still a *template string* (loguru
    interpolates `{message}` etc. itself), so colour tags are preserved
    and the JSON sink is unaffected.
    """
    suffix = " ".join(
        f"<yellow>{key}={{extra[{key}]}}</yellow>" for key in record["extra"] if key != "request_id"
    )
    body = f"{_HUMAN_BASE}{(' | ' + suffix) if suffix else ''} | <level>{{message}}</level>"
    # When format is a callable loguru does NOT auto-append the exception
    # block, so add it explicitly — otherwise tracebacks vanish in dev.
    return body + "\n{exception}"


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
            format=_human_format,
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
