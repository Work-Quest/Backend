
from django.db import models
import uuid
from .Project import Project


class ProjectInviteToken(models.Model):
    """
    NOTE:
    - This model is intentionally defined here because you requested not to edit other files.
    - In a typical Django app, this should live under `api/models/` and have migrations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="invite_tokens",
    )
    email = models.EmailField()
    token = models.CharField(max_length=128, unique=True, db_index=True)
    expired_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)  # NULL = not used yet
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "api"
        db_table = "project_invite_tokens"
        indexes = [
            models.Index(fields=["project", "email"]),
            models.Index(fields=["token"]),
            models.Index(fields=["expired_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"InviteToken(project={self.project_id}, email={self.email})"

    @property
    def project_id(self):
        # convenience for logs / debugging
        return getattr(self.project, "project_id", None)