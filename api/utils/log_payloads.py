from __future__ import annotations

from typing import Any, Optional


def _iso(dt) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def task_snapshot(task: Any) -> Optional[dict[str, Any]]:
    """
    Build a JSON-safe snapshot of a Task (model or domain wrapper).

    Intentionally stores only primitive JSON types so it can live inside TaskLog.payload.
    """
    if task is None:
        return None

    # Accept either Task model, Task domain (`_task`), or any object exposing `.task`.
    model = getattr(task, "_task", None) or getattr(task, "task", None) or task

    # Best-effort: if it doesn't look like a Task model, don't explode.
    if not hasattr(model, "task_id"):
        return None

    return {
        "task_id": str(getattr(model, "task_id", "")),
        "task_name": getattr(model, "task_name", None),
        "description": getattr(model, "description", None),
        "status": getattr(model, "status", None),
        "priority": int(getattr(model, "priority", 0) or 0),
        "deadline": _iso(getattr(model, "deadline", None)),
        "created_at": _iso(getattr(model, "created_at", None)),
        "completed_at": _iso(getattr(model, "completed_at", None))
    }


def project_member_snapshot(member: Any) -> Optional[dict[str, Any]]:
    """
    Build a JSON-safe snapshot of a ProjectMember (model or domain wrapper).
    """
    if member is None:
        return None

    # Accept either ProjectMember model, ProjectMember domain (`_member`), or any object exposing `.project_member`.
    model = getattr(member, "_member", None) or getattr(member, "project_member", None) or member
    if not hasattr(model, "project_member_id"):
        return None

    user = getattr(model, "user", None)
    username = None
    if user is not None:
        # BusinessUser has `username`, and also has `auth_user.username`
        username = getattr(user, "username", None) or getattr(getattr(user, "auth_user", None), "username", None)

    def _int_or_none(v):
        return int(v) if v is not None else None

    return {
        "project_member_id": str(getattr(model, "project_member_id", "")),
        "user_id": (str(getattr(user, "user_id")) if user is not None and getattr(user, "user_id", None) else None),
        "username": username,
        "status": getattr(model, "status", None),
        "hp": _int_or_none(getattr(model, "hp", None)),
        "max_hp": _int_or_none(getattr(model, "max_hp", None)),
        "score": _int_or_none(getattr(model, "score", None)),
    }


