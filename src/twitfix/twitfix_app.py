import json
import re
import textwrap
import urllib.parse
import urllib.request

import sanic
import sanic.response
import youtube_dl
from sanic.log import logger

from .exceptions import TwitterUserProtected
from .sanic_jinja import render_template

twitfix_app = sanic.Blueprint("twitfix-embeds")

pathregex = re.compile("\\w{1,15}\\/(status|statuses)\\/\\d{2,20}")

# Where may our links be posted?
# And what is the default appearance of these?
#
# Discord
# Telegram
# Slack
# Facebook
# Valve Steam Client
# Valve Steam FriendsUI
# January (image proxy RevoltChat)
generate_embed_user_agents = [
    "facebookexternalhit/1.1",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.57 Safari/537.36",
    "Mozilla/5.0 (Windows; U; Windows NT 10.0; en-US; Valve Steam Client/default/1596241936; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36",
    "Mozilla/5.0 (Windows; U; Windows NT 10.0; en-US; Valve Steam Client/default/0; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.4 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.4 facebookexternalhit/1.1 Facebot Twitterbot/1.0",
    "facebookexternalhit/1.1",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; Valve Steam FriendsUI Tenfoot/0; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36",
    "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:38.0) Gecko/20100101 Firefox/38.0",
    "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
    "TelegramBot (like TwitterBot)",
    "Mozilla/5.0 (compatible; January/1.0; +https://gitlab.insrt.uk/revolt/january)",
    "test",
]


@twitfix_app.route(
    "/"
)  # If the useragent is discord, return the embed, if not, redirect to configured repo directly
async def default(request):
    user_agent = request.headers.get("user-agent")
    if user_agent in generate_embed_user_agents:
        return await message(
            request,
            "TwitFix is an attempt to fix twitter video embeds in discord! created by Robin Universe :)\n\n💖\n\nClick me to be redirected to the repo!",
        )
    else:
        logger.info("Just redirecting to github")
        return sanic.response.redirect(request.app.config.REPO, status=301)


@twitfix_app.route("/oembed.json")  # oEmbed endpoint
async def oembedend(request):
    desc = request.args.get("desc", None)
    user = request.args.get("user", None)
    link = request.args.get("link", None)
    ttype = request.args.get("ttype", None)
    return sanic.response.json(
        {
            "type": ttype,
            "version": "1.0",
            "provider_name": request.app.config.APP_NAME,
            "provider_url": request.app.config.REPO,
            "title": desc,
            "author_name": user,
            "author_url": link,
        }
    )


@twitfix_app.route("/<sub_path:path>")  # Default endpoint used by everything
async def twitfix(request, sub_path):
    user_agent = request.headers.get("user-agent")
    match = pathregex.search(sub_path)
    logger.info(request.url)

    if request.host.startswith(
        f"d."
    ):  # Matches d.{fx}? Try to give the user a direct link
        if user_agent in generate_embed_user_agents:
            logger.info(f" ➤ [ D ] d. link shown to discord user-agent!")
            if request.url.endswith(".mp4") and "?" not in request.url:
                return await dl(request, sub_path[:-4])
            else:
                return await message(
                    request,
                    "To use a direct MP4 link in discord, remove anything past '?' and put '.mp4' at the end",
                )
        else:
            logger.info(f" ➤ [ R ] Redirect to MP4 using {request.host}")
            return await dir(request, sub_path)

    elif request.url.endswith((".mp4","%2Emp4")):
        twitter_url = "https://twitter.com/" + sub_path

        if "?" not in request.url:
            clean = twitter_url[:-4]
        else:
            clean = twitter_url

        return await dl(request, clean)

    elif request.url.endswith((".json","%2Ejson")):
        twitter_url = "https://twitter.com/" + sub_path

        if "?" not in request.url:
            clean = twitter_url[:-5]
        else:
            clean = twitter_url

        logger.info(" ➤ [ API ] VNF Json api hit!")

        vnf = link_to_vnf_from_api(request, clean.replace(".json", ""))

        if user_agent in generate_embed_user_agents:
            return await message(
                request,
                "VNF Data: ( discord useragent preview )\n\n"
                + json.dumps(vnf, default=str),
            )
        else:
            return sanic.response.json(vnf)

    elif request.url.endswith(("/1","/2","/3","/4","%2F1","%2F2","%2F3","%2F4")):
        twitter_url = "https://twitter.com/" + sub_path

        if "?" not in request.url:
            clean = twitter_url[:-2]
        else:
            clean = twitter_url

        image = int(request.url[-1]) - 1
        return await embed_video(request, clean, image)

    if match is not None:
        twitter_url = sub_path

        if match.start() == 0:
            twitter_url = "https://twitter.com/" + sub_path

        if user_agent in generate_embed_user_agents:
            return await embed_video(request, twitter_url)
        else:
            logger.info(" ➤ [ R ] Redirect to " + twitter_url)
            return sanic.response.redirect(twitter_url, status=301)
    else:
        return await message(request, "This doesn't appear to be a twitter URL")


