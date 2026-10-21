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
        "issues/",
        views.stock_issue_list,
        name="stock_issue_list",
    ),
    path(
        "issues/new/",
        views.stock_issue_create,
        name="stock_issue_create",
    ),
    path(
        "issues/<int:pk>/edit/",
        views.stock_issue_edit,
        name="stock_issue_edit",
    ),
    path(
        "issues/<int:pk>/delete/",
        views.stock_issue_delete,
        name="stock_issue_delete",
    ),

    path(
        '<int:pk>/edit/',
        views.movement_edit,
        name='movement_edit',
    ),
    
    path(
        "issues/<int:pk>/",
        views.stock_issue_detail,
        name="stock_issue_detail",
    ),


    path(
        '<int:pk>/delete/',
        views.movement_delete,
        name='movement_delete',
    ),
]