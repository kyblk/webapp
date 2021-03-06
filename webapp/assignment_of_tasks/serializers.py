from rest_framework import serializers
from .models import Task, Comment, Statuses, History_changed
from django.contrib.auth.models import User

class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = History_changed
        fields = ('old_assigned_to', 'new_assigned_to', 'old_status', 'new_status', 'old_percent', 'new_percent')

class StatusSerialiser(serializers.ModelSerializer):
    class Meta:
        model = Statuses
        fields = ('id', 'title', 'ended', 'sort')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'last_name', 'first_name')

class TaskShortSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    class Meta:
        model = Task
        fields = ('id', 'author', 'assigned_to', 'title', 'created_date', 'last_update_date', 'status', 'percent')

class CommentDetailSerializer(serializers.ModelSerializer):
    change_values = HistorySerializer(read_only=True)
    class Meta:
        model = Comment
        fields = ('author', 'text', 'created_date', 'change_state', 'change_values')

class TaskDetailSerializer(serializers.ModelSerializer):
    comments = CommentDetailSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    class Meta:
        model = Task
        fields = ('id', 'author', 'assigned_to', 'title', 'text', 'created_date', 'status', 'percent', 'comments')
