import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from .models import PasswordResetChallenge, User


logger = logging.getLogger(__name__)

PASSWORD_RESET_RESPONSE = (
    "If the account exists, a password reset code has been sent to its email."
)
INVALID_RESET_CODE_MESSAGE = "The reset code is invalid or expired."


class InvalidPasswordResetCode(Exception):
    pass


def find_active_user(identifier):
    normalized = str(identifier or "").strip()
    if not normalized:
        return None

    users = User.objects.filter(is_active=True)

    if "@" in normalized:
        return users.filter(email__iexact=normalized).first()

    user = users.filter(username__iexact=normalized).first()
    if user is not None:
        return user

    user = users.filter(phone_number=normalized).first()
    if user is not None:
        return user

    return users.filter(email__iexact=normalized).first()


def _code_digest(user_id, code):
    return salted_hmac(
        "patahao.accounts.password-reset",
        f"{user_id}:{code}",
    ).hexdigest()


def issue_password_reset_code(*, identifier, request_ip=None):
    user = find_active_user(identifier)
    if user is None:
        # Perform comparable local work while keeping the response generic.
        _code_digest(0, secrets.token_hex(4))
        return

    now = timezone.now()
    code = f"{secrets.randbelow(100_000_000):08d}"

    with transaction.atomic():
        PasswordResetChallenge.objects.filter(
            user=user,
            used_at__isnull=True,
        ).update(used_at=now)

        challenge = PasswordResetChallenge.objects.create(
            user=user,
            code_digest=_code_digest(user.pk, code),
            request_ip=request_ip,
            expires_at=now
            + timedelta(minutes=settings.PASSWORD_RESET_CODE_TTL_MINUTES),
        )

    message = (
        f"Hello {user.full_name or user.username},\n\n"
        f"Your Pata HAO password reset code is: {code}\n\n"
        f"It expires in {settings.PASSWORD_RESET_CODE_TTL_MINUTES} minutes. "
        "Use it only inside the Pata HAO app. Pata HAO staff will never ask "
        "you for this code.\n\n"
        f"Your sign-in username is: {user.username}\n\n"
        "If you did not request this reset, you can ignore this message."
    )

    try:
        sent_count = send_mail(
            subject="Your Pata HAO password reset code",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        if sent_count != 1:
            raise RuntimeError("The email backend did not accept the message.")
    except Exception:
        PasswordResetChallenge.objects.filter(pk=challenge.pk).update(
            used_at=timezone.now(),
        )
        logger.exception(
            "Unable to deliver a password reset code for user %s.",
            user.pk,
        )


def reset_password_with_code(*, identifier, code, new_password):
    user = find_active_user(identifier)
    if user is None:
        _code_digest(0, str(code or ""))
        raise InvalidPasswordResetCode(INVALID_RESET_CODE_MESSAGE)

    now = timezone.now()
    invalid_code = False

    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        challenge = (
            PasswordResetChallenge.objects.select_for_update()
            .filter(user=user, used_at__isnull=True)
            .order_by("-created_at")
            .first()
        )

        if challenge is None:
            invalid_code = True
        else:
            max_attempts = settings.PASSWORD_RESET_MAX_ATTEMPTS
            if (
                challenge.expires_at <= now
                or challenge.failed_attempts >= max_attempts
            ):
                challenge.used_at = now
                challenge.save(update_fields=("used_at",))
                invalid_code = True
            else:
                supplied_digest = _code_digest(
                    user.pk,
                    str(code or "").strip(),
                )
                if not constant_time_compare(
                    challenge.code_digest,
                    supplied_digest,
                ):
                    challenge.failed_attempts += 1
                    update_fields = ["failed_attempts"]
                    if challenge.failed_attempts >= max_attempts:
                        challenge.used_at = now
                        update_fields.append("used_at")
                    challenge.save(update_fields=update_fields)
                    invalid_code = True

        if not invalid_code:
            validate_password(new_password, user=user)

            user.set_password(new_password)
            user.is_email_verified = True
            user.save(update_fields=("password", "is_email_verified"))

            challenge.used_at = now
            challenge.save(update_fields=("used_at",))
            PasswordResetChallenge.objects.filter(
                user=user,
                used_at__isnull=True,
            ).exclude(pk=challenge.pk).update(used_at=now)

    if invalid_code:
        raise InvalidPasswordResetCode(INVALID_RESET_CODE_MESSAGE)

    return user
