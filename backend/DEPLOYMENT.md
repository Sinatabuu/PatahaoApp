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

## Release checks

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
property media and private mandate documents must be split and moved to
durable storage with private access controls for mandate files. The production
application server, health monitoring, log collection, and automated backup
policy must also be configured on the chosen hosting platform.
