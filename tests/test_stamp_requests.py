"""Regression tests for VDT-898 safe contention retries."""

import io
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from vbase_api.stamp_requests import _retry_delay, post_stamp_operation


def response(status, code=None, retry_after="3"):
    """Response."""
    result = Mock(status_code=status, headers={"Retry-After": retry_after})
    result.json.return_value = {"error_code": code}
    return result


class StampRequestTests(unittest.TestCase):
    """Test safe contention retries and request ownership."""

    def test_contention_replays_file_from_original_offset_and_enables_idempotency(self):
        """Test contention replays file from original offset and enables idempotency."""
        stream = io.BytesIO(b"prefix-payload")
        stream.seek(7)
        seen = []
        replies = iter([response(409, "stamp_in_progress"), response(201)])

        def send(*_args, **kwargs):
            """Send."""
            seen.append(
                (kwargs["files"]["file"][1].read(), kwargs["data"]["idempotent"])
            )
            return next(replies)

        session = Mock()
        session.post.side_effect = send
        with patch("vbase_api.stamp_requests.time.sleep") as sleep:
            result = post_stamp_operation(
                session,
                "https://example.test/api/v1/stamps",
                {"Authorization": "Bearer test-a"},
                data={"idempotent": "false"},
                files={"file": ("a.txt", stream)},
            )
        self.assertEqual(result.status_code, 201)
        self.assertEqual(seen, [(b"payload", "false"), (b"payload", "true")])
        sleep.assert_called_once_with(3)

    def test_noncontention_errors_are_not_retried(self):
        """Test noncontention errors are not retried."""
        for status, code in [
            (409, "stamp_reconciliation_required"),
            (409, None),
            (400, "stamp_in_progress"),
            (503, "stamp_in_progress"),
        ]:
            with self.subTest(status=status, code=code):
                session = Mock()
                session.post.return_value = response(status, code)
                with patch("vbase_api.stamp_requests.time.sleep") as sleep:
                    post_stamp_operation(
                        session,
                        "https://example.test/stamps",
                        {"Authorization": "Bearer test-a"},
                    )
                session.post.assert_called_once()
                sleep.assert_not_called()

    def test_exhaustion_is_bounded_without_sleep_after_final_attempt(self):
        """Test exhaustion is bounded without sleep after final attempt."""
        session = Mock()
        session.post.return_value = response(409, "stamp_in_progress")
        with patch("vbase_api.stamp_requests.time.sleep") as sleep:
            result = post_stamp_operation(
                session,
                "https://example.test/stamps",
                {"Authorization": "Bearer test-a"},
            )
        self.assertEqual(result.status_code, 409)
        self.assertEqual(session.post.call_count, 5)
        self.assertEqual(sleep.call_count, 4)

    def test_transport_failure_is_not_replayed(self):
        """Test transport failure is not replayed."""
        session = Mock()
        session.post.side_effect = TimeoutError("unknown outcome")
        with self.assertRaises(TimeoutError):
            post_stamp_operation(
                session,
                "https://example.test/stamps",
                {"Authorization": "Bearer test-a"},
            )
        session.post.assert_called_once()

    def test_same_credential_queue_is_shared_between_sessions(self):
        """Test same credential queue is shared between sessions."""
        entered = threading.Event()
        release = threading.Event()
        second_started = threading.Event()

        def first_send(*_args, **_kwargs):
            """First send."""
            entered.set()
            self.assertTrue(release.wait(3))
            return response(201)

        def second_send(*_args, **_kwargs):
            """Second send."""
            second_started.set()
            return response(201)

        first, second = Mock(), Mock()
        first.post.side_effect, second.post.side_effect = first_send, second_send
        with ThreadPoolExecutor(max_workers=3) as executor:
            one = executor.submit(
                post_stamp_operation,
                first,
                "https://example.test/stamps",
                {"Authorization": "Bearer test-a"},
            )
            self.assertTrue(entered.wait(3))
            two = executor.submit(
                post_stamp_operation,
                second,
                "https://example.test/collections",
                {"Authorization": "Bearer test-a"},
            )
            other = executor.submit(
                post_stamp_operation,
                second,
                "https://example.test/stamps",
                {"Authorization": "Bearer test-b"},
            )
            self.assertEqual(other.result(timeout=3).status_code, 201)
            second_started.clear()
            self.assertFalse(second_started.wait(0.05))
            release.set()
            one.result(timeout=3)
            two.result(timeout=3)
        self.assertTrue(second_started.is_set())

    def test_retry_after_fallback_and_http_date(self):
        """Test retry after fallback and http date."""
        self.assertEqual(_retry_delay("not a date"), 2)
        self.assertEqual(_retry_delay(""), 2)
        self.assertEqual(_retry_delay("0"), 0)
        self.assertEqual(_retry_delay("Wed, 21 Oct 2015 07:28:00 GMT"), 0)

    def test_nonseekable_upload_fails_without_resending(self):
        """Test nonseekable upload fails without resending."""

        class Stream:
            """Stream."""

            def read(self):
                """Read."""
                return b"payload"

        session = Mock()
        session.post.return_value = response(409, "stamp_in_progress")
        with self.assertRaisesRegex(ValueError, "non-seekable"):
            post_stamp_operation(
                session,
                "https://example.test/stamps",
                {"Authorization": "Bearer test-a"},
                files={"file": ("a.txt", Stream())},
            )
        session.post.assert_called_once()

    def test_malformed_error_body_is_not_retried(self):
        """Test malformed error body is not retried."""
        session = Mock()
        session.post.return_value = response(409)
        session.post.return_value.json.side_effect = ValueError("invalid json")
        post_stamp_operation(
            session, "https://example.test/stamps", {"Authorization": "Bearer test-a"}
        )
        session.post.assert_called_once()

    def test_list_multipart_entries_replay_original_bytes(self):
        """Multipart list forms preserve the same content after contention."""
        for outer_list in (False, True):
            with self.subTest(outer_list=outer_list):
                stream = io.BytesIO(b"prefix-payload")
                stream.seek(7)
                files = (
                    [("file", ["a.txt", stream])]
                    if outer_list
                    else {"file": ["a.txt", stream]}
                )
                payloads = []
                replies = iter([response(409, "stamp_in_progress"), response(201)])

                def send(*_args, **kwargs):
                    entry = (
                        kwargs["files"][0][1] if outer_list else kwargs["files"]["file"]
                    )
                    payloads.append(entry[1].read())
                    return next(replies)

                session = Mock()
                session.post.side_effect = send
                with patch("vbase_api.stamp_requests.time.sleep"):
                    post_stamp_operation(
                        session,
                        "https://example.test/stamps",
                        {"Authorization": "Bearer test-a"},
                        files=files,
                    )
                self.assertEqual(payloads, [b"payload", b"payload"])

    def test_asctime_retry_hint_uses_utc(self):
        """Obsolete HTTP-date syntax without a zone still denotes UTC."""
        with patch("vbase_api.stamp_requests.datetime") as clock:
            clock.now.return_value = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
            self.assertEqual(_retry_delay("Fri Nov  6 12:00:30 2026"), 30)

    def test_default_port_aliases_share_ownership(self):
        """Equivalent HTTP origins cannot bypass the credential queue."""
        for origin, alias in [
            ("https://example.test", "https://example.test:443"),
            ("http://example.test", "http://example.test:80"),
        ]:
            with self.subTest(origin=origin):
                entered, release, attempted, second_entered = (
                    threading.Event() for _ in range(4)
                )

                def first_send(*_args, **_kwargs):
                    entered.set()
                    if not release.wait(3):
                        raise TimeoutError("test barrier")
                    return response(201)

                first, second = Mock(), Mock()
                first.post.side_effect = first_send
                second.post.side_effect = lambda *_args, **_kwargs: (
                    second_entered.set(),
                    response(201),
                )[1]

                def second_request():
                    attempted.set()
                    return post_stamp_operation(
                        second,
                        alias + "/collections",
                        {"Authorization": "Bearer test-a"},
                    )

                with ThreadPoolExecutor(max_workers=2) as executor:
                    one = executor.submit(
                        post_stamp_operation,
                        first,
                        origin + "/stamps",
                        {"Authorization": "Bearer test-a"},
                    )
                    self.assertTrue(entered.wait(3))
                    two = executor.submit(second_request)
                    try:
                        self.assertTrue(attempted.wait(3))
                        self.assertFalse(second_entered.wait(0.05))
                    finally:
                        release.set()
                    one.result(timeout=3)
                    two.result(timeout=3)
