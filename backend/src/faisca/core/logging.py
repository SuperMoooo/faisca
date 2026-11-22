"""Structured logging for the whole app: key=value locally, one JSON object per line in production.

structlog renders the events; the standard library still carries them, so
uvicorn's and httpx's own log lines come out in the same format.
"""

import logging.config

import structlog

from faisca.core.config import Settings

# Processors every log line goes through, whether it was logged with
# structlog or with the standard library.
_SHARED_PROCESSORS: list[structlog.typing.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
]


def configure_logging(settings: Settings) -> None:
    """Routes every logger, uvicorn's included, through one structlog formatter."""
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if settings.is_production
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    logging.config.dictConfig(
        {
            "version": 1,
            # Keep loggers that libraries created at import time; otherwise
            # their messages would silently disappear.
            "disable_existing_loggers": False,
            "formatters": {
                "structured": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": [
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        renderer,
                    ],
                    "foreign_pre_chain": _SHARED_PROCESSORS,
                },
            },
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "structured"},
            },
            "root": {"handlers": ["console"], "level": settings.log_level},
            "loggers": {
                # uvicorn installs its own handlers; route them to ours instead.
                "uvicorn": {"handlers": ["console"], "propagate": False},
                "uvicorn.access": {"handlers": ["console"], "propagate": False},
                # httpx logs every request at INFO; the search logs say enough.
                "httpx": {"level": "WARNING"},
            },
        }
    )
    structlog.configure(
        processors=[
            *_SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
