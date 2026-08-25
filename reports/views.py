from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Admin, Student

@login_required
def dashboard   (request):

    if request.user.is_staff:
        return redirect('admin_list')

    return redirect('student_list')

@login_required
def admin_list(request):
    admins = Admin.objects.all()

    return render(request,'reports/admin_list.html',{'admins': admins})

@login_required
def student_list(request):
    students = Student.objects.all()

    return render(request,'reports/student_list.html',{'students': students})

@login_required
def profile(request):

    if request.user.is_staff:
        profile = request.user.admin_profile
        profile_type = 'Admin'
    else:
        profile = request.user.student_profile
        profile_type = 'Student'

    return render(
        request,
        'reports/profile.html',
        {
            'profile': profile,
            'profile_type': profile_type
        }
    )