@twitfix_app.route(
    "/other/<sub_path:path>"
)  # Show all info that Youtube-DL can get about a video as a json
async def other(request, sub_path):
    otherurl = request.url.split("/other/", 1)[1].replace(":/", "://")
    logger.info(" ➤ [ OTHER ]  Other URL embed attempted: " + otherurl)
    res = await embed_video(request, otherurl)
    return res


@twitfix_app.route(
    "/info/<sub_path:path>"
)  # Show all info that Youtube-DL can get about a video as a json
async def info(request, sub_path):
    infourl = request.url.split("/info/", 1)[1].replace(":/", "://")
    logger.info(" ➤ [ INFO ] Info data requested: " + infourl)
    with youtube_dl.YoutubeDL({"outtmpl": "%(id)s.%(ext)s"}) as ydl:
        result = ydl.extract_info(infourl, download=False)

    return result


@twitfix_app.route("/dl/<sub_path:path>")  # Download the tweets video, and rehost it
async def dl(request, sub_path):
    logger.info(
        f" ➤ [[ !!! TRYING TO DOWNLOAD FILE !!! ]] Downloading file from {sub_path}"
    )
    url = sub_path
    match = pathregex.search(url)
    if match is not None:
        twitter_url = url
        if match.start() == 0:
            twitter_url = "https://twitter.com/" + url

    mp4link = await direct_video_link(request, twitter_url)
    if not isinstance(mp4link, str):
        return mp4link

    if not mp4link:
        return await message(request, "No video file in tweet.")

    cache_hit, stored_identifier = request.app.config.STORAGE_MODULE.store_media(
        mp4link
    )
    if not cache_hit:
        request.app.config.STAT_MODULE.add_to_stat("downloads")
    response = request.app.config.STORAGE_MODULE.retrieve_media(stored_identifier)

    if response is None:
        return sanic.response.empty(status=404)
    if response["output"] == "url":
        logger.info("Cache response>")
        return sanic.response.redirect(response["url"])
    if response["output"] == "file":
        return await sanic.response.file(
            response["content"],
            headers={
                "max-age": 3600,
                "Content-Type": "video/mp4",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            },
        )
    return sanic.response.empty(status=404)


@twitfix_app.route(
    "/dir/<sub_path:path>"
)  # Try to return a direct link to the MP4 on twitters servers
async def dir(request, sub_path):
    user_agent = request.headers.get("user-agent")
    url = sub_path
    match = pathregex.search(url)
    if match is not None:
        twitter_url = url

        if match.start() == 0:
            twitter_url = "https://twitter.com/" + url

        if user_agent in generate_embed_user_agents:
            res = await embed_video(request, twitter_url)
            return res

        else:
            logger.info(" ➤ [ R ] Redirect to direct MP4 URL")
            return await direct_video(request, twitter_url)
    else:
        return sanic.response.redirect(url, status=301)


@twitfix_app.route("/favicon.ico")  # This shit don't work
async def favicon(request):
    return await sanic.response.file("static/favicon.ico", mime_type="image/x-icon")


def add_link_to_cache(request, video_link, vnf):
    res = request.app.config.LINKS_MODULE.add_link_to_cache(video_link, vnf)
    if res:
        request.app.config.STAT_MODULE.add_to_stat("linksCached")
    return res


def get_link_from_cache(request, video_link):
    res = request.app.config.LINKS_MODULE.get_link_from_cache(video_link)
    if res:
        request.app.config.STAT_MODULE.add_to_stat("embeds")
    return res


async def direct_video(
    request, video_link
):  # Just get a redirect to a MP4 link from any tweet link
    cached_vnf = get_link_from_cache(request, video_link)
    if cached_vnf is None:
        try:
            vnf = link_to_vnf(request, video_link)
            add_link_to_cache(request, video_link, vnf)
            logger.info(" ➤ [ D ] Redirecting to direct URL: " + vnf["url"])
            return sanic.response.redirect(vnf["url"], status=301)
        except TwitterUserProtected:
            return await message(request, "This user is guarding their tweets!")
        except Exception as e:
            logger.info(e)
            return await message(request, "Failed to scan your link!")
    else:
        logger.info(f" ➤ [ D ] Redirecting to direct URL: {cached_vnf['url']}")
        return sanic.response.redirect(cached_vnf["url"], status=301)


