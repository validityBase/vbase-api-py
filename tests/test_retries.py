"""Unit tests for vBase API retry behavior."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import requests

from vbase_api import RetryConfig, VBaseAPIClient, VBaseAPIError


def make_response(status_code, payload, reason=None):
    """Build a requests response suitable for client unit tests."""
    response = requests.Response()
    response.status_code = status_code
    response.reason = reason or ("OK" if status_code < 400 else "Error")
    response.url = "https://example.test/api/v1/test"
    response.headers["Content-Type"] = "application/json"
    response._content = json.dumps(payload).encode("utf-8")
    request = requests.Request("GET", response.url)
    response.request = request.prepare()
    return response


def collection_payload(name="Reports"):
    return {
        "id": 1,
        "name": name,
        "cid": "0xcollection",
        "is_pinned": True,
        "is_public": False,
        "created_at": "2026-08-10T12:00:00Z",
        "description": "Test collection",
    }


def receipt_payload():
    return {
        "transaction_hash": "0xtx",
        "user_address": "0xuser",
        "set_cid": "0xcollection",
        "object_cid": "0xobject",
        "timestamp": "2026-08-10T12:00:00Z",
        "chain_id": 137,
    }


class RetryConfigTests(unittest.TestCase):
    def test_rejects_invalid_attempt_count(self):
        with self.assertRaisesRegex(ValueError, "max_attempts"):
            RetryConfig(max_attempts=0)


class VBaseAPIClientRetryTests(unittest.TestCase):
    def setUp(self):
        self.client = VBaseAPIClient(
            api_key="test-token",
            base_url="https://example.test",
            retry_config=RetryConfig(
                max_attempts=3,
                initial_delay=0,
                delay_increment=0,
                max_delay=0,
            ),
        )
        self.client.session.request = Mock()

    def tearDown(self):
        self.client.close()

    def test_get_retries_transient_http_response(self):
        self.client.session.request.side_effect = [
            make_response(503, {"error": "temporarily unavailable"}),
            make_response(200, [collection_payload()]),
        ]

        collections = self.client.get_collections()

        self.assertEqual([collection.name for collection in collections], ["Reports"])
        self.assertEqual(self.client.session.request.call_count, 2)

    def test_get_does_not_retry_client_error(self):
        self.client.session.request.side_effect = [
            make_response(400, {"error": "invalid filter"}),
            make_response(200, []),
        ]

        with self.assertRaises(VBaseAPIError) as context:
            self.client.get_collections()

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(self.client.session.request.call_count, 1)

    def test_verify_retries_transport_failure_even_though_it_uses_post(self):
        self.client.session.request.side_effect = [
            requests.exceptions.ConnectionError("connection reset"),
            make_response(
                200,
                {"display_timezone": "UTC", "stamp_list": []},
            ),
        ]

        result = self.client.verify_stamps(["0xobject"])

        self.assertEqual(result.stamp_list, [])
        self.assertEqual(self.client.session.request.call_count, 2)
        self.assertEqual(self.client.session.request.call_args.args[0], "POST")

    def test_unlimited_window_idempotent_stamp_retries_transient_failure(self):
        self.client.session.request.side_effect = [
            make_response(503, {"error": "temporarily unavailable"}),
            make_response(200, {"commitment_receipt": receipt_payload()}),
        ]

        result = self.client.create_stamp(
            data="payload", idempotent=True, idempotency_window=0
        )

        self.assertEqual(result.commitment_receipt.object_cid, "0xobject")
        self.assertEqual(self.client.session.request.call_count, 2)

    def test_non_idempotent_stamp_is_not_retried(self):
        self.client.session.request.side_effect = [
            requests.exceptions.ConnectionError("connection reset"),
            make_response(201, {"commitment_receipt": receipt_payload()}),
        ]

        with self.assertRaises(VBaseAPIError):
            self.client.create_stamp(data="payload", idempotent=False)

        self.assertEqual(self.client.session.request.call_count, 1)

    def test_default_finite_window_stamp_is_not_retried(self):
        self.client.session.request.side_effect = [
            requests.exceptions.ConnectionError("connection reset"),
            make_response(200, {"commitment_receipt": receipt_payload()}),
        ]

        with self.assertRaises(VBaseAPIError):
            self.client.create_stamp(data="payload", idempotent=True)

        self.assertEqual(self.client.session.request.call_count, 1)

    def test_collection_is_read_before_repeating_create(self):
        self.client.session.request.side_effect = [
            make_response(503, {"error": "temporarily unavailable"}),
            make_response(200, [collection_payload()]),
        ]

        collection = self.client.create_collection(
            name="Reports",
            description="Test collection",
        )

        self.assertEqual(collection.cid, "0xcollection")
        self.assertEqual(self.client.session.request.call_count, 2)
        methods = [call.args[0] for call in self.client.session.request.call_args_list]
        self.assertEqual(methods, ["POST", "GET"])

    def test_collection_retries_create_when_read_finds_no_match(self):
        self.client.session.request.side_effect = [
            make_response(503, {"error": "temporarily unavailable"}),
            make_response(200, []),
            make_response(201, collection_payload()),
        ]

        collection = self.client.create_collection(
            name="Reports",
            description="Test collection",
        )

        self.assertEqual(collection.cid, "0xcollection")
        methods = [call.args[0] for call in self.client.session.request.call_args_list]
        self.assertEqual(methods, ["POST", "GET", "POST"])

    def test_collection_recovers_from_conflict_after_uncertain_create(self):
        self.client.session.request.side_effect = [
            make_response(503, {"error": "temporarily unavailable"}),
            make_response(200, []),
            make_response(409, {"error": "Collection already exists"}),
            make_response(200, [collection_payload()]),
        ]

        collection = self.client.create_collection(
            name="Reports",
            description="Test collection",
        )

        self.assertEqual(collection.cid, "0xcollection")
        methods = [call.args[0] for call in self.client.session.request.call_args_list]
        self.assertEqual(methods, ["POST", "GET", "POST", "GET"])

    def test_file_upload_reopens_path_for_retry(self):
        uploaded_bodies = []

        def send_request(method, url, **kwargs):
            del method, url
            upload = kwargs["files"]["file"]
            uploaded_bodies.append(upload[1].read())
            if len(uploaded_bodies) == 1:
                raise requests.exceptions.ConnectionError("connection reset")
            return make_response(
                201,
                {
                    "commitment_receipt": receipt_payload(),
                    "file_object": {
                        "file_name": "payload.bin",
                        "file_path": "stamped/payload.bin",
                    },
                },
            )

        self.client.session.request.side_effect = send_request

        with tempfile.TemporaryDirectory() as temp_directory:
            file_path = Path(temp_directory) / "payload.bin"
            file_path.write_bytes(b"same bytes on every attempt")
            result = self.client.upload_stamped_file("Reports", file_path)

        self.assertEqual(result.file_object.file_name, "payload.bin")
        self.assertEqual(
            uploaded_bodies,
            [b"same bytes on every attempt", b"same bytes on every attempt"],
        )

    def test_retry_can_be_disabled(self):
        client = VBaseAPIClient(
            api_key="test-token",
            base_url="https://example.test",
            retry_config=RetryConfig(enabled=False),
        )
        client.session.request = Mock(
            side_effect=[
                make_response(503, {"error": "temporarily unavailable"}),
                make_response(200, []),
            ]
        )
        self.addCleanup(client.close)

        with self.assertRaises(VBaseAPIError) as context:
            client.get_collections()

        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(client.session.request.call_count, 1)

    def test_retry_attempt_limit_is_respected(self):
        self.client.session.request.return_value = make_response(
            503, {"error": "temporarily unavailable"}
        )

        with self.assertRaises(VBaseAPIError) as context:
            self.client.get_collections()

        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(self.client.session.request.call_count, 3)


if __name__ == "__main__":
    unittest.main()
