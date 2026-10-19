# Recruitment and office appointment reports

The staff workspace has Applications and Reports sections. Reports use the same
staff-view permission as the applicant list. CSV downloads additionally require
partners.change_partnerapplication. There are no schema changes or migrations.

Pipeline counts describe current application status for applications submitted in
the selected Kenya calendar-day range, including declined and withdrawn records.
County matching is case-insensitive and exact. County aggregation displays the top
50 county entries. These are current snapshots, not historical transition counts.

The office schedule filters by appointment date, independently of application
submission date. It excludes declined and withdrawn applications and supports
upcoming, past and all recorded appointments. Upcoming means appointment time is
at or after the generated report time. Past does not imply attended or missed.
Pages contain at most 20 records. An appointment row opens the applicant's existing
screening record for follow-up.

CSV summary downloads contain status counts. Schedule downloads contain reference,
name, county, operating area, current status and Kenya-local appointment time;
phone/email and private identity information are excluded. CSV values are escaped
to avoid spreadsheet formula execution. Downloads include generation time, filters
and date-basis metadata. Schedule downloads exceeding 10,000 rows are rejected with
a request to narrow filters instead of being silently truncated. Existing API
no-store and trusted-origin controls also apply to reports and exports.

## Validation

31 recruitment, staff portal and report tests pass with pinned dependencies.
Report tests cover access controls, view-only export denial, county/status counts,
Kenya midnight boundaries, inclusive end dates, separate application/appointment
dates, closed-record exclusion, pagination, CSV formula escaping and Kenya time.
Updated DOM tests cover report rendering, drill-down and sign-out data clearing.
Live authenticated browser validation remains with an authorized staff user.
