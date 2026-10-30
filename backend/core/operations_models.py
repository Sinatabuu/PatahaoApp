from django.conf import settings
from django.db import models


class OperationsIssue(models.Model):
    key = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20)
    rule = models.CharField(max_length=40)
    source_id = models.PositiveBigIntegerField()
    reference = models.CharField(max_length=100)
    title = models.CharField(max_length=160)
    reason = models.TextField()
    next_action = models.TextField()
    priority = models.PositiveSmallIntegerField(default=2)
    state = models.CharField(max_length=15, default='open', choices=[('open', 'Needs decision'), ('following', 'Following up'), ('snoozed', 'Deferred'), ('resolved', 'Resolved')])
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    follow_up_at = models.DateTimeField(null=True, blank=True)
    first_detected_at = models.DateTimeField(auto_now_add=True)
    last_detected_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'first_detected_at', 'pk']
        indexes = [models.Index(fields=['category', 'state'], name='ops_category_state_idx')]


class OperationsEvent(models.Model):
    issue = models.ForeignKey(OperationsIssue, on_delete=models.PROTECT, related_name='events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=30)
    record = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-pk']

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError('Operations history cannot be edited.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Operations history cannot be deleted.')


class OperationsScan(models.Model):
    completed_at = models.DateTimeField(null=True)
