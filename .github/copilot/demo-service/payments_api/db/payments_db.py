"""
Payments Database Client
Connects to Payments DB (Aurora MySQL)
"""
import mysql.connector
from mysql.connector import pooling
import logging
import uuid
from typing import Optional
from datetime import datetime
from ..config import settings

logger = logging.getLogger(__name__)


class PaymentsDB:
    def __init__(self):
        self._pool = pooling.MySQLConnectionPool(
            pool_name="payments_pool",
            pool_size=5,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )

    def get_connection(self):
        return self._pool.get_connection()

    def get_account_balance(self, account_id: str) -> Optional[float]:
        """Get current account balance."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT balance FROM accounts WHERE account_id = %s",
                (account_id,)
            )
            result = cursor.fetchone()
            return float(result[0]) if result else None
        finally:
            cursor.close()
            conn.close()

    def create_transfer(
        self,
        sender_id: str,
        recipient_id: str,
        amount: float,
        transfer_type: str,
        card_last_four: Optional[str] = None
    ) -> str:
        """Create a new transfer record."""
        transfer_id = str(uuid.uuid4())
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO transfers
                (transfer_id, sender_account_id, recipient_account_id, amount,
                 transfer_type, card_last_four, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s)
                """,
                (transfer_id, sender_id, recipient_id, amount,
                 transfer_type, card_last_four, datetime.utcnow())
            )
            conn.commit()
            return transfer_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create transfer: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def update_account_balance(self, account_id: str, new_balance: float) -> bool:
        """Update account balance after transfer."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE accounts SET balance = %s, updated_at = %s WHERE account_id = %s",
                (new_balance, datetime.utcnow(), account_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update balance: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
