import time

import requests
from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
from requests.adapters import HTTPAdapter

from . import config

DEFAULT_TIMEOUT = 30


class TimeoutHTTPAdapter(HTTPAdapter):
    """canvasapi's internal requests.Session never sets a timeout, so a
    stalled connection to Canvas hangs the whole sync forever. Force one here."""

    def send(self, *args, **kwargs):
        # requests.Session.send() always passes `timeout` explicitly (as None
        # when the caller didn't set one), so setdefault() would never fire —
        # it only skips already-present keys, and None counts as present.
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = DEFAULT_TIMEOUT
        return super().send(*args, **kwargs)


def get_canvas() -> Canvas:
    canvas = Canvas(config.CANVAS_BASE_URL, config.CANVAS_API_TOKEN)
    session = canvas._Canvas__requester._session
    adapter = TimeoutHTTPAdapter()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return canvas


def with_retry(fn, *args, max_attempts=4, **kwargs):
    """Call fn(*args, **kwargs), retrying on rate limits, transient 5xx, and network timeouts."""
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(*args, **kwargs)
        except CanvasException as exc:
            status = getattr(exc, "response", None)
            status_code = getattr(status, "status_code", None) if status else None
            transient = status_code == 403 and "rate limit" in str(exc).lower()
            transient = transient or (status_code is not None and status_code >= 500)
            if not transient or attempt == max_attempts:
                raise
            time.sleep(2**attempt)
        except (requests.exceptions.RequestException, ConnectionError) as exc:
            if attempt == max_attempts:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


def active_courses(canvas: Canvas):
    """Enumerate active courses. Does not assume any particular count."""
    return list(
        with_retry(
            canvas.get_courses,
            enrollment_state="active",
            include=["total_scores", "current_grading_period_scores"],
        )
    )
