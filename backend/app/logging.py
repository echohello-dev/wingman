"""Settings-based logging setup shared by Wingman's process entrypoints.

Reuse the wide-event formatter so all entrypoints keep the same schema,
redaction and request correlation. See docs/logging.md.
"""

from app.config import settings
from app.logging_config import JsonFormatter, configure_logging as _configure_logging

__all__ = ["JsonFormatter", "configure_logging"]


def configure_logging(*, service: str = "wingman-backend") -> None:
    """Configure stdout logging; repeated calls keep a single root handler."""
    _configure_logging(
        level=settings.LOG_LEVEL,
        fmt=settings.LOG_FORMAT,
        service=service,
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
    )
