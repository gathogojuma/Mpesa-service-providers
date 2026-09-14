"""
Pesapal billing integration.

Handles:
- OAuth token generation
- IPN registration (for callbacks)
- Payment session creation
- Transaction status verification

Sandbox: https://cybqa.pesapal.com/pesapalv3/api/
Production: https://pay.pesapal.com/pesapalv3/api/
"""
import requests
from typing import Optional
from ..config import settings


class PesapalService:
    def __init__(self):
        self.consumer_key = settings.PESAPAL_CONSUMER_KEY
        self.consumer_secret = settings.PESAPAL_CONSUMER_SECRET
        self.base_url = settings.PESAPAL_BASE_URL.rstrip("/")
        self.ipn_url = settings.PESAPAL_IPN_URL

    def _get_access_token(self) -> Optional[str]:
        """Request an OAuth token from Pesapal."""
        url = f"{self.base_url}/Auth/RequestToken"
        payload = {
            "consumer_key": self.consumer_key,
            "consumer_secret": self.consumer_secret,
        }
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json().get("token")
            return None
        except Exception as e:
            print(f"Pesapal token error: {e}")
            return None

    def register_ipn(self) -> Optional[str]:
        """Register the IPN URL with Pesapal. Returns the IPN ID."""
        token = self._get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/URLSetup/RegisterIPN"
        payload = {
            "url": self.ipn_url,
            "ipn_notification_type": "POST",
        }
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json().get("ipn_id")
            return None
        except Exception as e:
            print(f"Pesapal IPN registration error: {e}")
            return None

    def submit_order(
        self,
        merchant_reference: str,
        amount: float,
        description: str,
        callback_url: str,
        ipn_id: str,
    ) -> Optional[dict]:
        """
        Create a payment session. Returns a dict with:
        - redirect_url: where to send the user to pay
        - order_tracking_id: Pesapal's identifier for this order
        """
        token = self._get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/Transactions/SubmitOrderRequest"
        payload = {
            "id": merchant_reference,
            "currency": "KES",
            "amount": amount,
            "description": description,
            "callback_url": callback_url,
            "notification_id": ipn_id,
            "billing_address": {
                "email_address": "",
                "phone_number": "",
                "country_code": "KE",
                "first_name": "",
                "middle_name": "",
                "last_name": "",
                "line_1": "",
                "line_2": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "zip_code": "",
            },
        }
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Pesapal order submission error: {e}")
            return None

    def get_transaction_status(self, order_tracking_id: str) -> Optional[str]:
        """
        Check the status of a transaction.
        Returns: "COMPLETED", "FAILED", "PENDING", or None on error.
        """
        token = self._get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/Transactions/GetTransactionStatus"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"order_tracking_id": order_tracking_id}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                return response.json().get("payment_status")
            return None
        except Exception as e:
            print(f"Pesapal status check error: {e}")
            return None


# Singleton
pesapal_service = PesapalService()
