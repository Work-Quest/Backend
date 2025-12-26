from django.db import models
import uuid
from django.contrib.auth.models import User

class BusinessUser(models.Model):
    auth_user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="business_profile",
    )
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    email = models.CharField(max_length=100, unique=True)
    profile_img = models.CharField(max_length=255,null=True, blank=True)

    def __str__(self):
        return self.username


