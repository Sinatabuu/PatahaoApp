# Staff partner training

This increment adds office training and supervisor certification to the staff web portal. It does not create user accounts, activate partners or change operational permissions.

## Deployment order

1. Deploy the backend commit from main.
2. In the fresh Railway service terminal at `/app`, run `python manage.py migrate`.
3. Confirm partners migration `0006_trainingcohort_trainingenrollment_trainingevent_and_more` is applied with `python manage.py showmigrations partners`.
4. Deploy the matching website branch. Do not publish the Training tab before the migration is applied.

No mobile build is required for these staff web changes. Build 26 remains pending the separate activation workflow.

## Permissions

All portal access requires active staff status and `partners.view_partnerapplication`. Cohort creation, enrollment and training records additionally require `partners.change_partnerapplication`. Certification, reopening and withdrawal require `partners.certify_partner_training`. Superusers already have these permissions. Ordinary staff must be assigned the appropriate permissions by an authorized administrator; the portal never elevates its own users.

## Office workflow

1. Screen the application and set it to Staff screening or Invited to office.
2. Open Training and create a cohort with a trainer, location and 1–10 unique training dates. The initial proposal is three days. Each cohort has at most 12 active trainees.
3. Copy the applicant reference from Applications into the cohort enrollment form. An application has one training record; reopen that record rather than duplicate it.
4. At the office, check original identity documents and the signed agreement. Only confirmation flags are stored. Keep identity numbers, scans and detailed verification notes in the secure physical file.
5. Record each session as present, absent or make-up completed. Assess the eight practical modules as competent or needing further training, then save.
6. An authorized supervisor certifies only after every training date has occurred in Kenya, every attendance requirement is complete, both office checks are confirmed and all eight modules are competent.
7. Certification locks the training record. A supervisor can reopen it for reassessment; reopening resets the module assessments. Withdrawal releases a cohort place. Rejoining a full cohort is rejected.

The applicant status page displays training progress after reference and phone verification. Saving records does not send SMS or WhatsApp messages. Staff must contact applicants directly until messaging is implemented.

## Integrity and validation

Enrollment, record updates and decisions write audit events in the same transaction. Stale record versions return HTTP 409 and require a reload. Certification never marks a payment successful or grants partner field access.

Validation: 43 Django tests across recruitment, staff screening, reports and training; JavaScript syntax checks; DOM tests for existing portal behavior and the training save/certify/logout flow. Local Django tests use SQLite; deployment uses PostgreSQL, with explicit row locks for cohort capacity and training decisions.
