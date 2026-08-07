from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError
from partners.models import Partner

from .services import (
    enforce_partner_operational_access,
    get_partner_capacity_summary,
)

class MyPartnerCapacityView(APIView):
    """
    Return the authenticated partner's current tier and
    property-publication capacity.
    """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request):
        if request.user.is_staff:
            return Response(
                {
                    "detail": (
                        "Staff accounts do not have partner "
                        "listing capacity."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if getattr(request.user, "role", None) != "partner":
            return Response(
                {
                    "detail": (
                        "Only partner accounts may access "
                        "partner capacity."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        partner = getattr(
            request.user,
            "partner_profile",
            None,
        )

        if partner is None:
            return Response(
                {
                    "detail": (
                        "This account does not have a partner "
                        "profile."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            enforce_partner_operational_access(
            partner,
            operation="view_partner_capacity",
                    )
        except ValidationError as exc:
                    detail = getattr(
                        exc,
                        "message_dict",
                        None,
                    )

                    if detail is None:
                        detail = getattr(
                            exc,
                            "messages",
                            None,
                        )

                    if detail is None:
                        detail = str(exc)

                    return Response(
                        {
                            "detail": detail,
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

        capacity = get_partner_capacity_summary(
            partner,
        )

        return Response(
            capacity,
            status=status.HTTP_200_OK,
        )