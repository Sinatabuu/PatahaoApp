import uuid
from django.db import models

MODULES = (
    ('ethics', 'Mission, ethics and partner responsibilities'),
    ('authorization', 'Property sourcing and owner authorization'),
    ('app', 'Using the partner application'),
    ('media', 'Property photography, video and accurate descriptions'),
    ('viewings', 'Customer service and viewing coordination'),
    ('payments', 'Viewing payments, refunds and credits'),
    ('deals', 'Rental and sale transactions'),
    ('safety', 'Customer safety, privacy and fraud prevention'),
)


def cohort_reference():
    return 'PH-COHORT-' + uuid.uuid4().hex[:12].upper()


class TrainingCohort(models.Model):
    reference = models.CharField(max_length=30, unique=True, default=cohort_reference, editable=False)
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=150)
    trainer_name = models.CharField(max_length=100)
    created_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='created_training_cohorts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']


class TrainingSession(models.Model):
    cohort = models.ForeignKey(TrainingCohort, on_delete=models.PROTECT, related_name='sessions')
    date = models.DateField()

    class Meta:
        ordering = ['date', 'pk']
        constraints = [models.UniqueConstraint(fields=['cohort', 'date'], name='unique_cohort_training_date')]


class TrainingEnrollment(models.Model):
    class State(models.TextChoices):
        ENROLLED = 'enrolled', 'In training'
        CERTIFIED = 'certified', 'Training certified — activation pending'
        WITHDRAWN = 'withdrawn', 'Training withdrawn'

    application = models.OneToOneField('partners.PartnerApplication', on_delete=models.PROTECT, related_name='training_enrollment')
    cohort = models.ForeignKey(TrainingCohort, on_delete=models.PROTECT, related_name='enrollments')
    state = models.CharField(max_length=20, choices=State.choices, default=State.ENROLLED)
    identity_checked = models.BooleanField(default=False)
    agreement_signed = models.BooleanField(default=False)
    certified_by = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.PROTECT, related_name='certified_trainees')
    certified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['application__full_name', 'pk']
        permissions = [('certify_partner_training', 'Can certify or reopen partner training')]


class TrainingAttendance(models.Model):
    enrollment = models.ForeignKey(TrainingEnrollment, on_delete=models.PROTECT, related_name='attendance')
    session = models.ForeignKey(TrainingSession, on_delete=models.PROTECT)
    result = models.CharField(max_length=20, choices=[('pending', 'Not recorded'), ('present', 'Present'), ('absent', 'Absent'), ('makeup', 'Make-up completed')], default='pending')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['enrollment', 'session'], name='unique_trainee_session_attendance')]
        ordering = ['session__date', 'pk']


class TrainingAssessment(models.Model):
    enrollment = models.ForeignKey(TrainingEnrollment, on_delete=models.PROTECT, related_name='assessments')
    module = models.CharField(max_length=30, choices=MODULES)
    result = models.CharField(max_length=20, choices=[('pending', 'Not assessed'), ('pass', 'Competent'), ('retrain', 'Further training required')], default='pending')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['enrollment', 'module'], name='unique_trainee_module_assessment')]
        ordering = ['pk']


class TrainingEvent(models.Model):
    cohort = models.ForeignKey(TrainingCohort, on_delete=models.PROTECT, related_name='events')
    enrollment = models.ForeignKey(TrainingEnrollment, null=True, blank=True, on_delete=models.PROTECT, related_name='events')
    actor = models.ForeignKey('accounts.User', on_delete=models.PROTECT)
    action = models.CharField(max_length=30)
    record = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError('Training history cannot be edited.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Training history cannot be deleted.')
