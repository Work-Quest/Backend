"""
WorkQuest Django admin — conventions:

- ``WorkQuestModelAdmin``: consistent UX; FKs use classic HTML ``<select>`` dropdowns
  (no autocomplete), with ordered querysets and ``select_related`` where helpful.
- ``list_select_related`` / ``list_prefetch_related``: fewer queries on changelists.
- Audit tables (``TaskLog``, ``ActivityLog``): no manual create; mutate only as superuser.
"""

from __future__ import annotations

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models.Achievement import Achievement
from .models.ActivityLog import ActivityLog
from .models.Boss import Boss
from .models.BossAttack import BossAttack
from .models.BusinessUser import BusinessUser
from .models.Effect import Effect
from .models.Item import Item
from .models.Project import Project
from .models.ProjectBoss import ProjectBoss
from .models.ProjectEndSummary import ProjectEndSummary
from .models.ProjectMember import ProjectMember
from .models.Report import Report
from .models.StatusEffect import StatusEffect
from .models.Task import Task
from .models.TaskLog import TaskLog
from .models.UserAchievement import UserAchievement
from .models.UserAttack import UserAttack
from .models.UserBossCollection import UserBossCollection
from .models.UserEffect import UserEffect
from .models.UserFeedback import UserFeedback
from .models.UserItem import UserItem
from .models.UserReport import UserReport
from .models.UserTask import UserTask

# ---------------------------------------------------------------------------
# Site branding (staff UX)
# ---------------------------------------------------------------------------

admin.site.site_header = _("WorkQuest administration")
admin.site.site_title = _("WorkQuest admin")
admin.site.index_title = _("Operations")

if admin.site.is_registered(User):
    admin.site.unregister(User)


@admin.register(User)
class WorkQuestUserAdmin(DjangoUserAdmin):
    search_fields = list(DjangoUserAdmin.search_fields)


# ---------------------------------------------------------------------------
# Base classes
# ---------------------------------------------------------------------------


