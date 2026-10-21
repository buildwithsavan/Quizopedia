from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('admin-login/', views.admin_login, name='admin_login'),
    path('login/verify-otp/', views.student_login_verify_otp, name='student_login_verify_otp'),
    path('login/resend-otp/', views.student_login_resend_otp, name='student_login_resend_otp'),
    path('logout/', views.user_logout, name='logout'),
    path('admins/', views.admin_list, name='admin_list'),
    path('students/', views.student_list, name='student_list'),
    path('pending-approvals/', views.pending_approvals, name='pending_approvals'),
    path('dashboard/', views.dashboard,name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.student_profile_update, name='student_profile_update'),
    path('profile/admin-edit/', views.admin_profile_update, name='admin_profile_update'),
    path('profile/withdraw/', views.student_withdraw_update, name='student_withdraw_update'),
    path('question/create/', views.create_question, name='create_question'),
    path('questions/', views.question_bank, name='question_bank'),
    path('questions/<int:question_id>/edit/', views.edit_question, name='edit_question'),
    path('questions/<int:question_id>/delete/', views.delete_question, name='delete_question'),
    path('students/<int:student_id>/approve/', views.approve_student, name='approve_student'),
    path('students/<int:student_id>/reject/', views.reject_student, name='reject_student'),
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/add/', views.subject_create, name='subject_create'),
    path('subjects/<int:subject_id>/edit/', views.subject_update, name='subject_update'),
    path('subjects/<int:subject_id>/delete/', views.subject_delete, name='subject_delete'),

    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/verify-otp/', views.password_reset_verify_otp, name='password_reset_verify_otp'),
    path('password-reset/resend-otp/', views.password_reset_resend_otp, name='password_reset_resend_otp'),
    path('password-reset/new-password/', views.password_reset_new_password, name='password_reset_new_password'),
    path('password-reset/complete/', views.password_reset_complete, name='password_reset_complete'),
    path('profile-update/<int:update_id>/approve/', views.approve_profile_update, name='approve_profile_update'),
    path('profile-update/<int:update_id>/reject/', views.reject_profile_update, name='reject_profile_update'),
]