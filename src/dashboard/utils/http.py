"""Small retrying HTTP helper."""

from __future__ import annotations

import time
from typing import Any

import requests

from dashboard.utils.sanitize import sanitize


RETRY_STATUSES = {429, 500, 502, 503, 504}
RETRY_EXCEPTIONS = (requests.Timeout, requests.ConnectionError)


def get_json(url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: int = 30, retries: int = 2) -> Any:
    return _get(url, params=params, headers=headers, timeout=timeout, retries=retries).json()


def get_text(url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: int = 30, retries: int = 2) -> str:
    return _get(url, params=params, headers=headers, timeout=timeout, retries=retries).text


def _get(url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: int = 30, retries: int = 2) -> requests.Response:
    session = requests.Session()
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = session.get(url, params=params, headers=headers, timeout=timeout)
            if response.status_code in RETRY_STATUSES and attempt < retries:
                time.sleep(0.5 * 2**attempt)
                continue
            response.raise_for_status()
            return response
        except RETRY_EXCEPTIONS as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.5 * 2**attempt)
                continue
            break
        except requests.RequestException as exc:
            last_error = exc
            break
    raise RuntimeError(sanitize(last_error or "request failed"))
