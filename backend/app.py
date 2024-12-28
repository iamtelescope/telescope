#!/usr/bin/env python

import os
import logging

from django.core.wsgi import get_wsgi_application
from gunicorn.app.base import BaseApplication

from telescope.config import get_config

logging.basicConfig(level=logging.DEBUG)


class TelescopeApp(BaseApplication):
    def __init__(self):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")
        self.application = get_wsgi_application()
        super(TelescopeApp, self).__init__()

    def load(self):
        return self.application

    def load_config(self):
        config = get_config()
        for key, value in config.get("gunicorn", {}).items():
            self.cfg.set(key, value)


def main():
    TelescopeApp().run()


if __name__ == "__main__":
    main()
