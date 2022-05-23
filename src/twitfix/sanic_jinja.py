from functools import wraps
from pathlib import Path

import sanic
from jinja2 import Environment, FileSystemLoader, select_autoescape


def configure_jinja(app: sanic.Sanic, templates_path: Path):
    app.config.update(
        {
            "JINJA": Environment(
                enable_async=True, loader=FileSystemLoader(templates_path)
            )
        }
    )


def using_template(template_name: str):
    def decorator(f):
        template = None

        @wraps(f)
        async def replacer(request, *args, **kwargs):
            nonlocal template
            response = await f(*args, **kwargs)
            if isinstance(response, dict):
                if not template:
                    template = request.app.config.JINJA.get_template(template_name)
                return sanic.html(await template.render_async(response))
            else:
                return response

        return replacer
    return decorator


async def render_template(request, template_name, **kwargs):
    template = request.app.config.JINJA.get_template(template_name)
    return sanic.html(await template.render_async(kwargs))
