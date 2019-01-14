from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout

from .models import User, Tag, Question, Answer, paginate
from .forms import AskForm, AnswerForm, SignupForm


def index(request, flag='new'):
    if flag == 'new':
        set_questions = Question.objects.new()
    elif flag == 'pop':
        set_questions = Question.objects.popular()
    else:
        set_questions = None
    trending = Question.objects.popular()
    paginator, page = paginate(request, set_questions)
    paginator.baseurl = '/?page='
    user = request.user
    return render(request, 'qa/index.html', {
        'list_questions': page.object_list,
        'paginator': paginator,
        'page': page,
        'user': user,
        'trending': trending,
    })


def question_add(request):
    if request.method == 'POST':
        form = AskForm(request.user, request.POST)
        if form.is_valid():
            question = form.save()
            url = question.get_url()
            return HttpResponseRedirect(url)
    else:
        form = AskForm(request.user)
    trending = Question.objects.popular()
    return render(request, 'qa/question_add.html', {
        'form': form,
        'trending': trending,
    })


def question_details(request, id_):
    question = get_object_or_404(Question, id=id_)
    user = request.user
    try:
        answer = Answer.objects.filter(question_id=question.id)
    except Answer.DoesNotExist:
        answer = None
    trending = Question.objects.popular()
    if request.method == 'POST':
        form = AnswerForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            url = question.get_url()
            return HttpResponseRedirect(url)
    else:
        form = AnswerForm(request.user, initial={'question': question.id})
    return render(request, 'qa/question_details.html', {
        'question': question,
        'answer': answer,
        'form': form,
        'trending': trending,
        'user': user,
    })


def signup(request):
    trending = Question.objects.popular()
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            login(request, user)
            url = request.POST.get('continue', '/')
            return HttpResponseRedirect(url)

    else:
        form = SignupForm()
    return render(request, 'qa/signup.html', {
        'form': form,
        'trending': trending,
    })


def login_(request):
    error = ''
    form = SignupForm()
    trending = Question.objects.popular()
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            url = request.POST.get('continue', '/')
            return HttpResponseRedirect(url)
        else:
            error = 'Invalid username/password'
    return render(request, 'qa/login.html', {
        'form': form,
        'error': error,
        'trending': trending,
    })


def search(request):
    pass


def logout_(request):
    logout(request)
    return HttpResponseRedirect(request.GET.get('continue', '/'))


def profile(request, id_user):
    error = ''
    user = request.user
    trending = Question.objects.popular()
    if request.user.id != id_user:
        error = 'Sorry!\nYou can watch only your profile page'
    return render(request, 'qa/profile.html',{
        'user': user,
        'trending': trending,
        'error': error,
    })
