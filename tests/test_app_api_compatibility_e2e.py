"""Live app verification contract through the installed Python API client."""

from __future__ import annotations

import hashlib
import os
import time
import unittest
import uuid

from vbase_api import VBaseAPIClient
from vbase_api.vbase_api_models import VerificationResult


class AppAPICompatibilityE2ETests(unittest.TestCase):
    """Catch app response changes that the published client cannot parse."""

    @classmethod
    def setUpClass(cls) -> None:
        api_key = os.environ.get("VBASE_API_KEY") or os.environ.get(
            "VBASE_API_KEY_CYPRESS"
        )
        if not api_key:
            if os.environ.get("GITHUB_ACTIONS") == "true":
                raise RuntimeError("Set VBASE_API_KEY for live compatibility tests.")
            raise unittest.SkipTest("Set VBASE_API_KEY for live compatibility tests.")
        base_url = (
            os.environ.get("BASE_URL")
            or os.environ.get("VBASE_APP_BASE_URL")
            or "https://staging.app.vbase.com"
        )
        cls.client = VBaseAPIClient(api_key=api_key, base_url=base_url.rstrip("/"))

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "client"):
            cls.client.close()

    def test_unstamped_cid_response(self) -> None:
        cid = "0x" + hashlib.sha3_256(uuid.uuid4().bytes).hexdigest()
        result = self.client.verify_stamps([cid], filter_by_user=True)
        self.assertIsInstance(result, VerificationResult)
        self.assertEqual(result.stamp_list, [])

    def test_stamp_then_verify(self) -> None:
        if os.environ.get("VBASE_COMPAT_STAMP_TEST") == "0":
            self.skipTest("Stamp creation disabled for this environment")

        cid = "0x" + hashlib.sha3_256(uuid.uuid4().bytes).hexdigest()
        created = self.client.create_stamp(
            data_cid=cid, store_stamped_file=False, idempotent=False
        )
        self.assertEqual(created.commitment_receipt.object_cid, cid)

        deadline = time.monotonic() + 120
        while True:
            result = self.client.verify_stamps([cid], filter_by_user=True)
            self.assertIsInstance(result, VerificationResult)
            matching = [stamp for stamp in result.stamp_list if stamp.object_cid == cid]
            if matching:
                self.assertEqual(matching[0].object_cid, cid)
                return
            if time.monotonic() >= deadline:
                self.fail(
                    f"Stamp {cid} did not appear in verification within 120 seconds"
                )
            time.sleep(3)


if __name__ == "__main__":
    unittest.main()
