# Partner recruitment first increment

The public website and app links share https://patahao.app/become-a-partner/.
Applications create PartnerApplication records only. They never create or activate
User or Partner accounts. Existing partner permissions are unchanged in this
increment; training, certification and their operational enforcement are the next
increment and must be completed before independent field onboarding is launched.

## Deploy in order

1. Merge the backend changes and deploy Railway.
2. In the Railway container run `python manage.py migrate`.
3. Staff with PartnerApplication permissions can screen applications under
   Django admin > Partners > Partner applications. Set screening status and an
   office appointment after contacting the applicant. Admin edits use Django's
   existing change log. Application reference is also the paper folder reference.
4. Deploy `patahao-website` after backend migration. Cloudflare serves `public/`.
5. Run `flutter pub get`, `flutter analyze`, and `flutter test`, then build the
   mobile app. This does not change the separate Google Play release branch.
6. Submit a clearly labelled test application on the deployed website, check the
   same reference in Django admin, then check its status on the public page.

Only https://patahao.app and https://www.patahao.app receive CORS access. Optional
PARTNER_APPLICATION_ORIGINS Django setting can allow a controlled preview origin.
No credentialed browser requests or customer login are required. Status lookup
requires the unguessable reference plus the submitted phone number and returns
no applicant contact details. Recruitment endpoints use 20 requests/hour per IP;
configure a shared Django cache before scaling to multiple worker processes or
replicas. Configure DRF's NUM_PROXIES to match trusted deployment infrastructure
before relying on forwarded IP throttling. Rate limits are abuse reduction, not
an authorization control.

No identity numbers, document uploads, reference documents or free-text private
verification notes are collected. Consent is required and its notice version and
submission time are stored. Agree on physical/digital retention procedures and
staff responsibilities before accepting real applicants. Email/SMS notifications,
cohort training, certification and partner activation are not implemented here.

## Verification

Ten focused recruitment tests pass using the repository's pinned dependencies
including Django 6.0.6. They cover validation, consent, retries, no account
creation, status privacy, origin restrictions, CSRF-free anonymous submissions,
rate limit CORS responses, and ignored activation fields. JavaScript syntax
checks pass. Browser visual QA is unavailable in this environment.

Flutter validation and dependency lock refresh remain pending. Automatic approval
review blocked SDK setup after it attempted cloud instance metadata access. No
workaround was attempted. Run mobile validation in the developer's trusted Flutter
environment before merging or distributing the mobile change.
