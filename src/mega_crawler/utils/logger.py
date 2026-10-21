import sys

from loguru import logger

from mega_crawler.utils.safety import redact


def configure_logging(settings):
    logger.remove()

    def clean(record):
        record["message"] = redact(record["message"], settings.secrets())
        record["extra"] = {}
        record["exception"] = None
        return True

    logger.add(sys.stderr, filter=clean, format="{time:HH:mm:ss} | {level} | {message}")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        settings.data_dir / "logs/goldintel.log",
        rotation="5 MB",
        retention="7 days",
        filter=clean,
        format="{time} | {level} | {message}",
        diagnose=False,
        backtrace=False,
    )
