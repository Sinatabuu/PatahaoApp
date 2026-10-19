# Staff partner training

The staff web portal supports office training, supervisor certification and activation of certified applicants into their existing app accounts. Applicants create their own app credentials; staff do not create passwords.

## Deployment order

1. Deploy the backend commit from main.
2. In the fresh Railway service terminal at `/app`, run `python manage.py migrate`.
3. Confirm partners migration `0010_partneractivation` is applied with `python manage.py showmigrations partners`.
4. Deploy the matching website branch. Do not publish the Training tab before the migration is applied.

No mobile build is required for these staff web changes. Build 26 remains on hold until the deployed activation flow and mobile partner access are verified.

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

## Applicant session selection

The public partner form now loads available morning/afternoon classes via `GET /api/partner-applications/sessions/` and submits to `POST /api/partner-applications/reserve/`. The applicant chooses the exact session; this flow never silently moves them to another class. It reserves their place, creates attendance and assessment records and sets the office appointment in one transaction. Staff still review the application; booking never grants partner access. Full or started sessions are excluded from availability and checked again under the shared cohort lock on submission.

The existing application-only endpoint is retained for older clients. Existing applications and enrollment records are unchanged. New public reservations require a session. Repeated identical submissions with the same random submission key return the same reference and booking, including after a class fills or starts. A conflicting retry or full session returns 409. No partial application survives a failed reservation. Booking events have no staff actor and display as Applicant self-booking; migration 0008 makes the audit actor nullable for that purpose.

The web page confirms the PH-APP reference, date, Kenya time and location on screen. SMS and WhatsApp delivery remain separate work. If no sessions are available, submission is disabled and applicants are directed to check again or contact support. Contact details remain in the form after a booking conflict. Only the random submission key is retained in session storage.

Validation for this release: 60 backend tests and four DOM suites, including public availability, reservation capacity, retries, privacy, CORS, audit rollback, full-session recovery and no-session behavior. Capacity tests run locally on SQLite; PostgreSQL concurrency is protected by the shared cohort row lock but has not been load-tested here.

## No-cash acknowledgement and office correction

The partner page prominently prohibits all cash transactions with customers and property owners, states immediate termination of the partnership for violations, and requires an explicit no-cash acknowledgement. Both application endpoints validate the acknowledgement server-side. New applications record `recruitment-nocash-2026-10` in the existing consent version field. Existing applicants are not retroactively marked as accepting the new notice.

Migration 0009 changes only training cohort locations equal to `nai` (case-insensitive) to `Nairobi`, as requested by the project owner. Existing booking references, training dates, capacity and results remain intact. The next date inherits the corrected location through the existing defaults mechanism. Apply the migration after backend deployment, then publish the matching website.

## Certified partner activation

Migration 0010 adds an immutable activation record linking one training enrollment to one partner profile, with the staff actor, timestamp and confirmed no-cash policy version. Only active staff with `partners.view_partnerapplication` and the separate `partners.activate_trained_partner` permission can prepare or perform activation. Superusers have the permission automatically; other staff need it assigned during account setup.

In Training, open the certified trainee. The activation section finds an existing active, non-staff app account by normalized Kenyan phone number. It blocks missing or ambiguous accounts, admin accounts, accounts already assigned a partner role and all existing partner profiles, including suspended profiles. The applicant must create their own app account using their application phone number before activation. Staff do not create passwords or elevate staff accounts here.

Staff confirm account ownership and the no-cash policy at the office, then select Activate partner. Certification, attendance, eight competent assessments, original-document verification, signed agreement, current application status and the record version are checked again under transaction locks. The existing user becomes a partner; a new approved active Partner profile and public partner code are created. Passwords, verified-contact flags, payments and customer history are preserved. No commission plan or payout is assigned by this action.

Role change, profile creation, activation record and audit event commit together. A retry returns the existing activation and never reactivates a subsequently suspended profile. Activation blocks ordinary training reopening/withdrawal and application closure; use the existing partner disciplinary management flow for suspension or termination.

The partner signs out and signs in again in the mobile app to load their current role. Property posting uses the existing private partner endpoint and creates drafts. It does not publish listings or bypass owner authorization, media checks, mandates or property verification. The public property endpoint now restricts generic create/update/delete actions to staff so an authenticated customer cannot bypass the partner admission path. Private property and media access also enforce central governance restrictions. Newly activated partners require valid onboarding certification through that shared guard; legacy partners are not forced through a retrospective certification process.

The applicant tracking page shows activation without exposing their app username or internal account ID. This increment sends no account messages and does not upload build 26.

Activation validation: all 544 backend tests pass after collecting local static assets. The full regression run uses SQLite and a temporary test-only fast password hasher; production password settings are unchanged. A focused account-to-property-draft test also passes with the normal configured password hasher. All five website DOM suites pass, including activation success, missing account guidance, permission visibility, office confirmations, locked activated records and logout clearing. No PostgreSQL concurrency load test was run; activation uses row locks and one-to-one database constraints to serialize admissions.

## Staff sign-in throttling correction

Browser OPTIONS requests no longer consume login limits. A POST-only volume cap permits 60 requests per minute per source. A separate failed-login limit allows ten failures per normalized account identifier and source in a rolling 15-minute window; successful sign-ins do not consume that failure budget. Throttle keys hash the identifier and source. Blocked POST responses retain CORS headers and Retry-After so the portal can show the readable throttling message instead of failing its preflight. Login connection errors now use sign-in-specific wording rather than the warning about an uncertain applicant save.

Validation: 17 focused staff portal and throttle tests pass, including repeated successful sign-ins, preflight exemption, failed-login blocking, identifier isolation, expiry and POST volume control. No database migration is required.
