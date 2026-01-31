from __future__ import annotations
from django.template.loader import render_to_string
from django.core.mail import EmailMessage


class EmailService:

    def send_invite_email(request, email_metadata, project_metadata):

        html_content = render_to_string('emails/invite.html', {
            'project_owner': project_metadata.get("project_owner"),
            'project_name': project_metadata.get("project_name"),
            'url' : project_metadata.get("invite_url"),
        })
        message = EmailMessage(
                subject=email_metadata.get("subject"),
                body=html_content,
                from_email="WorkQuesr Notification <onboarding@resend.dev>",
                to=email_metadata.get("recipients"),
            )
        message.content_subtype = "html"
        message.send()


        return True