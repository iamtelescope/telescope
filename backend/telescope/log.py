import os
import json
import logging


DEFAULT_FORMAT = (
    "%(asctime)s\t"
    "%(process)-6d\t"
    "%(threadName)-10s\t"
    "%(funcName)-30s\t"
    "%(name)-30s\t"
    "%(levelname)-8s\t"
    "%(message)s"
)

DEV_SEPARATOR = "-" * 80
DEV_FORMAT = (
    "%(asctime)s "
    "%(process)d "
    "%(threadName)s "
    "%(funcName)s "
    "%(name)-30s "
    "%(levelname)-8s\n"
    "%(message)s\n"
    f"{DEV_SEPARATOR}"
)


class JsonFormatter(logging.Formatter):
    def __init__(self):
        super(JsonFormatter, self).__init__()

    def format(self, record):
        result = {
            "timestamp": record.created,
            "msg": record.getMessage(),
            "stack_trace": "",
            "level": record.levelname,
            "logger_name": record.name,
            "pid": record.process,
            "thread_name": (
                record.processName
                if record.processName != "MainProcess"
                else record.threadName
            ),
            "uptime_milliseconds": record.relativeCreated,
            "rest": {},
        }

        if record.exc_info:
            result["stack_trace"] = self.formatException(record.exc_info)

        if record.args and isinstance(record.args, dict):
            result["rest"].update(record.args)

        return json.dumps(result, ensure_ascii=False)


class LogConfig:
    def __init__(
        self,
        config,
    ):
        self.config = config

    @property
    def handlers(self):
        return {
            "telescope": {
                "level": self.config.get("level", "DEBUG"),
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "filters": [],
            }
        }

    @property
    def formatters(self):
        formatters = {}
        fmt = self.config.get("format", "default")

        if fmt == "default":
            formatters["standard"] = {
                "format": DEFAULT_FORMAT,
            }
        elif fmt == "dev":
            formatters["standard"] = {
                "format": DEV_FORMAT,
            }
        elif fmt == "json":
            formatters["standard"] = {
                "()": JsonFormatter,
            }
        else:
            raise ValueError("unknown log format")
        return formatters

    @property
    def filters(self):
        return {}

    @property
    def loggers(self):
        return {
            "django": {
                "handlers": self.handlers.keys(),
                "level": self.config["levels"]["django"],
                "propagate": False,
            },
            "django.request": {
                "handlers": self.handlers.keys(),
                "level": self.config["levels"]["django.request"],
                "propagate": False,
            },
            "django.template": {
                "handlers": self.handlers.keys(),
                "level": self.config["levels"]["django.template"],
                "propagate": False,
            },
            "django.utils.autoreload": {
                "handlers": self.handlers.keys(),
                "level": self.config["levels"]["django.utils.autoreload"],
                "propagate": False,
            },
            "telescope": {
                "handlers": self.handlers.keys(),
                "level": self.config["levels"]["telescope"],
                "propagate": False,
            },
            "kubernetes.client.rest": {
                "handlers": self.handlers.keys(),
                "level": self.config["levels"]["kubernetes.client.rest"],
                "propagate": False,
            },
            "": {
                "handlers": self.handlers.keys(),
                "level": self.config["levels"]["all"],
                "propagate": False,
            },
        }

    def as_dict(self):
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": self.filters,
            "formatters": self.formatters,
            "handlers": self.handlers,
            "loggers": self.loggers,
        }
