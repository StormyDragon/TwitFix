import re
from contextvars import ContextVar

import google.cloud.logging_v2.handlers.handlers
import sanic
import sanic.log


def initialize_app(app: sanic.Sanic):
    @app.on_request
    async def set_trace_data(request: sanic.Request):
        trace_id, span_id, trace_sampled = _parse_xcloud_trace(
            request.headers.get("X_CLOUD_TRACE_CONTEXT")
        )
        http_request = {
            "requestMethod": request.method,
            "requestUrl": request.url,
            "userAgent": request.headers.get("user-agent"),
            "remoteIp": request.headers.get('x-forwarded-for'),
            # "protocol": request.request_line.rsplit(' ', 1)[-1].encode(),
        }
        request.app.ctx.trace.set([http_request, trace_id, span_id, trace_sampled])

    @app.before_server_start
    def setup(app, loop):
        app.ctx.trace = ContextVar("trace")

    def get_request_data_from_sanic():
        try:
            trace_data = app.ctx.trace.get(None)
            if not trace_data:
                return None, None, None, False

            [http_request, trace_id, span_id, trace_sampled] = trace_data
            return http_request, trace_id, span_id, trace_sampled
        except LookupError:
            print("Cloud logging; no request in trace context")
        except AttributeError:
            # Only happens for logs sent during server start, once our function
            # initializes the context var this stops occurring.
            pass

        return None, None, None, False

    google.cloud.logging_v2.handlers.handlers.get_request_data = (
        get_request_data_from_sanic
    )


def _parse_xcloud_trace(header):
    """Given an X_CLOUD_TRACE header, extract the trace and span ids.
    Args:
        header (str): the string extracted from the X_CLOUD_TRACE header
    Returns:
        Tuple[Optional[dict], Optional[str], bool]:
            The trace_id, span_id and trace_sampled extracted from the header
            Each field will be None if not found.
    """
    trace_id = span_id = None
    trace_sampled = False
    # see https://cloud.google.com/trace/docs/setup for X-Cloud-Trace_Context format
    if header:
        try:
            regex = r"([\w-]+)?(\/?([\w-]+))?(;?o=(\d))?"
            match = re.match(regex, header)
            trace_id = match.group(1)
            span_id = match.group(3)
            trace_sampled = match.group(5) == "1"
        except IndexError:
            pass
    return trace_id, span_id, trace_sampled
