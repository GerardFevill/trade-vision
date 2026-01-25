"""Centralized logging configuration using loguru"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import settings


def setup_logging():
    """Configure logging based on settings"""
    # Remove default handler
    logger.remove()

    # Console format
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # JSON format for structured logging
    json_format = (
        '{{"timestamp":"{time:YYYY-MM-DDTHH:mm:ss.SSSZ}",'
        '"level":"{level}",'
        '"logger":"{name}",'
        '"function":"{function}",'
        '"line":{line},'
        '"message":"{message}",'
        '"extra":{extra}}}'
    )

    # Add console handler
    if settings.log_format == "json":
        logger.add(
            sys.stdout,
            format=json_format,
            level=settings.log_level,
            colorize=False,
            serialize=True
        )
    else:
        logger.add(
            sys.stdout,
            format=console_format,
            level=settings.log_level,
            colorize=True
        )

    # Add file handler if configured
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            settings.log_file,
            format=json_format if settings.log_format == "json" else console_format,
            level=settings.log_level,
            rotation="10 MB",
            retention="7 days",
            compression="gz",
            serialize=settings.log_format == "json"
        )

    logger.info(
        "Logging configured",
        level=settings.log_level,
        format=settings.log_format,
        file=settings.log_file
    )


# Initialize logging on import
setup_logging()

# Re-export logger for convenience
__all__ = ["logger", "setup_logging"]
