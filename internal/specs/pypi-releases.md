# PyPI release process pilot (VPY-32)

## Scope and decisions

- Implement in `vbase-api-py` first; `vbase-py` rollout follows pilot validation.
- Continue from the version in `src/vbase_api/_version.py`.
- **Prepare release** reads the version from `main`, applies the maintainer's
  required patch/minor/major choice, finalizes the existing Unreleased entries,
  and opens a Release PR. It does not generate notes from commit messages.
- A maintainer approves bot PR workflows when prompted, obtains independent
  review, and merges to `main`. Merge authorizes publication: **Tag merged
  release** pushes the matching tag on the merged commit and dispatches the
  existing publish workflow at that tag.
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
| Maintainer selects patch/minor/major; preparation uses the current version from main and resets lower components | Version increment and preparation unit tests |
| Empty Unreleased entries, duplicate target versions, and existing release work stop preparation | Negative preparation tests and workflow guards |
| Review and required CI precede merge; bot-created PR workflows can be approved by a maintainer | Runbook and pilot PR evidence |
| Merged same-repository release PR automatically tags the merged commit and dispatches publication; unmerged, ordinary, and fork PRs do not | Tag workflow conditions, shell checks, and pilot evidence |
| Automatic publication follows release tagging; ordinary branch pushes and GitHub Releases do not start it | Workflow trigger review |
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
   version preparation, Release PR creation, automatic tags after merge, and
   GitHub Release creation after publication.
3. Run validator tests on supported CI Python versions, build and inspect real
   distributions, and independently review the implementation.
4. Run Prepare release with an explicit increment, approve PR workflows if
   prompted, and review the Release PR. Merge when publication is approved;
   automation pushes the matching tag and starts the publish workflow.
5. Record the workflow run, PyPI version, GitHub Release, and clean-environment
   installation result as pilot evidence in VPY-32. Until then, the live pilot
   remains unverified.
6. Roll out to `vbase-py` in a separate change after the pilot passes.
