from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='reports/login.html'),
        name='login'
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='logout'
    ),
    path('admins/', views.admin_list, name='admin_list'),
    path('students/', views.student_list, name='student_list'),
    path('dashboard/', views.dashboard,name='dashboard'),
    path('profile/', views.profile,name='profile'),
    path('profile/edit/', views.student_profile_update, name='student_profile_update'),
]