from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import BusinessUser
from api.services.cache_service import CacheService
from api.services.project_service import ProjectService
from api.services.achievement_service import get_overall_achievement_ids_for_user


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    cache_svc = CacheService()

    if request.method == "PATCH":
        try:
            user_data = BusinessUser.objects.get(username=user.username)
        except BusinessUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        selected_character_id = request.data.get("selected_character_id")
        bg_color_id = request.data.get("bg_color_id")

        if selected_character_id is not None:
            try:
                selected_character_id = int(selected_character_id)
            except (TypeError, ValueError):
                return Response(
                    {"error": "selected_character_id must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if selected_character_id < 1 or selected_character_id > 9:
                return Response(
                    {"error": "selected_character_id must be between 1 and 9."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user_data.selected_character_id = selected_character_id

        if bg_color_id is not None:
            try:
                bg_color_id = int(bg_color_id)
            except (TypeError, ValueError):
                return Response(
                    {"error": "bg_color_id must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if bg_color_id < 1 or bg_color_id > 8:
                return Response(
                    {"error": "bg_color_id must be between 1 and 8."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user_data.bg_color_id = bg_color_id

        if selected_character_id is None and bg_color_id is None:
            return Response(
                {"error": "No updatable fields provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_data.save(update_fields=["selected_character_id", "bg_color_id"])
        cache_svc.delete(cache_svc.keys.user_me(user.id))
        cache_svc.invalidate_all_business_users()

        return Response({"message": "Profile updated."}, status=status.HTTP_200_OK)

    def _load():
        userData = BusinessUser.objects.get(username=user.username)
        return {
            "id": userData.user_id,
            "username": userData.username,
            "name": userData.name,
            "email": userData.email,
            "profile_img": userData.profile_img,
            "selected_character_id": userData.selected_character_id,
            "bg_color_id": userData.bg_color_id,
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
      
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_achievements(request):
    """
    GET /me/achievements/

    Returns overall achievement IDs the authenticated user has unlocked
    across all projects (for profile page).
    """
    try:
        user = request.user
        if not user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        business_user = BusinessUser.objects.get(auth_user=user)
        achievement_ids = get_overall_achievement_ids_for_user(business_user)
        return Response({"achievement_ids": achievement_ids}, status=status.HTTP_200_OK)
    except BusinessUser.DoesNotExist:
        return Response(
            {"error": "Business user profile not found"},
            status=status.HTTP_400_BAD_REQUEST,
        )