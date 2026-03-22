"""
Seed a **small, rerunnable** demo world (default **4 users**, **2 projects**) that mirrors
what you would set up manually: same DB rows the real app reads, no external AI calls.

Canonical IDs (keep in sync with Frontend):
  • **Avatars / battle sprites** — seeded users use `selected_character_id` **1–3** only
    (`c01`–`c03`), matching the first three roster entries in `battleConfig.ts`.
  • **Boss catalog** — `Boss.boss_image` must be **b01, b02, b03** for Dracula, Golem,
    Gnoll (`battleConfig.ts` ENTITY_CONFIG.bosses). `ProjectBoss` rows reference `Boss`
    by UUID (`boss_id`); the API/JSON boss cards use string id from `boss.boss_id`.
  • **Items** — `Item.item_id` is a **UUID** (no fixed public id). Seed ensures **WQ Demo:**
    damage/debuff items linked to `Effect` rows (no Healing Salve demo row).
  • **Achievements UI** — string ids **"01"…"06"** only via
    `achievement_service.compute_achievement_ids` + `UserFeedback` + `TaskLog` (not the
    `Achievement` model). With all members **Alive**, **04 The Last Stand** cannot
    unlock (needs exactly one survivor); other ids can still match seeded logs/feedback.

**AI-shaped data:** `UserFeedback` + review `sentiment_score` mimic outputs you would get
after the AI/review pipeline. **Leave room for the app:** the **Working** project skews
toward `todo` / `inProgress` tasks so you can still move tasks to done, attack, etc. and
generate **real** `TaskLog` rows alongside seed history.

**Combat / score wiring:** Every seeded task uses **priority 1–3** (never 0), a non-null
**deadline**, and **`<prefix>_01` is always a `UserTask` assignee** — matching what
`game_service.player_attack` / `Game.player_attack` need for non-zero damage and score.

**Bosses:** Seeded `ProjectBoss` rows use **only Dracula (`b01`)** for Normal combat history.
A separate **`Special`** catalog row (**WQ Demo Special Summon**, image **b01**) is ensured so
`POST …/boss/setup/special/` (ProjectBattle) never hits an empty Special pool.

**Review Task:** Extra **done** tasks are assigned **only to teammates** (not `<prefix>_01`) so the
primary demo login sees **>3** reviewable items (UI shows 3 “latest” + more in the selector).
Mock **Report** / **UserReport** rows backfill **review history** (`GET .../review/get_all_review/`).

Usage:
  python manage.py seed_mock_user --reset
  python manage.py seed_mock_user --reset --players 4 --projects 2
  python manage.py seed_mock_user --username-prefix wqdemo --password secret

To remove mock data without re-seeding:
  python manage.py clear_mock_data [--username-prefix wqdemo] [--no-input]

Login as the first player:  <prefix>_01  (default wqdemo_01) / demo1234
"""

from __future__ import annotations

import json
import random
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from api.models.Boss import Boss
from api.models.BossAttack import BossAttack
from api.models.BusinessUser import BusinessUser
from api.models.Effect import Effect
from api.models.Item import Item
from api.models.Project import Project
from api.models.ProjectBoss import ProjectBoss
from api.models.ProjectEndSummary import ProjectEndSummary
from api.models.ProjectInviteToken import ProjectInviteToken
from api.models.ProjectMember import ProjectMember
from api.models.Report import Report
from api.models.Task import Task
from api.models.TaskLog import TaskLog
from api.models.UserAttack import UserAttack
from api.models.UserBossCollection import UserBossCollection
from api.models.UserEffect import UserEffect
from api.models.UserFeedback import UserFeedback
from api.models.UserItem import UserItem
from api.models.UserReport import UserReport
from api.models.UserTask import UserTask
from api.management.demo_world_cleanup import wipe_demo_world
from api.utils.log_payloads import project_member_snapshot, task_snapshot

User = get_user_model()

# Must match Frontend `src/constants/workCategories.ts` apiLabel values (Your Task Categories panel).
AI_WORK_CATEGORIES = [
    "Conducting Research",
    "Creating Content and Visuals",
    "Task Assignment and Scheduling",
    "Programming",
    "Working with Spreadsheets and Data",
    "Reviewing and Providing Feedback",
    "Documentation",
    "Testing",
    "Translation",
    "Sending Emails and Communication",
    "Finalizing and Submitting Work",
]

# Typical labels from AI-Service / k-means role output (CSV assignments).
AI_ASSIGNED_ROLES = [
    "Task finisher",
    "Helper",
    "Strategic planner",
    "Quality guardian",
    "Integrator",
    "Core contributor",
]

MOCK_FEEDBACK_TEMPLATE = """{name}, you are a very talented person, and your work in the coding field is outstanding. This shows that you have excellent coding skills. Your work speed is also quite good, especially on your fastest days, which means you can work quickly at times.

However, there are some areas you can improve, such as teamwork. You might need to pay more attention to collaborating with your team to work better with others. Another point is documentation and bug fixing—while you are already doing well, you could improve even further by focusing more on details. This would help increase your work efficiency.

Lastly, balancing your work schedule is important. Some days, your workload is too heavy, which might cause stress or exhaustion, affecting your work quality. If you can improve in these areas, you will be able to work at your full potential and be even more effective!"""


def _json_workload_per_day(rng: random.Random) -> str:
    """Same shape as AI pipeline: JSON array of task counts per day."""
    n = rng.randint(10, 16)
    return json.dumps([rng.randint(0, 10) for _ in range(n)])


def _json_work_speed_minutes(rng: random.Random) -> str:
    """JSON array of average minutes per task/day (parsed by FeedbackMetrics / AI service)."""
    n = rng.randint(10, 16)
    return json.dumps([round(rng.uniform(15.0, 95.0), 2) for _ in range(n)])


# --- wipe: see api.management.demo_world_cleanup (also used by clear_mock_data) ---


# --- catalog --------------------------------------------------------------

