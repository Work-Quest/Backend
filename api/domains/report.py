from __future__ import annotations

from dataclasses import dataclass

from api.models import Report as ReportModel, Task
from api.domains.project_member import ProjectMember


@dataclass(frozen=True)
class CreateReportCommand:
    """
    Command object for creating a Report (review/report content).
    Keep this minimal; extend as you add more report fields.
    """

    task_id: str
    report_name: str
    description: str


class Report:
    def __init__(self, report_model: ReportModel):
        self._report = report_model


    @property
    def report(self) -> ReportModel:
        return self._report

    @property
    def report_id(self):
        return self._report.report_id

    @property
    def task(self):
        return self._report.task
    
    @property
    def task_id(self):
        return self._report.task.task_id

    @property
    def description(self):
        return self._report.description

    @description.setter
    def description(self, value: str):
        self._report.description = value
        self._report.save(update_fields=["description"])

    @property
    def reporter(self):
        return ProjectMember(self._report.reporter)

    @property
    def sentiment_score(self):
        return self._report.sentiment_score

    @property
    def created_at(self):
        return self._report.created_at

    def delete(self):
        self._report.delete()

    def save(self):
        self._report.save()


