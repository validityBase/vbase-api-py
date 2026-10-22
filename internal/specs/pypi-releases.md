# PyPI release process pilot (VPY-32)

## Scope and decisions

- Implement in `vbase-api-py` first; `vbase-py` rollout follows pilot validation.
- Continue from the version in `src/vbase_api/_version.py`.
- A reviewed Release PR increments the version and finalizes the changelog
  before merge to `main`. A matching tag is pushed after merge.
- Support stable `vX.Y.Z` tags only, without leading zeroes in version components.
- Manual publication requires an existing tag and the same validation.
- Automatically create a GitHub Release after successful PyPI publication.
- Preserve the existing OIDC trusted publisher and `pypi` environment.

Contributor guidance is in [CONTRIBUTING.md](../../CONTRIBUTING.md). The detailed
maintainer runbook is [RELEASE_MANAGMENT.md](../../RELEASE_MANAGMENT.md).

## Acceptance criteria and evidence

| Criterion | Validation |
| --- | --- |
| User-facing PRs add an Unreleased entry; ordinary PRs do not bump versions | PR template and contributor instructions; reviewer checks |
| Release PR updates the version and dated release notes while retaining Unreleased | Validator unit tests and Release PR review |
| Automatic publishing starts on a tag push; branch pushes and GitHub Releases do not trigger it | Workflow trigger review |
| Manual dispatch requires a tag, and tagged commit belongs to main | Shared build job ref/ancestry guards; pilot workflow evidence |
| Tag is stable and matches the source version and newest changelog release | Positive and negative validator tests |
| Exactly one wheel and one source distribution match package name and tag version | Metadata validation tests; real build and twine check |
| Publication uses OIDC and GitHub Release creation follows successful publication | Job permissions/dependency review; authorized pilot evidence |
| Release notes contain only the matching changelog section | Extraction unit tests; pilot GitHub Release review |
| Contributors can prepare, publish, and verify a release | Runbook review and pilot execution |
| Implementation receives independent review | Independent reviewer findings resolved before completion |

## Delivery steps

1. Add changelog, contributor runbook, and PR checklist without bumping the version.
2. Implement shared validation for automatic and manual runs, distribution checks,
   and GitHub Release creation after publication.
3. Run validator tests on supported CI Python versions, build and inspect real
   distributions, and independently review the implementation.
4. Obtain explicit publication approval; prepare and merge the first Release PR,
   then push its matching tag.
5. Record the workflow run, PyPI version, GitHub Release, and clean-environment
   installation result as pilot evidence in VPY-32. Until then, the live pilot
   remains unverified.
6. Roll out to `vbase-py` in a separate change after the pilot passes.