def _ensure_catalog():
    """
    Only create catalog rows that match game mechanics / frontend assets.

    Bosses: names + `boss_image` ids **b01–b03** align with `Frontend/src/config/battleConfig.ts`
    (Dracula, Golem, Gnoll).
    """
    dmg_buff, _ = Effect.objects.get_or_create(
        effect_type=Effect.EffectType.DAMAGE_BUFF,
        value=10.0,
        defaults={
            "description": "Increases outgoing damage.",
            "effect_polarity": Effect.EffectPolarity.GOOD,
        },
    )
    heal_fx, _ = Effect.objects.get_or_create(
        effect_type=Effect.EffectType.HEAL,
        value=25.0,
        defaults={
            "description": "Restores HP.",
            "effect_polarity": Effect.EffectPolarity.GOOD,
        },
    )
    debuff, _ = Effect.objects.get_or_create(
        effect_type=Effect.EffectType.DAMAGE_DEBUFF,
        value=5.0,
        defaults={
            "description": "Reduces outgoing damage.",
            "effect_polarity": Effect.EffectPolarity.BAD,
        },
    )
    # Canonical bosses (battleConfig ENTITY_CONFIG.bosses b01–b03).
    # Must stay boss_type="Normal": `Game.initial_boss_setup` only picks Normal bosses
    # and Special bosses use different kill/phase rules in `domains/game.py`.
    boss_defs = [
        ("Dracula", "Normal", "b01"),
        ("Golem", "Normal", "b02"),
        ("Gnoll", "Normal", "b03"),
    ]
    bosses = []
    for name, btype, img in boss_defs:
        b, _ = Boss.objects.get_or_create(
            boss_name=name,
            defaults={"boss_type": btype, "boss_image": img},
        )
        # Keep image/type aligned if row existed from older seeds.
        dirty = False
        if (b.boss_image or "") != img:
            b.boss_image = img
            dirty = True
        if (b.boss_type or "") != btype:
            b.boss_type = btype
            dirty = True
        if dirty:
            b.save(update_fields=["boss_image", "boss_type"])
        bosses.append(b)

    # `GameService.setup_special_boss` → `Game.special_boss_setup` requires at least one
    # `Boss` with boss_type="Special". Manual DBs often already have one; empty Special
    # pool causes: No "Special" bosses available to choose (…). Not used for Normal combat.
    _ensure_special_summon_boss()

    return {
        "effects": (dmg_buff, heal_fx, debuff),
        "bosses": bosses,
    }


# Stable name so re-seeding does not multiply Special rows.
_SPECIAL_SUMMON_BOSS_NAME = "WQ Demo Special Summon"


def _ensure_special_summon_boss() -> Boss:
    """One Special boss (sprite b01) so `/boss/setup/special/` works like a configured prod DB."""
    sp, _ = Boss.objects.get_or_create(
        boss_name=_SPECIAL_SUMMON_BOSS_NAME,
        defaults={
            "boss_type": "Special",
            "boss_image": "b01",
        },
    )
    dirty = False
    if sp.boss_type != "Special":
        sp.boss_type = "Special"
        dirty = True
    if (sp.boss_image or "") != "b01":
        sp.boss_image = "b01"
        dirty = True
    if dirty:
        sp.save(update_fields=["boss_type", "boss_image"])
    return sp


# Stable Item.name seeds so reruns are idempotent and UserItem always has catalog rows.
_DEMO_ITEM_SEEDS: list[tuple[str, str, str]] = [
    ("WQ Demo: Damage Tonic", "Tied to DAMAGE_BUFF effect for inventory UI.", "DAMAGE_BUFF"),
    ("WQ Demo: Weakening Draft", "Tied to DAMAGE_DEBUFF effect.", "DAMAGE_DEBUFF"),
]


def _ensure_demo_items(
    dmg_buff: Effect,
    heal_fx: Effect,
    debuff: Effect,
) -> None:
    """Create demo Item rows if missing (UUID PK); wire to Effect FKs like manual admin entry."""
    effect_map = {
        "DAMAGE_BUFF": dmg_buff,
        "HEAL": heal_fx,
        "DAMAGE_DEBUFF": debuff,
    }
    for name, description, eff_key in _DEMO_ITEM_SEEDS:
        eff = effect_map[eff_key]
        it = Item.objects.filter(name=name).first()
        if it is None:
            Item.objects.create(name=name, description=description, effects=eff)
        elif it.effects_id != eff.effect_id:
            it.effects = eff
            it.description = description or it.description
            it.save(update_fields=["effects", "description"])


# --- content helpers (read like real product / eng work) -----------------

REAL_PROJECT_NAMES = [
    "Northwind — Customer Portal Revamp",
    "Ledgerly — Payments API Hardening",
    "Atlas Design System v3",
    "FieldOps Technician Mobile App",
    "Meridian Analytics — Event Pipeline",
    "HR Hub — Benefits Enrollment 2025",
    "ShopFront — Checkout Conversion Sprint",
    "VoiceNote AI — Beta Feedback Loop",
    "Compliance Vault — Audit Export Tool",
    "Partner API — Rate Limits & SLAs",
    "Learning Loop — Course Authoring MVP",
    "CareConsole — Patient Messaging Pilot",
]

