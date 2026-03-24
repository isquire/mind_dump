"""Shared helpers used across routes."""
from datetime import datetime
from urllib.parse import urlparse

from flask import redirect, request, url_for

VALID_VIEWS = ('work', 'all', 'personal')
VALID_CATEGORIES = ('work', 'personal')


def default_category() -> str:
    """Return 'work' during 9 AM–5 PM Mon–Fri, 'personal' otherwise."""
    now = datetime.now()
    if now.weekday() < 5 and 9 <= now.hour < 17:
        return 'work'
    return 'personal'


def apply_category_filter(query, view):
    """Filter a SQLAlchemy query to items matching `view` (no-op for 'all')."""
    if view in VALID_CATEGORIES:
        return query.filter_by(category=view)
    return query


def safe_referrer_redirect(fallback_endpoint: str, **kwargs):
    """Redirect to the Referer header only if it resolves to the same host.

    Guards against open-redirect attacks where a crafted Referer header could
    send the user to an external site.
    """
    referrer = request.referrer
    if referrer:
        parsed = urlparse(referrer)
        # Allow relative URLs (no netloc) or same-host absolute URLs
        if not parsed.netloc or parsed.netloc == request.host:
            return redirect(referrer)
    return redirect(url_for(fallback_endpoint, **kwargs))
