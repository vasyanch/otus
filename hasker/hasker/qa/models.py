from django.db import models

# Create your models here.
from django.contrib.auth.models import User
from django.http import Http404
from django.core.paginator import Paginator, EmptyPage


class Tag(models.Model):
    text = models.CharField(max_length=255)

    def __str__(self):
        return self.text


class QuestionManager(models.Manager):
    def new(self):
        return self.order_by('-added_at')

    def popular(self):
        return self.order_by('-rating', '-added_at')


class Question(models.Model):
    title = models.CharField(max_length=255)
    text = models.TextField()
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    added_at = models.DateTimeField(blank=True, auto_now_add=True)
    tags = models.ManyToManyField(Tag, related_name='questions')
    rating = models.IntegerField(default=0)
    #likes = models.ManyToManyField(User, related_name='Users')
    objects = QuestionManager()

    def __str__(self):
        return self.text

    def get_url(self):
        return '/question/{0}/'.format(str(self.id))

    def save(self, tags_str=[], *args, **kwargs):
        super(Question, self).save(*args, **kwargs)
        tags = []
        for t in tags_str:
            tag, created = Tag.objects.get_or_create(text=t)
            tags.append(tag)
        self.tags.add(*tags)


class Answer(models.Model):
    text = models.TextField()
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    added_at = models.DateTimeField(blank=True, auto_now_add=True)
    right_answer = models.BooleanField(default=False)
    question = models.ForeignKey(Question, null=False, on_delete=models.CASCADE)

    def __str__(self):
        return self.text


def paginate(request, qs):
    try:
        limit = int(request.GET.get('limit', 20))
    except ValueError:
        limit = 20
    if limit > 100:
        limit = 20
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        raise Http404
    paginator = Paginator(qs, limit)
    try:
        page = paginator.page(page)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    return paginator, page
