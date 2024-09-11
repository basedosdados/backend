# -*- coding: utf-8 -*-
from logging import Handler, LogRecord, __file__, currentframe, getLogger, root
from os import getenv
from sys import stdout

from loguru import logger

LOGGER_LEVEL = getenv("LOGGER_LEVEL", "DEBUG")
LOGGER_IGNORE = getenv("LOGGER_IGNORE", "").split(",")
LOGGER_SERIALIZE = bool(getenv("LOGGER_SERIALIZE", False))
LOGGER_FORMAT = "[{time:YYYY-MM-DD HH:mm:ss}] <lvl>{message}</>"


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


def setup_logger(logging_settings=None):
    root.handlers = [InterceptHandler()]
    root.setLevel(LOGGER_LEVEL)

    for name in root.manager.loggerDict.keys():
        getLogger(name).handlers = []
        getLogger(name).propagate = True
        if name in LOGGER_IGNORE:
            getLogger(name).setLevel("WARNING")

    logger.remove()
    logger.configure(
        handlers=[
            {
                "sink": stdout,
                "level": LOGGER_LEVEL,
                "format": LOGGER_FORMAT,
                "serialize": LOGGER_SERIALIZE,
            },
        ],
    )

    return logger
