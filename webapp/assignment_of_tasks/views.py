#! /usr/bin/env python
# -*- coding: utf-8 -*-
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Task, Comment, Statuses, History_changed
from .forms import TaskForm, CommentForm, UpdateTask, UserForm, ProfileUserForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpResponseForbidden
import simplejson
'''
API
'''
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from .serializers import TaskShortSerializer, TaskDetailSerializer, UserSerializer, StatusSerialiser
from rest_framework import serializers
import json
'''
'''

'''
НАСТРОЙКА ПАГИНАТОРА. Количество объектов на странице
'''
COUNT_PAGINATOR_PAGE = 5

'''
Отображение задач на разных url
'''
def task_list(request):
    tasks = Task.objects.order_by('-created_date').filter(status__ended=False)
    page = request.GET.get('page', 1)
    paginator = Paginator(tasks, COUNT_PAGINATOR_PAGE)
    try:
        tasks = paginator.page(page)
    except PageNotAnInteger:
        tasks = paginator.page(1)
    except EmptyPage:
        tasks = paginator.page(paginator.num_pages)
    return render(request, 'tasks/task_list.html', {'tasks' : tasks, 'title' : 'Список задач', 'pag' : tasks})

@login_required
def my_task_list(request):
    tasks = Task.objects.order_by('-created_date').filter(assigned_to=request.user, status__ended=False)
    page = request.GET.get('page', 1)
    paginator = Paginator(tasks, COUNT_PAGINATOR_PAGE)
    try:
        tasks = paginator.page(page)
    except PageNotAnInteger:
        tasks = paginator.page(1)
    except EmptyPage:
        tasks = paginator.page(paginator.num_pages)
    return render(request, 'tasks/task_list.html', {'tasks' : tasks, 'title' : 'Мои задачи'})

@login_required
def completed_task_list(request):
    tasks = Task.objects.order_by('-created_date').filter(status__ended=True)
    page = request.GET.get('page', 1)
    paginator = Paginator(tasks, COUNT_PAGINATOR_PAGE)
    try:
        tasks = paginator.page(page)
    except PageNotAnInteger:
        tasks = paginator.page(1)
    except EmptyPage:
        tasks = paginator.page(paginator.num_pages)
    return render(request, 'tasks/task_list.html', {'tasks' : tasks, 'title' : 'Завершенные задачи'})

@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)

    comments = task.comments.all()
    page = request.GET.get('page', 1)
    paginator = Paginator(comments, COUNT_PAGINATOR_PAGE)
    try:
        comments = paginator.page(page)
    except PageNotAnInteger:
        comments = paginator.page(1)
    except EmptyPage:
        comments = paginator.page(paginator.num_pages)

    return render(request, 'tasks/task_detail.html', {'task': task, 'comments': comments})
'''
'''

@login_required
def task_new(request):
    form = TaskForm()
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.author = request.user
            task.created_date = timezone.now()
            task.save()
            return redirect('task_detail', pk=task.pk)
    else:
        form = TaskForm()
    return render(request, 'tasks/task_edit.html', {'form': form})

@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid() and request.user == task.author or request.user.is_superuser:
            task = form.save(commit=False)
            task.created_date = timezone.now()
            task.save()
            return redirect('task_detail', pk=task.pk)
    else:
        form = TaskForm(instance=task)
    return render(request, 'tasks/task_edit.html', {'form': form})

@login_required
def task_remove(request, pk):
    if request.method == "GET":
        task = get_object_or_404(Task, pk=pk)
        if request.user == task.author or request.user.is_superuser:
            task.delete()
            return redirect('task_list')

@login_required
def add_comment_to_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == "POST":
        c_form = CommentForm(request.POST)
        u_task = UpdateTask(request.POST, instance=task)
        if c_form.is_valid():
            comment = c_form.save(commit=False)
            upd_task = u_task.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.created_date = timezone.now()
            if comment.change_state:
                updating_task(pk, comment, request.user, upd_task.assigned_to, upd_task.status, upd_task.percent)
            else:
                comment.save()
                task.last_update_date = timezone.now()
                task.save(update_fields=['last_update_date'])
            return redirect('task_detail', pk=task.pk)
    else:
        c_form = CommentForm()
        u_task = UpdateTask(instance=task)
    return render(request, 'tasks/add_comment_to_task.html', {'c_form': c_form, 'upd_task': u_task})

def updating_task (pk, comment, author, assigned_to, status, percent):
    task = get_object_or_404(Task, pk=pk)
    new_history_object = History_changed()
    #Пишем историю в поля коммента.
    new_history_object.old_assigned_to = task.assigned_to.get_full_name()
    new_history_object.new_assigned_to = assigned_to.get_full_name()
    new_history_object.old_status = task.status.title
    new_history_object.new_status = status.title
    new_history_object.old_percent = task.percent
    new_history_object.new_percent = percent
    new_history_object.save()
    ###
    task.assigned_to = assigned_to
    task.status = status
    task.percent = percent
    task.last_update_date = timezone.now()
    comment.task = task
    comment.author = author
    comment.change_values = new_history_object
    comment.save()
    task.save(update_fields=['status', 'assigned_to','last_update_date', 'percent'])

