"""
Delete all database rows created by `seed_mock_user` for a given username prefix.

Removes:
  - Django users whose username starts with ``<prefix>_`` (e.g. wqdemo_01 … wqdemo_12)
  - Every project any of those users own or are members of (CASCADE removes tasks,
    members, combat, feedback, invites, etc.)
  - TaskLog and ActivityLog rows for those project IDs
  - ProjectEndSummary rows tied to those projects or users

Does **not** remove shared catalog data (Boss, Effect, Item rows).

Usage:
  python manage.py clear_mock_data
  python manage.py clear_mock_data --username-prefix wqdemo
  python manage.py clear_mock_data --no-input   # skip confirmation prompt
"""

from django.core.management.base import BaseCommand, CommandError

from api.management.demo_world_cleanup import wipe_demo_world


class Command(BaseCommand):
    help = (
        "Delete all mock/demo data for users matching <prefix>_NN and their projects "
        "(same scope as seed_mock_user --reset)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username-prefix",
            default="wqdemo",
            help="Match usernames <prefix>_01, <prefix>_02, … (default: wqdemo).",
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Do not prompt for confirmation.",
        )

    def handle(self, *args, **options):
        prefix = options["username_prefix"].strip()
        if not prefix or "_" in prefix:
            raise CommandError("--username-prefix must be non-empty and must not contain '_'.")

        if not options["no_input"]:
            self.stdout.write(
                self.style.WARNING(
                    f"This will delete ALL users matching {prefix}_* and every project "
                    "they own or belong to."
                )
            )
            confirm = input(f'Type "{prefix}" to confirm: ').strip()
            if confirm != prefix:
                raise CommandError("Aborted.")

        summary = wipe_demo_world(username_prefix=prefix)

        self.stdout.write(
            self.style.SUCCESS(
                "Mock data cleared.\n"
                f"  Business users matched: {summary['business_users_matched']}\n"
                f"  Projects removed: {summary['projects_deleted']}\n"
                f"  TaskLog rows removed: {summary['task_logs_deleted']}\n"
                f"  ActivityLog rows removed: {summary['activity_logs_deleted']}\n"
                f"  ProjectEndSummary rows removed: {summary['project_end_summaries_deleted']}\n"
                f"  Django User rows removed: {summary['django_users_deleted']}"
            )
        )
