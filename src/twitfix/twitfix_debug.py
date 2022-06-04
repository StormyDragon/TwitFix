import asyncio

import sanic
import sanic.response

debug = sanic.Blueprint("twitfix_debug")

# https://ayytwitter.com/delay/102
# https://ayytwitter.com/stream_delay/101

@debug.route("/delay/<millis:int>")
async def delayed_response(request, millis):
    await asyncio.sleep(millis/1000)
    return sanic.response.html(f"""
<html prefix="og: http://ogp.me/ns#">
    <head>
        <meta property="og:site_name"                   content="AyyTwitter delay debugging ({millis})"/>
        <meta name="twitter:card"                       content="summary_large_image" />
        <meta name="twitter:title"                      content="Waited for {millis} milliseconds."  />
    </head>
</html>
    """.strip(), headers={"cache-control": "no-cache"})

@debug.route("/stream_delay/<millis:int>")
async def delayed_response(request, millis: int):
    response = f"""
<html prefix="og: http://ogp.me/ns#">
    <head>
        <meta property="og:site_name"                   content="AyyTwitter streaming delay debugging ({millis})"/>
        <meta name="twitter:card"                       content="summary_large_image" />
        <meta name="twitter:title"                      content="Waited for {millis} milliseconds."  />
    </head>
</html>
    """.strip()

    response = await request.respond(content_type="text/html", headers={"cache-control": "no-cache"})
    async with response as send:
        await asyncio.sleep(millis/1000)
        await send(response)
