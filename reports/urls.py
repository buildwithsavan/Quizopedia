from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('login/verify-otp/', views.student_login_verify_otp, name='student_login_verify_otp'),
    path('login/resend-otp/', views.student_login_resend_otp, name='student_login_resend_otp'),
    path('logout/', views.user_logout, name='logout'),
    path('admins/', views.admin_list, name='admin_list'),
    path('students/', views.student_list, name='student_list'),
    path('dashboard/', views.dashboard,name='dashboard'),
    path('profile/', views.profile,name='profile'),
    path('profile/edit/', views.student_profile_update, name='student_profile_update'),
    path('question/create/', views.create_question, name='create_question'),
    path('students/<int:student_id>/approve/', views.approve_student, name='approve_student'),
    path('students/<int:student_id>/reject/', views.reject_student, name='reject_student'),

    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/verify-otp/', views.password_reset_verify_otp, name='password_reset_verify_otp'),
    path('password-reset/resend-otp/', views.password_reset_resend_otp, name='password_reset_resend_otp'),
    path('password-reset/new-password/', views.password_reset_new_password, name='password_reset_new_password'),
    path('password-reset/complete/', views.password_reset_complete, name='password_reset_complete'),
]