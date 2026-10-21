from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('register', views.register),
    path('login', views.login),
    path('about', views.about),
    path('contact', views.contact),
    path('admin-dashboard', views.admin_dashboard),
    path('admin-dashboard/user/<int:id>', views.admin_user),
    path('admin-dashboard/user/<int:id>/status', views.toggle_user_status),
    path('admin-dashboard/message/<int:id>', views.admin_message),
]