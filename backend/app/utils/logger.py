import logging

from app.config import settings


def get_logger(name: str) -> logging.Logger:
    """Get configured logger."""
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(settings.LOG_LEVEL)
    return logger
