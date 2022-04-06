import os

from gunicorn.app.base import BaseApplication
from .twitfix_app import app


class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def main():
    port = os.environ["PORT"]
    workers = int(os.environ.get("WORKERS", 2))
    options = {
        "bind": f"0.0.0.0:{port}",
        "workers": workers,
    }
    StandaloneApplication(app, options).run()
