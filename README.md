# vbase-py

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


