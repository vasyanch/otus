from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('index/<flag>', views.index, name='index_pop'),
    path('ask/', views.question_add, name='ask'),
    path('question/<int:id_>/', views.question_details, name='question_details'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_, name='login'),
    path('search/', views.search, name='search'),
    path('profile/<int:id_user>/', views.profile, name='profile'),
    path('logout/', views.logout_, name='logout'),
]
