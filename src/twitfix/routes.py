from pathlib import Path

import sanic
import sanic.response
import twitter
from sanic.log import logger

from .config import load_json_config
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
app.blueprint(twitfix_app)
app.blueprint(stats)
app.blueprint(toy)

app.extend(cors=True, oas=False)


@app.middleware
async def peek(request):
    logger.info(f">>> {request.url}")


# If method is set to API or Hybrid, attempt to auth with the Twitter API
if app.config.DOWNLOAD_METHOD in ("api", "hybrid"):
    auth = twitter.oauth.OAuth(
        app.config.TWITTER_ACCESS_TOKEN,
        app.config.TWITTER_ACCESS_SECRET,
        app.config.TWITTER_API_KEY,
        app.config.TWITTER_API_SECRET,
    )
    twitter_api = twitter.Twitter(auth=auth)
    app.config.update({"TWITTER": twitter_api})

link_cache_system = app.config.LINK_CACHE
storage_module_type = app.config.STORAGE_MODULE
STAT_MODULE = initialize_stats(link_cache_system, app.config)
LINKS_MODULE = initialize_link_cache(link_cache_system, app.config)
STORAGE_MODULE = initialize_storage(storage_module_type, app.config)

base_url = app.config.BASE_URL

static_folder = Path("static").resolve()
template_folder = Path("templates").resolve()
configure_jinja(app, template_folder)
load_json_config(app)
app.static("/static", static_folder)
app.config.update(
    {
        "STAT_MODULE": STAT_MODULE,
        "LINKS_MODULE": LINKS_MODULE,
        "STORAGE_MODULE": STORAGE_MODULE,
        "BASE_URL": base_url,
    }
)