@login_required
def comment_remove(request, pk_task, pk_com):
    if request.method == "GET":
        comment = get_object_or_404(Comment, pk=pk_com)
        if comment.author == request.user or request.user.is_superuser:
            comment.delete()
        return redirect('task_detail', pk=pk_task)

'''
Профайл юзера. Изменение 
'''
@login_required
def user_profile(request):
    get_user = get_object_or_404(User, id = request.user.id)
    if request.method == "POST":

        change_password = PasswordChangeForm(request.user, request.POST)
        user_form = ProfileUserForm(data=request.POST, instance=get_user)
        if user_form.is_valid():
            get_user.first_name = user_form.cleaned_data['first_name']
            get_user.last_name = user_form.cleaned_data['last_name']
            get_user.save(update_fields=['first_name', 'last_name', ])
            messages.success(request, 'Информация в профиле обновлена!')
            return redirect('user_profile')
        if change_password.is_valid():
            user = change_password.save()
            #update_session_auth_hash(request, user)  # Important! После смены пароля - пользователю необходимо будет авторизоваться заного
            messages.success(request, 'Пароль успешно обновлен!')
            return redirect('user_profile')
        else:
            user_form = ProfileUserForm(instance=get_user)
            messages.warning(request, 'Пароль не был изменен!')
    else:
        change_password = PasswordChangeForm(request.user)
        user_form = ProfileUserForm(instance=get_user)
    return render(request, 'users/profile.html', {'user_form': user_form, 'change_password': change_password})

@login_required
def create_user(request):
    if request.method == "POST" and request.user.is_superuser == True:
        form = UserForm(data=request.POST)
        print(form.is_valid())
        if form.is_valid():
            form.cleaned_data['is_superuser'] = form.cleaned_data['is_staff']
            User.objects.create_user(**form.cleaned_data)
            messages.success(request, 'Пользователь успешно создан!')
            # redirect, or however you want to get to the main view
            return redirect('create_user')
        else:
            messages.warning(request, 'Пользователь не создан!')
    else:
        form = UserForm()

    return render(request, 'users/create_user.html', {'form': form})

@login_required
def user_list(request):
    if request.user.is_superuser == True:
        users = User.objects.all()
        return render(request, 'users/users.html', {'users': users })
    return HttpResponseForbidden()

'''
API methods
'''
@csrf_exempt
def task_list_api(request):
    if request.method == 'GET':
        tasks = Task.objects.all()
        serializer = TaskShortSerializer(tasks, many=True)
        return JsonResponse(serializer.data, safe=False)

    serializer = TaskShortSerializer()
    return JsonResponse(serializer.errors, status=400)

@login_required
def my_task_list_api(request):
    if request.method == 'GET':
        tasks = Task.objects.filter(assigned_to=request.user)
        serializer = TaskShortSerializer(tasks, many=True)
        return JsonResponse(serializer.data, safe=False)

    serializer = TaskShortSerializer()
    return JsonResponse(serializer.errors, status=400)

@csrf_exempt
def task_detail_api(request, pk):
    try:
        task = Task.objects.get(pk=pk)
    except Task.DoesNotExist:
        return JsonResponse({'error': 'not found'})

    if request.method == 'GET':
        json_task_detail = TaskDetailSerializer(task)
        return JsonResponse(json_task_detail.data)


'''
            import requests
            import json
            a = requests.post("http://127.0.0.1:8000/api/login/", data={"username": "testapi", "password": "111"})
            c = a.cookies
            r = requests.post("http://127.0.0.1:8000/api/task/24/comment/", 
            data=json.dumps({'text' : "test111" , 'change_state': "Y", "assigned_to": "mech", "status" : "4"}), cookies=c)
'''
@csrf_exempt
def add_comment_to_task_api(request, pk):
    if request.method == 'POST':
        json_string = request.body.decode()
        json_string = json.loads(json_string)
        print (json_string)
        comment = CommentForm(json_string)
        if comment.is_valid():
            print(True)
            task = get_object_or_404(Task, pk=pk)
            comment = comment.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.created_date = timezone.now()
            if json_string["change_state"] == "Y":
                assigned_to = get_object_or_404(User, username=json_string["assigned_to"])
                try:
                    status  = get_object_or_404(Statuses, id=int(json_string["status"]))
                except:
                    print (json_string["status"])
                    print ("err status")
                updating_task(pk, request.user, assigned_to, status, comment.text)
                print('Added comment with update')
            else:
                comment.save()
                task.last_update_date = timezone.now()
                task.save(update_fields=['last_update_date'])
                print('Added comment without update')
        else:
            print('Not valid comment')
        return HttpResponse()

@csrf_exempt
def get_statuses_api(request):
    if request.method == 'GET':
        statuses = Statuses.objects.all()
        statuses_list = StatusSerialiser(statuses, many=True)
        return JsonResponse(statuses_list.data, safe=False)

@csrf_exempt
def get_users_api(request):
    if request.method == 'GET':
        users = User.objects.all()
        json_users = UserSerializer(users,many=True)
        return JsonResponse(json_users.data, safe=False)