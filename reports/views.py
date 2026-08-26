from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Admin, Student, Question
from .forms import StudentProfileForm

@login_required
def dashboard(request):

    if request.user.is_staff:
        total_students = Student.objects.count()
        total_questions = Question.objects.count()

        return render(request, 'reports/dashboard.html', {'total_students': total_students, 'total_questions': total_questions})
    
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
        request,'reports/profile.html',{'profile': profile,'profile_type': profile_type})

@login_required
def student_profile_update(request):

    if request.user.is_staff:
        return redirect('profile')

    student = request.user.student_profile

    if request.method == 'POST':
        form = StudentProfileForm(request.POST)

        if form.is_valid():
            student.pending_name = form.cleaned_data['name']
            student.pending_email = form.cleaned_data['email']
            student.pending_phone = form.cleaned_data['phone']

            student.approval_status = 'pending'
            student.save()

            return redirect('profile')

    else:
        form = StudentProfileForm(
            initial={
                'name': student.name,
                'email': student.email,
                'phone': student.phone,
            }
        )

    return render(request, 'reports/student_profile_update.html', {'form': form})