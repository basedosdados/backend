# -*- coding: utf-8 -*-
from logging import Handler, LogRecord, __file__, currentframe, getLogger, root
from sys import stdout

from loguru import logger


class InterceptHandler(Handler):
    """Intercepts standard logging records and emits them with loguru"""

    def emit(self, record: LogRecord):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname)
            level = level.name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = currentframe(), 2
        while frame.f_code.co_filename == __file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logger(
    level: str = "INFO",
    serialize: bool = False,
    format: str = "[{time:YYYY-MM-DD HH:mm:ss}] <lvl>{message}</>",
):
    root.handlers = [InterceptHandler()]
    root.setLevel("DEBUG")

    for name in root.manager.loggerDict.keys():
        getLogger(name).handlers = []
        getLogger(name).propagate = True

    logger.remove()

    logger.add(
        stdout,
        level=level,
        format=format,
        serialize=serialize,
    )
    logger.add(
        "debug.log",
        level="DEBUG",
        format=format,
        rotation="30 MB",
        retention="7 days",
    )
