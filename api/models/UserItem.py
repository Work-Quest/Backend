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
    created_at = models.DateTimeField(auto_now_add=True)
