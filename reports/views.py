from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db import transaction
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import Admin, Student, Question, Subject, Option
from .forms import StudentProfileForm

def home(request):
    subjects = Subject.objects.annotate(question_count=Count('question'))
    return render(request, 'reports/home.html', {'subjects': subjects})


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

            if student.email:
                try:
                    send_mail(
                        subject='Quizopedia - Profile Update Request Submitted',
                        message=(
                            f'Hello {student.name},\n\n'
                            'We have received your profile update request on Quizopedia:\n'
                            f'- Requested Name: {student.pending_name}\n'
                            f'- Requested Email: {student.pending_email}\n'
                            f'- Requested Phone: {student.pending_phone}\n\n'
                            'Your changes are pending approval by an administrator. '
                            'You will receive another email notification once your request has been reviewed.\n\n'
                            'Best regards,\n'
                            'The Quizopedia Team'
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[student.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass

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


@login_required
def approve_student(request, student_id):
    if not request.user.is_staff:
        return redirect('home')

    student = get_object_or_404(Student, id=student_id)
    if student.approval_status == 'pending':
        target_email = student.pending_email or student.email

        student.name = student.pending_name or student.name
        student.email = student.pending_email or student.email
        student.phone = student.pending_phone or student.phone
        student.approval_status = 'approved'
        student.pending_name = ''
        student.pending_email = ''
        student.pending_phone = ''
        student.save()

        if student.user:
            student.user.email = student.email
            student.user.save()

        if target_email:
            try:
                send_mail(
                    subject='Quizopedia - Profile Update Approved!',
                    message=(
                        f'Hello {student.name},\n\n'
                        'Great news! Your profile update request has been APPROVED by an administrator.\n\n'
                        'Your updated details are now active:\n'
                        f'- Name: {student.name}\n'
                        f'- Email: {student.email}\n'
                        f'- Phone: {student.phone}\n\n'
                        'You can now sign in and see your updated profile.\n\n'
                        'Best regards,\n'
                        'The Quizopedia Team'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[target_email],
                    fail_silently=True,
                )
            except Exception:
                pass

        messages.success(request, f'Profile update for {student.name} approved successfully.')

    return redirect('student_list')


@login_required
def reject_student(request, student_id):
    if not request.user.is_staff:
        return redirect('home')

    student = get_object_or_404(Student, id=student_id)
    if student.approval_status == 'pending':
        target_email = student.pending_email or student.email
        student.approval_status = 'approved'
        student.pending_name = ''
        student.pending_email = ''
        student.pending_phone = ''
        student.save()

        if target_email:
            try:
                send_mail(
                    subject='Quizopedia - Profile Update Request Declined',
                    message=(
                        f'Hello {student.name},\n\n'
                        'Your recent profile update request was reviewed and declined by an administrator. '
                        'Your existing profile information remains unchanged.\n\n'
                        'If you believe this is in error, please contact your administrator.\n\n'
                        'Best regards,\n'
                        'The Quizopedia Team'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[target_email],
                    fail_silently=True,
                )
            except Exception:
                pass

        messages.info(request, f'Profile update for {student.name} was rejected.')

    return redirect('student_list')



@login_required
def create_question(request):
    if not request.user.is_staff:
        return redirect('home')

    subjects = Subject.objects.all().order_by('name')
    selected_subject_id = request.POST.get('subject') or request.GET.get('subject', '')

    if request.method == 'POST':
        subject_id = request.POST.get('subject', '').strip()
        question_text = request.POST.get('question_text', '').strip()
        options = [
            request.POST.get('option_1', '').strip(),
            request.POST.get('option_2', '').strip(),
            request.POST.get('option_3', '').strip(),
            request.POST.get('option_4', '').strip(),
        ]
        correct_option = request.POST.get('correct_option', '')

        errors = []

        try:
            subject = Subject.objects.get(pk=subject_id)
        except (Subject.DoesNotExist, ValueError, TypeError):
            subject = None
            errors.append('Please select a valid subject.')

        if not question_text:
            errors.append('Please enter the question.')

        if any(not option for option in options):
            errors.append('Please fill in all four options.')

        if correct_option not in {'1', '2', '3', '4'}:
            errors.append('Please select exactly one correct option.')

        if not errors:
            with transaction.atomic():
                question = Question.objects.create(
                    subject=subject,
                    question_text=question_text
                )

                Option.objects.bulk_create([
                    Option(
                        question=question,
                        option_text=option_text,
                        is_answer=(str(index) == correct_option)
                    )
                    for index, option_text in enumerate(options, start=1)
                ])

            messages.success(request, 'Question and all four options saved successfully!')
            return redirect('create_question')

        for error in errors:
            messages.error(request, error)

    return render(request, 'reports/create_question.html', {
        'subjects': subjects,
        'selected_subject_id': str(selected_subject_id),
    })