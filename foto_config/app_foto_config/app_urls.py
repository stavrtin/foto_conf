from django.urls import path
from . import views

urlpatterns = [
    path('', views.main_config, name='main_config'),
    path('add-config/', views.add_config, name='add_config'),
    path('edit-config/<int:pk>/', views.edit_config, name='edit_config'),
    path('delete-config/<int:pk>/', views.delete_config, name='delete_config'),
]