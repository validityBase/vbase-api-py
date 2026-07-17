"""Live file-integrity E2E coverage for the vBase API Python client.

These tests intentionally call the public ``VBaseAPIClient`` stamping methods
and then read the stored object from S3 to verify the final bytes. They are
skipped unless live E2E credentials are supplied through environment variables;
see ``internal/specs/e2e-file-integrity.md``.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
import unittest
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError as exc:  # pragma: no cover
    raise unittest.SkipTest(
        "Install requirements/lock/e2e.txt to run live file-integrity E2E tests."
    ) from exc

from vbase_api import VBaseAPIClient, VBaseAPIError


def _sha3_256_cid(payload: bytes) -> str:
    return "0x" + hashlib.sha3_256(payload).hexdigest()


def _first_env(*names: str) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _int_env(name: str, default: int) -> int:
    value = _first_env(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        raise ValueError(
            f"{name} must be an integer number of seconds; got {value!r}."
        ) from None


@dataclass(frozen=True)
class LiveE2EConfig:
    """Configuration needed for live app/API file-integrity tests."""

    api_key: str
    base_url: str
    s3_bucket: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_session_token: Optional[str]
    aws_region: str
    timeout: int

    @classmethod
    def from_env(cls) -> "LiveE2EConfig":
        api_key = _first_env("VBASE_API_KEY_CYPRESS", "VBASE_API_KEY")
        if not api_key:
            raise unittest.SkipTest(
                "Set VBASE_API_KEY_CYPRESS or VBASE_API_KEY to run live "
                "file-integrity E2E tests."
            )

        s3_bucket = _first_env("S3_VALIDATION_BUCKET")
        if not s3_bucket:
            raise unittest.SkipTest(
                "Set S3_VALIDATION_BUCKET to run live file-integrity E2E tests."
            )

        aws_access_key_id = _first_env("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = _first_env("AWS_SECRET_ACCESS_KEY", "AWS_SECRET_KEY")
        if not aws_access_key_id or not aws_secret_access_key:
            raise unittest.SkipTest(
                "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY "
                "(or AWS_SECRET_KEY) to download stored files from S3."
            )

        return cls(
            api_key=api_key,
            base_url=_first_env("BASE_URL", "SITE_URL") or "https://staging.app.vbase.com",
            s3_bucket=s3_bucket,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=_first_env("AWS_SESSION_TOKEN"),
            aws_region=_first_env("AWS_REGION", "AWS_DEFAULT_REGION") or "us-east-1",
            timeout=_int_env("FILE_INTEGRITY_E2E_TIMEOUT", 60),
        )


@dataclass(frozen=True)
class FileCase:
    """Source bytes for one integrity scenario."""

    label: str
    file_name: str
    content: bytes

    @property
    def object_cid(self) -> str:
        return _sha3_256_cid(self.content)


class VBaseAPIClientFileIntegrityE2ETests(unittest.TestCase):
    """Verify vbase-api-py stamped-file storage preserves exact bytes."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = LiveE2EConfig.from_env()
        cls.client = VBaseAPIClient(
            api_key=cls.config.api_key,
            base_url=cls.config.base_url.rstrip("/"),
            timeout=cls.config.timeout,
        )
        cls.s3_client = boto3.session.Session(
            aws_access_key_id=cls.config.aws_access_key_id,
            aws_secret_access_key=cls.config.aws_secret_access_key,
            aws_session_token=cls.config.aws_session_token,
            region_name=cls.config.aws_region,
        ).client("s3")

    @classmethod
    def tearDownClass(cls) -> None:
        client = getattr(cls, "client", None)
        if client is not None:
            client.close()

        s3_client = getattr(cls, "s3_client", None)
        if s3_client is not None:
            s3_client.close()

    @staticmethod
    def _file_cases(prefix: str) -> Iterable[FileCase]:
        suffix = uuid.uuid4().hex
        yield FileCase(
            label="text",
            file_name=f"{prefix}-{suffix}.txt",
            content=f"vbase-api-py {prefix} text payload {suffix}\n".encode("utf-8"),
        )
        yield FileCase(
            label="binary",
            file_name=f"{prefix}-{suffix}.bin",
            content=(
                bytes([0, 1, 2, 3, 4, 127, 128, 254, 255])
                + f" vbase-api-py {prefix} binary payload {suffix} ".encode("utf-8")
                + bytes([255, 0, 64, 32, 16, 8])
            ),
        )

    def _create_collection(self, name_prefix: str):
        collection_name = f"{name_prefix}-{uuid.uuid4().hex[:12]}"
        deadline = time.monotonic() + _int_env(
            "FILE_INTEGRITY_E2E_API_WAIT_SECONDS", 60
        )
        last_error = None

        while True:
            try:
                return self.client.create_collection(
                    name=collection_name,
                    description="vbase-api-py VDT-831 file-integrity E2E collection",
                    is_pinned=False,
                )
            except VBaseAPIError as exc:
                if not exc.status_code or exc.status_code < 500:
                    raise
                last_error = exc

            if time.monotonic() >= deadline:
                raise AssertionError(
                    f"Timed out creating collection {collection_name}; "
                    f"last error: {last_error}"
                ) from last_error

            time.sleep(5)

    def _write_temp_file(self, directory: Path, file_case: FileCase) -> Path:
        path = directory / file_case.file_name
        path.write_bytes(file_case.content)
        return path

    def _download_stored_file(self, file_path: str) -> bytes:
        deadline = time.monotonic() + _int_env(
            "FILE_INTEGRITY_E2E_STORAGE_WAIT_SECONDS", 120
        )
        last_error = None

        while time.monotonic() < deadline:
            try:
                response = self.s3_client.get_object(
                    Bucket=self.config.s3_bucket,
                    Key=file_path,
                )
                body = response["Body"]
                try:
                    payload = body.read()
                finally:
                    body.close()

                content_length = response.get("ContentLength")
                if content_length is not None and content_length != len(payload):
                    raise AssertionError(
                        f"S3 ContentLength mismatch for {file_path}: "
                        f"metadata={content_length}, bytes={len(payload)}"
                    )
                return payload
            except (BotoCoreError, ClientError, KeyError) as exc:
                last_error = str(exc)

            time.sleep(5)

        raise AssertionError(
            f"Stored file was not downloadable before timeout: {file_path}; "
            f"last error: {last_error}"
        )

    def _assert_file_object_path(self, file_path: str, collection_name: str) -> None:
        self.assertIn(
            f"/collections/{collection_name}/stamped/",
            file_path,
        )

    def _assert_download_integrity(self, file_path: str, file_case: FileCase) -> None:
        downloaded = self._download_stored_file(file_path)

        self.assertEqual(
            len(downloaded),
            len(file_case.content),
            f"{file_case.label} downloaded byte size",
        )
        self.assertEqual(
            _sha3_256_cid(downloaded),
            file_case.object_cid,
            f"{file_case.label} downloaded SHA3-256",
        )
        self.assertEqual(
            downloaded,
            file_case.content,
            f"{file_case.label} downloaded bytes",
        )

    def _wait_for_indexed_stamp(self, object_cid: str, collection_cid: str) -> None:
        deadline = time.monotonic() + _int_env(
            "FILE_INTEGRITY_E2E_INDEX_WAIT_SECONDS", 120
        )
        while time.monotonic() < deadline:
            result = self.client.verify_stamps([object_cid], filter_by_user=True)
            for receipt in result.stamp_list:
                if (
                    receipt.object_cid.lower() == object_cid.lower()
                    and receipt.set_cid.lower() == collection_cid.lower()
                ):
                    return
            time.sleep(5)

        raise AssertionError(
            f"Timed out waiting for indexed stamp: object_cid={object_cid}, "
            f"collection_cid={collection_cid}"
        )

    def test_create_stamp_with_storage_preserves_downloaded_file_bytes(self):
        """UC-A: create_stamp stores text and binary files without byte drift."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            for file_case in self._file_cases("create-stamp"):
                with self.subTest(format=file_case.label):
                    collection = self._create_collection(
                        f"vapi-create-{file_case.label}"
                    )
                    source_path = self._write_temp_file(temp_dir, file_case)

                    response = self.client.create_stamp(
                        file=source_path,
                        collection_name=collection.name,
                        store_stamped_file=True,
                        idempotent=False,
                    )

                    self.assertEqual(
                        response.commitment_receipt.object_cid.lower(),
                        file_case.object_cid.lower(),
                    )
                    self.assertEqual(
                        response.commitment_receipt.set_cid.lower(),
                        collection.cid.lower(),
                    )
                    self.assertIsNotNone(response.file_object)

                    file_path = response.file_object.file_path
                    self._assert_file_object_path(file_path, collection.name)
                    self._assert_download_integrity(file_path, file_case)

    def test_upload_stamped_file_preserves_downloaded_file_bytes(self):
        """UC-B: upload_stamped_file stores text and binary files without byte drift."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            for file_case in self._file_cases("upload-stamped-file"):
                with self.subTest(format=file_case.label):
                    collection = self._create_collection(
                        f"vapi-upload-{file_case.label}"
                    )
                    source_path = self._write_temp_file(temp_dir, file_case)

                    stamp = self.client.create_stamp(
                        data_cid=file_case.object_cid,
                        collection_cid=collection.cid,
                        store_stamped_file=False,
                        idempotent=False,
                    )
                    self.assertEqual(
                        stamp.commitment_receipt.object_cid.lower(),
                        file_case.object_cid.lower(),
                    )
                    self.assertEqual(
                        stamp.commitment_receipt.set_cid.lower(),
                        collection.cid.lower(),
                    )
                    self._wait_for_indexed_stamp(file_case.object_cid, collection.cid)

                    upload = self.client.upload_stamped_file(
                        collection_name=collection.name,
                        file=source_path,
                    )

                    self.assertEqual(
                        upload.commitment_receipt.object_cid.lower(),
                        file_case.object_cid.lower(),
                    )
                    self.assertEqual(
                        upload.commitment_receipt.set_cid.lower(),
                        collection.cid.lower(),
                    )
                    self.assertIsNotNone(upload.file_object)

                    file_path = upload.file_object.file_path
                    self._assert_file_object_path(file_path, collection.name)
                    self._assert_download_integrity(file_path, file_case)


if __name__ == "__main__":
    unittest.main()