class WorkQuestModelAdmin(admin.ModelAdmin):
    """Defaults for all app model admins."""

    empty_value_display = "—"
    save_on_top = True
    list_per_page = 50
    preserve_filters = True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Use readable, ordered querysets for every FK dropdown (default admin widget)."""
        model = db_field.remote_field.model
        qs = kwargs.get("queryset")

        if qs is None:
            qs = model._default_manager.all()

        if model is Project:
            qs = qs.order_by("project_name")
        elif model is BusinessUser:
            qs = qs.order_by("username")
        elif model is ProjectMember:
            qs = qs.select_related("user", "project").order_by(
                "project__project_name", "user__username"
            )
        elif model is Task:
            qs = qs.select_related("project").order_by(
                "project__project_name", "task_name"
            )
        elif model is Boss:
            qs = qs.order_by("boss_name")
        elif model is ProjectBoss:
            qs = qs.select_related("project", "boss").order_by(
                "project__project_name", "boss__boss_name"
            )
        elif model is Effect:
            qs = qs.order_by("effect_type", "value")
        elif model is Item:
            qs = qs.order_by("name")
        elif model is Achievement:
            qs = qs.order_by("name")
        elif model is Report:
            qs = qs.select_related("task", "task__project").order_by("-created_at")
        elif model is User:
            qs = qs.order_by("username")

        kwargs["queryset"] = qs
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        qs = kwargs.get("queryset")
        if qs is None:
            qs = db_field.remote_field.model._default_manager.all()
        if db_field.remote_field.model is Effect:
            qs = qs.order_by("effect_type", "value")
        kwargs["queryset"] = qs
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class AuditLogModelAdmin(WorkQuestModelAdmin):
    """
    Immutable-style logs: no manual create; staff can list/view read-only; only
    superusers may edit or delete (cleanup / incidents).
    """

    def has_view_permission(self, request, obj=None) -> bool:
        return bool(request.user.is_active and request.user.is_staff)

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return bool(request.user.is_superuser)

    def has_delete_permission(self, request, obj=None) -> bool:
        return bool(request.user.is_superuser)


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


class _ProjectMemberSelectWithProject(forms.Select):
    """Adds data-project-id on each <option> so admin JS can filter by project."""

    def __init__(self, *args, member_project_map=None, **kwargs):
        self.member_project_map = member_project_map or {}
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        if value not in (None, ""):
            pid = self.member_project_map.get(str(value))
            if pid is not None:
                option["attrs"]["data-project-id"] = pid
        return option


class ProjectEndSummaryAdminForm(forms.ModelForm):
    """
    Add flow: pick project (optional filter) + project member from dropdowns;
    status and boss snapshot use selects instead of opaque JSON/IDs.
    """

    project_filter = forms.ModelChoiceField(
        queryset=Project.objects.order_by("project_name"),
        required=False,
        label=_("Narrow by project"),
        empty_label=_("All projects — show every member"),
        help_text=_(
            "Optional: choose a project first to shorten the member list "
            "(members from other projects are disabled until you change this)."
        ),
    )

    project_member = forms.ModelChoiceField(
        queryset=ProjectMember.objects.none(),
        required=True,
        label=_("Project member"),
        help_text=_(
            "One leaderboard row per member. UUIDs are filled from this row; "
            "members who already have a summary are hidden when adding."
        ),
    )

    status = forms.ChoiceField(
        label=_("Member status"),
        choices=ProjectMember.STATUS_CHOICES,
        initial="Alive",
        help_text=_("Same values as project membership (Alive / Dead)."),
    )

    boss_preset = forms.ChoiceField(
        label=_("Boss snapshot"),
        choices=[
            (
                "from_project",
                _("Defeated bosses from this member’s project (same as app automation)"),
            ),
            ("empty", _("No bosses — empty list and boss count 0")),
            ("manual", _("Enter boss JSON and count manually below")),
        ],
        initial="from_project",
        help_text=_(
            "Avoids typing JSON unless you choose “manual”. "
            "“Defeated bosses” uses bosses marked Dead on that project."
        ),
    )

    class Meta:
        model = ProjectEndSummary
        fields = [
            "order",
            "name",
            "username",
            "score",
            "damage_deal",
            "damage_receive",
            "status",
            "is_mvp",
            "boss",
            "boss_count",
            "reduction_percent",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inst = self.instance

        if inst.pk:
            del self.fields["project_filter"]
            self.fields["boss_preset"].initial = "manual"
            st = inst.status
            if st and st not in dict(ProjectMember.STATUS_CHOICES):
                self.fields["status"].choices = list(ProjectMember.STATUS_CHOICES) + [
                    (st, st)
                ]
        else:
            self.initial.setdefault("boss", [])
            self.initial.setdefault("boss_count", 0)
            self.initial.setdefault("is_mvp", False)
            self.initial.setdefault("order", 1)

        base_pm = ProjectMember.objects.select_related("user", "project").order_by(
            "project__project_name", "user__username"
        )
        if inst.pk:
            pm_qs = base_pm
        else:
            taken = ProjectEndSummary.objects.values_list(
                "project_member_id", flat=True
            )
            pm_qs = base_pm.exclude(project_member_id__in=taken)

        # Build map from the same queryset the field will use.
        member_project_map = {str(m.pk): str(m.project_id) for m in pm_qs}
        # Widget must be set *before* assigning queryset: the queryset setter
        # does ``widget.choices = field.choices``. Replacing the widget after
        # that left an empty <select> (no options).
        self.fields["project_member"].widget = _ProjectMemberSelectWithProject(
            member_project_map=member_project_map
        )
        self.fields["project_member"].queryset = pm_qs

        if inst.pk:
            member = (
                ProjectMember.objects.select_related("user", "project")
                .filter(project_member_id=inst.project_member_id)
                .first()
            )
            if member is not None:
                self.fields["project_member"].initial = member
            self.fields["project_member"].disabled = True

    def full_clean(self):
        data = self.data
        if data:
            preset = data.get(self.add_prefix("boss_preset"))
            if preset is None:
                preset = data.get("boss_preset", "manual")
            if preset in ("from_project", "empty"):
                mutable = data.copy()
                mutable[self.add_prefix("boss")] = "[]"
                if preset == "empty":
                    mutable[self.add_prefix("boss_count")] = "0"
                self.data = mutable
        super().full_clean()

    def clean_project_member(self):
        member = self.cleaned_data["project_member"]
        if not self.instance.pk:
            if ProjectEndSummary.objects.filter(pk=member.project_member_id).exists():
                raise ValidationError(
                    _(
                        "This project member already has an end summary. "
                        "Edit that row or pick another member."
                    )
                )
        return member

    def save(self, commit=True):
        obj = super().save(commit=False)
        member = self.cleaned_data.get("project_member")
        if member is None and self.instance.pk:
            member = (
                ProjectMember.objects.select_related("user")
                .filter(project_member_id=self.instance.project_member_id)
                .first()
            )
        if member is not None:
            if not self.instance.pk:
                obj.project_member_id = member.project_member_id
            obj.project_id = member.project_id
            obj.user_id = member.user.user_id
            name = (obj.name or "").strip()
            username = (obj.username or "").strip()
            if not name:
                obj.name = member.user.name or member.user.username
            if not username:
                obj.username = member.user.username

        preset = self.cleaned_data.get("boss_preset", "manual")
        if preset == "from_project" and member is not None:
            dead = (
                ProjectBoss.objects.filter(
                    project_id=member.project_id, status="Dead"
                )
                .select_related("boss")
                .order_by("boss__boss_name")
            )
            boss_list = []
            for pb in dead:
                if pb.boss_id:
                    boss_list.append(
                        {
                            "id": str(pb.boss.boss_id),
                            "name": pb.boss.boss_name,
                            "type": pb.boss.boss_type,
                        }
                    )
            obj.boss = boss_list
            obj.boss_count = len(boss_list)
        elif preset == "empty":
            obj.boss = []
            obj.boss_count = 0
        # manual: values already on obj from ModelForm

        if commit:
            obj.save()
        return obj


@admin.register(ProjectEndSummary)
class ProjectEndSummaryAdmin(WorkQuestModelAdmin):
    form = ProjectEndSummaryAdminForm

    class Media:
        js = ("admin/js/project_end_summary_filter.js",)

    list_display = (
        "username",
        "name",
        "score",
        "user_id",
        "project_id",
        "updated_at",
    )
    list_filter = ("updated_at",)
    search_fields = ("name", "username", "user_id", "project_id", "project_member_id")
    ordering = ("-score", "-updated_at")
    date_hierarchy = "updated_at"

    def get_readonly_fields(self, request, obj=None):
        ro = ["updated_at"]
        if obj:
            ro.extend(["project_member_id", "project_id", "user_id"])
        return ro

    def get_fieldsets(self, request, obj=None):
        member_fields = (
            ("project_filter", "project_member") if obj is None else ("project_member",)
        )
        member_block = (
            _("Member"),
            {
                "description": _(
                    "Global leaderboard shows each user’s highest score (top 10). "
                    "Pick the project member this row is for; stored UUIDs are set automatically."
                ),
                "fields": member_fields,
            },
        )
        ids_block = (
            _("Linked IDs (read-only)"),
            {
                "description": _("Stored UUIDs for APIs and joins."),
                "fields": ("project_member_id", "project_id", "user_id"),
            },
        )
        scores_block = (
            _("Display & scores"),
            {
                "fields": (
                    "order",
                    "name",
                    "username",
                    "score",
                    "damage_deal",
                    "damage_receive",
                    "status",
                    "is_mvp",
                ),
            },
        )
        boss_block = (
            _("Boss snapshot"),
            {
                "description": _(
                    "Use the “Boss snapshot” dropdown for typical cases; "
                    "only edit JSON when you chose “manual”."
                ),
                "fields": ("boss_preset", "boss", "boss_count", "reduction_percent"),
            },
        )
        meta_block = (_("Meta"), {"fields": ("updated_at",)})
        if obj:
            return (member_block, ids_block, scores_block, boss_block, meta_block)
        return (member_block, scores_block, boss_block, meta_block)


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


@admin.register(BusinessUser)
class BusinessUserAdmin(WorkQuestModelAdmin):
    list_display = (
        "username",
        "name",
        "email",
        "user_id",
        "selected_character_id",
        "bg_color_id",
        "is_first_time",
    )
    list_filter = ("is_first_time",)
    search_fields = ("username", "name", "email", "user_id")
    ordering = ("username",)
    readonly_fields = ("user_id",)

    fieldsets = (
        (None, {"fields": ("user_id", "auth_user", "username", "name", "email")}),
        (
            _("Profile"),
            {"fields": ("profile_img", "selected_character_id", "bg_color_id", "is_first_time")},
        ),
    )


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0
    show_change_link = True
    fields = ("user", "hp", "max_hp", "score", "status")


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    show_change_link = True
    fields = ("task_name", "status", "priority", "deadline", "description")


class ProjectBossInline(admin.TabularInline):
    model = ProjectBoss
    extra = 0
    show_change_link = True
    fields = ("boss", "hp", "max_hp", "status", "phase")


@admin.register(Project)
class ProjectAdmin(WorkQuestModelAdmin):
    list_display = (
        "project_name",
        "project_id",
        "owner",
        "status",
        "completed_tasks",
        "total_tasks",
        "created_at",
        "deadline",
    )
    list_filter = ("status", "deadline_decision", "created_at")
    search_fields = ("project_name", "project_id")
    ordering = ("-created_at",)
    readonly_fields = ("project_id", "created_at")
    date_hierarchy = "created_at"
    list_select_related = ("owner",)
    inlines = (ProjectMemberInline, TaskInline, ProjectBossInline)

    fieldsets = (
        (None, {"fields": ("project_id", "owner", "project_name")}),
        (_("Progress"), {"fields": ("status", "total_tasks", "completed_tasks", "deadline")}),
        (_("Deadline decision"), {"fields": ("deadline_decision", "deadline_decision_date")}),
        (_("Meta"), {"fields": ("created_at",)}),
    )


@admin.register(ProjectMember)
class ProjectMemberAdmin(WorkQuestModelAdmin):
    list_display = (
        "project_member_id",
        "user",
        "project",
        "hp",
        "max_hp",
        "score",
        "status",
    )
    list_filter = ("status",)
    search_fields = (
        "project_member_id",
        "user__username",
        "user__name",
        "project__project_name",
    )
    ordering = ("-score",)
    list_select_related = ("user", "project")


@admin.register(Task)
class TaskAdmin(WorkQuestModelAdmin):
    list_display = (
        "task_name",
        "project",
        "status",
        "priority",
        "created_at",
        "deadline",
        "completed_at",
    )
    list_filter = ("status", "priority", "created_at")
    search_fields = ("task_name", "task_id", "description", "project__project_name")
    ordering = ("-created_at",)
    readonly_fields = ("task_id", "created_at")
    date_hierarchy = "created_at"
    list_select_related = ("project",)


@admin.register(UserTask)
class UserTaskAdmin(WorkQuestModelAdmin):
    list_display = ("project_member", "task")
    search_fields = (
        "project_member__user__username",
        "task__task_name",
        "task__task_id",
    )
    list_select_related = ("project_member__user", "project_member__project", "task")


# ---------------------------------------------------------------------------
# Bosses & combat
# ---------------------------------------------------------------------------


@admin.register(Boss)
class BossAdmin(WorkQuestModelAdmin):
    list_display = ("boss_name", "boss_type", "boss_id")
    list_filter = ("boss_type",)
    search_fields = ("boss_name", "boss_id")
    readonly_fields = ("boss_id",)


@admin.register(ProjectBoss)
class ProjectBossAdmin(WorkQuestModelAdmin):
    list_display = ("project", "boss", "hp", "max_hp", "status", "phase", "updated_at")
    list_filter = ("status", "phase", "created_at")
    search_fields = (
        "project_boss_id",
        "project__project_name",
        "boss__boss_name",
    )
    readonly_fields = ("project_boss_id", "created_at")
    date_hierarchy = "created_at"
    list_select_related = ("project", "boss")


@admin.register(BossAttack)
class BossAttackAdmin(WorkQuestModelAdmin):
    list_display = ("project_boss", "damage_point", "project_member", "timestamp")
    list_filter = ("timestamp",)
    search_fields = ("boss_attack_id",)
    readonly_fields = ("boss_attack_id", "timestamp")
    date_hierarchy = "timestamp"
    list_select_related = ("project_boss__project", "project_boss__boss", "project_member__user")


@admin.register(UserAttack)
class UserAttackAdmin(WorkQuestModelAdmin):
    list_display = ("project_member", "damage_point", "project_boss", "timestamp")
    list_filter = ("timestamp",)
    readonly_fields = ("user_attack_id", "timestamp")
    date_hierarchy = "timestamp"
    list_select_related = ("project_member__user", "project_boss__boss", "project_boss__project")


# ---------------------------------------------------------------------------
# Effects & items
# ---------------------------------------------------------------------------


@admin.register(Effect)
class EffectAdmin(WorkQuestModelAdmin):
    list_display = ("effect_type", "value", "effect_polarity", "rare_level", "created_at")
    list_filter = ("effect_type", "effect_polarity", "created_at")
    search_fields = ("description", "effect_id")
    readonly_fields = ("effect_id", "created_at")
    date_hierarchy = "created_at"


@admin.register(StatusEffect)
class StatusEffectAdmin(WorkQuestModelAdmin):
    list_display = ("name", "category", "duration_turns", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("name", "description", "status_effect_id")
    filter_vertical = ("effects",)
    readonly_fields = ("status_effect_id", "created_at")
    date_hierarchy = "created_at"


@admin.register(UserEffect)
class UserEffectAdmin(WorkQuestModelAdmin):
    list_display = ("project_member", "effect", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user_effect_id", "effect__effect_type")
    readonly_fields = ("user_effect_id", "created_at")
    date_hierarchy = "created_at"
    list_select_related = ("project_member__user", "effect")


@admin.register(Item)
class ItemAdmin(WorkQuestModelAdmin):
    list_display = ("name", "effects", "created_at")
    search_fields = ("name", "description", "item_id")
    readonly_fields = ("item_id", "created_at")
    date_hierarchy = "created_at"
    list_select_related = ("effects",)


@admin.register(UserItem)
class UserItemAdmin(WorkQuestModelAdmin):
    list_display = ("project_member", "item", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user_item_id", "item__name")
    readonly_fields = ("user_item_id", "created_at")
    date_hierarchy = "created_at"
    list_select_related = ("project_member__user", "item")


# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------


@admin.register(Achievement)
class AchievementAdmin(WorkQuestModelAdmin):
    list_display = ("name", "achievement_id")
    search_fields = ("name", "description", "achievement_id")
    readonly_fields = ("achievement_id",)


@admin.register(UserAchievement)
class UserAchievementAdmin(WorkQuestModelAdmin):
    list_display = ("user", "achievement", "project", "awarded_at")
    list_filter = ("awarded_at",)
    search_fields = ("user__username", "achievement__name", "project__project_name")
    readonly_fields = ("awarded_at",)
    date_hierarchy = "awarded_at"
    list_select_related = ("user", "achievement", "project")


@admin.register(UserBossCollection)
class UserBossCollectionAdmin(WorkQuestModelAdmin):
    list_display = ("user", "boss", "project", "defeat_at")
    list_filter = ("defeat_at",)
    search_fields = ("user__username", "boss__boss_name", "project__project_name")
    readonly_fields = ("defeat_at",)
    date_hierarchy = "defeat_at"
    list_select_related = ("user", "boss", "project")


# ---------------------------------------------------------------------------
# Reports & feedback
# ---------------------------------------------------------------------------


@admin.register(Report)
class ReportAdmin(WorkQuestModelAdmin):
    list_display = ("report_id", "task", "reporter", "sentiment_score", "created_at")
    list_filter = ("created_at", "sentiment_score")
    search_fields = ("report_id", "description")
    readonly_fields = ("report_id", "created_at")
    date_hierarchy = "created_at"
    list_select_related = ("task__project", "reporter__user")


@admin.register(UserReport)
class UserReportAdmin(WorkQuestModelAdmin):
    list_display = ("report", "reviewer", "receiver")
    search_fields = ("report__report_id",)
    list_select_related = ("report", "reviewer__user", "receiver__user")


@admin.register(UserFeedback)
class UserFeedbackAdmin(WorkQuestModelAdmin):
    list_display = (
        "feedback_id",
        "user",
        "project",
        "overall_quality_score",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = (
        "feedback_id",
        "feedback_text",
        "user__user__username",
        "user__user__name",
    )
    readonly_fields = ("feedback_id", "created_at")
    date_hierarchy = "created_at"
    list_select_related = ("user__user", "project")


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------


@admin.register(TaskLog)
class TaskLogAdmin(AuditLogModelAdmin):
    list_display = ("created_at", "event_type", "project_id", "actor_type", "actor_id")
    list_filter = ("event_type", "actor_type", "created_at")
    search_fields = ("id", "project_id", "actor_id")
    readonly_fields = ("id", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(ActivityLog)
class ActivityLogAdmin(AuditLogModelAdmin):
    list_display = ("created_at", "action", "project_id", "target_type", "target_id", "user")
    list_filter = ("action", "target_type", "created_at")
    search_fields = ("activity_id", "project_id", "target_id")
    readonly_fields = ("activity_id", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("user",)
