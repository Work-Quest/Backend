from rest_framework import serializers
from api.models.Task import Task

class TaskResponseSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    class Meta:
        model = Task
        fields = '__all__' 

class TaskRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        exclude = ('project',) 

   