from rest_framework import serializers
from .models import User


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


class CustomerRegistrationSerializer(serializers.ModelSerializer):
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