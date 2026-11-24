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

    @staticmethod
    def collection_payload(index):
        return {
            "id": index,
            "name": f"Collection {index}",
            "cid": f"0x{index:064x}",
            "is_pinned": False,
            "is_public": False,
            "created_at": "2026-10-26T00:00:00Z",
            "description": "",
        }

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

    def test_get_collections_follows_relative_next_links_with_filters(self):
        first_page = [self.collection_payload(index) for index in range(10000)]
        second_page = [self.collection_payload(10000)]
        with patch.object(
            self.client.session,
            "get",
            side_effect=[
                self.response(
                    200,
                    first_page,
                    {
                        "X-Total-Count": "10001",
                        "Link": (
                            "</api/v1/collections?limit=10000&offset=10000"
                            '&user_address=0xabc&is_pinned=false>; rel="next"'
                        ),
                    },
                ),
                self.response(200, second_page, {"X-Total-Count": "10001"}),
            ],
        ) as get:
            collections = self.client.get_collections(
                user_address="0xabc", is_pinned=False
            )

        self.assertEqual(len(collections), 10001)
        self.assertEqual(collections[-1].cid, second_page[0]["cid"])
        self.assertEqual(
            get.call_args_list[0].kwargs,
            {
                "params": {"user_address": "0xabc", "is_pinned": False},
                "timeout": 7,
            },
        )
        self.assertEqual(
            get.call_args_list[1].args[0],
            (
                "https://example.invalid/api/v1/collections?limit=10000"
                "&offset=10000&user_address=0xabc&is_pinned=false"
            ),
        )
        self.assertEqual(get.call_args_list[1].kwargs, {"params": None, "timeout": 7})

    def test_get_collections_propagates_later_page_error(self):
        with patch.object(
            self.client.session,
            "get",
            side_effect=[
                self.response(
                    200,
                    [self.collection_payload(1)],
                    {"Link": '</api/v1/collections?offset=1>; rel="next"'},
                ),
                self.response(503, {"error": "Indexer unavailable"}),
            ],
        ) as get:
            with self.assertRaises(vbase_api.VBaseAPIError) as raised:
                self.client.get_collections()

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(len(get.call_args_list), 2)

    def test_get_collections_rejects_cross_origin_next_link(self):
        with patch.object(
            self.client.session,
            "get",
            return_value=self.response(
                200,
                [self.collection_payload(1)],
                {"Link": '<https://example.com/collections?page=2>; rel="next"'},
            ),
        ) as get:
            with self.assertRaises(vbase_api.VBaseAPIError) as raised:
                self.client.get_collections()

        self.assertIn("different origin", str(raised.exception))
        get.assert_called_once()

    def test_get_collections_rejects_pagination_link_cycle(self):
        first_url = "https://example.invalid/api/v1/collections"
        with patch.object(
            self.client.session,
            "get",
            return_value=self.response(
                200,
                [self.collection_payload(1)],
                {"Link": f'<{first_url}>; rel="next"'},
            ),
        ) as get:
            with self.assertRaises(vbase_api.VBaseAPIError) as raised:
                self.client.get_collections()

        self.assertIn("cycle", str(raised.exception))
        get.assert_called_once()

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

    def test_stamp_problem_details_preserves_public_error_fields(self):
        response = self.response(
            429,
            {
                "type": "https://example.test/problems/rate-limit-exceeded",
                "title": "Rate Limit Exceeded",
                "status": 429,
                "detail": "Request rate limit exceeded.",
                "code": "RATE_LIMIT_EXCEEDED",
            },
            {
                "Content-Type": "application/problem+json; charset=utf-8",
                "Retry-After": "8",
            },
        )
        with patch.object(self.client.session, "post", return_value=response):
            with self.assertRaises(vbase_api.VBaseAPIError) as raised:
                self.client.create_stamp(data_cid="0xobject")

        error = raised.exception
        self.assertEqual(error.status_code, 429)
        self.assertEqual(error.error_code, "RATE_LIMIT_EXCEEDED")
        self.assertEqual(error.message, "Request rate limit exceeded.")
        self.assertEqual(error.retry_after, "8")

    def test_problem_details_ignores_invalid_field_types_and_uses_http_status(self):
        response = self.response(
            503,
            {"status": 429, "code": 42, "detail": {"unexpected": "object"}},
            {"Content-Type": "application/problem+json", "Retry-After": "10"},
        )
        with patch.object(self.client.session, "get", return_value=response):
            with self.assertRaises(vbase_api.VBaseAPIError) as raised:
                self.client.get_collections()

        error = raised.exception
        self.assertEqual(error.status_code, 503)
        self.assertIsNone(error.error_code)
        self.assertEqual(error.retry_after, "10")
        self.assertIn("503 Server Error", error.message)

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
