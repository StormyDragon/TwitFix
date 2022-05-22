import sanic
import sanic.response

toy = sanic.Blueprint("toys")


@toy.route("/bidoof/")
async def bidoof(request):
    return sanic.response.redirect(
        "https://cdn.discordapp.com/attachments/291764448757284885/937343686927319111/IMG_20211226_202956_163.webp",
        status=301,
    )
