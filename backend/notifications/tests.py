from django.test import SimpleTestCase

from .models import Notification
from .serializers import NotificationSerializer


class NotificationSerializerTests(SimpleTestCase):
    def test_exposes_direct_viewing_action_metadata(self):
        notification = Notification(
            id=71,
            user_id=2,
            viewing_id=41,
            title="Action required: viewing time changed",
            message="Review the revised viewing time.",
            notification_type=Notification.TYPE_VIEWING,
            action_label="Review new viewing time",
            requires_action=True,
            is_read=False,
        )

        data = NotificationSerializer(notification).data

        self.assertEqual(data["viewing"], 41)
        self.assertEqual(data["notification_type_label"], "Viewing")
        self.assertEqual(data["action_label"], "Review new viewing time")
        self.assertTrue(data["requires_action"])
        self.assertFalse(data["is_read"])
