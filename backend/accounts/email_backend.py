"""Transactional email over HTTPS for hosts that block outbound SMTP."""
import uuid

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend


class EmailDeliveryError(Exception):
    """A safe delivery error: never includes credentials, recipients or reset codes."""


class ResendEmailBackend(BaseEmailBackend):
    endpoint = 'https://api.resend.com/emails'
    # Bound network waits below the mobile app's 20-second request timeout.
    request_timeout = (3, 8)

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages or []:
            if not message.recipients():
                continue
            try:
                self._send(message)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent

    def _send(self, message):
        api_key = getattr(settings, 'RESEND_API_KEY', '').strip()
        if not api_key:
            raise ImproperlyConfigured('RESEND_API_KEY is required for HTTPS email delivery.')
        if message.attachments:
            raise EmailDeliveryError('Attachments are not supported by this email backend.')
        # Run Django's normal header validation before sending via JSON.
        message.message()
        payload = {'from': message.from_email, 'to': list(message.to), 'subject': message.subject}
        payload['html' if message.content_subtype == 'html' else 'text'] = message.body
        for alternative in getattr(message, 'alternatives', []):
            content, mimetype = alternative
            if mimetype != 'text/html':
                raise EmailDeliveryError('This alternative email format is not supported.')
            payload['html'] = content
        for field in ('cc', 'bcc', 'reply_to'):
            if getattr(message, field):
                payload[field] = list(getattr(message, field))
        if message.extra_headers:
            payload['headers'] = dict(message.extra_headers)
        if not hasattr(message, '_resend_idempotency_key'):
            message._resend_idempotency_key = str(uuid.uuid4())
        try:
            response = requests.post(
                self.endpoint,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'PataHao-TransactionalEmail/1.0',
                    'Idempotency-Key': message._resend_idempotency_key,
                },
                json=payload,
                timeout=self.request_timeout,
                allow_redirects=False,
            )
        except requests.RequestException:
            raise EmailDeliveryError('Unable to connect to the email provider over HTTPS.') from None
        if response.status_code not in (200, 201):
            raise EmailDeliveryError(f'Email provider rejected the request (HTTP {response.status_code}).')
        try:
            result = response.json()
        except ValueError:
            raise EmailDeliveryError('Email provider returned an invalid response.') from None
        if not isinstance(result, dict) or not isinstance(result.get('id'), str) or not result['id']:
            raise EmailDeliveryError('Email provider did not confirm acceptance.')
