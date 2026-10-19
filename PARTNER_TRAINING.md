# Staff partner training

This increment adds office training and supervisor certification to the staff web portal. It does not create user accounts, activate partners or change operational permissions.

## Deployment order

1. Deploy the backend commit from main.
2. In the fresh Railway service terminal at `/app`, run `python manage.py migrate`.
3. Confirm partners migration `0007_trainingcohort_scheduled_date_trainingcohort_slot_and_more` is applied with `python manage.py showmigrations partners`.
4. Deploy the matching website branch. Do not publish the Training tab before the migration is applied.

No mobile build is required for these staff web changes. Build 26 remains pending the separate activation workflow.

## Permissions

All portal access requires active staff status and `partners.view_partnerapplication`. Cohort creation, enrollment and training records additionally require `partners.change_partnerapplication`. Certification, reopening and withdrawal require `partners.certify_partner_training`. Superusers already have these permissions. Ordinary staff must be assigned the appropriate permissions by an authorized administrator; the portal never elevates its own users.

## Office workflow

1. Open Training and choose **Open a training date**. The system creates the 9 a.m.–noon and 2–5 p.m. classes in Kenya time. Set the office location once; the trainer starts with the signed-in staff name. Both settings are reused for later dates and can be changed before opening a date.
2. Open an applicant in Applications, choose the preferred date and select **Schedule training**. This staff decision sets the application to invited, records the assigned appointment and enrolls the existing PH-APP reference without copying it.
3. Classes fill chronologically: 12 morning places, then 12 afternoon places, then the next date staff have explicitly opened. A class that has started is skipped. Full classes cannot receive a thirteenth active trainee. If all available dates are full, nothing is changed; staff must open another date. Existing training records are retained and duplicate enrollment is rejected.
4. At the office, check original identity documents and the signed agreement. Only confirmation flags are stored. Keep identity numbers, scans and detailed verification notes in the secure physical file.
5. Record each session as present, absent or make-up completed. Assess the eight practical modules as competent or needing further training, then save.
6. An authorized supervisor certifies only after every training date has occurred in Kenya (scheduled morning/afternoon classes must also have finished), every attendance requirement is complete, both office checks are confirmed and all eight modules are competent.
7. Certification locks the training record. A supervisor can reopen it for reassessment; reopening resets the module assessments. Withdrawal releases a cohort place. Rejoining a full cohort is rejected.

The applicant status page displays training progress after reference and phone verification. Saving records does not send SMS or WhatsApp messages. Staff must contact applicants directly until messaging is implemented.

## Integrity and validation

Enrollment, record updates and decisions write audit events in the same transaction. Stale record versions return HTTP 409 and require a reload. Certification never marks a payment successful or grants partner field access.

Validation: 52 Django tests across recruitment, staff screening, reports and training allocation; JavaScript syntax checks; DOM tests for existing portal behavior and training save/certify/logout and date opening/allocation flows. Local Django tests use SQLite; deployment uses PostgreSQL, with explicit row locks for cohort capacity and training decisions.

## Automatic scheduling release

Migration 0007 adds nullable scheduling metadata to existing cohorts and a unique date/slot constraint. Legacy cohorts and their attendance and assessment records remain intact. The new UI opens dates instead of manually named cohorts and removes the reference-copy enrollment form. The legacy API remains for compatibility with already deployed staff pages; its cohort capacity lock remains enforced. Automated scheduling locks candidate cohorts in date/slot order, then the applicant, and records enrollment, appointment and audit events atomically. It never creates dates that staff have not opened.
