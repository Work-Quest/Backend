from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from api.services.email_service import EmailService


class EmailServiceTest(SimpleTestCase):
    @override_settings(EMAIL_NOTIFICATIONS_ENABLED=False)
    def test_send_invite_email_short_circuits_when_disabled(self):
        sent = EmailService.send_invite_email(
            MagicMock(),
            {"subject": "s", "recipients": ["a@b.com"]},
            {"project_owner": "o", "project_name": "p", "invite_url": "http://x"},
        )
        self.assertFalse(sent)