# Title must stay within Task.task_name max_length=100
REAL_WORK_ITEMS: list[tuple[str, str]] = [
    (
        "Define success metrics with PM for checkout funnel",
        "Align on primary KPI (conversion, AOV, latency). Document baseline in Notion and "
        "share with stakeholders before build starts.",
    ),
    (
        "Implement OAuth2 refresh flow on staging",
        "Support rotation of refresh tokens; add structured logs for auth failures. Pair with "
        "security review checklist.",
    ),
    (
        "Wire Stripe webhook retries and idempotency",
        "Handle 5xx from our API without dropping events. Store idempotency keys per invoice.",
    ),
    (
        "Draft technical design for read replicas",
        "Cover lag tolerance, failover, and ORM routing. Review with backend guild Thursday.",
    ),
    (
        "Fix pagination bug on team directory (iOS)",
        "Repro on iPhone 14; empty state flashes before load. Add loading skeleton + tests.",
    ),
    (
        "Migrate legacy CSV export to async job",
        "Move heavy exports to Celery/RQ pattern; email link when ready. Cap file size at 50MB.",
    ),
    (
        "Accessibility audit: focus order on settings screens",
        "Run axe-core; fix tab traps and contrast on toggles. Attach before/after to ticket.",
    ),
    (
        "Load test checkout under Black Friday profile",
        "Target 3x normal RPS; document bottlenecks in DB vs app tier.",
    ),
    (
        "Document on-call runbook for payments incidents",
        "Include dashboards, escalation paths, and rollback steps for last deployment.",
    ),
    (
        "Review open PRs for SQL N+1 queries",
        "Focus on list endpoints shipped last sprint; suggest select_related where safe.",
    ),
    (
        "Ship dark mode tokens for Atlas components",
        "Button, input, modal. Validate with design in Figma dev mode before merge.",
    ),
    (
        "Instrument key user paths in Amplitude",
        "Sign-up, first value action, churn risk events. Naming convention: domain.action.result.",
    ),
    (
        "Coordinate UAT with customer success (3 accounts)",
        "Schedule 45-min sessions; capture blockers in shared sheet.",
    ),
    (
        "Reduce P95 API latency on /v2/orders",
        "Profile hot path; consider caching hot SKUs and index on status+created_at.",
    ),
    (
        "Draft Q2 roadmap slides for leadership",
        "Themes: reliability, growth experiments, tech debt paydown. Keep to 8 slides.",
    ),
    (
        "Harden file upload validation (MIME + size)",
        "Block executables; virus scan hook for enterprise tier. Update API error messages.",
    ),
    (
        "E2E test: invite teammate and accept flow",
        "Playwright/Cypress; run in CI on main. Include email stub assertions.",
    ),
    (
        "Backfill historical invoices into new schema",
        "One-time script with dry-run; verify totals match finance export.",
    ),
    (
        "Design review: empty states for reporting module",
        "Bring 2 directions; align on copy tone with content design.",
    ),
    (
        "Tune feature flags for gradual rollout",
        "Start 5% internal, then 10% / 50% / 100%. Add kill switch runbook.",
    ),
    (
        "Resolve SonarQube hotspots in billing package",
        "Prioritize security findings; time-box to 2 days; create follow-ups for debt.",
    ),
    (
        "Update API changelog for partner developers",
        "Breaking changes in pagination; include migration snippet and sunset date.",
    ),
    (
        "Spike: vector search for help center",
        "Prototype with existing docs; measure recall@5 vs keyword search.",
    ),
    (
        "Fix timezone bugs in scheduled reports",
        "Use org-level TZ; add unit tests covering DST boundary.",
    ),
    (
        "Negotiate SLO draft with infrastructure",
        "Target 99.9% for core API; error budget policy and status page updates.",
    ),
    (
        "Clean up dead feature flags post-launch",
        "Remove code paths for 'checkout_v1'; confirm no traffic in last 14 days.",
    ),
    (
        "Workshop: incident response tabletop exercise",
        "Scenario: DB failover during peak. Assign roles; capture action items.",
    ),
    (
        "Implement soft delete for project artifacts",
        "30-day retention then purge job; ensure FK behavior documented.",
    ),
    (
        "Polish mobile navigation for thumb reach",
        "iOS HIG review; reduce tap targets below fold on SE-sized devices.",
    ),
    (
        "Add monitoring alert for queue depth",
        "Pager if > 10k for 15m; link to dashboard and recent deploys.",
    ),
    (
        "Interview loop: senior backend (2 candidates)",
        "Share rubric with panel; debrief same day; decision within 48h.",
    ),
    (
        "Refactor notification service for testability",
        "Extract providers; mock in unit tests; no behavior change.",
    ),
    (
        "Beta feedback synthesis — top 10 themes",
        "Tag 200+ notes; present summary in weekly product review.",
    ),
    (
        "Cost review: cloud spend anomaly last month",
        "Identify new NAT and egress; propose reserved capacity where applicable.",
    ),
    (
        "Localization pass for ES and FR (invoice PDF)",
        "Work with vendor; verify number and date formats; legal sign-off.",
    ),
    (
        "Security patch: dependency bump for auth library",
        "CVE medium; regression test login, refresh, and SSO flows.",
    ),
    (
        "Story mapping session for onboarding v2",
        "Outcome-based stories; cut scope for first slice shipping in 3 weeks.",
    ),
    (
        "Fix flaky integration test in CI (timing)",
        "Replace sleeps with deterministic waits; document pattern in README.",
    ),
    (
        "Prepare SOC2 evidence for access reviews",
        "Export IAM reports; attach ticket IDs for remediation items.",
    ),
    (
        "Prototype dashboard widget for CSAT trend",
        "Use existing chart component; fake data OK for demo to sales.",
    ),
    (
        "Align with Legal on data retention wording",
        "In-app privacy center copy; track redlines in shared doc.",
    ),
    (
        "Optimize image pipeline for CDN cache hit ratio",
        "WebP/AVIF variants; long TTL for static marketing assets.",
    ),
    (
        "Retrospective: what slowed the last release",
        "Focus on process; three keep / three try / three stop.",
    ),
    (
        "Seed lower environments with anonymized prod subset",
        "PII scrub script; document refresh cadence (weekly).",
    ),
    (
        "Draft comms plan for maintenance window",
        "Email + in-app banner; support macros; rollback owner named.",
    ),
    (
        "Pair with SRE on canary deployment checklist",
        "Metrics to watch; automatic promotion criteria; manual gate if error rate spikes.",
    ),
]

# Review Task UI (`ReviewTask.tsx`): viewer cannot review tasks they are assigned to; it shows
# up to 3 “latest” eligible done tasks plus the rest in a dropdown — need >3 done tasks with
# **no** `<prefix>_01` on assignees for the primary login to see a full panel.
REVIEW_PANEL_DONE_FOR_LEAD = 6


REVIEW_COMMENTS = [
    "Solid implementation — please add a regression test for the edge case we hit in staging.",
    "Nice refactor; consider extracting the retry helper so other services can reuse it.",
    "UX feels clearer. One nit: loading state should match the pattern on the settings page.",
    "Docs update appreciated. Can we link the ADR from the module docstring?",
    "Performance looks good on the sample data set; flag if we need a larger fixture in CI.",
    "Security: confirm we're not logging raw tokens anywhere in this path.",
    "Approving with minor comments — happy to merge after the typo fix in copy.",
    "Good catch on the race condition; thread-safety looks correct now.",
]

def _shuffled_work_indices(rng: random.Random) -> list[int]:
    ids = list(range(len(REAL_WORK_ITEMS)))
    rng.shuffle(ids)
    return ids


def _task_deadline(
    rng: random.Random,
    *,
    now: timezone.datetime,
    project_started: timezone.datetime,
    status: str,
    allow_null: bool = False,
) -> timezone.datetime | None:
    """
    Plausible deadlines. When allow_null is False (default for seed), every task has a
    deadline so `domains/game.py player_attack` can compute time_left / damage — NULL
    deadlines would break attack math; priority 0 would make damage and score always 0.
    """
    if allow_null and rng.random() < 0.08:
        return None
    if status == "done":
        return now - timedelta(days=rng.randint(3, 60), hours=rng.randint(0, 20))
    if status == "inProgress":
        return now + timedelta(days=rng.randint(1, 21), hours=rng.randint(0, 12))
    return now + timedelta(days=rng.randint(7, 75), hours=rng.randint(0, 18))


