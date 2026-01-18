# views/task.py
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from api.services.task_service import TaskService
from api.serializers.task_serializer import TaskRequestSerializer, TaskResponseSerializer
from api.models import BusinessUser


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_list(request, project_id):
    """
    Retrieve all tasks for a specific project.
    """
    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)
    task_service = TaskService(project_id, user)
    tasks = task_service.get_all_tasks()
    serializer = TaskResponseSerializer(tasks, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def task_create(request, project_id):
    """
    Create a new task for a specific project.

    Request Body:

        {
            "task_name": string,
            "description": string,
            "priority": string,
            "status": string
        }
    """
    print("requser:",request.data)

    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)
    task_service = TaskService(project_id, user)
    serializer = TaskRequestSerializer(data=request.data)
    if serializer.is_valid():
        task = task_service.create_task(serializer.validated_data)
        serializer = TaskResponseSerializer(task)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_detail(request, project_id, task_id):
    """
    Retrieve details of a specific task within a project.
    """
    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)
    task_service = TaskService(project_id, user)
    task = task_service.get_task(task_id)

    if not task:
        return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = TaskResponseSerializer(task)
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def task_move(request, project_id, task_id):
    """
    move an existing task within a project in kanbanboard.

    Request Body:

        {
            "status": string,
        }
    """
    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)
    task_service = TaskService(project_id, user)
    task = task_service.get_task(task_id)

    if not task:
        return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)

    moved_task = task_service.move_task(task_id, request.data)
    serializer = TaskResponseSerializer(moved_task)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def task_update(request, project_id, task_id):
    """
    Update an existing task within a project.

    Request Body:

        {
            "task_name": string,
            "priority": string,
            "description": string,
            "deadline": datetime,
            "priority": string,
            "status": string
        }
    """
    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)
    task_service = TaskService(project_id, user)
    task = task_service.get_task(task_id)

    if not task:
        return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = TaskRequestSerializer(task, data=request.data, partial=True)
    if serializer.is_valid():
        updated_task = task_service.edit_task(task_id, serializer.validated_data)
        serializer = TaskResponseSerializer(updated_task)
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def task_delete(request, project_id, task_id):
    """
    Delete a specific task from a project.
    """
    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)
    task_service = TaskService(project_id, user)
    if task_service.delete_task(task_id):
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def task_assign(request, project_id, task_id):
    """
    Assign a user to a task.

    Request Body:

        {
            "project_member_id": UUID
        }
    """

    project_member_id = request.data.get("project_member_id")
    if not project_member_id:
        return Response({"error": "project_member_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)
    task_service = TaskService(project_id, user)
    try:
        user_task, created = task_service.assign_user_to_task(task_id, project_member_id)
        if created:
            return Response({"message": "User assigned to task successfully"}, status=status.HTTP_201_CREATED)
        else:
            return Response({"message": "User already assigned to this task"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def task_unassign(request, project_id, task_id):
    """
    Unassign a user from a task.

    Request Body:

        {
            "project_member_id": UUID
        }
    """
    project_member_id = request.data.get("project_member_id")
    if not project_member_id:
        return Response({"error": "project_member_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    cur_user = request.user
    user = BusinessUser.objects.get(auth_user=cur_user)
    task_service = TaskService(project_id, user)
    try:
        if task_service.unassign_user_from_task(task_id, project_member_id):
            return Response({"message": "User unassigned from task successfully"}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
