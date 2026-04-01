"""
Visa API Client
Connects to 3rd Party Card Networks service
"""
import httpx
import logging
from typing import Optional
from dataclasses import dataclass
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class CardVerificationResult:
    verified: bool
    card_last_four: str
    network: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class VisaClient:
    def __init__(self):
        self.base_url = settings.VISA_API_URL
        self.api_key = settings.VISA_API_KEY
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

    def verify_card(self, card_token: str, amount: float) -> CardVerificationResult:
        """
        Verify card can process the transaction amount.
        Calls Visa Direct API for real-time card verification.
        """
        try:
            response = self._client.post(
                "/v1/cards/verify",
                json={
                    "card_token": card_token,
                    "amount": amount,
                    "currency": "USD"
                }
            )
            response.raise_for_status()
            data = response.json()

            return CardVerificationResult(
                verified=data["status"] == "approved",
                card_last_four=data["card_last_four"],
                network=data.get("network", "visa"),
                error_code=data.get("error_code"),
                error_message=data.get("error_message")
            )

        except httpx.TimeoutException as e:
            logger.error(f"Visa API timeout: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Visa API error: {e.response.status_code}")
            raise

    def close(self):
        self._client.close()
