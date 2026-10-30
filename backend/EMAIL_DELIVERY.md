# Password recovery over HTTPS

Railway blocks SMTP on Hobby, Free and Trial. This optional Django backend uses Resend's HTTPS API with the existing requests dependency. It does not change the selected backend automatically or require a mobile release/migration.

## Activate

1. Create/sign in to a business-owned Resend account and add `mail.patahao.app` as a sending domain. Verify the exact DNS records Resend supplies in Cloudflare. A sending subdomain avoids changing existing inbound mail routes. Configure sending only; leave root MX records untouched. Disable open/click tracking for recovery messages.
2. Create an API key restricted to sending from that verified domain. Copy it directly into Railway, not into chat or source control.
3. Apply these service variables together and deploy:

```text
DJANGO_EMAIL_BACKEND=accounts.email_backend.ResendEmailBackend
DJANGO_DEFAULT_FROM_EMAIL=Pata Hao <noreply@mail.patahao.app>
RESEND_API_KEY=<private domain-restricted sending key>
```

Use the actual verified subdomain if different. The Gmail sender address cannot replace a sending domain you own/verify. Gmail can remain the contact mailbox; users receive recovery messages at their existing registered addresses. SMTP host/port/password settings are unused by the HTTPS backend. Remove obsolete Gmail SMTP credentials once live delivery is confirmed.

4. Test Forgot password through the installed app using an account you control. Check inbox/spam, enter the code only in the app, change the password and verify sign-in. Provider API acceptance does not establish final inbox delivery; check its delivery status if necessary. Never paste codes, API keys or passwords in chat.

## Implementation and validation

Fixed endpoint `https://api.resend.com/emails`, Bearer auth, JSON, redirects disabled, connect/read timeouts 3/8 seconds, no automatic retry. Message-level UUID idempotency keys prevent duplicate acceptance when the same message object is retried. HTML alternatives and cc/bcc/reply-to are preserved; unsupported attachments/alternatives fail explicitly. Error messages never include recipient addresses, reset codes, credentials or raw provider bodies. Non-success responses, malformed JSON and missing acceptance IDs are failures. RESEND_API_KEY is required at send time, not during collectstatic.

Existing recovery semantics are preserved: failed delivery invalidates the challenge, responses remain account-neutral, codes expire and are single-use, wrong-code attempts are limited and changing a password revokes prior tokens. All 18 account tests pass, including eight HTTPS backend/integration tests with a fake provider. Real DNS verification, inbox delivery and phone testing remain pending external setup.

References:
- https://docs.railway.com/networking/outbound-networking
- https://github.com/resend/resend-openapi/blob/main/resend.yaml
- https://github.com/resend/resend-skills/blob/main/skills/resend/references/domains.md