def _pick_assignees_for_task(
    members: list[ProjectMember],
    rng: random.Random,
    *,
    ensure_username: str | None,
) -> list[ProjectMember]:
    """
    `game_service.player_attack` only runs for `UserTask` assignees. Ensure the primary
    demo login (`ensure_username`, e.g. wqdemo_01) is always included so completing a
    task and attacking credits that user like a hand-made project.
    """
    if not members:
        return []
    k = min(len(members), max(1, rng.randint(1, 3)))
    assignees = rng.sample(members, k=k)
    if not ensure_username:
        return assignees
    lead = next((m for m in members if m.user.username == ensure_username), None)
    if lead is None or lead in assignees:
        return assignees
    # Swap in lead; keep up to k members
    others = [m for m in assignees if m.pk != lead.pk]
    trimmed = others[: max(0, k - 1)]
    return [lead] + trimmed


def _pick_status(rng: random.Random, *, project_done: bool, prefer_open_for_app: bool) -> str:
    """
    `prefer_open_for_app` — Working projects: leave tasks for real Kanban / move_task /
    combat so the live app can append TaskLogs; still a few done rows for history.
    """
    if project_done:
        return rng.choices(
            population=["done", "done", "done", "todo", "backlog", "inProgress"],
            weights=[6, 6, 6, 1, 1, 1],
            k=1,
        )[0]
    if prefer_open_for_app:
        return rng.choices(
            population=["todo", "inProgress", "backlog", "done"],
            weights=[4, 4, 2, 1],
            k=1,
        )[0]
    return rng.choices(
        population=["done", "inProgress", "todo", "backlog"],
        weights=[3, 3, 2, 2],
        k=1,
    )[0]


def _member_indices_for_project(team_size: int, count: int) -> list[int]:
    """Full party on every project (deterministic), up to `count` capped by roster size."""
    n = max(0, min(count, team_size))
    return list(range(n))


def _assignees_for_task(task: Task) -> list[ProjectMember]:
    return [
        ut.project_member
        for ut in UserTask.objects.filter(task=task).select_related("project_member")
    ]


def _seed_mock_review_history(
    *,
    review_tasks: list[Task],
    lead: ProjectMember,
    others: list[ProjectMember],
    rng: random.Random,
    now: timezone.datetime,
    start_days_ago: int,
) -> None:
    """
    Populate `Report` + `UserReport` so GET .../review/get_all_review/ fills the
    Review Task history list (same shape as POST /review/report).
    """
    if not review_tasks:
        return

    # Primary login already reviewed these — they appear in history, not in "to review".
    n_lead_history = min(2, len(review_tasks))
    for t in review_tasks[:n_lead_history]:
        receivers = _assignees_for_task(t)
        if not receivers:
            continue
        rep = Report.objects.create(
            task=t,
            reporter=lead,
            description=rng.choice(REVIEW_COMMENTS),
            sentiment_score=rng.randint(2, 5),
        )
        for recv in receivers:
            UserReport.objects.create(report=rep, reviewer=lead, receiver=recv)
        past = now - timedelta(
            days=rng.randint(8, min(55, max(8, start_days_ago))),
            hours=rng.randint(0, 20),
        )
        Report.objects.filter(pk=rep.pk).update(created_at=past)

    # One teammate→teammate review for variety (still valid: reviewer not assignee).
    if len(review_tasks) >= 3 and len(others) >= 2:
        t_peer = review_tasks[2]
        reviewer_peer, assignee_peer = others[0], others[1]
        UserTask.objects.filter(task=t_peer).delete()
        UserTask.objects.get_or_create(project_member=assignee_peer, task=t_peer)
        receivers = _assignees_for_task(t_peer)
        if receivers:
            rep = Report.objects.create(
                task=t_peer,
                reporter=reviewer_peer,
                description=rng.choice(REVIEW_COMMENTS),
                sentiment_score=rng.randint(2, 5),
            )
            for recv in receivers:
                UserReport.objects.create(report=rep, reviewer=reviewer_peer, receiver=recv)
            past = now - timedelta(
                days=rng.randint(4, min(35, max(4, start_days_ago))),
                hours=rng.randint(0, 18),
            )
            Report.objects.filter(pk=rep.pk).update(created_at=past)


def _seed_review_eligible_done_tasks(
    *,
    project: Project,
    members: list[ProjectMember],
    first_username: str,
    rng: random.Random,
    now: timezone.datetime,
    start_days_ago: int,
    work_order: list[int],
) -> None:
    """
    Create done tasks assigned **only** to teammates (not `first_username`).

    Gameplay tasks always include `<prefix>_01` for attacks; Review Task hides any done task
    where the current member is an assignee, so the lead would otherwise see 0 review options.

    Also seeds past `Report` / `UserReport` rows so the Review Task **history** section is
    populated (GET .../review/get_all_review/).
    """
    others = [m for m in members if m.user.username != first_username]
    if not others:
        return

    lead = next((m for m in members if m.user.username == first_username), None)
    proj_started = now - timedelta(days=start_days_ago)
    review_tasks: list[Task] = []
    for i in range(REVIEW_PANEL_DONE_FOR_LEAD):
        wi = work_order[i % len(work_order)]
        title, body = REAL_WORK_ITEMS[wi]
        base = (title[:72] + f" [review {i + 1}]").strip()
        tname = base[:100]
        dl = _task_deadline(
            rng,
            now=now,
            project_started=proj_started,
            status="done",
        )
        tp = rng.randint(1, 3)
        t = Task.objects.create(
            project=project,
            task_name=tname,
            description=body,
            status="done",
            priority=tp,
            deadline=dl,
        )
        Task.objects.filter(pk=t.pk).update(
            completed_at=now
            - timedelta(
                days=rng.randint(2, min(75, max(3, start_days_ago))),
                hours=rng.randint(0, 20),
            )
        )
        k = min(len(others), max(1, rng.randint(1, 2)))
        for m in rng.sample(others, k=k):
            UserTask.objects.get_or_create(project_member=m, task=t)
        review_tasks.append(t)

    if lead:
        _seed_mock_review_history(
            review_tasks=review_tasks,
            lead=lead,
            others=others,
            rng=rng,
            now=now,
            start_days_ago=start_days_ago,
        )


@dataclass
class DemoUser:
    django_user: User
    business: BusinessUser


def _backdate_tasklog(qs, base: timezone.datetime, rng: random.Random) -> None:
    """
    Spread log timestamps between `base` and now. Never write future `created_at`
    (avoids “in about 1 month” in the Damage Log UI).
    """
    end = timezone.now()
    if base >= end:
        base = end - timedelta(days=1)
    span = int((end - base).total_seconds())
    if span < 60:
        span = 60
    for row in qs.iterator():
        offset = rng.randint(0, span - 1)
        dt = base + timedelta(seconds=offset)
        if dt > end:
            dt = end - timedelta(seconds=rng.randint(1, min(3600, span)))
        TaskLog.objects.filter(pk=row.pk).update(created_at=dt)


