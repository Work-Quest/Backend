from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.services.ai_service import AIService


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def analyze_sentiment(request):
    """
    POST /ai/sentiment/

    Body:
      { "text": "..." }
    """

    text = (request.data or {}).get("text", "")
    if not isinstance(text, str) or not text.strip():
        return Response({"error": "text is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = AIService().analyze_sentiment(text)
        return Response(result, status=status.HTTP_200_OK)
    except RuntimeError as e:
        # e.g. HuggingFace analyzer not installed/configured
        return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)




