from django.urls import path
from . import views


app_name = 'inventory'


urlpatterns = [
    path(
        '',
        views.movement_list,
        name='movement_list',
    ),

    path(
        'new/<str:kind>/',
        views.movement_create,
        name='movement_create',
    ),

    path(
        '<int:pk>/edit/',
        views.movement_edit,
        name='movement_edit',
    ),

    path(
        '<int:pk>/delete/',
        views.movement_delete,
        name='movement_delete',
    ),
]