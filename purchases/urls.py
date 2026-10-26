
from django.urls import path
from . import views

app_name = "purchases"

urlpatterns = [
    path("", views.invoice_list, name="invoice_list"),
    path("new/", views.invoice_create, name="invoice_create"),
    path("<int:pk>/pay/", views.invoice_pay, name="invoice_pay"),
]
