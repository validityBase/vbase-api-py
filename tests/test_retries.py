"""Unit tests for vBase API retry behavior."""

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, call

import requests
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
    wait_none,
)

from vbase_api import VBaseAPIClient, VBaseAPIError, default_retrying


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


def immediate_retrying(max_attempts=3):
    """Return the default retry controller without test delays."""
    return default_retrying().copy(
        stop=stop_after_attempt(max_attempts),
        wait=wait_none(),
    )


class NonSeekableStream(BytesIO):
    """Simulate an upload stream that cannot be rewound."""

    def seekable(self):
        return False

    def seek(self, *_args):
        raise OSError("stream is not seekable")


class DefaultRetryingTests(unittest.TestCase):
    def test_uses_two_second_linear_backoff_defaults(self):
        sleep = Mock()
        operation = Mock(
            side_effect=[
                requests.exceptions.ConnectionError("connection reset"),
                requests.exceptions.Timeout("request timed out"),
                "success",
            ]
        )
        retrying = default_retrying().copy(sleep=sleep)

        self.assertEqual(retrying(operation), "success")
        self.assertEqual(operation.call_count, 3)
        sleep.assert_has_calls([call(2.0), call(4.0)])

    def test_returns_independent_retry_controllers(self):
        self.assertIsNot(default_retrying(), default_retrying())


