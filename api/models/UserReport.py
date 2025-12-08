from django.db import models
from .Report import Report
from .BusinessUser import BusinessUser

class UserReport(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="user_reports")
    reviewer = models.ForeignKey(BusinessUser, on_delete=models.CASCADE, related_name="given_reports")
    receiver = models.ForeignKey(BusinessUser, on_delete=models.CASCADE, related_name="received_reports")
