from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/',  auth_views.LoginView.as_view(template_name='accounts/login.html'),  name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('users/',  views.user_list,   name='user_list'),
    path('users/new/',           views.user_create,        name='user_create'),
    path('users/<int:pk>/delete/', views.user_delete,      name='user_delete'),
]