class VBaseAPIClientRetryTests(unittest.TestCase):
    def setUp(self):
        self.client = VBaseAPIClient(
            api_key="test-token",
            base_url="https://example.test",
            retrying=immediate_retrying(),
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

    def test_malformed_success_json_raises_public_error_without_retry(self):
        operations = (
            ("get_collections", lambda: self.client.get_collections()),
            ("verify_stamps", lambda: self.client.verify_stamps(["0xobject"])),
            ("get_current_user", lambda: self.client.get_current_user()),
            ("get_user", lambda: self.client.get_user("0xuser")),
            ("create_stamp", lambda: self.client.create_stamp(data_cid="0xobject")),
        )
        for name, operation in operations:
            with self.subTest(operation=name):
                response = make_response(200, {})
                response._content = b"not-json"
                self.client.session.request.reset_mock(return_value=True)
                self.client.session.request.return_value = response

                with self.assertRaises(VBaseAPIError) as context:
                    operation()

                self.assertIsInstance(
                    context.exception.__cause__, requests.exceptions.JSONDecodeError
                )
                self.assertEqual(self.client.session.request.call_count, 1)

    def test_standard_retrying_object_controls_attempts(self):
        retrying = Retrying(
            stop=stop_after_attempt(2),
            wait=wait_none(),
            retry=lambda retry_state: False,
            retry_error_callback=lambda retry_state: "fallback",
        )
        client = VBaseAPIClient(
            api_key="test-token",
            base_url="https://example.test",
            retrying=retrying,
        )
        client.session.request = Mock(
            side_effect=[
                make_response(503, {"error": "temporarily unavailable"}),
                make_response(503, {"error": "still unavailable"}),
            ]
        )
        self.addCleanup(client.close)

        with self.assertRaises(VBaseAPIError) as context:
            client.get_collections()

        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(client.session.request.call_count, 2)
        self.assertFalse(retrying.reraise)
        self.assertIsNotNone(retrying.retry_error_callback)

    def test_retryable_http_statuses_can_be_overridden(self):
        client = VBaseAPIClient(
            api_key="test-token",
            base_url="https://example.test",
            retrying=immediate_retrying(),
            retry_status_codes=(500,),
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

    def test_retryable_http_statuses_must_be_errors(self):
        with self.assertRaisesRegex(ValueError, "HTTP error status codes"):
            VBaseAPIClient(
                api_key="test-token",
                retry_status_codes=(200,),
            )

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

    def test_default_finite_window_stamp_retries_transient_failure(self):
        self.client.session.request.side_effect = [
            requests.exceptions.ConnectionError("connection reset"),
            make_response(200, {"commitment_receipt": receipt_payload()}),
        ]

        result = self.client.create_stamp(data="payload", idempotent=True)

        self.assertEqual(result.commitment_receipt.object_cid, "0xobject")
        self.assertEqual(self.client.session.request.call_count, 2)

    def test_small_finite_window_stamp_is_not_retried(self):
        self.client.session.request.side_effect = [
            requests.exceptions.ConnectionError("connection reset"),
            make_response(200, {"commitment_receipt": receipt_payload()}),
        ]

        with self.assertRaises(VBaseAPIError):
            self.client.create_stamp(
                data="payload", idempotent=True, idempotency_window=10
            )

        self.assertEqual(self.client.session.request.call_count, 1)

    def test_finite_window_stops_before_delay_would_exceed_window(self):
        client = VBaseAPIClient(
            api_key="test-token",
            base_url="https://example.test",
            retrying=Retrying(
                stop=lambda retry_state: retry_state.attempt_number >= 3,
                wait=wait_fixed(12),
                retry=retry_if_exception_type(requests.exceptions.ConnectionError),
                reraise=True,
            ),
        )
        client.session.request = Mock(
            side_effect=[
                requests.exceptions.ConnectionError("connection reset"),
                make_response(200, {"commitment_receipt": receipt_payload()}),
            ]
        )
        self.addCleanup(client.close)

        with self.assertRaises(VBaseAPIError):
            client.create_stamp(data="payload", idempotent=True, idempotency_window=11)

        self.assertEqual(client.session.request.call_count, 1)

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

    def test_collection_on_second_page_prevents_repeating_create(self):
        first_page = make_response(200, [collection_payload(name="Other")])
        first_page.headers["Link"] = '</api/v1/collections?offset=10000>; rel="next"'
        self.client.session.request.side_effect = [
            make_response(503, {"error": "temporarily unavailable"}),
            first_page,
            make_response(200, [collection_payload()]),
        ]

        collection = self.client.create_collection("Reports", "Test collection")

        self.assertEqual(collection.name, "Reports")
        requests_sent = self.client.session.request.call_args_list
        self.assertEqual(
            [request.args[0] for request in requests_sent], ["POST", "GET", "GET"]
        )
        self.assertEqual(
            requests_sent[2].args[1], "https://example.test/api/v1/collections"
        )
        self.assertEqual(requests_sent[2].kwargs["params"], {"offset": 10000})

    def test_collection_page_failure_prevents_repeating_create(self):
        first_page = make_response(200, [])
        first_page.headers["Link"] = '</api/v1/collections?offset=10000>; rel="next"'
        self.client.session.request.side_effect = [
            make_response(503, {"error": "temporarily unavailable"}),
            first_page,
            make_response(403, {"error": "access denied"}),
        ]

        with self.assertRaises(VBaseAPIError) as context:
            self.client.create_collection("Reports", "Test collection")

        self.assertEqual(context.exception.status_code, 403)
        methods = [call.args[0] for call in self.client.session.request.call_args_list]
        self.assertEqual(methods, ["POST", "GET", "GET"])

    def test_collection_pagination_must_advance(self):
        first_page = make_response(200, [])
        first_page.headers["Link"] = '</api/v1/collections?offset=0>; rel="next"'
        self.client.session.request.side_effect = [
            make_response(503, {"error": "temporarily unavailable"}),
            first_page,
        ]

        with self.assertRaisesRegex(VBaseAPIError, "pagination offset did not advance"):
            self.client.create_collection("Reports", "Test collection")

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

    def test_seekable_stream_replays_from_initial_offset_and_stays_open(self):
        for method in ("create_stamp", "upload_stamped_file"):
            with self.subTest(method=method), BytesIO(b"prefix:payload") as stream:
                stream.seek(len(b"prefix:"))
                uploaded_bodies = []

                def send_request(_method, _url, **kwargs):
                    uploaded_bodies.append(kwargs["files"]["file"].read())
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
                getattr(self.client, method)(collection_name="Reports", file=stream)

                self.assertEqual(uploaded_bodies, [b"payload", b"payload"])
                self.assertFalse(stream.closed)

    def test_non_seekable_stream_is_sent_once_and_stays_open(self):
        for method in ("create_stamp", "upload_stamped_file"):
            with self.subTest(method=method), NonSeekableStream(b"payload") as stream:
                self.client.session.request.reset_mock()

                def send_request(_method, _url, **kwargs):
                    self.assertEqual(kwargs["files"]["file"].read(), b"payload")
                    raise requests.exceptions.ConnectionError("connection reset")

                self.client.session.request.side_effect = send_request
                with self.assertRaises(VBaseAPIError):
                    getattr(self.client, method)(collection_name="Reports", file=stream)

                self.client.session.request.assert_called_once()
                self.assertFalse(stream.closed)

    def test_retry_can_be_disabled(self):
        client = VBaseAPIClient(
            api_key="test-token",
            base_url="https://example.test",
            retrying=immediate_retrying(max_attempts=1),
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
        receipt = receipt_payload()
        response = make_response(
            503,
            {
                "error": "temporarily unavailable",
                "error_code": "operation_guard_unavailable",
                "commitment_receipt": receipt,
            },
        )
        response.headers["Retry-After"] = "5"
        self.client.session.request.return_value = response

        with self.assertRaises(VBaseAPIError) as context:
            self.client.get_collections()

        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(context.exception.error_code, "operation_guard_unavailable")
        self.assertEqual(context.exception.retry_after, "5")
        self.assertEqual(context.exception.commitment_receipt, receipt)
        self.assertEqual(self.client.session.request.call_count, 3)


if __name__ == "__main__":
    unittest.main()
