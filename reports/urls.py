from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
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
    path('question/create/', views.create_question, name='create_question'),
    path('students/<int:student_id>/approve/', views.approve_student, name='approve_student'),
    path('students/<int:student_id>/reject/', views.reject_student, name='reject_student'),

    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='reports/password_reset.html',
            email_template_name='reports/password_reset_email.html',
            subject_template_name='reports/password_reset_subject.txt',
            success_url='/password-reset/done/'
        ),
        name='password_reset'
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='reports/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='reports/password_reset_confirm.html',
            success_url='/password-reset-complete/'
        ),
        name='password_reset_confirm'
    ),
    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='reports/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
]