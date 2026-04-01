"""
Transfer Models
Request and response models for payment transfers
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class TransferType(str, Enum):
    STANDARD = "standard"
    INSTANT = "instant"


class TransferStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TransferRequest(BaseModel):
    sender_account_id: str = Field(..., description="Sender's account ID")
    recipient_account_id: str = Field(..., description="Recipient's account ID")
    amount: float = Field(..., gt=0, description="Transfer amount in USD")
    card_token: Optional[str] = Field(None, description="Card token for instant transfers")


class TransferResponse(BaseModel):
    transfer_id: str
    status: TransferStatus
    transfer_type: TransferType
    error_message: Optional[str] = None


class BalanceResponse(BaseModel):
    account_id: str
    balance: float
    cached: bool = False
