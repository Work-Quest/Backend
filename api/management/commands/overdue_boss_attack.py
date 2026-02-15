from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from api.models.Task import Task
from api.models.TaskLog import TaskLog
from api.services.game_service import GameService


ACTIVE_TASK_STATUSES = ("backlog", "todo", "inProgress")


class Command(BaseCommand):
    help = (
        "Auto-triggers a boss attack ONCE for each overdue (deadline passed), incomplete task "
        "that has at least one assignee. Uses TaskLog marker events for idempotency (no schema changes)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print which tasks would be processed; do not modify DB or call game logic.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Max number of overdue tasks to process in this run.",
        )
        parser.add_argument(
            "--project-id",
            type=str,
            default=None,
            help="Optional: only process tasks belonging to this project UUID.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run: bool = bool(options["dry_run"])
        limit: int = int(options["limit"])
        project_id: str | None = options.get("project_id") or None

        qs = (
            Task.objects.filter(
                status__in=ACTIVE_TASK_STATUSES,
                deadline__isnull=False,
                deadline__lt=now,
            )
            .filter(assigned_members__isnull=False)
            .distinct()
            .order_by("deadline")
        )
        if project_id:
            qs = qs.filter(project_id=project_id)

        tasks = list(qs[:limit])
        if dry_run:
            for t in tasks:
                self.stdout.write(
                    f"[DRY RUN] would boss-attack overdue task={t.task_id} project={t.project_id} deadline={t.deadline}"
                )
            self.stdout.write(self.style.SUCCESS(f"[DRY RUN] {len(tasks)} task(s) matched."))
            return

        svc = GameService()
        processed = 0
        attacked = 0
        failed = 0

        for t in tasks:
            processed += 1
            try:
                with transaction.atomic():
                    # Lock row to avoid double-processing if the scheduler overlaps.
                    locked = Task.objects.select_for_update().get(task_id=t.task_id)

                    # Re-check conditions under lock (idempotency + race safety)
                    if locked.status == "done":
                        continue
                    if locked.deadline is None or locked.deadline >= now:
                        continue
                    if not locked.assigned_members.exists():
                        continue
                    if TaskLog.objects.filter(
                        project_id=locked.project_id,
                        actor_type=TaskLog.ActorType.SYSTEM,
                        event_type=TaskLog.EventType.BOSS_ATTACK,
                        payload__task_id=str(locked.task_id),
                    ).exists():
                        continue

                    svc.boss_attack(str(locked.project_id), str(locked.task_id))
                    attacked += 1

                    # Marker log so we don't re-attack the same overdue task on the next run.
                    TaskLog.write(
                        project_id=locked.project_id,
                        actor_type=TaskLog.ActorType.SYSTEM,
                        actor_id=None,
                        event_type=TaskLog.EventType.BOSS_ATTACK,
                        payload={
                            "task_id": str(locked.task_id),
                            "damage": 0,
                            "player_hp": None,
                        },
                    )
            except Exception as e:
                failed += 1
                self.stderr.write(
                    f"[ERROR] overdue boss attack failed task={t.task_id} project={t.project_id}: {e}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Overdue boss attack complete. processed={processed} attacked={attacked} failed={failed}"
            )
        )


