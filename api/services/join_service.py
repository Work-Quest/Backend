from __future__ import annotations

import uuid
import secrets
from datetime import timedelta
from typing import Iterable, Optional, Sequence

from django.db import IntegrityError, models, transaction
from django.utils import timezone

from api.domains.project import Project as ProjectDomain
from api.models.BusinessUser import BusinessUser
from api.models.ProjectInviteToken import ProjectInviteToken
from api.models.Project import Project as ProjectModel
from api.models.ProjectMember import ProjectMember
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
    
    @transaction.atomic
    def accept_invite(self, token, user: BusinessUser | None = None):
        token = (token or "").strip()
        if not token:
            return {"error": "Invite token is required."}

        now = timezone.now()

        try:
            invite = (
                ProjectInviteToken.objects.select_for_update()
                .select_related("project")
                .get(token=token)
            )
        except ProjectInviteToken.DoesNotExist:
            return {"error": "Invalid invite token."}

        if invite.accepted_at is not None:
            return {"error": "Invite token has already been used."}

        if invite.expired_at and invite.expired_at < now:
            return {"error": "Invite token has expired."}

        if user is None:
            try:
                user = BusinessUser.objects.get(email__iexact=invite.email)
            except BusinessUser.DoesNotExist:
                return {"error": "No user found for the invited email."}
        else:
            if (user.email or "").strip().lower() != (invite.email or "").strip().lower():
                return {"error": "This invite token does not belong to the authenticated user."}

        project = invite.project

        # If already a member, still mark the invite as accepted so it can't be reused.
        if ProjectMember.objects.filter(user=user, project=project).exists():
            invite.accepted_at = now
            invite.save(update_fields=["accepted_at"])
            return {
                "message": "User is already a member of the project.",
                "project_id": str(project.project_id),
                "project_name": project.project_name,
            }

        domain = ProjectDomain(project)
        member_domain = domain._project_member_management.add_member(user)

        invite.accepted_at = now
        invite.save(update_fields=["accepted_at"])

        return {
            "message": "Invite accepted.",
            "project_id": str(project.project_id),
            "project_name": project.project_name,
            "project_member_id": str(member_domain.project_member_id),
            "user_id": str(user.user_id),
            "email": user.email,
        }
