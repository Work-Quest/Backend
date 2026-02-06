# views/review_view.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from api.models import BusinessUser
from api.serializers.report_serializer import UserReportResponseSerializer
from api.services.review_service import ReviewService


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def review_report(request, project_id):
    """
    POST /review/report/

    Skeleton request body:

    {
      "task_id": "uuid",
      "description": "string"
    }

    Returns: created Report + computed signals/scores + applied effect decision.
    """
    try:
        cur_user = request.user
        user = BusinessUser.objects.get(auth_user=cur_user)
        report, user_report = ReviewService().create_review_report(request.data, user, project_id)
        data = UserReportResponseSerializer(user_report, many=True).data
        return Response(data, status=status.HTTP_201_CREATED)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
    except BusinessUser.DoesNotExist:
        return Response({"error": "Business user profile not found"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)




