"""Helpers for calling DRF @api_view handlers from unit tests."""

from __future__ import annotations

from django.contrib.auth.models import User
from rest_framework.test import force_authenticate


def attach_authenticated_user(request, *, username: str = "testuser", pk: int = 1) -> User:
    """Bypass DEFAULT_AUTHENTICATION_CLASSES so IsAuthenticated passes."""
    user = User(username=username)
    user.pk = pk
    force_authenticate(request, user=user)
    return user