def _task_block_for_damage_log(ref_task: Task | None) -> dict | None:
    """
    Same shape as api.utils.log_payloads.task_snapshot (what game.py writes).
    Ensures task_name is a non-empty string so the Damage Log UI shows a title, not USER_ATTACK.
    """
    if ref_task is None:
        return None
    snap = task_snapshot(ref_task)
    if not snap:
        label = (getattr(ref_task, "task_name", None) or "").strip() or "Work task"
        return {
            "task_id": str(ref_task.task_id),
            "task_name": label,
            "description": getattr(ref_task, "description", None),
            "status": getattr(ref_task, "status", None),
            "priority": int(getattr(ref_task, "priority", 0) or 0),
            "deadline": None,
            "created_at": None,
            "completed_at": None,
        }
    label = snap.get("task_name")
    if label is None or not str(label).strip():
        snap = dict(snap)
        snap["task_name"] = "Work task"
    return snap


def _combat_task_candidates(project: Project) -> list[Task]:
    """
    Pool of tasks for USER_ATTACK / BOSS_ATTACK TaskLog rows.
    Each log should reference a different task where possible so the Damage Log is not one repeated title.
    """
    qs = (
        Task.objects.filter(project=project)
        .exclude(task_name__isnull=True)
        .exclude(task_name="")
    )
    out = list(qs)
    if not out:
        out = list(Task.objects.filter(project=project))
    return out


def _pick_combat_task(candidates: list[Task], rng: random.Random) -> Task | None:
    return rng.choice(candidates) if candidates else None


def _pick_items_for_grant(catalog: list[Item], count: int, rng: random.Random) -> list[Item]:
    """`count` catalog picks; use without replacement when possible, else repeat (small catalog)."""
    if count <= 0:
        return []
    if len(catalog) >= count:
        return rng.sample(catalog, k=count)
    return [rng.choice(catalog) for _ in range(count)]


def _inject_canonical_achievement_logs(
    *,
    project: Project,
    lead: ProjectMember | None,
    created_at: timezone.datetime,
    rng: random.Random,
) -> None:
    """
    Extra TaskLog rows matching `achievement_service._member_game_context` /
    `compute_achievement_ids` so real IDs 01 / 03 / 05 / 06 can unlock for the lead
    member (together with UserFeedback on a 0–100 scale and top score on the project).
    """
    if lead is None:
        return
    pid = str(project.project_id)
    mid = str(lead.project_member_id)
    pb_id = (
        ProjectBoss.objects.filter(project=project, status="Dead")
        .values_list("project_boss_id", flat=True)
        .first()
    )
    boss_actor = pb_id or lead.project_member_id
    rows = [
        TaskLog.write(
            project_id=pid,
            actor_type=TaskLog.ActorType.BOSS,
            actor_id=boss_actor,
            event_type=TaskLog.EventType.KILL_PLAYER,
            payload={"receiver_id": mid},
        ),
        TaskLog.write(
            project_id=pid,
            actor_type=TaskLog.ActorType.USER,
            actor_id=lead.project_member_id,
            event_type=TaskLog.EventType.USER_REVIVE,
            payload={"player_id": mid},
        ),
        TaskLog.write(
            project_id=pid,
            actor_type=TaskLog.ActorType.USER,
            actor_id=lead.project_member_id,
            event_type=TaskLog.EventType.KILL_BOSS,
            payload={"player_id": mid},
        ),
    ]
    # 05 One HP Legend: boss defeated while HP ratio ≤ 5%
    ProjectMember.objects.filter(pk=lead.pk).update(hp=3, max_hp=100)
    for log in rows:
        TaskLog.objects.filter(pk=log.pk).update(
            created_at=created_at
            + timedelta(
                days=rng.randint(8, min(55, 89)),
                hours=rng.randint(0, 20),
            )
        )


