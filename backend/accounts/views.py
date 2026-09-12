from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    CustomerPhoneSerializer,
    CustomerRegistrationSerializer,
    FlexibleTokenObtainPairSerializer,
    PasswordAwareTokenRefreshSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSerializer,
)
from .services import (
    INVALID_RESET_CODE_MESSAGE,
    PASSWORD_RESET_RESPONSE,
    InvalidPasswordResetCode,
    issue_password_reset_code,
    reset_password_with_code,
)


class FlexibleTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = FlexibleTokenObtainPairSerializer


class PasswordAwareTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    serializer_class = PasswordAwareTokenRefreshSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = CustomerPhoneSerializer(
            request.user,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "Phone number updated successfully.",
                "user": UserSerializer(request.user).data,
            },
            status=status.HTTP_200_OK,
        )


class CustomerRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CustomerRegistrationSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            {
                "message": "Customer account created successfully.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_request"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        issue_password_reset_code(
            identifier=serializer.validated_data["identifier"],
            request_ip=request.META.get("REMOTE_ADDR"),
        )

        return Response(
            {"message": PASSWORD_RESET_RESPONSE},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_confirm"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            reset_password_with_code(
                identifier=serializer.validated_data["identifier"],
                code=serializer.validated_data["code"],
                new_password=serializer.validated_data["new_password"],
            )
        except InvalidPasswordResetCode as error:
            raise ValidationError(
                {"code": [INVALID_RESET_CODE_MESSAGE]}
            ) from error
        except DjangoValidationError as error:
            raise ValidationError(
                {"new_password": list(error.messages)}
            ) from error

        return Response(
            {
                "message": (
                    "Your password has been changed. You can now sign in."
                )
            },
            status=status.HTTP_200_OK,
        )
