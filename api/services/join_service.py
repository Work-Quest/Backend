from __future__ import annotations

import uuid
import secrets
from datetime import timedelta
from typing import Iterable, Optional, Sequence

from django.db import IntegrityError, models, transaction
from django.utils import timezone

from api.models.ProjectInviteToken import ProjectInviteToken
from api.models.Project import Project as ProjectModel
from api.services.email_service import EmailService


class JoinService:
    """
    Join/invite related operations.

    This file currently only drafts invite-token + email sending skeleton.
    """

    @staticmethod
    def _normalize_emails(emails):
        return sorted({(e or "").strip().lower() for e in emails if (e or "").strip()})

    @staticmethod
    def _build_invite_url(invite_base_url, token):

        if not invite_base_url:
            return None
        return f"{invite_base_url}/join?token={token}"

    @transaction.atomic
    def invite_players(
        self,
        request,
        project_id,
        emails,
        invite_base_url = None,
        expires_in = timedelta(days=2)
    ):
        normalized_emails = self._normalize_emails(emails)
        if not normalized_emails:
            return {"error": "No valid recipient emails provided."}

        project = ProjectModel.objects.get(project_id=project_id)
        now = timezone.now()
        expires_at = now + expires_in

    
        failed = []
        created = []

        for email in normalized_emails:
            # Generate & persist a unique token (retry on rare collisions)
            invite_row = None
            for _ in range(5):
                token = secrets.token_urlsafe(32)  # ~43 chars, safe for URLs
                try:
                    invite_row = ProjectInviteToken.objects.create(
                        project=project,
                        email=email,
                        token=token,
                        expired_at=expires_at,
                        accepted_at=None,
                    )
                    break
                except IntegrityError:
                    invite_row = None
                    continue

            if invite_row is None:
                failed.append({"email": email, "error": "Failed to generate unique token."})
                continue

            # Send email via EmailService (template currently uses owner/name only)
            project_owner = (
                getattr(project.owner, "name", None)
                or getattr(project.owner, "full_name", None)
                or str(project.owner)
            )
            project_metadata = {
                "project_owner": project_owner,
                "project_name": project.project_name,
                # Optional metadata for future template wiring:
                "invite_token": invite_row.token,
                "invite_url": self._build_invite_url(invite_base_url, invite_row.token),
                "expires_at": invite_row.expired_at,
            }
            email_metadata = {
                "subject": "WorkQuest: You have been invited to party!",
                "recipients": [email],
            }

            try:
                EmailService.send_invite_email(
                    request=request,
                    email_metadata=email_metadata,
                    project_metadata=project_metadata,
                )
                created.append(invite_row)
            except Exception as e:
                # Keep token row for audit/debug; you can decide later to delete on failure.
                failed.append({"email": email, "error": str(e)})

        return {
            "project_id": str(project.project_id),
            "invited": [{"email": r.email, "token": r.token, "expired_at": r.expired_at} for r in created],
            "failed": failed,
        }