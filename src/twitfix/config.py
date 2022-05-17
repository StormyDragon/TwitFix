import json
import os
from pathlib import Path


def _env(suffix: str, optional=False):
    key = f"TWITFIX_{suffix}"
    value = os.environ.get(key)
    if value is None and not optional:
        raise LookupError(f"Config: could not locate {key} in environment.")
    return value


def load_configuration():
    if _env("CONFIG_FROM", optional=True) == "environment":
        link_cache = _env("LINK_CACHE")
        storage_module = _env("STORAGE_MODULE")
        config = {
            "config": {
                "link_cache": link_cache,
                "database": _env("DB", optional=link_cache != "mongo"),
                "table": _env("DB_TABLE", optional=link_cache != "mongo"),
                "storage_module": storage_module,
                "method": _env("DOWNLOAD_METHOD"),
                "color": _env("COLOR"),
                "appname": _env("APP_NAME"),
                "repo": _env("REPO"),
                "url": _env("BASE_URL"),
                "download_base": _env(
                    "STORAGE_LOCAL_BASE", optional=storage_module != "local"
                ),
                "gcp_bucket": _env(
                    "STORAGE_BUCKET", optional=storage_module != "gcp_storage"
                ),
            },
            "api": {
                "api_key": _env("TWITTER_API_KEY"),
                "api_secret": _env("TWITTER_API_SECRET"),
                "access_token": _env("TWITTER_ACCESS_TOKEN"),
                "access_secret": _env("TWITTER_ACCESS_SECRET"),
            },
        }
    else:
        config_file = Path(_env("CONFIG_JSON", optional=True) or "./config.json")
        if not config_file.exists():
            with config_file.open("w") as outfile:
                default_config = {
                    "config": {
                        "link_cache": "json",
                        "database": "[url to mongo database goes here]",
                        "table": "TwiFix",
                        "method": "youtube-dl",
                        "color": "#43B581",
                        "appname": "TwitFix",
                        "repo": "https://github.com/robinuniverse/twitfix",
                        "url": "https://localhost:8080",
                        "download_base": "./static/",
                        "storage_module": "local",
                    },
                    "api": {
                        "api_key": "[api_key goes here]",
                        "api_secret": "[api_secret goes here]",
                        "access_token": "[access_token goes here]",
                        "access_secret": "[access_secret goes here]",
                    },
                }
                json.dump(default_config, outfile, indent=4, sort_keys=True)
            config = default_config
        else:
            f = config_file.open()
            config = json.load(f)
            f.close()
    return config
