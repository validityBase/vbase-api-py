# vbase-api-py

vBase REST API Python Client

See [documentation](https://docs.vbase.com/) and the [Swagger UI](https://app.vbase.com/swagger/) for more details.

---

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE.txt](LICENSE.txt) file for details.

## Introduction

vBase creates a global auditable record of when data was created, by whom, and how it has changed (collectively, “data provenance”). Data producers can prove the provenance of their data to any external party, increasing its value and marketability. Data consumers can ensure the integrity of historical data and any derivative calculations. The result is trustworthy information that can be put into production quickly without expensive and time-consuming trials.

Verifiable provenance establishes the credibility of data and calculations. For example, if you wish to prove investment skill, the recipient must be sure they are receiving a complete and accurate record of your timestamped trades or portfolios.

vBase resolves several expensive market failures common to financial data. Some of the areas that benefit include:
- Provably point-in-time datasets
- Auditable investing track records
- Sound backtests, historical simulations, and time-series modeling

vBase services do not require access to the data itself, assuring privacy. They also do not rely on centralized intermediaries, eliminating the technical, operating, and business risks of a trusted party controlling your data and its validation. vBase ensures data security and interoperability that is unattainable with legacy centralized systems. It does so by storing digital fingerprints of data, metadata, and revisions on secure public blockchains.

With vBase, creating and consuming provably correct data is as easy as pressing a button.

## References
- [vBase Website](https://vbase.com)
- [vBase Documentation](https://docs.vbase.com/)
- [vBase Swagger UI](https://app.vbase.com/swagger/)
- [vBase API Python Client Issues](https://github.com/validityBase/vbase-api-py/issues)

## Installation

Install the package using pip:

```bash
pip install vbase-api
```

## Quick Start

### Getting Your API Key

To use the vBase API, you'll need an API key (Bearer token). You can obtain this from your [vBase account settings](https://app.vbase.com/profile#account_settings).

### Basic Usage

```python
from vbase_api import VBaseAPIClient

# Initialize the client
client = VBaseAPIClient(api_key="your-bearer-token")

# Stamp some data
stamp = client.create_stamp(data="Important data to be stamped")
print(f"Stamped with CID: {stamp.commitment_receipt.object_cid}")

# List your collections
collections = client.get_collections()
for collection in collections:
    print(f"{collection.name}: {collection.cid}")
```

## Retries

The client retries transient transport failures and HTTP `408`, `429`, `500`,
`502`, `503`, and `504` responses for read operations and retry-safe writes.
The default policy makes three attempts with linear delays of two and four
seconds.

```python
from tenacity import stop_after_attempt, wait_incrementing

from vbase_api import VBaseAPIClient, default_retrying

client = VBaseAPIClient(
    api_key="your-bearer-token",
    retrying=default_retrying().copy(
        stop=stop_after_attempt(5),
        wait=wait_incrementing(start=2, increment=2, max=30),
    ),
)
```

The client accepts a standard `tenacity.Retrying` controller. Start with
`default_retrying()` and use its `copy()` method to override selected Tenacity
strategies while preserving the default transient-error policy. Set
`stop=stop_after_attempt(1)` to disable retries. Retryable HTTP statuses can be
overridden separately with the `retry_status_codes` client argument. The client
combines those HTTP retries with the supplied controller without modifying it.

Stamp creation is retried when `idempotent=True` and `idempotency_window` is
either non-positive (unlimited) or greater than ten seconds. Finite-window
retries stop before the next delay would reach the window. Non-idempotent stamps
are sent once. File uploads are retried only when the input is a path or a
seekable stream.
