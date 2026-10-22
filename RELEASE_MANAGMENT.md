# Release management

Releases publish the `vbase-api` package from `validityBase/vbase-api-py`.
Choose a version increment in GitHub Actions. Automation reads the current
version, opens a Release PR, and publishes after that PR is reviewed and merged.

## 1. Prepare the changelog

Add user-facing changes under `[Unreleased]` in `CHANGELOG.md` through ordinary
PRs. Use Added, Changed, Deprecated, Removed, Fixed, or Security categories, with
PR references when available. Merge these changes to `main` before preparing
its release. At least one changelog entry is required.

The action finalizes these existing entries; it does not infer release notes
or breaking changes from commit messages.

## 2. Run Prepare release

1. Open the repository's
   [Actions page](https://github.com/validityBase/vbase-api-py/actions).
2. Select **Prepare release**, then **Run workflow**.
3. Select the `main` branch.
4. Choose the version increment and click **Run workflow**:

   | Choice | Use for | Example from 0.1.3 |
   | --- | --- | --- |
   | `patch` | Compatible bug fixes | 0.1.4 |
   | `minor` | Compatible new features | 0.2.0 |
   | `major` | Breaking API changes | 1.0.0 |

The repository must allow **GitHub Actions to create and approve pull
requests** in Settings → Actions → General → Workflow permissions. The workflow
uses the built-in GitHub token; it does not approve or merge its own PR.

The action starts from the latest `main` and:

- Reads `src/vbase_api/_version.py` and calculates the next stable version.
- Creates `release/vNEXT_VERSION` with the updated version file.
- Moves `[Unreleased]` entries into `## [NEXT_VERSION] - YYYY-MM-DD`, using the
  UTC preparation date, and retains an empty `[Unreleased]` section.
- Validates the result, runs the release-script tests, and opens a Release PR
  containing only the version and changelog changes.

An existing open Release PR, an existing target branch/tag, or an empty
`[Unreleased]` section stops preparation. Only stable versions are supported.

Alternatively, run the same action with GitHub CLI:

```bash
gh workflow run prepare-release.yml --repo validityBase/vbase-api-py --ref main -f bump=patch
```

Replace `patch` with `minor` or `major` as appropriate. Do not edit the version
file or create a release branch manually for this automated flow.

## 3. Approve workflows and review the Release PR

Open the Release PR created by the action. If GitHub displays
**Approve workflows to run**, a maintainer with write access must click it to
start CI for the bot-created PR.

Review the selected increment, resulting version, and changelog entries.
Confirm that the notes describe the changes being released and that the
version bump fits their compatibility impact. Obtain independent review and
wait for required repository checks to pass.

**Merge the Release PR into `main` only when ready to publish.** Merging is the
publication approval; no separate tag push is needed.

## 4. Automatic tagging and publication

After the Release PR merges, **Tag merged release** automatically:

1. Checks out that PR's merged commit on `main`.
2. Validates that the `release/vX.Y.Z` branch, source version, and newest dated
   changelog section match.
3. Creates and pushes `vX.Y.Z` on the merged commit. An existing tag pointing
   elsewhere is rejected.
4. Starts **Publish Python Package to PyPI** at that tag. This explicit dispatch
   is required because tag pushes made with the built-in GitHub token do not
   trigger another workflow automatically.

The publish workflow validates the release again, builds and checks the wheel
and source archive, and uploads them through the existing PyPI trusted
publisher. Any configured `pypi` environment approval still applies. After PyPI
succeeds, it automatically creates the GitHub Release with the changelog notes.

Closing an unmerged PR, merging an ordinary PR, or merging a release branch
from a fork does not run the tag job. Never move or reuse a pushed release tag.

## 5. Verify publication

On the [Actions page](https://github.com/validityBase/vbase-api-py/actions), check
that **Tag merged release** and all jobs in **Publish Python Package to PyPI**
succeeded. Confirm the new version and both distribution files on
[PyPI](https://pypi.org/project/vbase-api/), and check the tag and notes on the
[GitHub Release](https://github.com/validityBase/vbase-api-py/releases).

Install the published package in a fresh environment. These commands use
`0.1.4` as an example; replace it throughout with the released version:

```bash
python -m venv venv/release-check-0.1.4
source venv/release-check-0.1.4/bin/activate
python -m pip install --index-url https://pypi.org/simple --no-cache-dir vbase-api==0.1.4
python -m pip check
python -c "from importlib.metadata import version; import vbase_api; assert version('vbase-api') == vbase_api.__version__ == '0.1.4'; print(vbase_api.__file__); print(version('vbase-api'))"
deactivate
```

Use a new directory if the example environment already exists. Confirm the
printed import path belongs to that environment and the version is correct.

## Manual publication

For an approved manual publication, select an existing release tag containing
the workflow and validator:

```bash
gh workflow run publish-pypi.yml --repo validityBase/vbase-api-py --ref v0.1.4
```

Manual runs use the same validation. Branch refs are rejected. Do not dispatch
a version already published to PyPI.
