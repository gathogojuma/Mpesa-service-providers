import json
import base64
import requests
from typing import Optional
from datetime import datetime
from ..config import settings

class MpesaService:
    def __init__(self):
        self.is_mock = settings.MOCK_MPESA
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.callback_url = settings.MPESA_CALLBACK_URL

    async def stk_push(self, phone_number: str, amount: float, transaction_id: str):
        """Initiate STK Push"""
        if self.is_mock:
            return {"status": "mock", "transaction_id": transaction_id}

        # Real M-Pesa implementation
        access_token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{self.shortcode}{self.passkey}{timestamp}".encode()
        ).decode()

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": self.callback_url,
            "AccountReference": transaction_id,
            "TransactionDesc": "Payment for services"
        }

        response = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            headers=headers,
            json=payload
        )
        return response.json()

    async def simulate_approval(self, transaction_id: str):
        """Simulate M-Pesa callback for mock mode"""
        if not self.is_mock:
            return

        # Simulate callback to your own endpoint
        callback_data = {
            "transaction_id": transaction_id,
            "amount": 100.0,  # Would be the actual amount
            "phone": "254712345678",
            "mpesa_transaction_id": f"MOCK{transaction_id[:8]}",
            "status": "confirmed"
        }

        # Call the callback endpoint
        try:
            response = requests.post(
                f"{settings.MPESA_CALLBACK_URL}",
                json=callback_data,
                timeout=5
            )
            return response.json()
        except Exception as e:
            print(f"Mock callback failed: {e}")
            return {"status": "failed", "error": str(e)}

    def _get_access_token(self):
        """Get M-Pesa access token"""
        auth = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        headers = {"Authorization": f"Basic {auth}"}
        response = requests.get(
            "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
            headers=headers
        )
        return response.json().get("access_token")
