import logging

import structlog

from app.core.config import settings


class _NoisyEndpointFilter(logging.Filter):
    """Drop uvicorn access logs for health/metrics polling endpoints."""

    NOISY_PATHS: tuple[str, ...] = ("/health", "/ready", "/metrics")

    def filter(self, record: logging.LogRecord) -> bool:
        return not any(path in record.getMessage() for path in self.NOISY_PATHS)


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    logging.getLogger("uvicorn.access").addFilter(_NoisyEndpointFilter())
