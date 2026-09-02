from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import ANY, patch

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from partners.models import Partner
from properties.models import Property

from .models import Viewing, ViewingEvent


User = get_user_model()


class ViewingCompletionDealHandoffTests(APITestCase):
    def setUp(self):
        self.partner_user = User.objects.create_user(
            username="viewing_handoff_partner",
            email="viewing-handoff-partner@example.com",
            password="TestPassword123!",
            role=User.ROLE_PARTNER,
        )

        self.customer = User.objects.create_user(
            username="viewing_handoff_customer",
            email="viewing-handoff-customer@example.com",
            password="TestPassword123!",
            role=User.ROLE_CUSTOMER,
        )

        self.partner = Partner.objects.create(
            user=self.partner_user,
            business_name="Viewing Handoff Partner",
            display_name="Viewing Handoff Partner",
            partner_type=Partner.PARTNER_TYPE_AGENT,
            verification_status=Partner.STATUS_APPROVED,
            is_active=True,
        )

        self.property = Property.objects.create(
            partner=self.partner,
            title="Repeat Viewing Sale Property",
            property_type=Property.TYPE_HOUSE,
            listing_type=Property.LISTING_SALE,
            price=Decimal("8500000.00"),
            county="Nairobi",
            town="Roysambu",
            estate="Garden Estate",
            address="Repeat Viewing Test Address",
            bedrooms=4,
            bathrooms=3,
            description="Property used to test repeat viewing completion.",
            status=Property.STATUS_DRAFT,
        )

        self.viewing = Viewing.objects.create(
            customer=self.customer,
            property=self.property,
            assigned_partner=self.partner,
            requested_date=date(2027, 1, 20),
            requested_time=time(10, 30),
            confirmed_date=date(2027, 1, 20),
            confirmed_time=time(10, 30),
            payment_reference="TEST-PAID-VIEWING-001",
            status=Viewing.Status.CONFIRMED,
        )

    def test_completion_uses_pic_returned_by_certificate_service(self):
        reused_introduction = SimpleNamespace(
            id=101,
            certificate_number="PH-PIC-EXISTING",
            status="converted_to_deal",
            protected_from=None,
            protected_until=None,
            protection_period_days=90,
        )

        reused_deal = SimpleNamespace(
            id=201,
            deal_number="PH-DEAL-EXISTING",
            status="draft",
            deal_type="sale",
            customer_id=self.customer.id,
            partner_id=self.partner.id,
            property_id=self.property.id,
            commission_amount=Decimal("255000.00"),
        )

        self.client.force_authenticate(
            user=self.partner_user,
        )

        with patch(
            "viewings.views.create_property_introduction_certificate",
            return_value=(
                reused_introduction,
                False,
            ),
        ) as create_certificate:
            with patch(
                "viewings.views.create_deal_from_pic",
                return_value=(
                    reused_deal,
                    False,
                ),
                create=True,
            ) as create_from_pic:
                response = self.client.post(
                    reverse(
                        "viewing-complete-viewing",
                        kwargs={
                            "pk": self.viewing.pk,
                        },
                    ),
                    {
                        "completion_notes": (
                            "Customer completed a repeat viewing."
                        ),
                    },
                    format="json",
                )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        create_certificate.assert_called_once_with(
            viewing=ANY,
            actor=self.partner_user,
        )

        create_from_pic.assert_called_once_with(
            introduction=reused_introduction,
            actor=self.partner_user,
        )

        self.viewing.refresh_from_db()

        self.assertEqual(
            self.viewing.status,
            Viewing.Status.COMPLETED,
        )

        self.assertEqual(
            self.viewing.events.filter(
                event_type=(
                    ViewingEvent.EventType.VIEWING_COMPLETED
                ),
            ).count(),
            1,
        )
