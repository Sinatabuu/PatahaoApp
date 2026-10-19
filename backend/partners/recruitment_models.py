import uuid

from django.db import models


def application_reference():
    return 'PH-APP-' + uuid.uuid4().hex.upper()


class PartnerApplication(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Application received'
        SCREENING = 'screening', 'Staff screening'
        INVITED = 'invited', 'Invited to office'
        WITHDRAWN = 'withdrawn', 'Withdrawn'
        DECLINED = 'declined', 'Not proceeding'

    id = models.BigAutoField(primary_key=True)
    reference = models.CharField(max_length=40, unique=True, default=application_reference, editable=False)
    submission_key = models.UUIDField(unique=True, editable=False)
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=12)
    email = models.EmailField(blank=True)
    county = models.CharField(max_length=100)
    operating_area = models.CharField(max_length=150)
    partner_type = models.CharField(max_length=20, choices=[('agent', 'Agent'), ('agency', 'Agency'), ('owner', 'Property owner'), ('developer', 'Developer'), ('new', 'New to property work')])
    experience = models.CharField(max_length=20, choices=[('new', 'No previous experience'), ('under_two', 'Less than two years'), ('two_plus', 'Two years or more')])
    training_availability = models.CharField(max_length=20, choices=[('weekdays', 'Weekdays'), ('weekends', 'Weekends'), ('flexible', 'Flexible')])
    consent_version = models.CharField(max_length=30, default='recruitment-2026-10', editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    office_appointment = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} — {self.full_name}'
