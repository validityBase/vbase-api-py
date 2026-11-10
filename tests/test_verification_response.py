"""Offline regression coverage for verification response compatibility."""

import unittest
from dataclasses import asdict
from unittest.mock import Mock, patch

from vbase_api import VBaseAPIClient, VerificationResult


class VerificationResponseTests(unittest.TestCase):
    def setUp(self):
        self.client = VBaseAPIClient(
            api_key="test-key", base_url="https://api.example.test", timeout=17
        )
        self.addCleanup(self.client.close)
        self.receipt = {
            "transaction_hash": "0xtransaction",
            "user_address": "0xuser",
            "set_cid": "0xcollection",
            "object_cid": "0xobject",
            "timestamp": "2026-11-10T18:31:54+00:00",
            "chain_id": 137,
        }

    def test_verify_stamps_accepts_current_and_legacy_timezone_responses(self):
        for timezone_fields in (
            {},
            {"display_timezone": "UTC"},
            {"display_timezone": "Europe/Vienna"},
            {"display_timezone": None},
        ):
            with self.subTest(timezone_fields=timezone_fields):
                response = Mock()
                response.json.return_value = {
                    "stamp_list": [self.receipt],
                    **timezone_fields,
                }
                with patch.object(
                    self.client.session, "post", return_value=response
                ) as post:
                    result = self.client.verify_stamps(
                        [self.receipt["object_cid"]], filter_by_user=True
                    )

                post.assert_called_once_with(
                    "https://api.example.test/api/v1/stamps/verify",
                    json={"cids": [self.receipt["object_cid"]], "filter_by_user": True},
                    timeout=17,
                )
                response.raise_for_status.assert_called_once_with()
                self.assertIsInstance(result, VerificationResult)
                self.assertEqual(
                    result.display_timezone, timezone_fields.get("display_timezone")
                )
                self.assertEqual(
                    [asdict(stamp) for stamp in result.stamp_list], [self.receipt]
                )

    def test_verify_stamps_accepts_empty_or_omitted_stamp_list_without_timezone(self):
        for payload in ({"stamp_list": []}, {}):
            with self.subTest(payload=payload):
                response = Mock()
                response.json.return_value = payload
                with patch.object(self.client.session, "post", return_value=response):
                    result = self.client.verify_stamps(
                        ["0xobject"], filter_by_user=True
                    )

                self.assertIsNone(result.display_timezone)
                self.assertEqual(result.stamp_list, [])

    def test_missing_required_receipt_field_still_raises(self):
        receipt = dict(self.receipt)
        del receipt["timestamp"]
        response = Mock()
        response.json.return_value = {"stamp_list": [receipt]}
        with patch.object(self.client.session, "post", return_value=response):
            with self.assertRaisesRegex(KeyError, "timestamp"):
                self.client.verify_stamps([receipt["object_cid"]], filter_by_user=True)


if __name__ == "__main__":
    unittest.main()
