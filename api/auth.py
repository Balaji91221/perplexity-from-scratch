"""Per-device "auth": stable UUID per browser, sent as X-User-Id header.

This is NOT real authentication. It's a tag that lets threads + documents be
scoped to a device. Don't expose this service to the open internet without
adding real auth.
"""

import re

from fastapi import Request

from config import ANON_USER_ID

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def get_user_id(request: Request) -> str:
    """Read the X-User-Id header for normal API calls, falling back to a
    `?uid=` query param for cases where headers can't be set (iframes loading
    the PDF file route)."""
    candidate = request.headers.get("x-user-id") or request.query_params.get("uid") or ""
    if UUID_RE.match(candidate):
        return candidate.lower()
    return ANON_USER_ID
