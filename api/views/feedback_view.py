from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import BusinessUser
from api.models.ProjectMember import ProjectMember
from api.serializers.feedback_serializer import UserFeedbackSerializer
from api.services.feedback_service import feedbackService


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_project_feedback(request, project_id):
    """
    GET /project/<uuid:project_id>/feedback/

    Returns personalized feedback for the authenticated user's membership in the project.
    """
    try:
        cur_user = request.user
        user = BusinessUser.objects.get(auth_user=cur_user)

        requester_member = ProjectMember.objects.get(project_id=project_id, user=user)
        fb = feedbackService().get_feedback(requester_member.project_member_id, project_id)

        return Response(UserFeedbackSerializer(fb).data, status=status.HTTP_200_OK)
    except BusinessUser.DoesNotExist:
        return Response({"error": "Business user profile not found"}, status=status.HTTP_400_BAD_REQUEST)
    except ProjectMember.DoesNotExist:
        return Response({"error": "User is not a member of this project."}, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


