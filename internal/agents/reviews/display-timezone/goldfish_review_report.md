# Display timezone compatibility review

Status: resolved; no open findings.

Target: [compatibility specification and implementation plan](../../../specs/display-timezone-compatibility.md).

## Review scope

This was a scoped EGM Goldfish review of an urgent client compatibility fix.
The full five-stage design-document workflow and iterative convergence loop
were not run. Each reviewer used a fresh conversation context
(`fork_turns: "none"`), read the EGM Codex integration, its persona and the
implementation-readiness standard, and performed a read-only review. Host
instruction-file exclusion was not independently verified. No reviewer was
given parent conversation history or persistent agent memory.

| Reviewer | Target | Status | Findings |
| --- | --- | --- | --- |
| `timezone_plan_review` / implementation readiness | Original full plan, source, offline regression tests, contributor guide | Completed | None |
| `timezone_codebase_review` / codebase details | Original full plan, client/models/exports, CI workflows, local app verification view and response models | Completed | None |
| `timezone_final_review` / codebase details | Final full plan, final source, regression tests, changelog, contributor guide and Git diff | Completed | None |
| `timezone_pr_review` / codebase details | Rebased PR diff, full updated plan, source, tests, CI command, Actions spec and changelog | Completed | None |

All reviewers explicitly confirmed reading their required persona, standard,
target, and supplied context files. The final reviewer reread the changed
documentation after the user requested deprecation and confirmed that it
matches the implemented behavior. Tests were run by the primary agent;
reviewers did not run tests or edit files.

## Verified behavior

- `VerificationResult.from_dict` uses `data.get("display_timezone")`.
- The deprecated attribute is `Optional[str]`; absent/null values become
  `None`, and supplied legacy values remain intact.
- Constructor field order, public exports, receipt values, timestamps, and
  account settings are preserved.
- Documentation directs callers to timezone information in receipt timestamps.
- No package version, dependency, release, or deployment changes were made.

## Validation evidence

Commands were run from the repository root through `rtk`.

Before the production fix:

```bash
PYTHONPATH=src /Users/roman/.pyenv/versions/3.11.10/bin/python -m unittest tests.test_verification_response -v
```

Exit 1: missing-timezone cases reproduced `KeyError: 'display_timezone'`
at the reported parser lookup. Legacy/null timezone cases and required-receipt
validation already passed.

After the fix and deprecation documentation:

```bash
PYTHONPATH=src /Users/roman/.pyenv/versions/3.11.10/bin/python -m unittest discover -s tests -v
PYTHONPATH=src /Users/roman/.pyenv/versions/3.12.2/bin/python -m unittest discover -s tests -v
```

Both exited 0; all three offline tests passed. Python 3.11 skipped the live
E2E module because its dependencies were unavailable. Python 3.12 skipped the
live E2E class because `VBASE_API_KEY` was absent. No live API/storage writes
were performed.

```bash
/Users/roman/.cache/pre-commit/repotbgfix4g/py_env-python3.11/bin/black --check --target-version py311 tests/test_verification_response.py
/Users/roman/.cache/pre-commit/reposhme46ik/py_env-python3.11/bin/isort --check-only tests/test_verification_response.py
PYTHONPATH=src /Users/roman/.pyenv/versions/3.12.2/bin/python -c 'import vbase_api; print(vbase_api.__file__)'
git -c core.whitespace=cr-at-eol diff --check
```

All exited 0. The import resolved to this checkout's source. Formatter tools
came from the exact cached revisions declared in `.pre-commit-config.yaml`.
The whitespace check accounts for existing CRLF source line endings.

## PR preparation validation

The fix branch was rebased onto `origin/main` at
`5792c6d7b057b296b3258f442e8657a01ced69db`. The changelog conflict was resolved
by keeping the existing release history below the new Unreleased entries.
The production-source patch is unchanged by the rebase.

Current main includes offline client tests. The existing compatibility job
now also runs the new verification regression module. Its exact command was
run with both local Python interpreters:

```bash
PYTHONPATH=src /Users/roman/.pyenv/versions/3.11.10/bin/python -m unittest tests.test_api_client tests.test_verification_response -v
PYTHONPATH=src /Users/roman/.pyenv/versions/3.12.2/bin/python -m unittest tests.test_api_client tests.test_verification_response -v
```

Both exited 0: seven offline tests passed, with no skips. Full discovery also
passed on both interpreters, with the same live E2E skips described above.
Workflow YAML parsing, the expected offline test command, and the diff
whitespace check (accounting for CRLF) passed. Python 3.8 is covered by the
existing CI matrix; it was not available for local validation.

## Existing check failures and limits

- Black and isort checks on the two modified production files exited 1. The
  same checks against temporary copies of both files from `HEAD` also exited
  1, confirming existing formatting drift. Their whole-file changes were not
  applied. The complete mutating pre-commit suite was not run.
- `python -m pip check` exited 1 in both existing interpreters. Python 3.11
  reported unrelated web3/protobuf, TensorFlow/numpy/tensorboard, vbase and
  pandas-ta-classic dependency conflicts. Python 3.12 reported unrelated
  polygon-api-client/certifi and ccxt/coincurve conflicts. These existing
  interpreter environments and package dependencies were not changed.
- Production remains affected until a fixed client package is installed in
  the environment runner. Publishing and deployment need explicit approval.
