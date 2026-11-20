"""Client request/response contracts that run without live services."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

import vbase_api


class APIClientTests(unittest.TestCase):
    def setUp(self):
        self.client = vbase_api.VBaseAPIClient(
            api_key="test-only-key", base_url="https://example.invalid", timeout=7
        )
        self.addCleanup(self.client.close)
        self.receipt = {
            "transaction_hash": "0xtransaction",
            "user_address": "0xuser",
            "set_cid": "0xset",
            "object_cid": "0xobject",
            "timestamp": "2026-10-26T00:00:00Z",
            "chain_id": 1,
        }

    @staticmethod
    def response(status, payload, headers=None):
        response = requests.Response()
        response.status_code = status
        response._content = json.dumps(payload).encode("utf-8")
        response.headers.update(headers or {})
        return response

    def test_collection_request_and_response(self):
        payload = {
            "id": 1,
            "name": "Example",
            "cid": "0xset",
            "is_pinned": True,
            "is_public": False,
            "created_at": "2026-10-26T00:00:00Z",
            "description": "Example collection",
        }
        with patch.object(
            self.client.session, "post", return_value=self.response(201, payload)
        ) as post:
            collection = self.client.create_collection("Example", "Example collection")
        self.assertEqual(collection.cid, "0xset")
        self.assertEqual(collection.name, "Example")
        post.assert_called_once_with(
            "https://example.invalid/api/v1/collections",
            json={
                "name": "Example",
                "cid": None,
                "description": "Example collection",
                "is_pinned": True,
            },
            timeout=7,
        )

    def test_stamp_response_types(self):
        for status, expected in [
            (200, vbase_api.IdempotentStampResponse),
            (201, vbase_api.StampCreatedResponse),
        ]:
            with self.subTest(status=status):
                with patch.object(
                    self.client.session,
                    "post",
                    return_value=self.response(
                        status, {"commitment_receipt": self.receipt}
                    ),
                ):
                    stamp = self.client.create_stamp(data_cid="0xobject")
                    self.assertIsInstance(stamp, expected)
                    self.assertEqual(stamp.commitment_receipt.object_cid, "0xobject")

    def test_upload_closes_file_after_request(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.bin"
            path.write_bytes(b"example")
            with patch.object(
                self.client.session,
                "post",
                return_value=self.response(201, {"commitment_receipt": self.receipt}),
            ) as post:
                result = self.client.upload_stamped_file("Example", path)
            uploaded = post.call_args.kwargs["files"]["file"][1]
            self.assertTrue(uploaded.closed)
            self.assertEqual(result.commitment_receipt.object_cid, "0xobject")

    def test_api_error_preserves_status_and_message(self):
        with patch.object(
            self.client.session,
            "get",
            return_value=self.response(403, {"error": "Access denied"}),
        ):
            with self.assertRaises(vbase_api.VBaseAPIError) as raised:
                self.client.get_collections()
        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(str(raised.exception), "[403] Access denied")

    def test_api_error_rejects_non_object_json_without_leaking_attribute_error(self):
        with patch.object(
            self.client.session,
            "get",
            return_value=self.response(503, []),
        ):
            with self.assertRaises(vbase_api.VBaseAPIError) as raised:
                self.client.get_collections()

        self.assertEqual(raised.exception.status_code, 503)

    def test_api_error_two_argument_construction_remains_supported(self):
        error = vbase_api.VBaseAPIError("Access denied", 403)

        self.assertEqual(str(error), "[403] Access denied")
        self.assertIsNone(error.error_code)
        self.assertIsNone(error.retry_after)
        self.assertIsNone(error.commitment_receipt)

    def test_api_error_metadata_is_keyword_only(self):
        with self.assertRaises(TypeError):
            vbase_api.VBaseAPIError("Busy", 409, "stamp_in_progress")

    def test_retry_after_preserved_for_non_json_error_body(self):
        response = requests.Response()
        response.status_code = 503
        response._content = b"<html>Service Unavailable</html>"
        response.headers["Retry-After"] = "30"
        with patch.object(self.client.session, "get", return_value=response):
            with self.assertRaises(vbase_api.VBaseAPIError) as raised:
                self.client.get_collections()

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.retry_after, "30")
        self.assertIsNone(raised.exception.error_code)
        self.assertIsNone(raised.exception.commitment_receipt)

    def test_retry_after_preserved_for_non_object_json_error_body(self):
        with patch.object(
            self.client.session,
            "get",
            return_value=self.response(429, [], {"Retry-After": "2"}),
        ):
            with self.assertRaises(vbase_api.VBaseAPIError) as raised:
                self.client.get_collections()

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.retry_after, "2")

    def test_malformed_error_metadata_types_are_ignored(self):
        with patch.object(
            self.client.session,
            "get",
            return_value=self.response(
                500, {"error": "Boom", "error_code": 5, "commitment_receipt": [1]}
            ),
        ):
            with self.assertRaises(vbase_api.VBaseAPIError) as raised:
                self.client.get_collections()

        self.assertEqual(str(raised.exception), "[500] Boom")
        self.assertIsNone(raised.exception.error_code)
        self.assertIsNone(raised.exception.commitment_receipt)

    def test_stamp_in_progress_error_contract(self):
        with patch.object(
            self.client.session,
            "post",
            return_value=self.response(
                409,
                {
                    "error": "Stamp is already in progress",
                    "error_code": "stamp_in_progress",
                },
                {"Retry-After": "5"},
            ),
        ):
            with self.assertRaises(vbase_api.VBaseAPIError) as raised:
                self.client.create_stamp(data_cid="0xobject")
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.error_code, "stamp_in_progress")
        self.assertEqual(raised.exception.retry_after, "5")
        self.assertIsNone(raised.exception.commitment_receipt)

    def test_operation_guard_unavailable_error_contract_with_receipt(self):
        with patch.object(
            self.client.session,
            "post",
            return_value=self.response(
                503,
                {
                    "error": "Operation guard is unavailable",
                    "error_code": "operation_guard_unavailable",
                    "commitment_receipt": self.receipt,
                },
                {"Retry-After": "10"},
            ),
        ):
            with self.assertRaises(vbase_api.VBaseAPIError) as raised:
                self.client.create_stamp(data_cid="0xobject")
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.error_code, "operation_guard_unavailable")
        self.assertEqual(raised.exception.retry_after, "10")
        self.assertEqual(raised.exception.commitment_receipt, self.receipt)


if __name__ == "__main__":
    unittest.main()
