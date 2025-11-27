"""
vBase API Models

Data models for vBase API request and response objects.
See https://app.vbase.com/swagger for API documentation.
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Collection:
    """
    Collection model representing a vBase collection.
    
    Attributes:
        id: Collection ID
        name: Collection name
        cid: Collection CID
        is_pinned: Whether the collection is pinned
        is_public: Whether the collection is public
        created_at: Creation timestamp
        description: Collection description
    """
    id: int
    name: str
    cid: str
    is_pinned: bool
    is_public: bool
    created_at: str
    description: str

    @classmethod
    def from_dict(cls, data: dict) -> 'Collection':
        """Create a Collection from a dictionary."""
        return cls(
            id=data['id'],
            name=data['name'],
            cid=data['cid'],
            is_pinned=data['is_pinned'],
            is_public=data['is_public'],
            created_at=data['created_at'],
            description=data['description']
        )


@dataclass
class Error:
    """
    Error response model.
    
    Attributes:
        error: Error message
        details: Optional error details
    """
    error: str
    details: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Error':
        """Create an Error from a dictionary."""
        return cls(
            error=data['error'],
            details=data.get('details')
        )


@dataclass
class CommitmentReceipt:
    """
    Commitment receipt from blockchain stamping.
    
    Attributes:
        transaction_hash: Blockchain transaction hash
        user_address: User's blockchain address
        set_cid: Set CID
        object_cid: Object CID
        timestamp: Timestamp of the stamp
        chain_id: Blockchain chain ID
    """
    transaction_hash: str
    user_address: str
    set_cid: str
    object_cid: str
    timestamp: str
    chain_id: int

    @classmethod
    def from_dict(cls, data: dict) -> 'CommitmentReceipt':
        """Create a CommitmentReceipt from a dictionary."""
        return cls(
            transaction_hash=data['transaction_hash'],
            user_address=data['user_address'],
            set_cid=data['set_cid'],
            object_cid=data['object_cid'],
            timestamp=data['timestamp'],
            chain_id=data['chain_id']
        )


@dataclass
class FileObject:
    """
    File object metadata.
    
    Attributes:
        file_name: Name of the file
        file_path: Path to the file
    """
    file_name: str
    file_path: str

    @classmethod
    def from_dict(cls, data: dict) -> 'FileObject':
        """Create a FileObject from a dictionary."""
        return cls(
            file_name=data['file_name'],
            file_path=data['file_path']
        )


@dataclass
class IdempotentStampResponse:
    """
    Response for idempotent stamp requests (200 status).
    
    Attributes:
        commitment_receipt: The commitment receipt from blockchain
    """
    commitment_receipt: CommitmentReceipt

    @classmethod
    def from_dict(cls, data: dict) -> 'IdempotentStampResponse':
        """Create an IdempotentStampResponse from a dictionary."""
        return cls(
            commitment_receipt=CommitmentReceipt.from_dict(data['commitment_receipt'])
        )


@dataclass
class StampCreatedResponse:
    """
    Response for newly created stamp (201 status).
    
    Attributes:
        commitment_receipt: The commitment receipt from blockchain
        file_object: Optional file object metadata
    """
    commitment_receipt: CommitmentReceipt
    file_object: Optional[FileObject] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'StampCreatedResponse':
        """Create a StampCreatedResponse from a dictionary."""
        file_obj = None
        if 'file_object' in data and data['file_object']:
            file_obj = FileObject.from_dict(data['file_object'])
        
        return cls(
            commitment_receipt=CommitmentReceipt.from_dict(data['commitment_receipt']),
            file_object=file_obj
        )


@dataclass
class VerificationResult:
    """
    Result from verifying CIDs.
    
    Attributes:
        display_timezone: Timezone for display
        stamp_list: List of commitment receipts for verified stamps
    """
    display_timezone: str
    stamp_list: List[CommitmentReceipt]

    @classmethod
    def from_dict(cls, data: dict) -> 'VerificationResult':
        """Create a VerificationResult from a dictionary."""
        stamp_list = [
            CommitmentReceipt.from_dict(stamp) 
            for stamp in data.get('stamp_list', [])
        ]
        
        return cls(
            display_timezone=data['display_timezone'],
            stamp_list=stamp_list
        )


@dataclass
class AccountSettings:
    """
    User account settings.
    
    Attributes:
        name: User's name
        email: User's email address
        persistent_id: Persistent user ID
        description: User description
        display_timezone: Display timezone
        date_joined: Date user joined
        last_address: Last blockchain address
        last_name: User's last name
        last_is_verified: Whether last address is verified
        storage_type: Storage type (e.g., 'ipfs')
    """
    name: str
    email: str
    persistent_id: str
    description: str
    display_timezone: str
    date_joined: str
    last_address: str
    last_name: str
    last_is_verified: bool
    storage_type: str

    @classmethod
    def from_dict(cls, data: dict) -> 'AccountSettings':
        """Create AccountSettings from a dictionary."""
        return cls(
            name=data['name'],
            email=data['email'],
            persistent_id=data['persistent_id'],
            description=data['description'],
            display_timezone=data['display_timezone'],
            date_joined=data['date_joined'],
            last_address=data['last_address'],
            last_name=data['last_name'],
            last_is_verified=data['last_is_verified'],
            storage_type=data['storage_type']
        )
