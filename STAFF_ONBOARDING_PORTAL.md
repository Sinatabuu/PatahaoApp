# Staff onboarding portal

Daily screening work takes place at https://patahao.app/staff/, not Django admin.

## Deployment

1. Deploy the backend changes, then run `python manage.py migrate` in the new
   Railway container. Migration partners.0005_partnerapplicationevent adds only
   the screening history table.
2. Deploy the matching `patahao-website` changes.
3. Sign in on the portal using an existing authorized staff account. Superusers
   have access. Other staff need `partners.view_partnerapplication` to read and
   `partners.change_partnerapplication` to save screening changes. An account
   must also be active and have `is_staff=True`. Initial staff permissions remain
   an administrator responsibility; the public page cannot create staff accounts.
4. Find the existing test application, update its screening status or appointment,
   and confirm both the portal history and public application progress.

## Behavior

Search by name, reference, phone, area or county; filter by application status.
Select an application to see contact details, availability, screening history,
and office appointment. Office appointment input and output use Africa/Nairobi
(Kenya, UTC+03:00), regardless of the staff member's browser timezone.

Changes require a selected action and the application's current updated_at value.
Stale edits return HTTP 409 instead of silently overwriting another staff member.
The application update and audit event commit together. Screening event rows
record staff actor, timestamp, action, prior/new status and appointment. The
portal exposes no event-edit or event-delete operation. Existing Django admin
history is not imported into the new portal history.

The staff API checks permissions on every request. Sign-in issues an access token
for twenty minutes without a refresh token. The page keeps it in memory only;
reload requires sign-in, and fifteen minutes of inactivity signs the user out.
Logout clears displayed applicant information and search terms. It discards the
browser token; it does not revoke an already copied JWT before its expiry.
Password changes or staff permission removal invalidate subsequent access.
API responses set Cache-Control: no-store and use explicit trusted-origin CORS.
Login attempts are throttled by IP using the configured Django cache; a shared
cache is required for a global limit across workers/replicas.

No identity-document upload, unrestricted private notes, account activation,
email/SMS notification, cohort training or certification is included. Staff
contact applicants directly. No partner permission is granted by screening.

## Validation

22 recruitment/staff tests pass with the repository's pinned dependencies.
They cover anonymous/customer denial, read-only staff, sign-in, permission
removal, origin restrictions, invitation validation, Kenya timestamps, stale
edits, immutable event instance methods, and rollback when audit writing fails.
Website DOM tests cover login, applicant rendering, XSS-safe names, saving Kenya
appointments and clearing data on sign-out. Browser visual QA is unavailable in
the managed workspace; live layout and interaction need user review.
