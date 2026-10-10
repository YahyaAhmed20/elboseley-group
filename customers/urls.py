from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.customer_list, name='customer_list'),
    path('new/', views.customer_create, name='customer_create'),
    path('<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    path('<int:pk>/pdf/', views.customer_pdf, name='customer_pdf'),
    path('<int:pk>/telegram-test/', views.customer_telegram_test, name='customer_telegram_test'),
]
