"""
vBase API Client

This module provides a Python client for interacting with the vBase API.
The client supports operations for collections, stamps, and users.

API Documentation: https://docs.vbase.com/
Swagger: https://app.vbase.com/swagger/
"""

import json
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any, BinaryIO, Union

from ._version import __version__
from .vbase_api_models import (
    Collection,
    StampCreatedResponse,
    IdempotentStampResponse,
    VerificationResult,
    AccountSettings,
)

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

class VBaseAPIClient:
    """
    Client for interacting with the vBase API.

    The vBase API provides endpoints for stamping data on the blockchain,
    managing vBase collections, and verifying stamped content.

    Args:
        api_key: Bearer token for API authentication
        base_url: Base URL of the vBase API (default: https://app.vbase.com)
        timeout: Request timeout in seconds (default: 30)

    Example:
        >>> client = VBaseAPIClient(api_key="your-bearer-token")
        >>> collections = client.list_collections()
        >>> stamp = client.create_stamp(data={"hello": "world"})
    """

    DEFAULT_BASE_URL = "https://app.vbase.com"
    API_VERSION = "v1"

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 30
    ):
        """Initialize the vBase API client."""
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'User-Agent': f'vBase API Python Client v{__version__}',
        })

    def _get_url(self, endpoint: str) -> str:
        """Construct the full API URL for an endpoint."""
        endpoint = endpoint.lstrip('/')
        return f"{self.base_url}/api/{self.API_VERSION}/{endpoint}"

    def _handle_response(self, response: requests.Response) -> Any:
        """Handle API response and raise appropriate exceptions."""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', str(e))
                raise VBaseAPIError(error_msg, response.status_code) from e
            except (ValueError, json.JSONDecodeError) as exc:
                raise VBaseAPIError(str(e), response.status_code) from exc
        except requests.exceptions.RequestException as e:
            raise VBaseAPIError(f"Request failed: {str(e)}") from e

    def _prepare_file_upload(self, file: Union[str, Path, BinaryIO]) -> tuple:
        """
        Prepare a file for upload.
        
        Args:
            file: File path (string or Path) or file-like object
            
        Returns:
            Tuple of (filename, file_object, content_type) suitable for requests files parameter
        """
        if isinstance(file, (str, Path)):
            file_path = Path(file)
            return (file_path.name, open(file_path, 'rb'), 'application/octet-stream')
        else:
            # Assume it's a file-like object
            return file

    def _close_files(self, files: Dict[str, Any]) -> None:
        """
        Close any opened files in the files dictionary.
        
        Args:
            files: Dictionary of file tuples from requests
        """
        for file_tuple in files.values():
            if hasattr(file_tuple, '__iter__') and len(file_tuple) > 1:
                file_obj = file_tuple[1]
                if hasattr(file_obj, 'close'):
                    file_obj.close()

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
            >>> collections = client.get_collections(is_pinned=True)
            >>> for collection in collections:
            ...     print(f"{collection.name}: {collection.cid}")
        """
        params = {}
        if user_address is not None:
            params['user_address'] = user_address
        if is_pinned is not None:
            params['is_pinned'] = is_pinned

        response = self.session.get(
            self._get_url('collections'),
            params=params,
            timeout=self.timeout
        )
        data = self._handle_response(response)
        return [Collection.from_dict(item) for item in data]

    def create_collection(
        self,
        name: str,
        description: str,
        cid: str = None,
        is_pinned: bool = True
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
            >>> collection = client.create_collection(
            ...     name="My Collection",
            ...     cid="0x1234567890abcdef...",
            ...     description="A sample collection",
            ...     is_pinned=True
            ... )
            >>> print(f"Created: {collection.name}")
        """
        data = {
            'name': name,
            'cid': cid,
            'description': description,
            'is_pinned': is_pinned
        }

        response = self.session.post(
            self._get_url('collections'),
            json=data,
            timeout=self.timeout
        )
        result = self._handle_response(response)
        return Collection.from_dict(result)

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
        idempotency_window: int = 3600
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

        Returns:
            StampCreatedResponse (201 status) or IdempotentStampResponse (200 status)

        Raises:
            VBaseAPIError: If the request fails
            ValueError: If invalid parameters are provided
        
        Example:
            >>> # Stamp inline data
            >>> stamp = client.create_stamp(data={"hello": "world"})
            >>> print(f"Object CID: {stamp.commitment_receipt.object_cid}")
            
            >>> # Stamp a file
            >>> stamp = client.create_stamp(file="document.pdf", collection_name="Documents")
            >>> if stamp.file_object:
            ...     print(f"File: {stamp.file_object.file_name}")
            
            >>> # Stamp an existing CID
            >>> stamp = client.create_stamp(data_cid="Qm...")
        """
        if not any([file, data, data_cid]):
            raise ValueError("At least one of 'file', 'data', or 'data_cid' must be provided")

        if collection_cid and collection_name:
            raise ValueError("Only one of 'collection_cid' or 'collection_name' can be specified")

        form_data = {
            'store_stamped_file': store_stamped_file,
            'idempotent': idempotent,
            'idempotency_window': idempotency_window
        }

        if data_cid:
            form_data['data_cid'] = data_cid
        if collection_cid:
            form_data['collection_cid'] = collection_cid
        if collection_name:
            form_data['collection_name'] = collection_name
        if file_name:
            form_data['file_name'] = file_name

        files = {}

        # Handle file parameter
        if file:
            files['file'] = self._prepare_file_upload(file)

        # Handle data parameter
        if data:
            if isinstance(data, dict):
                form_data['data'] = json.dumps(data)
            else:
                form_data['data'] = data

        try:
            response = self.session.post(
                self._get_url('stamps'),
                data=form_data,
                files=files if files else None,
                timeout=self.timeout
            )
            result = self._handle_response(response)

            # Return appropriate response type based on status code
            if response.status_code == 200:
                return IdempotentStampResponse.from_dict(result)
            else:
                return StampCreatedResponse.from_dict(result)
        finally:
            self._close_files(files)

    def upload_stamped_file(
        self,
        collection_name: str,
        file: Union[str, Path, BinaryIO]
    ) -> StampCreatedResponse:
        """
        Upload a file that has been previously stamped.

        This endpoint validates that the file exists in the blockchain for the
        authenticated user and specified collection.

        Args:
            collection_name: Collection name for blockchain verification (case-insensitive)
            file: Previously stamped file to be uploaded (path or file-like object)

        Returns:
            StampCreatedResponse with commitment receipt and file object

        Raises:
            VBaseAPIError: If validation fails or file not found in blockchain

        Example:
            >>> result = client.upload_stamped_file(
            ...     collection_name="My Collection",
            ...     file="stamped_document.pdf"
            ... )
            >>> print(f"Uploaded: {result.file_object.file_name}")
        """
        form_data = {
            'collection_name': collection_name
        }

        files = {}

        files['file'] = self._prepare_file_upload(file)

        try:
            response = self.session.post(
                self._get_url('stamps/upload-stamped-file'),
                data=form_data,
                files=files,
                timeout=self.timeout
            )
            result = self._handle_response(response)
            return StampCreatedResponse.from_dict(result)
        finally:
            self._close_files(files)

    def verify_stamps(
        self,
        cids: List[str],
        filter_by_user: bool = False
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
            >>> result = client.verify_stamps(
            ...     cids=["0xbd...1", "0xcd...2"],
            ...     filter_by_user=True
            ... )
            >>> for stamp in result.stamp_list:
            ...     print(f"Found stamp at {stamp.timestamp}")
        """
        data = {
            'cids': cids,
            'filter_by_user': filter_by_user
        }

        response = self.session.post(
            self._get_url('stamps/verify'),
            json=data,
            timeout=self.timeout
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
            >>> user = client.get_current_user()
            >>> print(f"User email: {user.email}")
        """
        response = self.session.get(
            self._get_url('users/me'),
            timeout=self.timeout
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
            >>> user = client.get_user("0x...")
            >>> print(f"User name: {user.name}")
        """
        response = self.session.get(
            self._get_url(f'users/{user_address}'),
            timeout=self.timeout
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
    timeout: int = 30
) -> VBaseAPIClient:
    """
    Create a vBase API client.

    Args:
        api_key: Bearer token for API authentication
        base_url: Base URL of the vBase API
        timeout: Request timeout in seconds

    Returns:
        Configured VBaseAPIClient instance

    Example:
        >>> client = create_client(api_key="your-bearer-token")
        >>> collections = client.get_collections()
    """
    return VBaseAPIClient(api_key=api_key, base_url=base_url, timeout=timeout)
