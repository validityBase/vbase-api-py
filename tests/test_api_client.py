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
    def response(status, payload):
        response = requests.Response()
        response.status_code = status
        response._content = json.dumps(payload).encode("utf-8")
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


if __name__ == "__main__":
    unittest.main()
