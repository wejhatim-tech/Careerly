from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('register', views.register),
    path('login', views.login),
    path('about', views.about),
    path('contact', views.contact),
    path('logout', views.logout),
    path('profile', views.profile),
    path('profile/create', views.create_profile),
    path('profile/edit', views.edit_profile),
    path('profile/skill/add', views.add_skill),
    path('profile/skill/<int:skill_id>/remove', views.remove_skill),
]