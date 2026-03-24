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

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        DEFAULT_FROM_EMAIL="from@example.com",
    )
    @patch("api.services.email_service.render_to_string", return_value="<html/>")
    @patch("api.services.email_service.EmailMessage")
    def test_send_invite_email_returns_true_when_notifications_enabled(
        self, mock_msg_cls, _render
    ):
        mock_msg = MagicMock()
        mock_msg_cls.return_value = mock_msg

        sent = EmailService.send_invite_email(
            MagicMock(),
            {"subject": "Join us", "recipients": ["a@b.com"]},
            {
                "project_owner": "owner",
                "project_name": "Proj",
                "invite_url": "http://invite",
            },
        )

        self.assertTrue(sent)
        mock_msg.send.assert_called_once()
