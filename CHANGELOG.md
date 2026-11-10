# Changelog

All notable changes are documented here, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Earlier releases were not tracked in this file; see the
[commit history](https://github.com/validityBase/vbase-api-py/commits/main/)
for prior changes.

## [Unreleased]

## [0.1.5] - 2026-11-10

### Deprecated

- `VerificationResult.display_timezone` is retained for compatibility. Use the
  timezone information in each receipt's `timestamp` instead.

### Fixed

- Accept stamp verification responses without `display_timezone`, returning
  `None` for the legacy attribute while preserving values from older APIs.

## [0.1.4] - 2026-10-26

### Added

- Compatibility test matrix for Python 3.8, 3.11, and 3.12.
