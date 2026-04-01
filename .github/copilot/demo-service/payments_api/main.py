"""
Payments API Gateway
OrbitPay payment processing service
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from .clients.redis_client import RedisCache
from .clients.visa_client import VisaClient
from .db.payments_db import PaymentsDB
from .models.transfer import TransferRequest, TransferResponse, BalanceResponse

app = FastAPI(title="Payments API Gateway", version="1.0.0")
logger = logging.getLogger(__name__)

redis = RedisCache()
visa = VisaClient()
db = PaymentsDB()


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/v1/accounts/{account_id}/balance", response_model=BalanceResponse)
def get_balance(account_id: str):
    """Get account balance from cache or database."""
    cached = redis.get(f"balance:{account_id}")
    if cached:
        return BalanceResponse(account_id=account_id, balance=float(cached), cached=True)

    balance = db.get_account_balance(account_id)
    if balance is None:
        raise HTTPException(status_code=404, detail="Account not found")

    redis.set(f"balance:{account_id}", str(balance), ttl=300)
    return BalanceResponse(account_id=account_id, balance=balance, cached=False)


@app.post("/v1/transfers/standard", response_model=TransferResponse)
def create_standard_transfer(request: TransferRequest):
    """Create a standard transfer (settles in 1-3 business days)."""
    sender_balance = db.get_account_balance(request.sender_account_id)
    if sender_balance is None:
        raise HTTPException(status_code=404, detail="Sender account not found")
    if sender_balance < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    transfer_id = db.create_transfer(
        sender_id=request.sender_account_id,
        recipient_id=request.recipient_account_id,
        amount=request.amount,
        transfer_type="standard"
    )

    redis.delete(f"balance:{request.sender_account_id}")

    return TransferResponse(
        transfer_id=transfer_id,
        status="pending",
        transfer_type="standard"
    )


# TODO: Add POST /v1/transfers/instant endpoint
# Requirements:
# - Check sender balance from Redis cache
# - Verify card with Visa API
# - Write transfer record to Payments DB
# - Handle failures gracefully
