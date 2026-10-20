from django.urls import path
from . import views

app_name = 'servicecenter'

urlpatterns = [
    path('', views.repair_list, name='repair_list'),
    path('receive/', views.repair_receive, name='repair_receive'),
    path('qz/sign/', views.qz_sign, name='qz_sign'),

    path('<int:pk>/work/', views.repair_work, name='repair_work'),
    path('<int:pk>/deliver/', views.repair_deliver, name='repair_deliver'),
    path('devices/search/', views.device_search, name='device_search'),
    path('customers/search/', views.customer_search, name='customer_search'),
    path('<int:pk>/receipt/', views.repair_receipt, name='repair_receipt'),

    path('devices/', views.device_list, name='device_list'),
    path('devices/<int:pk>/', views.device_detail, name='device_detail'),
    
]