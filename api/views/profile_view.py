
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.services.auth_service import register_user, login_user
from rest_framework import status
from api.models import BusinessUser
from api.services.cache_service import CacheService
from api.services.project_service import ProjectService


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    cache_svc = CacheService()

    def _load():
        userData = BusinessUser.objects.get(username=user.username)
        return {
            "id": userData.user_id,
            "username": userData.username,
            "name": userData.name,
            "email": userData.email,
            "profile_img": userData.profile_img,
        }

    data = cache_svc.read_through(
        key=cache_svc.keys.user_me(user.id),
        ttl_seconds=30,
        loader=_load,
    )
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_finished_projects(request):
    """
    Get finished projects for a user.
    Returns list of projects with project_name, score, and boss_count.
    Accepts optional user_id query parameter. If not provided, uses authenticated user.
    """
    try:
        user_id = request.query_params.get('user_id', None)
        
        if user_id:
            # Fetch data for specified user
            try:
                target_user = BusinessUser.objects.get(user_id=user_id)
            except BusinessUser.DoesNotExist:
                return Response(
                    {"error": "User not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            project_service = ProjectService()
            finished_projects = project_service.get_user_finished_projects(user_id=user_id)
        else:
            # Use authenticated user (backward compatible)
            cur_user = request.user
            user = BusinessUser.objects.get(auth_user=cur_user)
            project_service = ProjectService()
            finished_projects = project_service.get_user_finished_projects(user=user)
        
        return Response(
            finished_projects,
            status=status.HTTP_200_OK,
        )
    except BusinessUser.DoesNotExist:
        return Response(
            {"error": "User not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_profile_stats(request):
    """
    Get user profile statistics including highest score, project count, and total bosses defeated.
    Accepts optional user_id query parameter. If not provided, uses authenticated user.
    """
    try:
        user_id = request.query_params.get('user_id', None)
        
        if user_id:
            # Fetch data for specified user
            try:
                target_user = BusinessUser.objects.get(user_id=user_id)
            except BusinessUser.DoesNotExist:
                return Response(
                    {"error": "User not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            project_service = ProjectService()
            stats = project_service.get_user_profile_stats(user_id=user_id)
        else:
            # Use authenticated user (backward compatible)
            cur_user = request.user
            user = BusinessUser.objects.get(auth_user=cur_user)
            project_service = ProjectService()
            stats = project_service.get_user_profile_stats(user=user)
        
        return Response(
            stats,
            status=status.HTTP_200_OK,
        )
    except BusinessUser.DoesNotExist:
        return Response(
            {"error": "User not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_defeated_bosses(request):
    """
    Get unique bosses defeated by a user.
    Returns list of bosses with id, name, and type.
    Accepts optional user_id query parameter. If not provided, uses authenticated user.
    """
    try:
        user_id = request.query_params.get('user_id', None)
        
        if user_id:
            # Fetch data for specified user
            try:
                target_user = BusinessUser.objects.get(user_id=user_id)
            except BusinessUser.DoesNotExist:
                return Response(
                    {"error": "User not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            project_service = ProjectService()
            defeated_bosses = project_service.get_user_defeated_bosses(user_id=user_id)
        else:
            # Use authenticated user (backward compatible)
            cur_user = request.user
            user = BusinessUser.objects.get(auth_user=cur_user)
            project_service = ProjectService()
            defeated_bosses = project_service.get_user_defeated_bosses(user=user)
        
        return Response(
            defeated_bosses,
            status=status.HTTP_200_OK,
        )
    except BusinessUser.DoesNotExist:
        return Response(
            {"error": "User not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )