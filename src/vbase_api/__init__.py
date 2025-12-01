# src/simplemath/__init__.py

from ._version import __version__
from .vbase_api_client import VBaseAPIError, VBaseAPIClient
from .vbase_api_models import (
    Collection,
    StampCreatedResponse,
    IdempotentStampResponse,
    VerificationResult,
    AccountSettings,
)

__all__ = [
    "__version__",
    "VBaseAPIClient",
    "VBaseAPIError",
    "Collection",
    "StampCreatedResponse",
    "IdempotentStampResponse",
    "VerificationResult",
    "AccountSettings",
]
