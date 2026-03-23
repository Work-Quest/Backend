import logging

from django.conf import settings
from django.db import transaction

import requests
from requests import exceptions as req_exc

from api.models.Project import Project
from api.models.ProjectMember import ProjectMember
from api.models.UserFeedback import UserFeedback


class feedbackService:
    def __init__(self):
        self.AI_SERVICE_URL = settings.AI_SERVICE_URL
        self.ETL_SERVICE_URL = getattr(settings, "ETL_SERVICE_URL", None)

    @transaction.atomic
    def get_feedback(self, project_member_id, project_id):
        """
        Get personalize feedback from AI_service
        """
        user_feedback = UserFeedback.objects.filter(user_id=project_member_id, project_id=project_id).first()

        # if don't have feedback existed then call ETL service first, then AI service to get feedback and save to database
        if not user_feedback:
            # # Call ETL service to process data before generating feedback (first-time calculation)
            # if self.ETL_SERVICE_URL:
            #     try:
            #         etl_url = (self.ETL_SERVICE_URL or "").strip()
            #         if not etl_url.rstrip("/").endswith("/etl/run"):
            #             etl_url = etl_url.rstrip("/") + "/etl/run"

            #         etl_response = requests.post(
            #             etl_url,
            #             timeout=300,  # ETL can take a while, allow up to 5 minutes
            #         )

            #         if etl_response.status_code == 200:
            #             etl_data = etl_response.json() or {}
            #             if etl_data.get("status") == "SUCCESS":
            #                 print(f"ETL service completed successfully: {etl_data.get('duration_seconds', 0):.2f}s")
            #             else:
            #                 print(f"ETL service completed with status: {etl_data.get('status', 'UNKNOWN')}")
            #         else:
            #             # Log the full error response to see what went wrong
            #             print(f"ETL service returned status code {etl_response.status_code}")
            #             try:
            #                 etl_data = etl_response.json() or {}
            #                 print(f"ETL Error Details:")
            #                 print(f"  Status: {etl_data.get('status', 'UNKNOWN')}")
            #                 print(f"  Duration: {etl_data.get('duration_seconds', 0)}s")
            #                 if etl_data.get('stderr'):
            #                     print(f"  Stderr: {etl_data.get('stderr', '')[:1000]}")  # First 1000 chars
            #                 if etl_data.get('stdout'):
            #                     print(f"  Stdout: {etl_data.get('stdout', '')[:500]}")  # First 500 chars
            #             except Exception as e:
            #                 print(f"Could not parse error response: {e}")
            #                 print(f"Response text: {etl_response.text[:500]}")
            #     except req_exc.RequestException as e:
            #         print(f"ETL service is unreachable at {etl_url}: {e}. Continuing with feedback generation.")
            #     except Exception as e:
            #         print(f"Error calling ETL service: {e}. Continuing with feedback generation.")
            # else:
            #     print("ETL_SERVICE_URL not configured, skipping ETL call")
            # get user name 
            member = ProjectMember.objects.get(project_member_id=project_member_id)
            user_name = member.user.username
            project = Project.objects.get(project_id=project_id)
            
            data = {
                "project_member_id": str(project_member_id),
                "user_name": user_name
            }

            url = (self.AI_SERVICE_URL or "").strip()
            if not url:
                raise Exception("AI_SERVICE_URL is not configured")
            if not url.rstrip("/").endswith("/feedback"):
                url = url.rstrip("/") + "/feedback"

            try:
                response = requests.post(
                    url,
                    json=data,
                    timeout=300,
                )
            except req_exc.RequestException as e:
                raise Exception(f"AI service is unreachable at {url}: {e}")
            if response.status_code != 200:
                raise Exception("AI service error")

            try:
                response_data = response.json() or {}
            except Exception as e:
                raise Exception(f"AI service returned invalid JSON: {e}")
            
            user_feedback = UserFeedback.objects.create(
                user=member,
                project=project,
                feedback_text=response_data.get("feedback"),
                overall_quality_score=response_data.get("overall_quality_score"),
                team_work=response_data.get("team_work"),
                strength=response_data.get("work_category"),
                work_load_per_day=response_data.get("work_load_per_day"),
                work_speed=response_data.get("work_speed"),
                role_assigned=response_data.get("assigned_role"),
                diligence=response_data.get("diligence"),
                )   
            
        return user_feedback

        
