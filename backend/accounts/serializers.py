from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.utils import get_md5_hash_password

from .models import User
from .services import find_active_user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone_number",
            "full_name",
            "role",
            "is_verified",
            "trust_score",
            "is_staff",
            "is_superuser",
        ]

        read_only_fields = [
            "id",
            "username",
            "email",
            "phone_number",
            "full_name",
            "role",
            "is_verified",
            "trust_score",
            "is_staff",
            "is_superuser",
        ]


class FlexibleTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        identifier = attrs.get(self.username_field, "")
        user = find_active_user(identifier)

        if user is not None:
            attrs[self.username_field] = user.get_username()

        return super().validate(attrs)


class PasswordAwareTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
        user = User.objects.filter(pk=user_id).first() if user_id else None

        if user is None or not api_settings.USER_AUTHENTICATION_RULE(user):
            raise AuthenticationFailed(
                "No active account was found for this session.",
                code="no_active_account",
            )

        if api_settings.CHECK_REVOKE_TOKEN:
            token_password_hash = refresh.payload.get(
                api_settings.REVOKE_TOKEN_CLAIM
            )
            if token_password_hash != get_md5_hash_password(user.password):
                raise AuthenticationFailed(
                    "This session ended because the account password changed.",
                    code="password_changed",
                )

        return super().validate(attrs)


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "phone_number",
            "full_name",
            "password",
            "password_confirm",
        ]

    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(
            email__iexact=value,
        ).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return value

    def validate_username(self, value):
        value = value.strip()

        if User.objects.filter(
            username__iexact=value,
        ).exists():
            raise serializers.ValidationError(
                "This username is already in use."
            )

        return value

    def validate_phone_number(self, value):
        if value is None:
            return value

        value = value.strip()

        if not value:
            return None

        if User.objects.filter(
            phone_number=value,
        ).exists():
            raise serializers.ValidationError(
                "An account with this phone number already exists."
            )

        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {
                    "password_confirm": (
                        "The passwords do not match."
                    )
                }
            )

        candidate_user = User(
            username=attrs.get("username", ""),
            email=attrs.get("email", ""),
            full_name=attrs.get("full_name", ""),
            role=User.ROLE_CUSTOMER,
        )

        try:
            validate_password(
                attrs["password"],
                user=candidate_user,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {"password": list(error.messages)}
            ) from error

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")

        password = validated_data.pop("password")

        user = User(
            **validated_data,
            role=User.ROLE_CUSTOMER,
        )

        user.set_password(password)
        user.save()

        return user

class CustomerPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "phone_number",
        ]

    def validate_phone_number(self, value):
        if value is None:
            raise serializers.ValidationError(
                "A phone number is required."
            )

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "A phone number is required."
            )

        existing_user = (
            User.objects
            .filter(phone_number=value)
            .exclude(pk=self.instance.pk)
            .exists()
        )

        if existing_user:
            raise serializers.ValidationError(
                "An account with this phone number already exists."
            )

        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        max_length=254,
        allow_blank=False,
        trim_whitespace=True,
    )


class PasswordResetConfirmSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        max_length=254,
        allow_blank=False,
        trim_whitespace=True,
    )
    code = serializers.RegexField(
        regex=r"^\d{8}$",
        error_messages={
            "invalid": "Enter the 8-digit reset code.",
        },
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {
                    "new_password_confirm": (
                        "The passwords do not match."
                    )
                }
            )

        return attrs
