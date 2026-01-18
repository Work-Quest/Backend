from django.db import models
from .ProjectMember import ProjectMember
from .Report import Report

class UserReport(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="user_reports")
    reviewer = models.ForeignKey(ProjectMember, on_delete=models.CASCADE, related_name="given_reports")
    receiver = models.ForeignKey(ProjectMember, on_delete=models.CASCADE, related_name="received_reports")
