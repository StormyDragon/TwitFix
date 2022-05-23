from pathlib import Path

import sanic
import sanic.response
import twitter
from sanic.log import logger
from sanic_cors import CORS, cross_origin

from .config import load_configuration, load_json_config
from .link_cache import initialize_link_cache
from .sanic_jinja import configure_jinja
from .stats_module import initialize_stats
from .storage_module import initialize_storage
from .twitfix_app import twitfix_app
from .twitfix_stats import stats
from .twitfix_toys import toy


@stats.middleware
async def lock_stats(request):
    logger.info(" ➤ [ X ] Stats have been disabled.")
    return sanic.response.empty(status=401)


app = sanic.Sanic("twitfix", env_prefix="TWITFIX_")
CORS(app)
app.blueprint(twitfix_app)
app.blueprint(stats)
app.blueprint(toy)


@app.middleware
async def peek(request):
    logger.info(f">>> {request.url}")


# Read config from config.json. If it does not exist, create new.
config = load_configuration()

# If method is set to API or Hybrid, attempt to auth with the Twitter API
if config["config"]["method"] in ("api", "hybrid"):
    auth = twitter.oauth.OAuth(
        config["api"]["access_token"],
        config["api"]["access_secret"],
        config["api"]["api_key"],
        config["api"]["api_secret"],
    )
    twitter_api = twitter.Twitter(auth=auth)
    app.config.update({"TWITTER": twitter_api})

link_cache_system = config["config"]["link_cache"]
storage_module_type = config["config"]["storage_module"]
STAT_MODULE = initialize_stats(link_cache_system, config)
LINK_CACHE = initialize_link_cache(link_cache_system, config)
STORAGE_MODULE = initialize_storage(storage_module_type, config)

base_url = config["config"]["url"]

static_folder = Path("static").resolve()
template_folder = Path("templates").resolve()
configure_jinja(app, template_folder)
load_json_config(app)
app.static("/static", static_folder)
app.config.update(
    {
        "STAT_MODULE": STAT_MODULE,
        "LINK_CACHE": LINK_CACHE,
        "STORAGE_MODULE": STORAGE_MODULE,
        "CONFIG": config,
        "BASE_URL": base_url,
    }
)
