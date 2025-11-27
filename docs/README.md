# vbase-py

vBase REST API Python Client

See [documentation](https://docs.vbase.com/) and the [Swagger UI](https://app.vbase.com/swagger/) for more details.

---

## Installation

Install the package using pip:

```bash
pip install vbase-api-py
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

## Usage Guide

### Creating a Client

The `VBaseAPIClient` can be initialized with your API key:

```python
from vbase_api import VBaseAPIClient

# Basic initialization
client = VBaseAPIClient(api_key="your-bearer-token")

# With custom base URL and timeout
client = VBaseAPIClient(
    api_key="your-bearer-token",
    base_url="https://app.vbase.com",
    timeout=60
)

# Using context manager (recommended)
with VBaseAPIClient(api_key="your-bearer-token") as client:
    collections = client.get_collections()
    # Client resources are automatically cleaned up
```

### Stamping Data

The `create_stamp()` method is the core functionality of vBase. It allows you to create a blockchain-verified timestamp of your data.

#### Stamp Inline Data

```python
# Stamp text data
stamp = client.create_stamp(
    data="Important document content"
)
print(f"Object CID: {stamp.commitment_receipt.object_cid}")
print(f"Transaction: {stamp.commitment_receipt.transaction_hash}")
print(f"Timestamp: {stamp.commitment_receipt.timestamp}")

```

#### Stamp a File

```python
# Stamp a file from disk
stamp = client.create_stamp(file="report.pdf")

# Stamp a file and add to a collection
stamp = client.create_stamp(
    file="portfolio.csv",
    collection_name="Investment Records",
    idempotent=False
)

# Access file information
if stamp.file_object:
    print(f"File: {stamp.file_object.file_name}")
    print(f"Path: {stamp.file_object.file_path}")
```

#### Stamp precalculated CID, without uploading actual data

```python
# Stamp a CID that already exists
stamp = client.create_stamp(
    data_cid="0xbd9c71f7277c841210dd60b84be775e0a48cd6643c5e28eebf8f11b95b893201",
    collection_name="My Collection"
)
```

### Working with Collections

Collections help organize your stamped data into logical groups.

#### List Collections

```python
# Get all collections
collections = client.get_collections()
for collection in collections:
    print(f"{collection.name} - {collection.description}")

# Filter by pinned status
pinned_collections = client.get_collections(is_pinned=True)

# Filter by user address
user_collections = client.get_collections(user_address="0x...")
```

#### Create a Collection

```python
collection = client.create_collection(
    name="Investment Track Records",
    description="Auditable portfolio holdings and trades"
)
print(f"Created collection: {collection.name}")
```

### Verifying Stamps

Verify that specific CIDs have been stamped on the blockchain.

```python
# Verify one or more CIDs
result = client.verify_stamps(
    cids=[
        "0xbd9c71f7277c841210dd60b84be775e0a48cd6643c5e28eebf8f11b95b893201",
        "0xcd9c71f7277c841210dd60b84be775e0a48cd6643c5e28eebf8f11b95b893202"
    ]
)

# Check results
print(f"Timezone: {result.display_timezone}")
for stamp in result.stamp_list:
    print(f"Found stamp:")
    print(f"  CID: {stamp.object_cid}")
    print(f"  Timestamp: {stamp.timestamp}")
    print(f"  Transaction: {stamp.transaction_hash}")
    print(f"  User: {stamp.user_address}")

# Verify CIDs for current user only
result = client.verify_stamps(
    cids=["0xbd9c71f7277c841210dd60b84be775e0a48cd6643c5e28eebf8f11b95b893201"],
    filter_by_user=True
)
```

### Upload Previously Stamped Files

Upload a file that has already been stamped to vBase storage.

```python
result = client.upload_stamped_file(
    collection_name="Investment Records",
    file="previously_stamped.pdf"
)
print(f"Uploaded: {result.file_object.file_name}")
```

### User Account Information

```python
# Get current user information
user = client.get_current_user()
print(f"Email: {user.email}")
print(f"Name: {user.name}")
print(f"Timezone: {user.display_timezone}")
print(f"Address: {user.last_address}")

# Get another user's information by address
other_user = client.get_user("0x1234123412341234123412341234123412341234")
print(f"User name: {other_user.name}")
```

## Error Handling

The client raises `VBaseAPIError` for API-related errors:

```python
from vbase_api import VBaseAPIClient, VBaseAPIError

client = VBaseAPIClient(api_key="your-bearer-token")

try:
    stamp = client.create_stamp(data={"test": "data"})
except VBaseAPIError as e:
    print(f"Error: {e.message}")
    if e.status_code:
        print(f"Status code: {e.status_code}")
```

## Response Objects

The client returns typed response objects for easy data access:

- **`StampCreatedResponse`**: Returned when a new stamp is created (201 status)
  - `commitment_receipt`: CommitmentReceipt object
  - `file_object`: FileObject (optional)

- **`IdempotentStampResponse`**: Returned when stamp already exists (200 status)
  - `commitment_receipt`: CommitmentReceipt object

- **`CommitmentReceipt`**: Blockchain stamp details
  - `transaction_hash`: Blockchain transaction hash
  - `user_address`: User's blockchain address
  - `set_cid`: Set CID (collection)
  - `object_cid`: Object CID (stamped data)
  - `timestamp`: ISO format timestamp
  - `chain_id`: Blockchain chain ID

- **`Collection`**: Collection information
  - `id`, `name`, `cid`, `description`
  - `is_pinned`, `is_public`, `is_portfolio`
  - `created_at`

- **`AccountSettings`**: User account details
  - `name`, `email`, `persistent_id`
  - `display_timezone`, `date_joined`
  - `last_address`, `last_is_verified`

## Complete Example

```python
from vbase_api_py import VBaseAPIClient, VBaseAPIError

def main():
    # Initialize client
    with VBaseAPIClient(api_key="your-bearer-token") as client:
        try:
            # Get user info
            user = client.get_current_user()
            print(f"Authenticated as: {user.email}")
            
            # Create a collection
            collection = client.create_collection(
                name="Trading Records",
                cid=None,
                description="Timestamped trading data",
                is_pinned=True
            )
            
            # Stamp trading data
            trade_data = {
                "symbol": "AAPL",
                "shares": 100,
                "price": 150.25,
                "timestamp": "2025-11-24T10:30:00Z"
            }
            
            stamp = client.create_stamp(
                data=trade_data,
                collection_name="Trading Records"
            )
            
            print(f"Trade stamped!")
            print(f"  CID: {stamp.commitment_receipt.object_cid}")
            print(f"  Transaction: {stamp.commitment_receipt.transaction_hash}")
            print(f"  Blockchain timestamp: {stamp.commitment_receipt.timestamp}")
            
            # Verify the stamp
            verification = client.verify_stamps(
                cids=[stamp.commitment_receipt.object_cid]
            )
            
            if verification.stamp_list:
                print("Stamp verified on blockchain!")
            
        except VBaseAPIError as e:
            print(f"API Error: {e}")

if __name__ == "__main__":
    main()
```
