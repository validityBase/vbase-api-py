# VDT-898: sequential stamping and safe retries

Only HTTP 409 with JSON `error_code=stamp_in_progress` is automatically replayed.
Wait for `Retry-After` (integer seconds or an HTTP date); missing/invalid hints
use two seconds. Stop after five attempts and surface the final failure.
Preserve the original payload, multipart stream offset and filename; retries of
stamp creation enable `idempotent=true`. Generic 409, reconciliation-required,
transport errors and ambiguous 5xx outcomes are not replayed.

Local queues share ownership across instances using the same app origin and
credential. Different users with different keys remain concurrent. The app's
VDT-896 guard supplies authoritative exclusion across processes and multiple
keys for one user. Client-local queues do not establish distributed exclusion.
Deploy these callers before or with VDT-896; do not enable server contention
until callers use versions containing these changes.
