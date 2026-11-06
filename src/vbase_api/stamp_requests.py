"""Serialize local mutations and replay only server-confirmed contention."""

import hashlib
import threading
import time
import weakref
from collections.abc import Mapping
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit

import requests

_MAX_ATTEMPTS = 5
_DEFAULT_RETRY_SECONDS = 2
_BUSY_STATUS = 409
_BUSY_CODE = "stamp_in_progress"
_ERROR_CODE = "error_code"
_RETRY_AFTER = "Retry-After"
_IDEMPOTENT = "idempotent"
_AUTHORIZATION = "Authorization"
_FILE_CONTENT_INDEX = 1
_DEFAULT_PORTS = {"http": 80, "https": 443}
_registry_lock = threading.Lock()
_user_locks: weakref.WeakValueDictionary = weakref.WeakValueDictionary()


def _retry_delay(value: str) -> float:
    try:
        if value.isascii() and value.isdigit():
            return float(int(value))
        retry_at = parsedate_to_datetime(value)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        return max(0, (retry_at - datetime.now(timezone.utc)).total_seconds())
    except (ValueError, TypeError, OverflowError):
        return _DEFAULT_RETRY_SECONDS


def _file_offsets(files: Any) -> list[tuple[Any, int | None]]:
    """Remember every multipart stream, including repeated names and list entries."""
    offsets = []
    entries = (
        files.values()
        if isinstance(files, Mapping)
        else (entry[_FILE_CONTENT_INDEX] for entry in files)
    )
    for stream in entries:
        stream = (
            stream[_FILE_CONTENT_INDEX] if isinstance(stream, (tuple, list)) else stream
        )
        if hasattr(stream, "read"):
            try:
                offset = stream.tell()
            except (AttributeError, OSError):
                offset = None
            offsets.append((stream, offset))
    return offsets


def post_stamp_operation(
    session: requests.Session, url: str, headers: dict[str, str], **kwargs: Any
) -> requests.Response:
    """POST under a process-local credential queue; return the final response.

    The app guard remains authoritative across processes and API keys. Unknown
    transport/5xx outcomes are never replayed. Multipart streams must be seekable
    to retry; their original offsets, filenames and content are preserved.
    """
    parsed = urlsplit(url)
    key = (
        parsed.scheme.lower(),
        parsed.hostname,
        parsed.port if parsed.port is not None else _DEFAULT_PORTS.get(parsed.scheme),
        hashlib.sha256(headers.get(_AUTHORIZATION, "").encode()).digest(),
    )
    with _registry_lock:
        lock = _user_locks.get(key)
        if lock is None:
            lock = threading.RLock()
            _user_locks[key] = lock
    with lock:
        offsets = _file_offsets(kwargs.get("files") or {})
        for attempt in range(_MAX_ATTEMPTS):
            response = session.post(url, headers=headers, **kwargs)
            if response.status_code != _BUSY_STATUS:
                return response
            try:
                body = response.json()
            except ValueError:
                return response
            if not isinstance(body, dict) or body.get(_ERROR_CODE) != _BUSY_CODE:
                return response
            if attempt == _MAX_ATTEMPTS - 1:
                return response
            for stream, offset in offsets:
                if offset is None:
                    raise ValueError("Cannot retry a non-seekable stamp upload")
                stream.seek(offset)
            form = kwargs.get("data")
            if isinstance(form, dict) and _IDEMPOTENT in form:
                kwargs["data"] = {**form, _IDEMPOTENT: "true"}
            delay = _retry_delay(response.headers.get(_RETRY_AFTER, ""))
            response.close()
            time.sleep(delay)
    raise AssertionError("Unreachable retry state")
