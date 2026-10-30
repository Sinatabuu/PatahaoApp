# Staff operations watchdog — first release

This release is the reliable follow-up foundation for the planned operations agent. It uses deterministic database rules, not an LLM. No API key or AI-provider cost is required. It does not send messages, query Daraja, approve partners, credit payments, process refunds or change business records. AI summaries, approved reminder delivery, property review and conversational reports remain later stages.

## Staff use

Sign in at https://patahao.app/staff/. Authorized staff land on **Today’s priorities**. Opening that tab checks current records for managers; readers see the last completed scan. **Check current records** runs another scan. The last successful scan and an older-than-30-minutes warning are visible.

Each issue shows a reference, why it was flagged, the next action, a minimal live source record, owner, due time and history. Onboarding issues open the applicant or training record directly. Payment/viewing issues supply their IDs and references for the existing staff app workflows; this release does not create a new finance processing screen.

**I will follow up** assigns the current staff member and a 24-hour follow-up. **Defer** requires a future Kenya-time date within seven days. Due issues return to Needs decision on the next scan. Repeated scans do not duplicate issues. A scan closes an issue only when its trigger no longer applies; contacting someone never marks the underlying transaction successful. Recurrent conditions reopen the same issue with history retained. A source update can clear an inactivity trigger even though further human work remains; the rule starts counting from that new update.

## Initial rules

- Payment processing for at least 20 minutes, measured from initiated_at (updated_at fallback).
- Paid viewing awaiting partner response, with no update for at least two hours.
- Customer-requested refund/credit unprocessed for at least 24 hours.
- Open application without enrollment, with no update for at least 48 hours.
- Unactivated certified enrollment.
- Unactivated, non-withdrawn training record with no update for 24 hours after its last scheduled class has ended. This is a reminder only; it creates no time-based activation gate.

These are initial operational thresholds, not customer service promises. No class attendance or assessment becomes mandatory.

## Permissions

Existing staff portal login requires active staff with partners.view_partnerapplication. Add core.view_operationsissue to see the queue and core.change_operationsissue to manage follow-ups/run scans. Superusers already have them after migration.

Issue visibility ALSO requires the source permission: payments.view_payment, viewings.view_viewing, or partners.view_partnerapplication. Counts, lists, details and mutations all use those category checks. A recruiter cannot discover finance issues by guessing IDs. No phone, email, identity document, provider payload, callback token or password is copied into issues. Browser tokens remain in memory; responses are no-store and origin restricted. All changes use revision checks and append audit events.

## Deploy and run

1. Deploy backend main and apply migrations using `/app/.venv/bin/python manage.py migrate`.
2. Run `/app/.venv/bin/python manage.py scan_operations` once. It prints only the number of active issues.
3. Deploy the website and sign out/in to refresh staff permissions in the session.
4. For unattended monitoring, configure a separate Railway cron service from the SAME repository/main, root `/backend`, using the same Django environment and database through Railway variable references. Start command: `/app/.venv/bin/python manage.py scan_operations`. Schedule: `*/15 * * * *` (every 15 minutes, UTC); no public domain or health check. Use a terminating cron process, not a second Gunicorn service. Apply migrations on the web service before enabling cron. Never replace the web service's start command or schedule. Cron consumes Railway usage; monitor its runs and last-scan freshness. No cron service is provisioned by this code.

Until step 4 is configured, checks happen on manager portal entry/tab selection/manual scan, not continuously while staff are away. The scanner exits nonzero on failure and rolls back its entire scan; the last-success timestamp is not advanced on failure. Its singleton database row serializes overlapping PostgreSQL scans. Source business transactions can still change during a scan, so a flag is evidence to review, not an authoritative payment or activation decision.

## Verification

`PATAHAO_ENVIRONMENT=development python manage.py test core.test_operations partners.test_staff_portal`

New tests cover thresholds, repeat scans, due follow-ups, automatic closure, rollback on scan failure, finance visibility, unauthenticated/origin denial, stale writes, deferral limits, no arbitrary close, no financial writes, private payload exclusion, safe source projection and Kenya-time training follow-ups. The existing PostgreSQL CI workflow also runs these tests against PostgreSQL 16.

Website: install jsdom in an external temporary directory, then run `NODE_PATH=/path/to/node_modules node tests/operations.cjs` and the existing portal test scripts. Tests cover landing, read-only users, safe text rendering, double-click protection, conflict errors and clearing data on logout.
