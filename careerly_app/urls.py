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
    path('logout', views.logout),
    path('profile', views.profile),
    path('profile/create', views.create_profile),
    path('profile/edit', views.edit_profile),
    path('profile/skill/add', views.add_skill),
    path('profile/skill/<int:skill_id>/remove', views.remove_skill),
    path('job', views.job_details),
    path('job/ai', views.job_ai),
    path('dashboard', views.dashboard),
    path('dashboard/find-jobs', views.find_jobs),
    path('job/apply', views.apply_job),
    path('application/<int:id>', views.application_details),
    path('job/favorite', views.favorite_job),
    path('favorite/<int:id>', views.favorite_details),
    path('favorite/<int:id>/remove', views.remove_favorite),
]