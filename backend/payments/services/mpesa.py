import base64
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from django.conf import settings


class MpesaAPIError(Exception):
    """Raised when the Daraja API request fails."""

    def __init__(
        self,
        message: str,
        payload: dict | None = None,
    ):
        super().__init__(message)
        self.payload = payload or {}

class MpesaClient:
    def __init__(self):
        self.environment = getattr(
            settings,
            "MPESA_ENVIRONMENT",
            "sandbox",
        ).strip().lower()
        self.consumer_key = getattr(settings, "MPESA_CONSUMER_KEY", "")
        self.consumer_secret = getattr(settings, "MPESA_CONSUMER_SECRET", "")
        self.shortcode = getattr(settings, "MPESA_SHORTCODE", "174379")
        self.passkey = getattr(settings, "MPESA_PASSKEY", "")
        self.callback_url = getattr(settings, "MPESA_CALLBACK_URL", "")
        self.transaction_type = getattr(
            settings,
            "MPESA_TRANSACTION_TYPE",
            "CustomerPayBillOnline",
        )
        self.timeout = getattr(settings, "MPESA_HTTP_TIMEOUT", 30)

        if self.environment == "production":
            self.base_url = "https://api.safaricom.co.ke"
        else:
            self.base_url = "https://sandbox.safaricom.co.ke"

    def _validate_configuration(self):
        missing = []

        required_values = {
            "MPESA_CONSUMER_KEY": self.consumer_key,
            "MPESA_CONSUMER_SECRET": self.consumer_secret,
            "MPESA_SHORTCODE": self.shortcode,
            "MPESA_PASSKEY": self.passkey,
            "MPESA_CALLBACK_URL": self.callback_url,
        }

        for name, value in required_values.items():
            if not value:
                missing.append(name)

        if missing:
            raise MpesaAPIError(
                "Missing M-Pesa configuration: " + ", ".join(missing)
            )

    @staticmethod
    def _safe_audit_payload(payload: dict) -> dict:
        """Remove credentials and derived secrets before persistence."""

        safe_payload = dict(payload)

        for key in {
            "Password",
            "SecurityCredential",
            "Authorization",
        }:
            if key in safe_payload:
                safe_payload[key] = "[REDACTED]"

        return safe_payload

    @staticmethod
    def _whole_shilling_amount(amount: Any) -> int:
        """Return a safe Daraja amount without silently truncating cents."""

        try:
            decimal_amount = Decimal(str(amount))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise MpesaAPIError(
                "M-Pesa amount must be a positive whole number."
            ) from exc

        if (
            not decimal_amount.is_finite()
            or decimal_amount <= Decimal("0")
            or decimal_amount != decimal_amount.to_integral_value()
        ):
            raise MpesaAPIError(
                "M-Pesa amount must be a positive whole number."
            )

        return int(decimal_amount)

    def get_access_token(self) -> str:
        self._validate_configuration()

        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"

        try:
            response = requests.get(
                url,
                auth=(self.consumer_key, self.consumer_secret),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise MpesaAPIError(
                f"Unable to connect to M-Pesa: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise MpesaAPIError(
                (
                    "M-Pesa returned a non-JSON token response. "
                    f"HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                ),

        payload={
            "http_status": response.status_code,
            "raw_response": response.text[:1000],
            "content_type": response.headers.get("Content-Type", ""),
            "url": response.url,
        },
    ) from exc

        if response.status_code != 200:
            raise MpesaAPIError(
                payload.get(
                    "errorMessage",
                    payload.get(
                        "error_description",
                        payload.get(
                            "error",
                            "M-Pesa token request failed.",
                        ),
                    ),
                ),
                payload={
                    "http_status": response.status_code,
                    "response": payload,
                    "url": response.url,
                },
            )

        access_token = payload.get("access_token")

        if not access_token:
            raise MpesaAPIError(
                "M-Pesa token response did not contain an access token."
            )

        return access_token

    def _generate_password(self) -> tuple[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        raw_value = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(
            raw_value.encode("utf-8")
        ).decode("utf-8")

        return password, timestamp

    def initiate_stk_push(
        self,
        *,
        phone_number: str,
        amount: Any,
        account_reference: str,
        transaction_description: str,
    ) -> dict:
        self._validate_configuration()
        whole_amount = self._whole_shilling_amount(amount)

        access_token = self.get_access_token()
        password, timestamp = self._generate_password()

        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": self.transaction_type,
            "Amount": whole_amount,
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": self.callback_url,
            "AccountReference": account_reference[:12],
            "TransactionDesc": transaction_description[:13],
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise MpesaAPIError(
                f"Unable to send M-Pesa STK Push: {exc}"
            ) from exc

        try:
            response_payload = response.json()
        except ValueError as exc:
            raise MpesaAPIError(
                "M-Pesa returned an invalid STK Push response."
            ) from exc

        if response.status_code not in {200, 201}:
            raise MpesaAPIError(
                response_payload.get(
                    "errorMessage",
                    response_payload.get(
                        "ResponseDescription",
                        "M-Pesa STK Push request failed.",
                    ),
                ),
                payload=response_payload,
            )

        if str(response_payload.get("ResponseCode", "")) != "0":
            raise MpesaAPIError(
                response_payload.get(
                    "errorMessage",
                    response_payload.get(
                        "ResponseDescription",
                        "M-Pesa rejected the STK Push request.",
                    ),
                ),
                payload=response_payload,
            )
        response_payload["_request_payload"] = payload

        return response_payload

    def stk_push(
        self,
        *,
        phone_number: str,
        amount: Any,
        account_reference: str,
        description: str,
    ) -> tuple[dict, dict]:
        provider_response = self.initiate_stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=account_reference,
            transaction_description=description,
        )

        request_payload = provider_response.pop(
            "_request_payload",
            {},
        )

        return (
            self._safe_audit_payload(request_payload),
            provider_response,
        )

    def query_stk_push(
        self,
        *,
        checkout_request_id: str,
    ) -> tuple[dict, dict]:
        """Query Daraja for the current state of an STK Push attempt."""

        self._validate_configuration()

        checkout_request_id = str(checkout_request_id).strip()

        if not checkout_request_id:
            raise MpesaAPIError(
                "CheckoutRequestID is required for M-Pesa reconciliation."
            )

        access_token = self.get_access_token()
        password, timestamp = self._generate_password()

        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise MpesaAPIError(
                f"Unable to query M-Pesa STK Push: {exc}"
            ) from exc

        try:
            response_payload = response.json()
        except ValueError as exc:
            raise MpesaAPIError(
                "M-Pesa returned an invalid STK query response.",
                payload={
                    "http_status": response.status_code,
                    "raw_response": response.text[:1000],
                    "content_type": response.headers.get(
                        "Content-Type",
                        "",
                    ),
                },
            ) from exc

        if response.status_code not in {200, 201}:
            raise MpesaAPIError(
                response_payload.get(
                    "errorMessage",
                    response_payload.get(
                        "ResponseDescription",
                        "M-Pesa STK query failed.",
                    ),
                ),
                payload=response_payload,
            )

        if str(response_payload.get("ResponseCode", "")) != "0":
            raise MpesaAPIError(
                response_payload.get(
                    "errorMessage",
                    response_payload.get(
                        "ResponseDescription",
                        "M-Pesa rejected the STK query.",
                    ),
                ),
                payload=response_payload,
            )

        return (
            self._safe_audit_payload(payload),
            response_payload,
        )
