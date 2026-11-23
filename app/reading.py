"""Turn an uploaded article into HTML a reader can scan.

The source is escaped before Markdown runs, so a file cannot inject markup.
"""

from __future__ import annotations

import html
import re
from urllib.parse import urlsplit

import markdown

_HREF = re.compile(r"""(?P<attr>href|src)=(?P<quote>["'])(?P<url>.*?)(?P=quote)""")


def article_html(source: str) -> str:
    rendered = markdown.markdown(
        html.escape(source),
        extensions=["fenced_code", "nl2br", "sane_lists"],
        output_format="html",
    )
    return _HREF.sub(_guard_url, rendered)


def _guard_url(match: re.Match[str]) -> str:
    url = html.unescape(match.group("url"))
    if _allowed(url):
        return match.group(0)
    return f"{match.group('attr')}={match.group('quote')}#{match.group('quote')}"


def _allowed(url: str) -> bool:
    if url.startswith("//"):
        return False
    parsed = urlsplit(url)
    if parsed.scheme in {"http", "https", "mailto"}:
        return True
    if parsed.scheme:
        return False
    return url.startswith(("#", "/"))
