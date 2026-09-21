"""
Pesapal billing integration (DEBUG VERSION).

Handles:
- OAuth token generation
- IPN registration
- Payment session creation
- Transaction status verification
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

        print(f"[PESAPAL DEBUG] Requesting token from {url}")
        print(f"[PESAPAL DEBUG] Consumer key present: {bool(self.consumer_key)}")
        print(f"[PESAPAL DEBUG] Consumer key length: {len(self.consumer_key) if self.consumer_key else 0}")
        print(f"[PESAPAL DEBUG] Consumer secret present: {bool(self.consumer_secret)}")

        try:
            response = requests.post(url, json=payload, timeout=30)
            print(f"[PESAPAL DEBUG] Token response status: {response.status_code}")
            print(f"[PESAPAL DEBUG] Token response body: {response.text[:500]}")

            if response.status_code == 200:
                data = response.json()
                token = data.get("token")
                if token:
                    print(f"[PESAPAL DEBUG] Got token (length: {len(token)})")
                    return token
                else:
                    print(f"[PESAPAL DEBUG] No token in response. Full response: {data}")
                    return None
            return None
        except Exception as e:
            print(f"[PESAPAL DEBUG] Token exception: {type(e).__name__}: {e}")
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
            print(f"[PESAPAL DEBUG] IPN response status: {response.status_code}")
            print(f"[PESAPAL DEBUG] IPN response body: {response.text[:500]}")
            if response.status_code == 200:
                return response.json().get("ipn_id")
            return None
        except Exception as e:
            print(f"[PESAPAL DEBUG] IPN error: {type(e).__name__}: {e}")
            return None

    def submit_order(
        self,
        merchant_reference: str,
        amount: float,
        description: str,
        callback_url: str,
        ipn_id: str,
    ) -> Optional[dict]:
        """Create a payment session."""
        token = self._get_access_token()
        if not token:
            print("[PESAPAL DEBUG] Cannot submit order — no token")
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
                "email_address": "test@example.com",
                "phone_number": "254700000001",
                "country_code": "KE",
                "first_name": "Test",
                "middle_name": "",
                "last_name": "User",
                "line_1": "",
                "line_2": "",
                "city": "Nairobi",
                "state": "",
                "postal_code": "",
                "zip_code": "",
            },
        }
        headers = {"Authorization": f"Bearer {token}"}

        print(f"[PESAPAL DEBUG] Submitting order to {url}")
        print(f"[PESAPAL DEBUG] Merchant ref: {merchant_reference}")
        print(f"[PESAPAL DEBUG] Amount: {amount}")
        print(f"[PESAPAL DEBUG] IPN ID: {ipn_id}")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            print(f"[PESAPAL DEBUG] Order response status: {response.status_code}")
            print(f"[PESAPAL DEBUG] Order response body: {response.text[:1000]}")

            if response.status_code == 200:
                data = response.json()
                if data.get("redirect_url"):
                    return data
                else:
                    print(f"[PESAPAL DEBUG] No redirect_url. Full response: {data}")
                    return None
            return None
        except Exception as e:
            print(f"[PESAPAL DEBUG] Order error: {type(e).__name__}: {e}")
            return None

    def get_transaction_status(self, order_tracking_id: str) -> Optional[str]:
        """Check the status of a transaction."""
        token = self._get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/Transactions/GetTransactionStatus"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"order_tracking_id": order_tracking_id}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"[PESAPAL DEBUG] Status response: {response.status_code} — {response.text[:300]}")
            if response.status_code == 200:
                return response.json().get("payment_status")
            return None
        except Exception as e:
            print(f"[PESAPAL DEBUG] Status error: {type(e).__name__}: {e}")
            return None


pesapal_service = PesapalService()
