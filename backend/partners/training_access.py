from rest_framework import serializers


def enforce_onboarding_certification(partner):
    """Protect newly activated accounts without changing legacy partner access."""
    activation = getattr(partner, 'onboarding_activation', None)
    if activation and (activation.enrollment.state != 'certified' or
                       activation.enrollment.application.status in ('declined','withdrawn')):
        raise serializers.ValidationError('This partner’s onboarding approval is no longer valid. Contact staff.')
