from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional, TypeVar

from django.core.cache import cache

T = TypeVar("T")


@dataclass(frozen=True)
class CacheKeys:
    """
    Centralized cache key factory to keep keys consistent and easy to invalidate.
    """

    namespace: str = "workquest"

    def key(self, *parts: object) -> str:
        safe_parts = [self.namespace, *[str(p) for p in parts if p is not None]]
        return ":".join(safe_parts)

    # ---- Game ----
    def project_boss(self, project_id: object) -> str:
        return self.key("game", "project_boss", project_id)

    def boss_status(self, project_id: object) -> str:
        return self.key("game", "boss_status", project_id)

    def user_statuses(self, project_id: object) -> str:
        return self.key("game", "user_statuses", project_id)

    def game_status(self, project_id: object) -> str:
        return self.key("game", "game_status", project_id)

    def all_bosses(self) -> str:
        return self.key("game", "all_bosses")

    # ---- Projects ----
    def user_projects(self, user_id: object) -> str:
        return self.key("project", "user_projects", user_id)

    def project_members(self, project_id: object) -> str:
        return self.key("project", "members", project_id)

    # ---- Logs ----
    def project_game_logs(self, project_id: object) -> str:
        return self.key("log", "project_game_logs", project_id)

    # ---- Tasks ----
    def project_tasks(self, project_id: object, user_id: object) -> str:
        return self.key("task", "project_tasks", project_id, user_id)

    def task_detail(self, project_id: object, task_id: object, user_id: object) -> str:
        return self.key("task", "task_detail", project_id, task_id, user_id)

    def project_tasks_pattern(self, project_id: object) -> str:
        # wildcard user_id
        return self.key("task", "project_tasks", project_id, "*")

    def task_detail_pattern(self, project_id: object) -> str:
        # wildcard task_id and user_id
        return self.key("task", "task_detail", project_id, "*", "*")

    # ---- User ----
    def user_me(self, user_id: object) -> str:
        return self.key("user", "me", user_id)


class CacheService:
    """
    Redis-backed cache helpers using Django's cache framework (configured to Redis via django-redis).

    - Read-through: on cache miss, load from source and populate cache.
    - Write-through: on write, update cache immediately (we use this mainly as "set after compute" plus invalidations).
    """

    def __init__(self, *, keys: CacheKeys | None = None):
        self.keys = keys or CacheKeys()

    # -------- Core ops --------
    def get(self, key: str) -> Optional[T]:
        return cache.get(key)

    def set(self, key: str, value: T, *, ttl_seconds: int) -> T:
        cache.set(key, value, timeout=ttl_seconds)
        return value

    def delete(self, key: str) -> None:
        cache.delete(key)

    def delete_many(self, keys: Iterable[str]) -> None:
        cache.delete_many(list(keys))

    def delete_pattern(self, pattern: str) -> int:
        """
        Best-effort delete by key pattern (requires django-redis).

        Returns number of keys deleted (0 if backend doesn't support pattern delete).
        """
        try:
            from django_redis import get_redis_connection  # type: ignore
        except Exception:
            return 0

        try:
            conn = get_redis_connection("default")
            deleted = 0
            # Use SCAN to avoid blocking Redis.
            for key in conn.scan_iter(match=pattern, count=500):
                conn.delete(key)
                deleted += 1
            return deleted
        except Exception:
            return 0

    # -------- Strategies --------
    def read_through(self, *, key: str, ttl_seconds: int, loader: Callable[[], T]) -> T:
        cached = cache.get(key)
        if cached is not None:
            return cached
        value = loader()
        cache.set(key, value, timeout=ttl_seconds)
        return value

    def write_through(self, *, key: str, value: T, ttl_seconds: int) -> T:
        return self.set(key, value, ttl_seconds=ttl_seconds)

    # -------- Domain invalidation helpers --------
    def invalidate_project_game(self, project_id: object) -> None:
        self.delete_many(
            [
                self.keys.project_boss(project_id),
                self.keys.boss_status(project_id),
                self.keys.user_statuses(project_id),
                self.keys.game_status(project_id),
            ]
        )

    def invalidate_project_members(self, project_id: object) -> None:
        self.delete(self.keys.project_members(project_id))

    def invalidate_user_projects(self, user_id: object) -> None:
        self.delete(self.keys.user_projects(user_id))

    def invalidate_project_logs(self, project_id: object) -> None:
        self.delete(self.keys.project_game_logs(project_id))

    def invalidate_project_tasks(self, project_id: object) -> None:
        # Clear per-user caches for this project's tasks list + task details.
        self.delete_pattern(self.keys.project_tasks_pattern(project_id))
        self.delete_pattern(self.keys.task_detail_pattern(project_id))


