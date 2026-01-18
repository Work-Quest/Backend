# views/game_view.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from api.models import BusinessUser
from api.services.game_service import GameService
from api.serializers.game_serializer import BossSerializer, ProjectBossSerializer

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
        boss_domain = service.get_project_boss(project_id)

        # Convert domain object to dict for serialization
        boss_data = {
            "project_boss_id": boss_domain._boss.project_boss_id,
            "project": boss_domain._boss.project.project_id,
            "boss": boss_domain._boss.boss.boss_id if boss_domain._boss.boss else None,
            "boss_name": boss_domain.name if boss_domain._boss.boss else None,
            "boss_image": boss_domain.image if boss_domain._boss.boss else None,
            "hp": boss_domain.hp,
            "max_hp": boss_domain.max_hp,
            "status": boss_domain.status,
        }

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
        bosses = service.get_all_bosses()
        serializer = BossSerializer(bosses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
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
            "project_boss_id": boss_domain._boss.project_boss_id,
            "project": boss_domain._boss.project.project_id,
            "boss": boss_domain._boss.boss.boss_id,
            "boss_name": boss_domain.name,
            "boss_image": boss_domain.image,
            "hp": boss_domain.hp,
            "max_hp": boss_domain.max_hp,
            "status": boss_domain.status,
        }

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


# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def attack_boss(request, project_id):
#     """
#     Attack the project boss, dealing damage.

#     Request Body:
#         {
#             "damage": int  # Amount of damage to deal
#         }
#     """
#     try:
#         damage = request.data.get("damage")
#         if damage is None or not isinstance(damage, int) or damage <= 0:
#             return Response(
#                 {"error": "Damage must be a positive integer"},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         service = GameService()
#         result = service.attack_boss(project_id, damage)

#         return Response(
#             {
#                 "message": "Attack successful",
#                 "damage_dealt": result["damage_dealt"],
#                 "remaining_hp": result["remaining_hp"],
#                 "boss_defeated": result["boss_defeated"]
#             },
#             status=status.HTTP_200_OK,
#         )
#     except ValueError as e:
#         return Response(
#             {"error": str(e)},
#             status=status.HTTP_404_NOT_FOUND,
#         )
#     except Exception as e:
#         return Response(
#             {"error": str(e)},
#             status=status.HTTP_400_BAD_REQUEST,
#         )
