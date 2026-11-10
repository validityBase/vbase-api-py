# Verification response timezone compatibility

## Problem and scope

`VBaseAPIClient.verify_stamps()` fails with `KeyError: 'display_timezone'`
when the API returns its current verification response. This prevents the
environment runner from identifying files that have already been stamped.
The API returns `stamp_list` without a display timezone. The failure occurs
when a client parser indexes that removed response key.

## Required behavior

- Verification responses without `display_timezone` deserialize successfully;
  `VerificationResult.display_timezone` is `None`.
- Older responses retain their supplied timezone, including non-UTC values.
  Explicit JSON null remains `None`.
- Receipt fields, including timestamps, remain unchanged. An empty or omitted
  `stamp_list` still produces an empty list. Missing required receipt fields
  still raise `KeyError`.
- Retain the exported model, attribute, and dataclass constructor field order
  for compatibility. Do not invent a timezone or convert timestamps locally.
- Mark `VerificationResult.display_timezone` deprecated in the model and
  client documentation and changelog. Direct callers to the timezone
  information in each receipt's `timestamp`. Do not add runtime warnings.
- Account settings retains its existing contract. No dependency, version,
  release, deployment, or downstream repository changes are part of this fix.

## Implementation plan

1. Create `tests/test_verification_response.py` using `unittest` and
   `unittest.mock`. Exercise the public `verify_stamps` method with a mocked
   HTTP response, without API credentials or network calls. Cover missing,
   legacy, and null timezone values; full receipts; empty/omitted stamp lists;
   and missing required receipt fields. Assert the verification request keeps
   its CIDs, `filter_by_user=True`, URL, and timeout. Reproduce the failure
   before changing production code.
2. Modify `src/vbase_api/vbase_api_models.py`: change only
   `VerificationResult.display_timezone` to `Optional[str]`, describe its
   deprecation and `None` when absent, and use `data.get("display_timezone")`
   in its parser. Keep the constructor field order and stamp parser behavior.
3. Modify `src/vbase_api/vbase_api_client.py` to describe the optional legacy
   timezone and its deprecation in the `verify_stamps` return documentation.
   Modify `CHANGELOG.md` with Unreleased fix/deprecation entries and
   `CONTRIBUTING.md` to distinguish offline regression tests from
   credential-dependent live tests.
4. Run offline regression tests and repository-declared checks, preserving
   unrelated formatting. Record unavailable checks and existing failures.
   Obtain independent fresh-context EGM review of the plan and completed
   change before considering the implementation complete.
5. Modify `.github/workflows/python-compatibility.yml` to include
   `tests.test_verification_response` alongside `tests.test_api_client` in
   the existing offline client-test command, and keep
   `internal/specs/github-actions.md` aligned.

## Operational boundary

The fix takes effect in the environment runner after the updated client is
installed there. Preparing this patch does not update an installed production
package. Publishing and deployment require separate explicit approval.
