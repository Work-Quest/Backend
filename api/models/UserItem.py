import uuid
from django.db import models
from .ProjectMember import ProjectMember

class UserItem(models.Model):

    user_item_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    project_member = models.ForeignKey(
        ProjectMember,
        on_delete=models.CASCADE,
        related_name="items"
    )

    item = models.ForeignKey(
        "Item",
        on_delete=models.CASCADE,
        related_name="owned_by"
    )

    quantity = models.IntegerField(default=1)

    is_equipped = models.BooleanField(
        default=False,
        help_text="for equipment or passive item"
    )

    cooldown_remaining = models.IntegerField(
        null=True, blank=True,
        help_text="turn-based cooldown"
    )

    obtained_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("project_member", "item")
