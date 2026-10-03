# Pata HAO staging deployment package

These templates support an Ubuntu/Debian server running Nginx, systemd,
Gunicorn, and a managed PostgreSQL database. They are deliberately examples:
replace every `example.com`, database, path, and credential placeholder before
installation.

## 1. Server prerequisites

Install Python 3.12, `python3-venv`, Nginx, `ffmpeg`, `ffprobe`, a PostgreSQL
client, and Certbot. Create a non-login `patahao` service account and these
directories:

```bash
sudo install -d -o patahao -g www-data -m 0750 /srv/patahao
sudo install -d -o patahao -g www-data -m 0750 /var/lib/patahao/media
sudo install -d -o root -g root -m 0750 /etc/patahao
```

Use a managed PostgreSQL database for staging. Do not copy the development
SQLite database into service.

## 2. Install one immutable release

Check out an approved release tag into `/srv/patahao/current`, then install its
pinned dependencies into `/srv/patahao/venv`:

```bash
python3.12 -m venv /srv/patahao/venv
/srv/patahao/venv/bin/python -m pip install --upgrade pip
/srv/patahao/venv/bin/python -m pip install -r /srv/patahao/current/backend/requirements.txt
```

Copy `backend.env.example` to `/etc/patahao/backend.env`, replace every
placeholder, and protect the installed file:

```bash
sudo chown root:root /etc/patahao/backend.env
sudo chmod 0600 /etc/patahao/backend.env
```

## 3. Validate and release

Load the environment without printing it, then run the release checks from
`/srv/patahao/current/backend`:

```bash
set -a
. /etc/patahao/backend.env
set +a
/srv/patahao/venv/bin/python manage.py check
/srv/patahao/venv/bin/python manage.py check --deploy
/srv/patahao/venv/bin/python manage.py migrate --plan
/srv/patahao/venv/bin/python manage.py migrate
/srv/patahao/venv/bin/python manage.py collectstatic --noinput
/srv/patahao/venv/bin/python -m gunicorn --check-config --config config/gunicorn.py config.wsgi:application
```

Back up the database and uploaded files before every migration. Never run a
release when `migrate --plan` contains an unexpected operation.

## 4. Start the service and reverse proxy

Install `patahao-backend.service.example` as
`/etc/systemd/system/patahao-backend.service`. Install the edited Nginx example
as `/etc/nginx/sites-available/patahao-api`, obtain the TLS certificate, and
enable the site. Validate both configurations before restarting:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now patahao-backend
sudo systemctl status patahao-backend --no-pager
sudo nginx -t
sudo systemctl reload nginx
```

## 5. External acceptance checks

From a different network, confirm:

```bash
curl --fail --silent --show-error https://api.staging.example.com/health/live/
curl --fail --silent --show-error https://api.staging.example.com/health/ready/
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' https://api.staging.example.com/media/mandates/test
```

The first two requests must return HTTP 200. The mandate-media probe must
return HTTP 404. Also complete password-recovery delivery, property-photo,
walkthrough-video, viewing-payment sandbox, refund/credit, and deal-outcome
tests before promoting a release.

The local media allowlist in the Nginx template is only a staging bridge.
Public production still requires durable public object storage/CDN and a
separate private document store.
