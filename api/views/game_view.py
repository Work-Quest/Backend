# views/game_view.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from api.models import BusinessUser
from api.models.ProjectMember import ProjectMember
from api.services.game_service import GameService
from api.serializers.game_serializer import BossSerializer, ProjectBossSerializer
from api.services.cache_service import CacheService

# -------------------------
# Boss Query
# -------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_project_boss(request, project_id):
    """
    Get the boss for a specific project.

    Returns boss information including HP, status, and boss details.
    """
    try:
        service = GameService()
        cache_svc = CacheService()

        def _load():
            boss_domain = service.get_project_boss(project_id)
            # Convert domain object to dict for serialization
            return {
                "project_boss_id": boss_domain.project_boss.project_boss_id,
                "project": boss_domain.project_boss.project.project_id,
                "boss": boss_domain.boss.boss_id if boss_domain.boss else None,
                "boss_name": boss_domain.name if boss_domain.boss else None,
                "boss_image": boss_domain.image if boss_domain.boss else None,
                "hp": boss_domain.hp,
                "max_hp": boss_domain.max_hp,
                "status": boss_domain.status,
                "phase": boss_domain.phase,
            }

        boss_data = cache_svc.read_through(
            key=cache_svc.keys.project_boss(project_id),
            ttl_seconds=5,
            loader=_load,
        )

        return Response(boss_data, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_all_bosses(request):
    """
    Get all available bosses in the system.
    """
    try:
        service = GameService()
        cache_svc = CacheService()
        data = cache_svc.read_through(
            key=cache_svc.keys.all_bosses(),
            ttl_seconds=300,
            loader=lambda: list(BossSerializer(service.get_all_bosses(), many=True).data),
        )
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


# -------------------------
# Boss Actions
# -------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def setup_project_boss(request, project_id):
    """
    Setup boss for a project.

    This endpoint selects a random boss and sets HP based on project tasks.
    Requires project ownership or membership.

    Request Body:

        {}  # No body required, boss is set up automatically
    """
    try:
        service = GameService()
        boss_domain = service.setup_boss_for_project(project_id)

        boss_data = {
            "project_boss_id": boss_domain.project_boss.project_boss_id,
            "project": boss_domain.project_boss.project.project_id,
            "boss": boss_domain.boss.boss_id,
            "boss_name": boss_domain.name,
            "boss_image": boss_domain.image,
            "hp": boss_domain.hp,
            "max_hp": boss_domain.max_hp,
            "status": boss_domain.status,
        }

        CacheService().invalidate_project_game(project_id)
        CacheService().invalidate_project_logs(project_id)

        return Response(
            {
                "message": "Boss setup completed successfully",
                "boss": boss_data
            },
            status=status.HTTP_200_OK,
        )
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


# -----------------
# Game Actions
# -----------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def player_attack(request, project_id):
    """
    Player attacks the boss using a completed task.

    Request Body:

        {
            "player_id": "uuid",  
            "task_id": "uuid"     
        }
    """
    try:
        player_id = request.data.get("player_id")
        task_id = request.data.get("task_id")

        if not player_id or not task_id:
            return Response(
                {"error": "player_id and task_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = GameService()
        result = service.player_attack(project_id, player_id, task_id)

        CacheService().invalidate_project_game(project_id)
        CacheService().invalidate_project_logs(project_id)
        CacheService().invalidate_project_member_status_effects(project_id)

        return Response(
            {
                "message": "Player attack successful",
                "result": result
            },
            status=status.HTTP_200_OK,
        )
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def boss_attack(request, project_id):
    """
    Boss attacks players assigned to a task.

    Request Body:

        {
            "task_id": "uuid"
        }
    """
    try:
        task_id = request.data.get("task_id")
        if not task_id:
            return Response(
                {"error": "task_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = GameService()
        result = service.boss_attack(project_id, task_id)

        CacheService().invalidate_project_game(project_id)
        CacheService().invalidate_project_logs(project_id)
        CacheService().invalidate_project_member_status_effects(project_id)

        return Response(
            {
                "message": "Boss attack successful",
                "result": result
            },
            status=status.HTTP_200_OK,
        )
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def player_heal(request, project_id):
    """
    Player heals another player.

    Request Body:
        {
            "healer_id": "uuid",  # ID of the healing player
            "player_id": "uuid",  # ID of the player to heal
            "heal_value": int     # Amount of HP to restore
        }
    """
    try:
        healer_id = request.data.get("healer_id")
        player_id = request.data.get("player_id")
        heal_value = request.data.get("heal_value")

        if not healer_id or not player_id or heal_value is None:
            return Response(
                {"error": "healer_id, player_id, and heal_value are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(heal_value, int) or heal_value <= 0:
            return Response(
                {"error": "heal_value must be a positive integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = GameService()
        result = service.player_heal(project_id, healer_id, player_id, heal_value)

        CacheService().invalidate_project_game(project_id)
        CacheService().invalidate_project_logs(project_id)

        return Response(
            {
                "message": "Player heal successful",
                "result": result
            },
            status=status.HTTP_200_OK,
        )
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def player_support(request, project_id):
    """
    Apply support (buff/effect or item) from a review Report.

    Body:
    
      { 
        "report_id": "uuid" 
      }
    """
    try:
        report_id = request.data.get("report_id")
        if not report_id:
            return Response(
                {"error": "report_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cur_user = request.user
        user = BusinessUser.objects.get(auth_user=cur_user)

        service = GameService()
        result = service.player_support(project_id, report_id, user)

        CacheService().invalidate_project_game(project_id)
        CacheService().invalidate_project_logs(project_id)
        CacheService().invalidate_project_member_items(project_id)
        CacheService().invalidate_project_member_status_effects(project_id)

        return Response(
            {
                "message": "Player support applied successfully",
                "result": result,
            },
            status=status.HTTP_200_OK,
        )
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
    except BusinessUser.DoesNotExist:
        return Response({"error": "Business user profile not found"}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# -----------------
# Real-time Status
# -----------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_boss_status(request, project_id):
    """
    Get real-time boss status for a project.

    Returns current HP, max HP, status, and boss information.
    """
    try:
        service = GameService()
        cache_svc = CacheService()
        boss_status = cache_svc.read_through(
            key=cache_svc.keys.boss_status(project_id),
            ttl_seconds=5,
            loader=lambda: service.get_boss_status(project_id),
        )

        return Response(boss_status, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_statuses(request, project_id):
    """
    Get real-time status for all users in a project.

    Returns HP, max HP, score, and status for all project members.
    """
    try:
        service = GameService()
        cache_svc = CacheService()
        user_statuses = cache_svc.read_through(
            key=cache_svc.keys.user_statuses(project_id),
            ttl_seconds=3,
            loader=lambda: service.get_user_statuses(project_id),
        )

        return Response(user_statuses, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_game_status(request, project_id):
    """
    Get comprehensive real-time game status including boss and all users.

    Returns combined status information for real-time updates.
    """
    try:
        service = GameService()
        cache_svc = CacheService()
        game_status = cache_svc.read_through(
            key=cache_svc.keys.game_status(project_id),
            ttl_seconds=3,
            loader=lambda: service.get_game_status(project_id),
        )

        return Response(game_status, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def setup_special_boss(request, project_id):
    """
    Setup special boss for a project.

    Request Body:

        {}  # No body required
    """
    try:
        service = GameService()
        project_boss_model = service.setup_special_boss(project_id)

        boss_data = {
            "project_boss_id": project_boss_model.project_boss_id,
            "project": project_boss_model.project.project_id,
            "boss": project_boss_model.boss.boss_id if project_boss_model.boss else None,
            "boss_name": project_boss_model.boss.boss_name if project_boss_model.boss else None,
            "boss_image": project_boss_model.boss.boss_image if project_boss_model.boss else None,
            "hp": project_boss_model.hp,
            "max_hp": project_boss_model.max_hp,
            "status": project_boss_model.status,
        }

        CacheService().invalidate_project_game(project_id)
        CacheService().invalidate_project_logs(project_id)

        return Response(
            {
                "message": "Special boss setup completed successfully",
                "boss": boss_data
            },
            status=status.HTTP_200_OK,
        )
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def revive(request, project_id):
    """
    Revive a dead player in a project.

    Request Body:

        {
            "player_id": "uuid"
        }
    """
    try:
        player_id = request.data.get("player_id")

        if not project_id or not player_id:
            return Response(
                {"error": "project_id and player_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = GameService()
        service.revive_player(project_id, player_id)

        CacheService().invalidate_project_game(project_id)
        CacheService().invalidate_project_logs(project_id)

        return Response(
            {
                "message": "Player revived successfully"
            },
            status=status.HTTP_200_OK,
        )
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


# -----------------
# Project Member Items
# -----------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_project_member_items(request, project_id):
    """
    List the currently logged-in user's owned items for this project.
    """
    try:
        cur_user = request.user
        user = BusinessUser.objects.get(auth_user=cur_user)

        requester_member = ProjectMember.objects.get(project_id=project_id, user=user)
        target_member_id = str(requester_member.project_member_id)

        service = GameService()
        cache_svc = CacheService()

        def _load():
            # Explicit player_id so the service uses the same member id as the cache key.
            return service.get_project_member_items(project_id, user, player_id=target_member_id)

        data = cache_svc.read_through(
            key=cache_svc.keys.project_member_items(project_id, target_member_id),
            ttl_seconds=3,
            loader=_load,
        )

        return Response(data, status=status.HTTP_200_OK)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
    except BusinessUser.DoesNotExist:
        return Response({"error": "Business user profile not found"}, status=status.HTTP_400_BAD_REQUEST)
    except ProjectMember.DoesNotExist:
        return Response({"error": "User is not a member of this project."}, status=status.HTTP_403_FORBIDDEN)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def use_project_member_item(request, project_id):
    """
    Use/consume an owned item and apply its effect.

    Body:
    
    {
        "item_id" : uuid,
        "player_id" : uuid
    }
    """
    try:
        cur_user = request.user
        user = BusinessUser.objects.get(auth_user=cur_user)

        item_id = request.data.get("item_id")
        player_id = request.data.get("player_id")
        if not item_id:
            return Response({"error": "item_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        service = GameService()
        # Default player_id to requester to support targeted cache invalidation
        requester_member = ProjectMember.objects.get(project_id=project_id, user=user)
        target_member_id = requester_member.project_member_id

        result = service.use_project_member_item(
            project_id,
            user,
            item_id=str(item_id),
            player_id=target_member_id,
        )

        CacheService().invalidate_project_game(project_id)
        CacheService().invalidate_project_logs(project_id)
        CacheService().invalidate_project_member_items(project_id, target_member_id)
        CacheService().invalidate_project_member_status_effects(project_id)

        return Response(
            {"message": "Item used successfully", "result": result},
            status=status.HTTP_200_OK,
        )
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
    except BusinessUser.DoesNotExist:
        return Response({"error": "Business user profile not found"}, status=status.HTTP_400_BAD_REQUEST)
    except ProjectMember.DoesNotExist:
        return Response({"error": "User is not a member of this project."}, status=status.HTTP_403_FORBIDDEN)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# -----------------
# Project Member Status + Effects
# -----------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_project_member_status_effects(request, project_id):
    """
    Get the currently logged-in user's status plus their current effects.
    """
    try:
        cur_user = request.user
        user = BusinessUser.objects.get(auth_user=cur_user)

        requester_member = ProjectMember.objects.get(project_id=project_id, user=user)
        target_member_id = str(requester_member.project_member_id)

        service = GameService()
        cache_svc = CacheService()
        data = cache_svc.read_through(
            key=cache_svc.keys.project_member_status_effects(project_id, target_member_id),
            ttl_seconds=3,
            loader=lambda: service.get_project_member_status_effects(project_id, user, player_id=target_member_id),
        )
        return Response(data, status=status.HTTP_200_OK)
    except PermissionError as e:
        return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
    except BusinessUser.DoesNotExist:
        return Response({"error": "Business user profile not found"}, status=status.HTTP_400_BAD_REQUEST)
    except ProjectMember.DoesNotExist:
        return Response({"error": "User is not a member of this project."}, status=status.HTTP_403_FORBIDDEN)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


