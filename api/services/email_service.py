from __future__ import annotations
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
import requests
import os
import resend

class EmailService:

    def send_invite_email(request, email_metadata, project_metadata):
        # Allow disabling outbound emails in certain environments (e.g., local dev / tests)
        if not getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", True):
            return False

        html_content = render_to_string('emails/invite.html', {
            'project_owner': project_metadata.get("project_owner"),
            'project_name': project_metadata.get("project_name"),
            'url' : project_metadata.get("invite_url"),
        })

        params: resend.Emails.SendParams = {
            "from": "WorkQuest Notification <noreply@workquest.best>",
            "to": email_metadata.get("recipients"),
            "subject": email_metadata.get("subject"),
            "html": html_content,
        }
        email = resend.Emails.send(params)
        print(email)

        return True
