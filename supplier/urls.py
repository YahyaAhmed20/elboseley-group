from django.urls import path
from . import views

app_name = "supplier"

urlpatterns = [
    path("", views.supplier_list, name="supplier_list"),
    path("new/", views.supplier_create, name="supplier_create"),
    path(
        "<int:pk>/edit/",
        views.supplier_edit,
        name="supplier_edit",
    ),
    path(
        "<int:pk>/delete/",
        views.supplier_delete,
        name="supplier_delete",
    ),
    path(
        "<int:pk>/statement/",
        views.supplier_statement,
        name="supplier_statement",
    ),
]