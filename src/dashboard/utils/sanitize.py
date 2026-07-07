"""Credential sanitization helpers."""

from __future__ import annotations

import os
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SECRET_SUFFIXES = ("_KEY", "_TOKEN", "_SECRET")
SECRET_QUERY_KEYS = {"api_key", "token", "access_token", "authorization"}


def sanitize(value: object) -> str:
    text = str(value)
    text = _sanitize_urls(text)
    text = re.sub(r"(?i)(authorization:\s*)(bearer\s+)?[^\s,;]+", r"\1***", text)
    for name, secret in os.environ.items():
        if name.endswith(SECRET_SUFFIXES) and secret:
            text = text.replace(secret, "***")
    return text


def _sanitize_urls(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        url = match.group(0)
        parts = urlsplit(url)
        query = urlencode(
            [(key, "***" if key.lower() in SECRET_QUERY_KEYS else value) for key, value in parse_qsl(parts.query, keep_blank_values=True)]
        )
        return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment)).replace("%2A%2A%2A", "***")

    return re.sub(r"https?://[^\s)>\]]+", repl, text)
