from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from api.services.task_service import TaskService
from api.serializers.task_serializer import TaskSerializer


@api_view(['GET'])
def task_list(request, project_id):
    task_service = TaskService(project_id)
    tasks = task_service.get_all_tasks()
    serializer = TaskSerializer(tasks, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def task_create(request, project_id):
    task_service = TaskService(project_id)
    serializer = TaskSerializer(data=request.data)
    if serializer.is_valid():
        task = task_service.create_task(serializer.validated_data)
        serializer = TaskSerializer(task)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def task_detail(request, project_id, task_id):
    task_service = TaskService(project_id)
    task = task_service.get_task(task_id)

    if not task:
        return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = TaskSerializer(task)
    return Response(serializer.data)


@api_view(['PUT'])
def task_update(request, project_id, task_id):
    task_service = TaskService(project_id)
    task = task_service.get_task(task_id)

    if not task:
        return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = TaskSerializer(task, data=request.data, partial=True)
    if serializer.is_valid():
        updated_task = task_service.edit_task(task_id, serializer.validated_data)
        serializer = TaskSerializer(updated_task)
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def task_delete(request, project_id, task_id):
    task_service = TaskService(project_id)
    if task_service.delete_task(task_id):
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def task_assign(request, project_id, task_id):
    project_member_id = request.data.get("project_member_id")
    if not project_member_id:
        return Response({"error": "project_member_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    task_service = TaskService(project_id)
    try:
        user_task, created = task_service.assign_user_to_task(task_id, project_member_id)
        if created:
            return Response({"message": "User assigned to task successfully"}, status=status.HTTP_201_CREATED)
        else:
            return Response({"message": "User already assigned to this task"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def task_unassign(request, project_id, task_id):
    project_member_id = request.data.get("project_member_id")
    if not project_member_id:
        return Response({"error": "project_member_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    task_service = TaskService(project_id)
    try:
        if task_service.unassign_user_from_task(task_id, project_member_id):
            return Response({"message": "User unassigned from task successfully"}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