async def direct_video_link(
    request,
    video_link,
):  # Just get a redirect to a MP4 link from any tweet link
    cached_vnf = get_link_from_cache(request, video_link)
    if cached_vnf is None:
        try:
            vnf = link_to_vnf(request, video_link)
            add_link_to_cache(request, video_link, vnf)
            logger.info(f" ➤ [ D ] Redirecting to direct URL: {vnf['url']}")
            return vnf["url"]
        except TwitterUserProtected:
            return await message(request, "This user is guarding their tweets!")
        except Exception as e:
            logger.info(e)
            return await message(request, "Failed to scan your link!")
    else:
        logger.info(f" ➤ [ D ] Redirecting to direct URL: {cached_vnf['url']}")
        return cached_vnf["url"]


async def embed_video(request, video_link, image=0):  # Return Embed from any tweet link
    cached_vnf = get_link_from_cache(request, video_link)

    if cached_vnf is None:
        try:
            vnf = link_to_vnf(request, video_link)
            add_link_to_cache(request, video_link, vnf)
            return await embed(request, video_link, vnf, image)
        except TwitterUserProtected:
            return await message(request, "This user is guarding their tweets!")
        except Exception as e:
            logger.info(e)
            return await message(request, "Failed to scan your link!")
    else:
        return await embed(request, video_link, cached_vnf, image)


def tweetInfo(
    url,
    tweet="",
    desc="",
    thumb="",
    uploader="",
    screen_name="",
    pfp="",
    tweetType="",
    images="",
    hits=0,
    likes=0,
    rts=0,
    time="",
    qrt={},
    nsfw=False,
):  # Return a dict of video info with default values
    vnf = {
        "tweet": tweet,
        "url": url,
        "description": desc,
        "thumbnail": thumb,
        "uploader": uploader,
        "screen_name": screen_name,
        "pfp": pfp,
        "type": tweetType,
        "images": images,
        "hits": hits,
        "likes": likes,
        "rts": rts,
        "time": time,
        "qrt": qrt,
        "nsfw": nsfw,
    }
    return vnf


def link_to_vnf_from_api(request, video_link):
    logger.info(" ➤ [ + ] Attempting to download tweet info from Twitter API")
    twid = int(
        re.sub(r"\?.*$", "", video_link.rsplit("/", 1)[-1])
    )  # gets the tweet ID as a int from the passed url
    tweet = request.app.config.TWITTER.statuses.show(_id=twid, tweet_mode="extended")
    # For when I need to poke around and see what a tweet looks like
    # logger.info(tweet)
    protected = tweet["user"]["protected"]
    if protected:
        raise TwitterUserProtected()

    text = tweet["full_text"]
    nsfw = tweet.get("possibly_sensitive", False)
    qrt = {}
    url = ""
    thumb = ""
    imgs = ["", "", "", "", ""]
    logger.info(" ➤ [ + ] Tweet Type: " + tweetType(tweet))
    # Check to see if tweet has a video, if not, make the url passed to the VNF the first t.co link in the tweet
    if tweetType(tweet) == "Video":
        if tweet["extended_entities"]["media"][0]["video_info"]["variants"]:
            best_bitrate = 0
            thumb = tweet["extended_entities"]["media"][0]["media_url"]
            for video in tweet["extended_entities"]["media"][0]["video_info"][
                "variants"
            ]:
                if (
                    video["content_type"] == "video/mp4"
                    and video["bitrate"] > best_bitrate
                ):
                    url = video["url"]
                    best_bitrate = video["bitrate"]
    elif tweetType(tweet) == "Text":
        pass
    else:
        imgs = ["", "", "", "", ""]
        i = 0
        for media in tweet["extended_entities"]["media"]:
            imgs[i] = media["media_url_https"]
            i = i + 1

        # logger.info(imgs)
        imgs[4] = str(i)
        thumb = tweet["extended_entities"]["media"][0]["media_url_https"]

    if "quoted_status" in tweet:
        qrt["desc"] = tweet["quoted_status"]["full_text"]
        qrt["handle"] = tweet["quoted_status"]["user"]["name"]
        qrt["screen_name"] = tweet["quoted_status"]["user"]["screen_name"]

    vnf = tweetInfo(
        url,
        video_link,
        text,
        thumb,
        tweet["user"]["name"],
        tweet["user"]["screen_name"],
        tweet["user"]["profile_image_url"],
        tweetType(tweet),
        likes=tweet["favorite_count"],
        rts=tweet["retweet_count"],
        time=tweet["created_at"],
        qrt=qrt,
        images=imgs,
        nsfw=nsfw,
    )

    return vnf