class Command(BaseCommand):
    help = (
        "Seed a small demo squad (default 4 users, 2 projects) with bosses b01–b03, "
        "demo items, and achievement-shaped feedback + TaskLogs. "
        "Use --reset to clear prior <prefix>_NN users."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username-prefix",
            default="wqdemo",
            help="Usernames will be <prefix>_01 … <prefix>_NN (default: wqdemo).",
        )
        parser.add_argument(
            "--players",
            type=int,
            default=4,
            help="Number of demo accounts (default: 4).",
        )
        parser.add_argument(
            "--projects",
            type=int,
            default=2,
            help="Number of projects to create (default: 2). First half Done, rest Working.",
        )
        parser.add_argument(
            "--tasks-per-project",
            type=int,
            default=8,
            help="Tasks per project (default: 8). Working projects skew open for real app actions.",
        )
        parser.add_argument(
            "--password",
            default="demo1234",
            help="Password for every demo user.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all users matching <prefix>_NN and their projects first.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="RNG seed for reproducible data (default: 42).",
        )

    def handle(self, *args, **options):
        prefix = options["username_prefix"].strip()
        if not prefix or "_" in prefix:
            raise CommandError("--username-prefix must be non-empty and must not contain '_'.")
        n_players = max(1, min(24, options["players"]))
        n_projects = max(1, min(8, options["projects"]))
        tasks_per = max(4, min(40, options["tasks_per_project"]))
        password = options["password"]
        rng = random.Random(options["seed"])

        first_u = f"{prefix}_01"
        if User.objects.filter(username=first_u).exists() and not options["reset"]:
            raise CommandError(
                f'User {first_u!r} exists. Run with --reset or change --username-prefix.'
            )

        now = timezone.now()

        with transaction.atomic():
            if options["reset"]:
                self.stdout.write(f"Removing prior {prefix}_* demo users (if any)…")
                wipe_demo_world(username_prefix=prefix)

            cat = _ensure_catalog()
            dmg_buff, heal_fx, debuff = cat["effects"]
            bosses = cat["bosses"]
            _ensure_demo_items(dmg_buff, heal_fx, debuff)
            # Drop legacy demo heal item so inventory mock matches current catalog.
            Item.objects.filter(name="WQ Demo: Healing Salve").delete()

            # Inventory: all Items except disallowed names (e.g. Sharpening oil); includes WQ Demo:* seeds.
            catalog_items = [
                it
                for it in Item.objects.all()
                if "sharpening oil" not in (it.name or "").lower()
            ]
            if not catalog_items and Item.objects.exists():
                self.stdout.write(
                    self.style.WARNING(
                        "All Item rows were filtered out (e.g. Sharpening oil only) — skipping UserItem inventory."
                    )
                )
            elif not catalog_items:
                self.stdout.write(
                    self.style.WARNING(
                        "No Item rows after catalog setup — skipping UserItem inventory."
                    )
                )

            demo_users: list[DemoUser] = []
            display_names = [
                "Maya Chen",
                "Jordan Lee",
                "Sam Rivera",
                "Alex Kim",
                "Riley Patel",
                "Casey Wu",
                "Quinn Brooks",
                "Avery Singh",
                "Noah Garcia",
                "Skyler Fox",
                "Jamie Ortiz",
                "Taylor Ng",
                "Reese Park",
                "Drew Hayes",
                "Blake Ali",
                "Rowan Cole",
            ]
            for i in range(1, n_players + 1):
                uname = f"{prefix}_{i:02d}"
                du, _ = User.objects.get_or_create(
                    username=uname,
                    defaults={"email": f"{uname}@workquest.demo"},
                )
                du.email = f"{uname}@workquest.demo"
                du.set_password(password)
                du.save()
                dn = display_names[(i - 1) % len(display_names)]
                bu, _ = BusinessUser.objects.get_or_create(
                    auth_user=du,
                    defaults={
                        "name": dn,
                        "username": uname,
                        "email": du.email,
                        "is_first_time": False,
                        # 1→c01, 2→c02, 3→c03 only (first three battle roster characters).
                        "selected_character_id": ((i - 1) % 3) + 1,
                        "bg_color_id": ((i - 1) % 8) + 1,
                    },
                )
                bu.name = dn
                bu.username = uname
                bu.email = du.email
                bu.is_first_time = False
                bu.selected_character_id = ((i - 1) % 3) + 1
                bu.save()
                demo_users.append(DemoUser(django_user=du, business=bu))

            # Project specs: first half-ish Done, rest Working; full roster on each project.
            name_pool = list(REAL_PROJECT_NAMES)
            rng.shuffle(name_pool)
            specs = []
            done_count = max(1, n_projects // 2)
            for p in range(n_projects):
                is_done = p < done_count
                start_ago = 90 - p * 20 + rng.randint(-4, 4)
                member_count = n_players
                name = name_pool[p % len(name_pool)][:50]
                if is_done:
                    dl_ago = start_ago - rng.randint(14, 40)
                    specs.append(
                        {
                            "name": name,
                            "status": "Done",
                            "start_days_ago": start_ago,
                            "deadline_days_ago": max(5, dl_ago),
                            "members": member_count,
                            "decision": "closed",
                        }
                    )
                else:
                    specs.append(
                        {
                            "name": name,
                            "status": "Working",
                            "start_days_ago": start_ago,
                            "deadline_days_from_now": rng.randint(10, 55),
                            "members": member_count,
                            "decision": None,
                        }
                    )

            projects: list[Project] = []
            project_members: list[list[ProjectMember]] = []

            for pidx, spec in enumerate(specs):
                owner = demo_users[pidx % len(demo_users)].business
                created_at = now - timedelta(days=spec["start_days_ago"])
                if spec["status"] == "Done":
                    deadline = now - timedelta(days=spec["deadline_days_ago"])
                    proj = Project.objects.create(
                        owner=owner,
                        project_name=spec["name"],
                        status="Done",
                        deadline=deadline,
                        deadline_decision=spec["decision"],
                        deadline_decision_date=deadline + timedelta(days=2),
                    )
                else:
                    deadline = now + timedelta(days=spec["deadline_days_from_now"])
                    proj = Project.objects.create(
                        owner=owner,
                        project_name=spec["name"],
                        status="Working",
                        deadline=deadline,
                    )
                Project.objects.filter(pk=proj.pk).update(created_at=created_at)
                projects.append(proj)

                idxs = _member_indices_for_project(n_players, spec["members"])
                members: list[ProjectMember] = []
                for mi in idxs:
                    bu = demo_users[mi].business
                    score = (
                        999_999
                        if (pidx == 0 and bu.username == first_u)
                        else rng.randint(80, 2200)
                    )
                    hp = rng.randint(20, 100)
                    # All party members stay Alive in mock data (no dead players in the game UI).
                    m = ProjectMember.objects.create(
                        project=proj,
                        user=bu,
                        hp=hp,
                        max_hp=100,
                        score=score,
                        status="Alive",
                    )
                    members.append(m)
                project_members.append(members)

            # Tasks + assignments + reviews
            for pidx, proj in enumerate(projects):
                members = project_members[pidx]
                is_done = proj.status == "Done"
                work_order = _shuffled_work_indices(rng)
                proj_started = now - timedelta(days=specs[pidx]["start_days_ago"])
                for t_i in range(tasks_per):
                    title, body = REAL_WORK_ITEMS[work_order[t_i % len(work_order)]]
                    st = _pick_status(
                        rng,
                        project_done=is_done,
                        prefer_open_for_app=not is_done,
                    )
                    tname = title[:100]
                    dl = _task_deadline(
                        rng,
                        now=now,
                        project_started=proj_started,
                        status=st,
                    )
                    # Priority 1–3 only: player_attack damage = BASE_PLAYER_DAMAGE * priority * …;
                    # priority 0 ⇒ 0 damage, 0 score. Boss setup also requires sum(priority) > 0.
                    task_priority = rng.randint(1, 3)
                    t = Task.objects.create(
                        project=proj,
                        task_name=tname,
                        description=body,
                        status=st,
                        priority=task_priority,
                        deadline=dl,
                    )
                    if st == "done":
                        Task.objects.filter(pk=t.pk).update(
                            completed_at=now
                            - timedelta(
                                days=rng.randint(1, min(90, specs[pidx]["start_days_ago"])),
                                hours=rng.randint(0, 20),
                            )
                        )

                    assignees = _pick_assignees_for_task(
                        members, rng, ensure_username=first_u
                    )
                    for m in assignees:
                        UserTask.objects.get_or_create(project_member=m, task=t)

                    want_review = (is_done and rng.random() < 0.42) or (
                        not is_done and rng.random() < 0.12
                    )
                    if st == "done" and want_review and len(members) >= 2:
                        reporter = rng.choice(assignees) if assignees else rng.choice(members)
                        others = [m for m in members if m.pk != reporter.pk]
                        if not others:
                            continue
                        reviewer = rng.choice(others)
                        rep = Report.objects.create(
                            task=t,
                            reporter=reporter,
                            description=rng.choice(REVIEW_COMMENTS),
                            sentiment_score=rng.randint(2, 5),
                        )
                        recv = rng.choice(
                            [m for m in members if m.pk not in (reporter.pk, reviewer.pk)]
                            or [reporter]
                        )
                        UserReport.objects.create(
                            report=rep,
                            reviewer=reviewer,
                            receiver=recv,
                        )
                        Report.objects.filter(pk=rep.pk).update(
                            created_at=now
                            - timedelta(
                                days=rng.randint(
                                    0, min(85, specs[pidx]["start_days_ago"])
                                ),
                                hours=rng.randint(0, 20),
                            )
                        )

                # Review Task: >3 done tasks without primary login on assignees (see REVIEW_PANEL_*).
                _seed_review_eligible_done_tasks(
                    project=proj,
                    members=members,
                    first_username=first_u,
                    rng=rng,
                    now=now,
                    start_days_ago=specs[pidx]["start_days_ago"],
                    work_order=work_order,
                )

                # recount tasks
                ts = Task.objects.filter(project=proj)
                Project.objects.filter(pk=proj.pk).update(
                    total_tasks=ts.count(),
                    completed_tasks=ts.filter(status="done").count(),
                )

            # Bosses, damage, logs per project
            for pidx, proj in enumerate(projects):
                members = project_members[pidx]
                tm = max(1, len(members))
                tm_c = min(tm, 12)  # keep combat row counts sane for large parties
                created_at = now - timedelta(days=specs[pidx]["start_days_ago"])
                # Always Dracula (b01): same Normal boss FK as a hand-made project, not random b02/b03.
                main_boss = bosses[0]
                pb_dead = ProjectBoss.objects.create(
                    project=proj,
                    boss=main_boss,
                    hp=0,
                    max_hp=400 + rng.randint(0, 400),
                    status="Dead",
                    phase=rng.randint(1, 3),
                )
                pb_alive = ProjectBoss.objects.create(
                    project=proj,
                    boss=main_boss,
                    hp=rng.randint(50, 400),
                    max_hp=800,
                    status="Alive",
                    phase=1,
                )
                ProjectBoss.objects.filter(pk=pb_dead.pk).update(
                    created_at=created_at,
                    updated_at=created_at + timedelta(days=rng.randint(5, 40)),
                )
                ProjectBoss.objects.filter(pk=pb_alive.pk).update(created_at=created_at)

                # TaskLog payloads must match api.utils.log_payloads + Frontend DamageLog
                # (task.task_name, actor.username, target.username, damage as int).
                combat_tasks = _combat_task_candidates(proj)
                members_for_logs = list(
                    ProjectMember.objects.filter(project=proj).select_related("user")
                )

                for _ in range(
                    rng.randint(max(3, tm_c + 1), min(16, 4 + tm_c * 3))
                ):
                    m = rng.choice(members)
                    UserAttack.objects.create(
                        project_member=m,
                        damage_point=rng.randint(15, 180),
                        project_boss=pb_dead,
                    )
                for _ in range(rng.randint(max(2, tm_c), min(12, 2 + tm_c * 2))):
                    m = rng.choice(members)
                    BossAttack.objects.create(
                        project_boss=pb_dead,
                        damage_point=rng.randint(10, 95),
                        project_member=m,
                    )
                for _ in range(rng.randint(max(2, tm_c // 2), min(8, 2 + tm_c))):
                    m = rng.choice(members)
                    UserAttack.objects.create(
                        project_member=m,
                        damage_point=rng.randint(10, 90),
                        project_boss=pb_alive,
                    )

                # TaskLog combat (same payload shape as domains/game.py for DamageLog UI)
                for m in members_for_logs:
                    for _ in range(rng.randint(1, max(2, min(4, tm_c)))):
                        hit = _pick_combat_task(combat_tasks, rng)
                        dmg = int(rng.randint(10, 150))
                        TaskLog.write(
                            project_id=str(proj.project_id),
                            actor_type=TaskLog.ActorType.USER,
                            actor_id=m.project_member_id,
                            event_type=TaskLog.EventType.USER_ATTACK,
                            payload={
                                "task_id": str(hit.task_id) if hit else None,
                                "task": _task_block_for_damage_log(hit),
                                "actor": project_member_snapshot(m),
                                "damage": dmg,
                                "boss_hp": int(rng.randint(50, 600)),
                            },
                        )
                for _ in range(rng.randint(max(2, tm_c), min(10, 3 + tm_c * 2))):
                    m = rng.choice(members_for_logs)
                    hit = _pick_combat_task(combat_tasks, rng)
                    dmg = int(rng.randint(8, 80))
                    TaskLog.write(
                        project_id=str(proj.project_id),
                        actor_type=TaskLog.ActorType.BOSS,
                        actor_id=pb_dead.project_boss_id,
                        event_type=TaskLog.EventType.BOSS_ATTACK,
                        payload={
                            "task_id": str(hit.task_id) if hit else None,
                            "task": _task_block_for_damage_log(hit),
                            "damage": dmg,
                            "target_player_id": str(m.project_member_id),
                            "target": project_member_snapshot(m),
                            "player_id": str(m.project_member_id),
                            "player": project_member_snapshot(m),
                        },
                    )

                done_tasks = list(Task.objects.filter(project=proj, status="done")[:8])
                for t in done_tasks:
                    m = rng.choice(members)
                    # Match domains/task_management.move_task payload shape. DamageLog UI uses
                    # payload.damage for the +N column (not score_recieve); without it, TASK_COMPLETED shows +0.
                    pri = int(getattr(t, "priority", 0) or 0)
                    damage_show = int(max(12, 18 + pri * 14 + rng.randint(0, 55)))
                    TaskLog.write(
                        project_id=str(proj.project_id),
                        actor_type=TaskLog.ActorType.USER,
                        actor_id=m.project_member_id,
                        event_type=TaskLog.EventType.TASK_COMPLETED,
                        payload={
                            "task_id": str(t.task_id),
                            "deadline": (t.deadline.isoformat() if t.deadline else None),
                            "complete_at": (
                                t.completed_at.isoformat() if t.completed_at else None
                            ),
                            "task": _task_block_for_damage_log(t),
                            "actor": project_member_snapshot(m),
                            "damage": damage_show,
                            "score_recieve": int(round(damage_show * 0.1)),
                        },
                    )

                # Backdate logs for this project
                logs = TaskLog.objects.filter(project_id=str(proj.project_id))
                _backdate_tasklog(logs, created_at, rng)

                # Backdate attacks
                ua = UserAttack.objects.filter(project_boss__project=proj)
                ba = BossAttack.objects.filter(project_boss__project=proj)
                for model_qs, fld in ((ua, "timestamp"), (ba, "timestamp")):
                    for row in model_qs.iterator():
                        delta = timedelta(
                            days=rng.randint(0, min(95, specs[pidx]["start_days_ago"])),
                            hours=rng.randint(0, 23),
                        )
                        type(row).objects.filter(pk=row.pk).update(
                            **{fld: created_at + delta}
                        )

                # UserFeedback — one row per member; **mocks post-AI pipeline** (no HuggingFace call).
                # Same field shapes as `feedback_service` / project-end UI. Scores 0–100 for
                # achievement_service thresholds (02 / 03 / 06); boost <prefix>_01.
                for m in members:
                    display_name = (m.user.name or m.user.username or "").strip() or m.user.username
                    is_primary = m.user.username == first_u
                    UserFeedback.objects.create(
                        user=m,
                        project=proj,
                        feedback_text=MOCK_FEEDBACK_TEMPLATE.format(name=display_name),
                        overall_quality_score=(
                            82.0 if is_primary else round(rng.uniform(68.0, 92.0), 1)
                        ),
                        team_work=(
                            84.0 if is_primary else round(rng.uniform(62.0, 90.0), 1)
                        ),
                        strength=rng.choice(AI_WORK_CATEGORIES),
                        work_load_per_day=_json_workload_per_day(rng),
                        work_speed=_json_work_speed_minutes(rng),
                        role_assigned=rng.choice(AI_ASSIGNED_ROLES),
                        diligence=(
                            76.0 if is_primary else round(rng.uniform(65.0, 88.0), 1)
                        ),
                    )

                # UserEffect (seed also creates Effect rows via _ensure_catalog).
                for m in rng.sample(members, k=min(len(members), rng.randint(2, 5))):
                    if rng.random() < 0.4:
                        UserEffect.objects.create(
                            project_member=m,
                            effect=rng.choice([dmg_buff, debuff, heal_fx]),
                        )

                # UserItem: grant from catalog (includes WQ Demo:* items); repeats if catalog is tiny.
                if catalog_items and members:
                    for m in members:
                        n_grant = 2 + rng.randint(0, 2)  # 2–4 each — light manual-style bags
                        for it in _pick_items_for_grant(catalog_items, n_grant, rng):
                            UserItem.objects.create(project_member=m, item=it)

                # Collections for defeated boss (same Dracula / b01 as ProjectBoss rows).
                for m in rng.sample(members, k=min(len(members), rng.randint(2, 4))):
                    UserBossCollection.objects.get_or_create(
                        user=m.user,
                        boss=main_boss,
                        project=proj,
                    )

                if proj.status == "Working":
                    invite_local = f"hiring.proj{pidx+1}.{secrets.token_hex(3)}"
                    ProjectInviteToken.objects.create(
                        project=proj,
                        email=f"{invite_local}@partner.example.com",
                        token=secrets.token_urlsafe(24)[:128],
                        expired_at=now + timedelta(days=30),
                    )

            # Real achievement IDs (01–06): see achievement_service + injected logs on project 1.
            if projects and project_members:
                lead0 = next(
                    (m for m in project_members[0] if m.user.username == first_u),
                    None,
                )
                if lead0:
                    ca0 = now - timedelta(days=specs[0]["start_days_ago"])
                    _inject_canonical_achievement_logs(
                        project=projects[0],
                        lead=lead0,
                        created_at=ca0,
                        rng=rng,
                    )

            # ProjectEndSummary rows power /api/user/finished-projects/ (not Project.status alone).
            # Only fields the ORM + get_project_end_summary().values() use (no extra columns).
            for pidx, proj in enumerate(projects):
                if proj.status != "Done":
                    continue
                members = project_members[pidx]
                boss_rows = ProjectBoss.objects.filter(project=proj, status="Dead").select_related(
                    "boss"
                )
                boss_list = []
                for pb in boss_rows:
                    if pb.boss_id:
                        boss_list.append(
                            {
                                "id": str(pb.boss.boss_id),
                                "name": pb.boss.boss_name,
                                "type": pb.boss.boss_type,
                            }
                        )
                boss_count = len(boss_list)

                scored = []
                for m in members:
                    dmg_deal = (
                        UserAttack.objects.filter(
                            project_member=m,
                            project_boss__project=proj,
                        ).aggregate(total=Sum("damage_point"))["total"]
                        or 0
                    )
                    dmg_recv = (
                        BossAttack.objects.filter(
                            project_member=m,
                            project_boss__project=proj,
                        ).aggregate(total=Sum("damage_point"))["total"]
                        or 0
                    )
                    done_n = UserTask.objects.filter(
                        project_member=m,
                        task__project=proj,
                        task__status="done",
                    ).count()
                    total_score = int(m.score + done_n * 12 + dmg_deal // 4)
                    scored.append((total_score, dmg_deal, dmg_recv, m))

                scored.sort(key=lambda x: x[0], reverse=True)
                for order, (total_score, dmg_deal, dmg_recv, m) in enumerate(scored, start=1):
                    display_name = (m.user.name or m.user.username or "Member")[:255]
                    ProjectEndSummary.objects.create(
                        project_member_id=m.project_member_id,
                        project_id=proj.project_id,
                        user_id=m.user.user_id,
                        order=order,
                        name=display_name,
                        username=m.user.username,
                        score=total_score,
                        damage_deal=int(dmg_deal),
                        damage_receive=int(dmg_recv),
                        status=m.status,
                        is_mvp=(order == 1),
                        boss=boss_list,
                        boss_count=boss_count,
                        reduction_percent=None,
                    )

            # Backdate tasks created_at
            for pidx, proj in enumerate(projects):
                base = now - timedelta(days=specs[pidx]["start_days_ago"])
                for t in Task.objects.filter(project=proj).iterator():
                    delta = timedelta(
                        days=rng.randint(0, max(1, specs[pidx]["start_days_ago"] - 1)),
                        hours=rng.randint(0, 20),
                    )
                    Task.objects.filter(pk=t.pk).update(created_at=base + delta)

        self.stdout.write(self.style.SUCCESS("Demo world seeded."))
        self.stdout.write(
            f"  Log in as {first_u!r} / {password!r} (plus {prefix}_02 … {prefix}_{n_players:02d})."
        )
        self.stdout.write(f"  Projects: {n_projects}  Players: {n_players}  Tasks/project ≈ {tasks_per}")
