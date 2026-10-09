# API Client Retries

## Scope

`VBaseAPIClient` provides default retries for transient failures while
preserving the API operation's state-change semantics.

## Default Policy

- Three attempts in total.
- Linear waits of two seconds before attempt two and four seconds before attempt
  three.
- Retry `requests` connection and timeout failures.
- Retry HTTP `408`, `429`, `500`, `502`, `503`, and `504`.
- Return the final failure as `VBaseAPIError`.
- Callers can supply a standard `tenacity.Retrying` controller. The
  `default_retrying()` factory returns a new controller with the default policy,
  and callers can use `Retrying.copy()` to override selected strategies.
- Retryable HTTP statuses are configured separately on `VBaseAPIClient` because
  Tenacity does not model HTTP responses. The client adds the corresponding
  retry condition and `reraise=True` to a copy of the supplied controller, so
  the caller's object is not modified and final request failures remain
  `VBaseAPIError` instances.

## Operation Safety

- `get_collections`, `get_current_user`, and `get_user` are retry-safe reads.
- `verify_stamps` is a retry-safe read even though its transport method is
  `POST`.
- `create_stamp` is retried when `idempotent=True`, the input is replayable, and
  `idempotency_window` is either non-positive (unlimited) or greater than ten
  seconds.
- Positive finite windows use Tenacity's monotonic elapsed-time deadline. A
  retry is not started when its next delay would reach or exceed the window.
- Positive idempotency windows of ten seconds or less are sent once.
- `create_stamp(idempotent=False)` is sent once because the current API has no
  request identity that can distinguish a retry from a second intended stamp.
- `create_collection` checks for a collection matching the requested name,
  CID, description, and pin state before repeating a create request.
- `upload_stamped_file` is retry-safe because the server returns the existing
  file association for duplicate uploads.

## Multipart Inputs

Path inputs are reopened for every attempt. Caller-owned seekable streams are
rewound to their initial position and are not closed by the client. Automatic
retry is disabled for non-seekable streams because their content cannot be
replayed safely.

## Non-Retryable Failures

Client errors such as HTTP `400`, `401`, `403`, `404`, and ordinary `409`
responses are returned immediately. Response parsing and model validation
errors are also not retried.

Supporting guaranteed retries for non-idempotent stamps requires a separate
server contract, such as a persisted request idempotency key. That behavior is
outside this client-only policy.