def link_to_vnf_from_youtubedl(video_link):
    logger.info(
        f" ➤ [ X ] Attempting to download tweet info via YoutubeDL: {video_link}"
    )
    with youtube_dl.YoutubeDL({"outtmpl": "%(id)s.%(ext)s"}) as ydl:
        result = ydl.extract_info(video_link, download=False)
        vnf = tweetInfo(
            result["url"],
            video_link,
            result["description"].rsplit(" ", 1)[0],
            result["thumbnail"],
            result["uploader"],
        )
        return vnf


def link_to_vnf(request, video_link):  # Return a VideoInfo object or die trying
    config_method = request.app.config.DOWNLOAD_METHOD
    if config_method == "hybrid":
        try:
            return link_to_vnf_from_api(request, video_link)
        except TwitterUserProtected:
            logger.info(" ➤ [ X ] User is protected, stop.")
            raise
        except Exception as e:
            logger.error(f" ➤ [ !!! ] API Failed {e}")
            return link_to_vnf_from_youtubedl(video_link)
    elif config_method == "api":
        try:
            return link_to_vnf_from_api(request, video_link)
        except TwitterUserProtected:
            logger.info(" ➤ [ X ] User is protected, stop.")
            raise
        except Exception as e:
            logger.error(f" ➤ [ X ] API Failed {e}")
            return None
    elif config_method == "youtube-dl":
        try:
            return link_to_vnf_from_youtubedl(video_link)
        except Exception as e:
            logger.error(f" ➤ [ X ] Youtube-DL Failed {e}")
            return None
    else:
        logger.info(
            "Please set the method key in your config file to 'api' 'youtube-dl' or 'hybrid'"
        )
        return None


async def message(request, text):
    return await render_template(
        request,
        "default.html",
        message=text,
        color=request.app.config.COLOR,
        appname=request.app.config.APP_NAME,
        repo=request.app.config.REPO,
        url=request.app.config.BASE_URL,
    )


async def embed(request, video_link, vnf, image):
    logger.info(
        f" ➤ [ E ] Embedding {vnf['type']}: {vnf['url'] or (video_link, image)}"
    )

    desc = re.sub(r" http.*t\.co\S+", "", vnf["description"])
    urlUser = urllib.parse.quote(vnf["uploader"])
    urlDesc = urllib.parse.quote(desc)
    urlLink = urllib.parse.quote(video_link)
    likeDisplay = "\n\n💖 " + str(vnf["likes"]) + " 🔁 " + str(vnf["rts"]) + "\n"

    try:
        if vnf["type"] == "":
            desc = desc
        elif vnf["type"] == "Video":
            desc = desc
        elif vnf["qrt"] == {}:  # Check if this is a QRT and modify the description
            desc = desc + likeDisplay
        else:
            qrtDisplay = (
                "\n─────────────\n ➤ QRT of "
                + vnf["qrt"]["handle"]
                + " (@"
                + vnf["qrt"]["screen_name"]
                + "):\n─────────────\n'"
                + vnf["qrt"]["desc"]
                + "'"
            )
            desc = desc + qrtDisplay + likeDisplay
    except:
        vnf["likes"] = 0
        vnf["rts"] = 0
        vnf["time"] = 0
        logger.info(" ➤ [ X ] Failed QRT check - old VNF object")

    if vnf["type"] == "Text":  # Change the template based on tweet type
        template = "text.html"
    if vnf["type"] == "Image":
        image = vnf["images"][image]
        template = "image.html"
    if vnf["type"] == "Video":
        urlDesc = urllib.parse.quote(
            textwrap.shorten(desc, width=220, placeholder="...")
        )
        template = "video.html"
    if vnf["type"] == "":
        urlDesc = urllib.parse.quote(
            textwrap.shorten(desc, width=220, placeholder="...")
        )
        template = "video.html"

    # Change the theme color to red if this post is not worksafe.
    color = "#800020" if vnf["nsfw"] else "#7FFFD4"

    return await render_template(
        request,
        template,
        likes=vnf["likes"],
        rts=vnf["rts"],
        time=vnf["time"],
        screenName=vnf["screen_name"],
        vidlink=vnf["url"],
        pfp=vnf["pfp"],
        vidurl=vnf["url"],
        desc=desc,
        pic=image,
        user=vnf["uploader"],
        video_link=video_link,
        color=color,
        appname=request.app.config.APP_NAME,
        repo=request.app.config.REPO,
        url=request.app.config.BASE_URL,
        urlDesc=urlDesc,
        urlUser=urlUser,
        urlLink=urlLink,
    )


def tweetType(tweet):  # Are we dealing with a Video, Image, or Text tweet?
    if "extended_entities" in tweet:
        if "video_info" in tweet["extended_entities"]["media"][0]:
            out = "Video"
        else:
            out = "Image"
    else:
        out = "Text"

    return out
