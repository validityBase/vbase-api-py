"""
vBase API Client

This module provides a Python client for interacting with the vBase API.
The client supports operations for collections, stamps, and users.

API Documentation: https://docs.vbase.com/
Swagger: https://app.vbase.com/swagger/
"""

import json
from pathlib import Path
from typing import Any, BinaryIO, Callable, Dict, List, Optional, TypeVar, Union

import requests
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt
from tenacity.wait import wait_incrementing

from ._version import __version__
from .retry import RetryConfig
from .vbase_api_models import (
    AccountSettings,
    Collection,
    IdempotentStampResponse,
    StampCreatedResponse,
    VerificationResult,
)

ResultType = TypeVar("ResultType")


class VBaseAPIError(Exception):
    """Base exception for vBase API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self):
        error_msg = f"{self.message}"
        if self.status_code:
            error_msg = f"[{self.status_code}] {error_msg}"
        return error_msg


class _RetryableHTTPError(Exception):
    """Internal exception used to let Tenacity retry transient responses."""

    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class VBaseAPIClient:
    """
    Client for interacting with the vBase API.

    The vBase API provides endpoints for stamping data on the blockchain,
    managing vBase collections, and verifying stamped content.

    Args:
        api_key: Bearer token for API authentication
        base_url: Base URL of the vBase API (default: https://app.vbase.com)
        timeout: Request timeout in seconds (default: 30)
        retry_config: Retry behavior for retry-safe API operations

    Example:
        .. code-block:: python

            client = VBaseAPIClient(api_key="your-bearer-token")
            collections = client.list_collections()
            stamp = client.create_stamp(data={"hello": "world"})
    """

    DEFAULT_BASE_URL = "https://app.vbase.com"
    API_VERSION = "v1"

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 30,
        retry_config: Optional[RetryConfig] = None,
    ):
        """Initialize the vBase API client."""
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "User-Agent": f"vBase API Python Client v{__version__}",
            }
        )

    def _get_url(self, endpoint: str) -> str:
        """Construct the full API URL for an endpoint."""
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/api/{self.API_VERSION}/{endpoint}"

    @staticmethod
    def _get_response_error(response: requests.Response) -> str:
        """Extract a useful API error message from an HTTP response."""
        try:
            error_data = response.json()
        except (ValueError, json.JSONDecodeError):
            return response.reason or f"HTTP {response.status_code}"

        if isinstance(error_data, dict):
            return str(error_data.get("error") or response.reason or error_data)
        return response.reason or str(error_data)

    def _handle_response(self, response: requests.Response) -> Any:
        """Handle an API response and raise the public client exception."""
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise VBaseAPIError(
                self._get_response_error(response), response.status_code
            ) from exc
        return response.json()

    def _request_once(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> requests.Response:
        """Send one HTTP request and classify transient HTTP responses."""
        response = self.session.request(
            method,
            self._get_url(endpoint),
            timeout=self.timeout,
            **kwargs,
        )
        if response.status_code in self.retry_config.retry_status_codes:
            error = _RetryableHTTPError(
                self._get_response_error(response), response.status_code
            )
            response.close()
            raise error
        return response

    def _execute_with_retry(
        self,
        operation: Callable[[], ResultType],
        *,
        retry_safe: bool,
    ) -> ResultType:
        """Execute an operation with the configured linear retry policy."""
        should_retry = (
            retry_safe
            and self.retry_config.enabled
            and self.retry_config.max_attempts > 1
        )

        try:
            if not should_retry:
                return operation()

            retrying = Retrying(
                retry=retry_if_exception_type(
                    (
                        requests.exceptions.ConnectionError,
                        requests.exceptions.Timeout,
                        _RetryableHTTPError,
                    )
                ),
                wait=wait_incrementing(
                    start=self.retry_config.initial_delay,
                    increment=self.retry_config.delay_increment,
                    max=self.retry_config.max_delay,
                ),
                stop=stop_after_attempt(self.retry_config.max_attempts),
                reraise=True,
            )
            return retrying(operation)
        except _RetryableHTTPError as exc:
            raise VBaseAPIError(exc.message, exc.status_code) from exc
        except requests.exceptions.RequestException as exc:
            raise VBaseAPIError(f"Request failed: {str(exc)}") from exc

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        retry_safe: bool,
        **kwargs: Any,
    ) -> requests.Response:
        """Send a request, applying retries only when replay is safe."""
        return self._execute_with_retry(
            lambda: self._request_once(method, endpoint, **kwargs),
            retry_safe=retry_safe,
        )

    @staticmethod
    def _get_stream_position(file: Union[str, Path, BinaryIO]) -> Optional[int]:
        """Return the current position when a caller-owned stream is replayable."""
        if isinstance(file, (str, Path)):
            return 0
        try:
            if file.seekable():
                return file.tell()
        except (AttributeError, OSError):
            pass
        return None

    def _prepare_file_upload(
        self,
        file: Union[str, Path, BinaryIO],
        stream_position: Optional[int] = None,
    ) -> tuple:
        """
        Prepare a file for upload.

        Args:
            file: File path (string or Path) or file-like object
            stream_position: Position to restore before replaying a caller-owned stream

        Returns:
            Tuple of (prepared_file, opened_file). prepared_file is suitable for
            the requests files parameter; opened_file is the client-owned file
            handle to close, or None for caller-owned streams.
        """
        if isinstance(file, (str, Path)):
            file_path = Path(file)
            file_object = open(file_path, "rb")
            return (
                (file_path.name, file_object, "application/octet-stream"),
                file_object,
            )

        if stream_position is not None:
            file.seek(stream_position)
        return file, None

    # ========================================================================
    # Collections API
    # ========================================================================

    def get_collections(
        self,
        user_address: Optional[str] = None,
        is_pinned: Optional[bool] = None,
    ) -> List[Collection]:
        """
        Get collections with optional filtering.

        Args:
            user_address: Filter by user address
            is_pinned: Filter by pinned status

        Returns:
            List of Collection objects

        Raises:
            VBaseAPIError: If the request fails

        Example:
            .. code-block:: python

                collections = client.get_collections(is_pinned=True)
                for collection in collections:
                    print(f"{collection.name}: {collection.cid}")
        """
        params = {}
        if user_address is not None:
            params["user_address"] = user_address
        if is_pinned is not None:
            params["is_pinned"] = is_pinned

        response = self._request(
            "GET",
            "collections",
            retry_safe=True,
            params=params,
        )
        data = self._handle_response(response)
        return [Collection.from_dict(item) for item in data]

    def _find_matching_collection(
        self,
        *,
        name: str,
        description: str,
        cid: Optional[str],
        is_pinned: bool,
    ) -> Optional[Collection]:
        """Find a collection matching a create request after an uncertain result."""
        for collection in self.get_collections():
            if collection.name != name:
                continue
            if cid is not None and collection.cid.lower() != cid.lower():
                continue
            if collection.description != description:
                continue
            if collection.is_pinned != is_pinned:
                continue
            return collection
        return None

    def create_collection(
        self, name: str, description: str, cid: str = None, is_pinned: bool = True
    ) -> Collection:
        """
        Create a new user collection.

        Args:
            name: Collection name
            cid: Collection CID
            description: Collection description
            is_pinned: Whether the collection is pinned

        Returns:
            Created Collection object

        Raises:
            VBaseAPIError: If the request fails or collection already exists

        Example:
            .. code-block:: python

                collection = client.create_collection(
                    name="My Collection",
                    cid="0x1234567890abcdef...",
                    description="A sample collection",
                    is_pinned=True
                )
                print(f"Created: {collection.name}")
        """
        data = {
            "name": name,
            "cid": cid,
            "description": description,
            "is_pinned": is_pinned,
        }

        request_attempts = 0

        def create_attempt() -> Collection:
            nonlocal request_attempts

            if request_attempts:
                existing = self._find_matching_collection(
                    name=name,
                    description=description,
                    cid=cid,
                    is_pinned=is_pinned,
                )
                if existing is not None:
                    return existing

            request_attempts += 1
            response = self._request_once("POST", "collections", json=data)
            result = self._handle_response(response)
            return Collection.from_dict(result)

        try:
            return self._execute_with_retry(create_attempt, retry_safe=True)
        except VBaseAPIError as exc:
            if exc.status_code == 409 and request_attempts > 1:
                existing = self._find_matching_collection(
                    name=name,
                    description=description,
                    cid=cid,
                    is_pinned=is_pinned,
                )
                if existing is not None:
                    return existing
            raise

    # ========================================================================
    # Stamps API
    # ========================================================================

    def create_stamp(
        self,
        file: Optional[Union[str, Path, BinaryIO]] = None,
        data: Optional[Union[str, Dict]] = None,
        file_name: Optional[str] = None,
        data_cid: Optional[str] = None,
        collection_cid: Optional[str] = None,
        collection_name: Optional[str] = None,
        store_stamped_file: bool = True,
        idempotent: bool = True,
        idempotency_window: int = 3600,
    ) -> Union[StampCreatedResponse, IdempotentStampResponse]:
        """
        Stamp a file, data, or CID.

        At least one of 'file', 'data', or 'data_cid' must be provided.
        If you want to add the stamp to a collection,
        one collection parameter (collection_cid or collection_name) should be specified.

        Args:
            file: Binary file to be stamped (path or file-like object)
            data: Inline text or JSON data to be stamped (string or dict)
            file_name: Custom file name for data (only used when 'data' is provided)
            data_cid: Existing CID to stamp
            collection_cid: Optional CID of collection to group stamped object
            collection_name: Optional name of collection (case-insensitive)
            store_stamped_file: Whether to store the stamped file (default: True)
            idempotent: Enable idempotency (default: True)
            idempotency_window: Idempotency window in seconds (default: 3600)

        Retries:
            Requests are retried only when ``idempotent`` is true, the
            idempotency window is non-positive (unlimited), and any file input
            can be replayed. Finite-window and non-idempotent stamps are always
            sent once.

        Returns:
            StampCreatedResponse (201 status) or IdempotentStampResponse (200 status)

        Raises:
            VBaseAPIError: If the request fails
            ValueError: If invalid parameters are provided

        Example:
            .. code-block:: python

                # Stamp inline data
                stamp = client.create_stamp(data={"hello": "world"})
                print(f"Object CID: {stamp.commitment_receipt.object_cid}")

                # Stamp a file
                stamp = client.create_stamp(file="document.pdf", collection_name="Documents")
                if stamp.file_object:
                    print(f"File: {stamp.file_object.file_name}")

                # Stamp an existing CID
                stamp = client.create_stamp(data_cid="Qm...")
        """
        if not any([file, data, data_cid]):
            raise ValueError(
                "At least one of 'file', 'data', or 'data_cid' must be provided"
            )

        if collection_cid and collection_name:
            raise ValueError(
                "Only one of 'collection_cid' or 'collection_name' can be specified"
            )

        form_data = {
            "store_stamped_file": store_stamped_file,
            "idempotent": idempotent,
            "idempotency_window": idempotency_window,
        }

        if data_cid:
            form_data["data_cid"] = data_cid
        if collection_cid:
            form_data["collection_cid"] = collection_cid
        if collection_name:
            form_data["collection_name"] = collection_name
        if file_name:
            form_data["file_name"] = file_name

        # Handle data parameter
        if data:
            if isinstance(data, dict):
                form_data["data"] = json.dumps(data)
            else:
                form_data["data"] = data

        stream_position = self._get_stream_position(file) if file else None
        replayable_input = not file or stream_position is not None
        retry_safe = idempotent and idempotency_window <= 0 and replayable_input

        def stamp_attempt() -> Union[StampCreatedResponse, IdempotentStampResponse]:
            files: Dict[str, Any] = {}
            opened_file = None
            try:
                if file:
                    files["file"], opened_file = self._prepare_file_upload(
                        file, stream_position
                    )

                response = self._request_once(
                    "POST",
                    "stamps",
                    data=form_data,
                    files=files if files else None,
                )
                result = self._handle_response(response)

                if response.status_code == 200:
                    return IdempotentStampResponse.from_dict(result)
                return StampCreatedResponse.from_dict(result)
            finally:
                if opened_file is not None:
                    opened_file.close()

        return self._execute_with_retry(stamp_attempt, retry_safe=retry_safe)

    def upload_stamped_file(
        self, collection_name: str, file: Union[str, Path, BinaryIO]
    ) -> StampCreatedResponse:
        """
        Upload a file that has been previously stamped.

        This endpoint validates that the file exists in the blockchain for the
        authenticated user and specified collection.

        Args:
            collection_name: Collection name for blockchain verification (case-insensitive)
            file: Previously stamped file to be uploaded (path or file-like object)

        Retries:
            Paths and seekable streams are replayed with the configured retry
            policy. Non-seekable streams are sent once.

        Returns:
            StampCreatedResponse with commitment receipt and file object

        Raises:
            VBaseAPIError: If validation fails or file not found in blockchain

        Example:
            .. code-block:: python

                result = client.upload_stamped_file(
                    collection_name="My Collection",
                    file="stamped_document.pdf"
                )
                print(f"Uploaded: {result.file_object.file_name}")
        """
        form_data = {"collection_name": collection_name}

        stream_position = self._get_stream_position(file)

        def upload_attempt() -> StampCreatedResponse:
            opened_file = None
            try:
                prepared_file, opened_file = self._prepare_file_upload(
                    file, stream_position
                )
                response = self._request_once(
                    "POST",
                    "stamps/upload-stamped-file",
                    data=form_data,
                    files={"file": prepared_file},
                )
                result = self._handle_response(response)
                return StampCreatedResponse.from_dict(result)
            finally:
                if opened_file is not None:
                    opened_file.close()

        return self._execute_with_retry(
            upload_attempt,
            retry_safe=stream_position is not None,
        )

    def verify_stamps(
        self, cids: List[str], filter_by_user: bool = False
    ) -> VerificationResult:
        """
        Verify one or more Content IDs (CIDs).

        This endpoint checks whether Content IDs (SHA3 hash) have previously been
        stamped on the blockchain using vBase. If a match is found, returns the full
        stamp details including timestamp, blockchain address, and other stamp details.

        Args:
            cids: Array of CIDs to verify
            filter_by_user: When true, only return results owned by the current user

        Returns:
            VerificationResult with display timezone and stamp list

        Raises:
            VBaseAPIError: If the request fails

        Example:
            .. code-block:: python

                result = client.verify_stamps(
                    cids=["0xbd...1", "0xcd...2"],
                    filter_by_user=True
                )
                for stamp in result.stamp_list:
                    print(f"Found stamp at {stamp.timestamp}")
        """
        data = {"cids": cids, "filter_by_user": filter_by_user}

        response = self._request(
            "POST",
            "stamps/verify",
            retry_safe=True,
            json=data,
        )
        result = self._handle_response(response)
        return VerificationResult.from_dict(result)

    # ========================================================================
    # Users API
    # ========================================================================

    def get_current_user(self) -> AccountSettings:
        """
        Retrieve current user account settings.

        Returns:
            AccountSettings for the authenticated user

        Raises:
            VBaseAPIError: If the request fails

        Example:
            .. code-block:: python

                user = client.get_current_user()
                print(f"User email: {user.email}")
        """
        response = self._request(
            "GET",
            "users/me",
            retry_safe=True,
        )
        result = self._handle_response(response)
        return AccountSettings.from_dict(result)

    def get_user(self, user_address: str) -> AccountSettings:
        """
        Retrieve user account settings by address.

        Args:
            user_address: The user's blockchain address

        Returns:
            AccountSettings for the specified user

        Raises:
            VBaseAPIError: If the request fails or user not found

        Example:
            .. code-block:: python

                user = client.get_user("0x...")
                print(f"User name: {user.name}")
        """
        response = self._request(
            "GET",
            f"users/{user_address}",
            retry_safe=True,
        )
        result = self._handle_response(response)
        return AccountSettings.from_dict(result)

    def close(self):
        """Close the session and cleanup resources."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience function for quick client creation
def create_client(
    api_key: str,
    base_url: str = VBaseAPIClient.DEFAULT_BASE_URL,
    timeout: int = 30,
    retry_config: Optional[RetryConfig] = None,
) -> VBaseAPIClient:
    """
    Create a vBase API client.

    Args:
        api_key: Bearer token for API authentication
        base_url: Base URL of the vBase API
        timeout: Request timeout in seconds
        retry_config: Retry behavior for retry-safe API operations

    Returns:
        Configured VBaseAPIClient instance

    Example:
        .. code-block:: python

            client = create_client(api_key="your-bearer-token")
            collections = client.get_collections()
    """
    return VBaseAPIClient(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        retry_config=retry_config,
    )
