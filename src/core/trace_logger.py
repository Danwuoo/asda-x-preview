import structlog

logger = structlog.get_logger()


def log_trace(message: str, **kwargs) -> None:
    """Simple wrapper around structlog logger."""
    logger.info(message, **kwargs)
