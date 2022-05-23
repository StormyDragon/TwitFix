import json
import os
from pathlib import Path

from sanic.log import logger


def load_json_config(app):
    if app.config.get("CONFIG_FROM") != "environment":
        logger.info("Using legacy configuration method.")
        config_file = Path(app.config.get("CONFIG_JSON", "./config.json"))
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
                        "storage_module": "local_storage",
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

        app.config.update(
            {
                "LINK_CACHE": config["config"]["link_cache"],
                "STORAGE_MODULE": config["config"]["storage_module"],
                "MONGO_DB": config["config"]["database"],
                "MONGO_DB_TABLE": config["config"]["table"],
                "DOWNLOAD_METHOD": config["config"]["method"],
                "COLOR": config["config"]["color"],
                "APP_NAME": config["config"]["appname"],
                "REPO": config["config"]["repo"],
                "BASE_URL": config["config"]["url"],
                "STORAGE_LOCAL_BASE": config["config"]["download_base"],
                "STORAGE_BUCKET": config["config"]["gcp_bucket"],
                "TWITTER_API_KEY": config["api"]["api_key"],
                "TWITTER_API_SECRET": config["api"]["api_secret"],
                "TWITTER_ACCESS_TOKEN": config["api"]["access_token"],
                "TWITTER_ACCESS_SECRET": config["api"]["access_secret"],
            }
        )
