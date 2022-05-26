import re
import urllib
from datetime import date

import sanic
import sanic.response
from sanic.log import logger

from .sanic_jinja import render_template

stats = sanic.Blueprint("twitfix_stats")


@stats.route("/stats/")
async def statsPage(request):
    today = str(date.today())
    stats = request.app.config.STAT_MODULE.get_stats(today)
    return render_template(
        "stats.html",
        embeds=stats["embeds"],
        downloadss=stats["downloads"],
        api=stats["api"],
        linksCached=stats["linksCached"],
        date=today,
    )


@stats.route("/latest/")
async def latest(request):
    return render_template("latest.html")


@stats.route("/top/")  # Try to return the most hit video
async def top(request):
    try:
        [vnf] = request.app.config.LINKS_MODULE.get_links_from_cache("hits", 1, 0)
    except ValueError:
        logger.info(" ➤ [ ✔ ] Top video page loaded: None yet...")
        return sanic.response.empty()
    desc = re.sub(r" http.*t\.co\S+", "", vnf["description"])
    logger.info(" ➤ [ ✔ ] Top video page loaded: " + vnf["tweet"])
    return render_template(
        "inline.html",
        page="Top",
        vidlink=vnf["url"],
        vidurl=vnf["url"],
        desc=desc,
        pic=vnf["thumbnail"],
        user=vnf["uploader"],
        video_link=vnf["url"],
        color=request.app.config.COLOR,
        appname=request.app.config.APP_NAME,
        repo=request.app.config.REPO,
        url=request.app.config.BASE_URL,
        tweet=vnf["tweet"],
    )


@stats.route("/api/latest/")  # Return some raw VNF data sorted by top tweets
async def apiLatest(request):
    tweets = request.args.get("tweets", default=10, type=int)
    page = request.args.get("page", default=0, type=int)

    if tweets > 15:
        tweets = 1

    vnf = request.app.config.LINKS_MODULE.get_links_from_cache("_id", tweets, tweets * page)

    logger.info(" ➤ [ ✔ ] Latest video API called")
    request.app.config.STAT_MODULE.add_to_stat("api")
    return sanic.response.json(vnf)


@stats.route("/api/top/")  # Return some raw VNF data sorted by top tweets
async def apiTop(request):
    tweets = request.args.get("tweets", default=10, type=int)
    page = request.args.get("page", default=0, type=int)

    if tweets > 15:
        tweets = 1

    vnf = request.app.config.LINKS_MODULE.get_links_from_cache("hits", tweets, tweets * page)

    logger.info(" ➤ [ ✔ ] Top video API called")
    request.app.config.STAT_MODULE.add_to_stat("api")
    return sanic.response.json(vnf)

@stats.route(
    "/api/stats/"
)  # Return a json of a usage stats for a given date (defaults to today)
async def apiStats(request):
    try:
        request.app.config.STAT_MODULE.add_to_stat("api")
        today = str(date.today())
        desiredDate = request.args.get("date", default=today, type=str)
        stat = request.app.config.STAT_MODULE.get_stats(desiredDate)
        logger.info(" ➤ [ ✔ ] Stats API called")
        return sanic.response.json(stat)
    except:
        logger.info(" ➤ [ ✔ ] Stats API failed")
        return sanic.response.empty(500)
