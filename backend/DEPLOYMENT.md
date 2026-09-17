# Pata HAO backend environments

The backend has explicit `development`, `staging`, and `production` runtime
modes. Development remains the default so the existing SQLite and mock-payment
testing workflow continues until a deployed environment is deliberately
configured.

| Mode | Debug | Database | Mock payment handoff | HTTPS cookies/redirect |
| --- | --- | --- | --- | --- |
| `development` | On by default | SQLite by default | Available by default | Off |
| `staging` | Forced off | PostgreSQL required | Always disabled | On |
| `production` | Forced off | PostgreSQL required | Always disabled | On |

## Required deployed settings

Set these through the hosting provider's secret/environment configuration:

```dotenv
PATAHAO_ENVIRONMENT=production
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=replace-with-a-long-random-production-secret
DJANGO_ALLOWED_HOSTS=patahao-api.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://patahao-api.example.com
DATABASE_URL=postgresql://user:password@host:5432/database?sslmode=require
DJANGO_SECURE_HSTS_SECONDS=3600
ENABLE_DEVELOPMENT_PAYMENT_HANDOFF=false
```

Use `.env.example` as the complete variable reference. Never commit a real
`.env` file or production secret. Treat the Django key that was previously
hard-coded in the repository as exposed and never reuse it for staging or
production.

## Sandbox-first M-Pesa rollout

Keep real customer charges disabled until Pata HAO has its approved Safaricom
business payment product and production Daraja credentials:

```dotenv
MPESA_ENVIRONMENT=sandbox
MPESA_LIVE_PAYMENTS_ENABLED=false
```

Development may use Daraja sandbox credentials and an HTTPS test callback at
`/api/payments/mpesa/callback/`. Each STK request is recorded as a separate
payment attempt. Callback amount, phone number, merchant request ID, checkout
request ID, receipt number, and transaction time must all match before the
viewing is credited. Staff may query an attempt for reconciliation, but a
query response alone never creates a successful receipt.

When the Safaricom production setup is ready, configure all of the following
in the hosting provider's secret store:

```dotenv
PATAHAO_ENVIRONMENT=production
ENABLE_DEVELOPMENT_PAYMENT_HANDOFF=false
MPESA_ENVIRONMENT=production
MPESA_LIVE_PAYMENTS_ENABLED=true
MPESA_CONSUMER_KEY=replace-with-production-consumer-key
MPESA_CONSUMER_SECRET=replace-with-production-consumer-secret
MPESA_SHORTCODE=replace-with-approved-shortcode-or-till
MPESA_PASSKEY=replace-with-production-passkey
MPESA_CALLBACK_URL=https://patahao-api.example.com/api/payments/mpesa/callback/
MPESA_TRANSACTION_TYPE=CustomerPayBillOnline
```

Use `CustomerPayBillOnline` for an approved PayBill or
`CustomerBuyGoodsOnline` for an approved Buy Goods Till. Production startup
fails closed if the live flag, credentials, HTTPS callback, transaction type,
or development-handoff setting is unsafe. Do not switch these values until
the actual Safaricom product is known.

The payment migrations add unique financial-reference constraints. They first
check existing rows and stop with an explicit error if duplicate payment,
checkout, receipt, or commission-payout references require staff review. Do
not edit or delete historical payment evidence merely to make a migration
pass; investigate and document each conflict.

## Release checks

Install `ffmpeg` and `ffprobe` on every application worker before enabling
property walkthrough uploads. The server uses them to verify the codec,
duration, and resolution and to generate a safe thumbnail. Keep the default
binary names unless the deployment installs them at explicit paths:

```dotenv
VIDEO_FFPROBE_BINARY=ffprobe
VIDEO_FFMPEG_BINARY=ffmpeg
VIDEO_PROCESSING_TIMEOUT_SECONDS=45
```

Allow at least 105 MB request bodies at the reverse proxy so multipart
overhead does not reject a valid 100 MB video. The application worker and
proxy request timeouts must also exceed the 45-second processing limit. Keep
the public API limit at 100 MB; do not raise it merely to accept 4K uploads.

From `backend/`, with the deployed environment variables loaded:

```bash
python manage.py check
python manage.py check --deploy
python manage.py migrate --plan
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py test
```

Start HSTS with the documented one-hour value. After HTTPS has been verified
for every relevant subdomain, increase it to `31536000` and consider enabling
`DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` and
`DJANGO_SECURE_HSTS_PRELOAD`. Django will intentionally report its two HSTS
hardening warnings during this cautious rollout period.

Back up the current database and uploaded media before migration. Moving the
existing SQLite testing data into PostgreSQL is a separate, deliberate data
migration; do not point production at the existing SQLite file.

## Remaining infrastructure work

`DJANGO_MEDIA_ROOT` still refers to local disk. Before public production,
property photos and videos must move to durable object storage/CDN, while
private mandate documents must use separate private access controls. The
production application server, health monitoring, log collection, and
automated backup policy must also be configured on the chosen hosting
platform.
