from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count, Prefetch
from django.db import transaction
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
import random
import time
from .models import Admin, Student, Question, Subject, Option, PendingProfileUpdate, StudentOTP
from .forms import StudentProfileForm
from django.utils import timezone
from django.core.paginator import Paginator

OTP_RESEND_COOLDOWN = 30

def home(request):
    subjects = Subject.objects.annotate(question_count=Count('question')).order_by('name')
    return render(request, 'reports/home.html', {'subjects': subjects})


@login_required
def dashboard(request):
    if not request.user.is_staff:
        return redirect('profile')

    total_students = Student.objects.count()
    total_questions = Question.objects.count()
    total_subjects = Subject.objects.count()
    pending_count = PendingProfileUpdate.objects.filter(status='pending').count()

    enrolled_students = Student.objects.all().order_by('id')

    return render(
        request,
        'reports/dashboard.html',
        {
            'total_students': total_students,
            'total_questions': total_questions,
            'total_subjects': total_subjects,
            'pending_count': pending_count,
            'enrolled_students': enrolled_students,
        }
    )


@login_required
def question_bank(request):
    if not request.user.is_staff:
        return redirect('profile')

    subjects = Subject.objects.all().order_by('name')
    selected_subject_id = request.GET.get('subject', '').strip()

    questions = Question.objects.select_related('subject').prefetch_related(
        Prefetch('option_set', queryset=Option.objects.order_by('id'))
    ).all()

    if selected_subject_id:
        questions = questions.filter(subject_id=selected_subject_id)

    questions = questions.order_by('subject__name', 'id')

    questions_data = {
        str(q.id): {
            'id': q.id,
            'subject_id': q.subject_id,
            'subject_name': q.subject.name,
            'question_text': q.question_text,
            'options': [
                {'id': opt.id, 'text': opt.option_text, 'is_answer': opt.is_answer}
                for opt in q.option_set.all()
            ]
        }
        for q in questions
    }

    return render(
        request,
        'reports/question_bank.html',
        {
            'subjects': subjects,
            'selected_subject_id': selected_subject_id,
            'questions': questions,
            'questions_data': questions_data,
            'total_questions_count': questions.count(),
        }
    )



@login_required
def admin_list(request):
    if not request.user.is_staff:
        return redirect('profile')
    admins = Admin.objects.all().order_by('id')
    return render(request, 'reports/admin_list.html', {'admins': admins})

@login_required
def student_list(request):
    if not request.user.is_staff:
        return redirect('profile')
    students = Student.objects.all().order_by('id')

    return render(
        request,
        'reports/student_list.html',
        {
            'students': students,
        }
    )


@login_required
def pending_approvals(request):
    if not request.user.is_staff:
        return redirect('profile')

    pending_updates = PendingProfileUpdate.objects.filter(
        status='pending'
    ).select_related('student').order_by('-submitted_at')

    return render(
        request,
        'reports/pending_approvals.html',
        {
            'pending_updates': pending_updates,
        }
    )

@login_required
def profile(request):
    if request.user.is_staff:
        profile_obj = getattr(request.user, 'admin_profile', None)
        if not profile_obj:
            profile_obj, _ = Admin.objects.get_or_create(
                user=request.user,
                defaults={
                    'name': request.user.get_full_name() or request.user.username,
                    'email': request.user.email or '',
                    'phone': '',
                }
            )
        profile_type = 'Admin'
        pending_update = None
        update_history = []
    else:
        profile_obj = getattr(request.user, 'student_profile', None)
        if not profile_obj:
            profile_obj, _ = Student.objects.get_or_create(
                user=request.user,
                defaults={
                    'name': request.user.get_full_name() or request.user.username,
                    'email': request.user.email or '',
                    'phone': '',
                }
            )
        profile_type = 'Student'
        pending_update = PendingProfileUpdate.objects.filter(
            student=profile_obj, status='pending'
        ).order_by('-submitted_at').first()

        update_history = profile_obj.pending_profile_updates.order_by('-submitted_at')[:5]

    return render(
        request,
        'reports/profile.html',
        {
            'profile': profile_obj,
            'profile_type': profile_type,
            'pending_update': pending_update,
            'update_history': update_history,
        }
    )

@login_required
def admin_profile_update(request):
    if not request.user.is_staff:
        messages.error(request, "Only administrators can update admin profiles.")
        return redirect('profile')

    admin_obj = getattr(request.user, 'admin_profile', None)
    if not admin_obj:
        admin_obj, _ = Admin.objects.get_or_create(
            user=request.user,
            defaults={
                'name': request.user.get_full_name() or request.user.username,
                'email': request.user.email or '',
                'phone': '',
            }
        )

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()

        if not name:
            messages.error(request, 'Full legal name is required.')
            return redirect('profile')

        if not email:
            messages.error(request, 'Email address is required.')
            return redirect('profile')

        admin_obj.name = name
        admin_obj.email = email
        admin_obj.phone = phone
        admin_obj.save()

        request.user.email = email
        name_parts = name.split(None, 1)
        request.user.first_name = name_parts[0]
        request.user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        request.user.save()

        messages.success(request, 'Admin profile updated successfully!')
        return redirect('profile')

    return redirect('profile')

@login_required
def student_profile_update(request):
    if request.user.is_staff:
        return redirect('profile')

    student = getattr(request.user, 'student_profile', None)
    if not student:
        student, _ = Student.objects.get_or_create(
            user=request.user,
            defaults={
                'name': request.user.get_full_name() or request.user.username,
                'email': request.user.email or '',
                'phone': '',
                'approval_status': 'approved',
            }
        )

    pending_update = PendingProfileUpdate.objects.filter(
        student=student, status='pending'
    ).order_by('-submitted_at').first()

    if request.method == 'POST':
        form = StudentProfileForm(request.POST)
        if form.is_valid():
            new_name = form.cleaned_data['name'].strip()
            new_email = form.cleaned_data['email'].strip()
            new_phone = form.cleaned_data['phone'].strip()

            if (new_name == student.name and
                new_email == student.email and
                new_phone == student.phone):
                messages.info(
                    request,
                    'The details entered match your current active profile. No changes were submitted.'
                )
                return redirect('profile')

            if pending_update:
                pending_update.name = new_name
                pending_update.email = new_email
                pending_update.phone = new_phone
                pending_update.submitted_at = timezone.now()
                pending_update.save()
            else:
                pending_update = PendingProfileUpdate.objects.create(
                    student=student,
                    name=new_name,
                    email=new_email,
                    phone=new_phone,
                    status='pending',
                )

            student.pending_name = new_name
            student.pending_email = new_email
            student.pending_phone = new_phone
            student.approval_status = 'pending'
            student.save()

            if student.email:
                try:
                    send_mail(
                        subject='Quizopedia - Profile Update Request Submitted',
                        message=(
                            f'Hello {student.name},\n\n'
                            'We have received your profile update request on Quizopedia:\n'
                            f'- Requested Name: {pending_update.name}\n'
                            f'- Requested Email: {pending_update.email}\n'
                            f'- Requested Phone: {pending_update.phone}\n\n'
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

            messages.success(
                request,
                'Your profile update request has been successfully submitted and is awaiting administrator approval.'
            )
            return redirect('profile')
    else:
        initial_data = {
            'name': pending_update.name if pending_update else student.name,
            'email': pending_update.email if pending_update else student.email,
            'phone': pending_update.phone if pending_update else student.phone,
        }
        form = StudentProfileForm(initial=initial_data)

    update_history = student.pending_profile_updates.order_by('-submitted_at')[:5]

    return render(
        request,
        'reports/student_profile_update.html',
        {
            'form': form,
            'student': student,
            'pending_update': pending_update,
            'update_history': update_history,
        }
    )

@login_required
def student_withdraw_update(request):
    if request.user.is_staff:
        return redirect('dashboard')

    student = getattr(request.user, 'student_profile', None)
    if not student:
        return redirect('profile')

    if request.method == 'POST':
        pending = PendingProfileUpdate.objects.filter(
            student=student, status='pending'
        ).first()
        if pending:
            pending.delete()
        student.pending_name = ''
        student.pending_email = ''
        student.pending_phone = ''
        student.approval_status = 'approved'
        student.save()
        messages.success(
            request,
            'Your pending profile update request has been withdrawn. Your current profile remains active.'
        )

    return redirect('profile')

@login_required
def approve_student(request, student_id):
    if not request.user.is_staff:
        return redirect('home')

    student = get_object_or_404(Student, id=student_id)

    pending_update = PendingProfileUpdate.objects.filter(
        student=student,
        status='pending'
    ).order_by('-submitted_at').first()

    if pending_update:
        target_email = pending_update.email or student.email

        student.name = pending_update.name
        student.email = pending_update.email
        student.phone = pending_update.phone
        student.approval_status = 'approved'
            
        student.save()

        if student.user:
            student.user.email = student.email
            student.user.save()

        pending_update.status = 'approved'
        pending_update.reviewed_at = timezone.now()
        pending_update.save()

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

                        'Best regards,\n'
                        'The Quizopedia Team'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[target_email],
                    fail_silently=True,
                )
            except Exception:
                pass

        messages.success(
            request,
            f'Profile update for {student.name} approved successfully.'
        )

    redirect_to = request.GET.get('next') or request.POST.get('next') or request.META.get('HTTP_REFERER') or 'student_list'
    return redirect(redirect_to)


@login_required
def reject_student(request, student_id):
    if not request.user.is_staff:
        return redirect('home')

    student = get_object_or_404(Student, id=student_id)

    pending_update = PendingProfileUpdate.objects.filter(
        student=student,
        status='pending'
    ).order_by('-submitted_at').first()

    if pending_update:
        return redirect('reject_profile_update', update_id=pending_update.id)

    student.approval_status = 'approved'
    student.save()
    messages.success(request, f'Student {student.name} record updated.')
    redirect_to = request.GET.get('next') or request.POST.get('next') or request.META.get('HTTP_REFERER') or 'student_list'
    return redirect(redirect_to)


@login_required
def approve_profile_update(request, update_id):
    if not request.user.is_staff:
        return redirect('home')

    pending_update = get_object_or_404(
        PendingProfileUpdate,
        id=update_id,
        status='pending'
    )
    student = pending_update.student

    target_email = pending_update.email or student.email

    student.name = pending_update.name
    student.email = pending_update.email
    student.phone = pending_update.phone
    student.approval_status = 'approved'
    student.save()

    if student.user:
        student.user.email = student.email
        student.user.save()

    pending_update.status = 'approved'
    pending_update.reviewed_at = timezone.now()
    pending_update.save()

    if target_email:
        send_mail(
            subject='Quizopedia - Profile Update Approved!',
            message=(
                f'Hello {student.name},\n\n'
                'Your profile update request has been approved.\n\n'
                f'Name: {student.name}\n'
                f'Email: {student.email}\n'
                f'Phone: {student.phone}\n\n'
                'Best regards,\nThe Quizopedia Team'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[target_email],
            fail_silently=True,
        )

    messages.success(request, 'Profile update approved successfully.')
    redirect_to = request.GET.get('next') or request.POST.get('next') or request.META.get('HTTP_REFERER') or 'pending_approvals'
    return redirect(redirect_to)


@login_required
def reject_profile_update(request, update_id):
    if not request.user.is_staff:
        return redirect('home')

    pending_update = get_object_or_404(
        PendingProfileUpdate,
        id=update_id,
        status='pending'
    )
    student = pending_update.student
    requested_change = pending_update.requested_changes_display

    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        if not rejection_reason:
            messages.error(request, 'Please provide a reason for rejection.')
            return redirect('reject_profile_update', update_id=update_id)

        pending_update.status = 'rejected'
        pending_update.rejection_reason = rejection_reason
        pending_update.reviewed_at = timezone.now()
        pending_update.save()

        student.approval_status = 'approved'
        student.save()

        recipients = list(set(filter(None, [student.email, pending_update.email])))

        if recipients:
            email_body = (
                f"Hello {student.name},\n\n"
                "Your profile update request has been reviewed and rejected.\n"
                f"Reason: {rejection_reason}\n\n"
                "Your existing profile information remains unchanged.\n\n"
                "Best regards,\n"
                "The Quizopedia Team"
            )
            try:
                send_mail(
                    subject="Quizopedia — Profile Update Request Rejected",
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipients,
                    fail_silently=False,
                )
            except Exception:
                pass

        messages.success(request, f'Profile update request for {student.name} was rejected.')
        return redirect('pending_approvals')

    return render(request, 'reports/reject_profile_update.html', {
        'pending_update': pending_update,
        'student': student,
        'requested_change': requested_change,
        'default_example_reason': 'The provided email address could not be verified.',
    })



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


@login_required
def edit_question(request, question_id):
    if not request.user.is_staff:
        return redirect('home')

    question = get_object_or_404(Question, pk=question_id)
    subjects = Subject.objects.all().order_by('name')
    options = list(question.option_set.order_by('id'))

    if request.method == 'POST':
        subject_id = request.POST.get('subject', '').strip()
        question_text = request.POST.get('question_text', '').strip()
        option_texts = [
            request.POST.get(f'option_{i}', '').strip()
            for i in range(1, 5)
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

        if any(not text for text in option_texts):
            errors.append('Please fill in all four options.')

        if correct_option not in {'1', '2', '3', '4'}:
            errors.append('Please select exactly one correct option.')

        if not errors:
            with transaction.atomic():
                question.subject = subject
                question.question_text = question_text
                question.save()

                for index, option_text in enumerate(option_texts, start=1):
                    if index <= len(options):
                        option = options[index - 1]
                        option.option_text = option_text
                        option.is_answer = (str(index) == correct_option)
                        option.save()
                    else:
                        Option.objects.create(
                            question=question,
                            option_text=option_text,
                            is_answer=(str(index) == correct_option)
                        )

                for extra_option in options[4:]:
                    extra_option.delete()

            messages.success(request, 'Question updated successfully!')
            return redirect('question_bank')

        for error in errors:
            messages.error(request, error)
        return redirect('question_bank')

    return render(request, 'reports/edit_question.html', {
        'question': question,
        'subjects': subjects,
        'options': options,
        'option_values': [
            request.POST.get(f'option_{i}', options[i - 1].option_text)
            if i <= len(options) else ''
            for i in range(1, 5)
        ],
        'correct_option': (
            request.POST.get('correct_option')
            or next(
                (
                    str(i)
                    for i, option in enumerate(options, start=1)
                    if option.is_answer
                ),
                ''
            )
        ),
    })




@login_required
def subject_list(request):
    if not request.user.is_staff:
        messages.error(request, "Only administrators can manage subjects.")
        return redirect('home')

    search_query = request.GET.get('search', '').strip()

    subjects = Subject.objects.all().order_by('name')

    if search_query:
        subjects = subjects.filter(name__icontains=search_query)

    paginator = Paginator(subjects, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'reports/subject_list.html', {
        'subjects': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    })


@login_required
def subject_create(request):
    if not request.user.is_staff:
        messages.error(request, "Only administrators can manage subjects.")
        return redirect('home')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if not name:
            messages.error(request, "Subject name is required.")
            return redirect('subject_list')
        elif Subject.objects.filter(name__iexact=name).exists():
            messages.error(request, "This subject already exists.")
            return redirect('subject_list')
        else:
            Subject.objects.create(
                name=name,
                description=description,
            )
            messages.success(request, "Subject created successfully.")
            return redirect('subject_list')

    return render(request, 'reports/subject_form.html', {
        'page_title': 'Add Subject',
    })


@login_required
def subject_update(request, subject_id):
    if not request.user.is_staff:
        messages.error(request, "Only administrators can manage subjects.")
        return redirect('home')

    subject = get_object_or_404(Subject, pk=subject_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if not name:
            messages.error(request, "Subject name is required.")
            return redirect('subject_list')
        elif Subject.objects.filter(
            name__iexact=name
        ).exclude(pk=subject.pk).exists():
            messages.error(request, "Another subject already uses this name.")
            return redirect('subject_list')
        else:
            subject.name = name
            subject.description = description
            subject.save()
            messages.success(request, "Subject updated successfully.")
            return redirect('subject_list')

    return render(request, 'reports/subject_form.html', {
        'subject': subject,
        'page_title': 'Update Subject',
    })


@login_required
def subject_delete(request, subject_id):
    if not request.user.is_staff:
        messages.error(request, "Only administrators can manage subjects.")
        return redirect('home')

    subject = get_object_or_404(Subject, pk=subject_id)

    if request.method == 'POST':
        subject.delete()
        messages.success(request, "Subject deleted successfully.")
        return redirect('subject_list')

    return render(request, 'reports/subject_confirm_delete.html', {
        'subject': subject,
    })



def password_reset_request(request):
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        user = User.objects.filter(email__iexact=email).first()

        if user:
            otp = f"{random.randint(100000, 999999)}"
            expiry = time.time() + 120  

            request.session['pw_reset_user_id'] = user.id
            request.session['pw_reset_email'] = user.email
            request.session['pw_reset_otp'] = otp
            request.session['pw_reset_expiry'] = expiry
            request.session['pw_reset_verified'] = False

            student_profile = getattr(user, 'student_profile', None)
            if student_profile:
                StudentOTP.objects.create(
                    student=student_profile,
                    otp=otp,
                    expires_at=timezone.now() + timedelta(seconds=120),
                    is_used=False
                )

            try:
                send_mail(
                    subject='Quizopedia - Password Reset OTP',
                    message=(
                        f'Hello {user.username},\n\n'
                        'A request was made to reset your Quizopedia account password.\n\n'
                        f'Your One-Time Password (OTP) is:\n\n'
                        f'    {otp}\n\n'
                        'This OTP is valid for 2 minutes. Please enter this code promptly.\n\n'
                        'If you did not request this, please ignore this email.\n\n'
                        'Best regards,\n'
                        'The Quizopedia Team'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                request.session['pw_reset_resend_after'] = time.time() + OTP_RESEND_COOLDOWN
                return redirect('password_reset_verify_otp')
            except Exception as e:
                messages.error(request, 'Unable to send email at this moment. Please try again.')
        else:
            messages.error(request, 'No registered user was found with that email address.')

    return render(request, 'reports/password_reset.html')



def password_reset_verify_otp(request):
    email = request.session.get('pw_reset_email')
    otp = request.session.get('pw_reset_otp')
    expiry = request.session.get('pw_reset_expiry', 0)

    if not email or not otp:
        return redirect('password_reset')
    now = time.time()
    remaining_seconds = max(0, int(expiry - now))
    is_expired = remaining_seconds <= 0

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        if now > expiry:
            is_expired = True
            remaining_seconds = 0
            messages.error(
                request,
                'Your OTP has expired! Please click "Resend OTP" below to receive a new code.'
            )
        elif entered_otp != str(otp):
            messages.error(
                request,
                'Invalid OTP code. Please check your email and try again.'
            )
        else:
            request.session['pw_reset_verified'] = True
            user_id = request.session.get('pw_reset_user_id')
            if user_id:
                u = User.objects.filter(id=user_id).first()
                if u and hasattr(u, 'student_profile'):
                    StudentOTP.objects.filter(student=u.student_profile, otp=entered_otp, is_used=False).update(is_used=True)
            return redirect('password_reset_new_password')
        
    resend_seconds = max(
        0,
        int(
            request.session.get('pw_reset_resend_after', 0)
            - time.time()
        )
    )
    return render(
        request,
        'reports/password_reset_verify_otp.html',
        {
            'email': email,
            'remaining_seconds': remaining_seconds,
            'is_expired': is_expired,
            'resend_seconds': resend_seconds,
        }
    )

def password_reset_resend_otp(request):
    
    if request.method != 'POST':
        return redirect('password_reset_verify_otp')

    email = request.session.get('pw_reset_email')
    user_id = request.session.get('pw_reset_user_id')
    
    if not email or not user_id:
        return redirect('password_reset')

    user = User.objects.filter(id=user_id, email__iexact=email).first()
    if not user:
        return redirect('password_reset')
    now = time.time()
    resend_after = request.session.get('pw_reset_resend_after', 0)
    remaining = int(resend_after - now)
    if remaining > 0:
        messages.warning(
            request,
            f'Please wait {remaining} seconds before requesting another OTP.'
        )
        return redirect('password_reset_verify_otp')

    new_otp = f"{random.randint(100000, 999999)}"

    try:
        send_mail(
            subject='Quizopedia - New Password Reset OTP',
            message=(
                f'Hello {user.username},\n\n'
                'Here is your new OTP for resetting your Quizopedia password:\n\n'
                f'    {new_otp}\n\n'
                'This OTP is valid for 2 minutes.\n\n'
                'Best regards,\n'
                'The Quizopedia Team'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        now = time.time()
        request.session['pw_reset_otp'] = new_otp
        request.session['pw_reset_expiry'] = now + 120
        request.session['pw_reset_resend_after'] = now + OTP_RESEND_COOLDOWN
        request.session['pw_reset_verified'] = False

        student_profile = getattr(user, 'student_profile', None)
        if student_profile:
            StudentOTP.objects.create(
                student=student_profile,
                otp=new_otp,
                expires_at=timezone.now() + timedelta(seconds=120),
                is_used=False
            )

        messages.success(request, f'A new OTP has been sent to {email}.')

    except Exception:
        messages.error(
            request,
            'Failed to send new OTP. Please try again later.'
        )

    return redirect('password_reset_verify_otp')


def password_reset_new_password(request):
    
    user_id = request.session.get('pw_reset_user_id')
    verified = request.session.get('pw_reset_verified')

    if not user_id or not verified:
        return redirect('password_reset')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        p1 = request.POST.get('password', '')
        p2 = request.POST.get('confirm_password', '')

        if not p1 or not p2:
            messages.error(request, 'Please provide both password fields.')
        elif p1 != p2:
            messages.error(request, 'Passwords do not match.')
        elif len(p1) < 4:
            messages.error(request, 'Password must be at least 4 characters.')
        else:
            user.set_password(p1)
            user.save()

            for key in [
                'pw_reset_user_id',
                'pw_reset_email',
                'pw_reset_otp',
                'pw_reset_expiry',
                'pw_reset_verified',
                'pw_reset_resend_after',
            ]:
                request.session.pop(key, None)

            return redirect('password_reset_complete')

    return render(request, 'reports/password_reset_new_password.html')


def password_reset_complete(request):
    
    return render(request, 'reports/password_reset_complete.html')

def admin_login(request):
    """Explicit login view for administrators."""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('dashboard')
        return redirect('profile')
    return user_login(request, is_admin=True)


def user_login(request, is_admin=False):
   
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('dashboard')
        return redirect('profile')

    next_url = request.POST.get('next') or request.GET.get('next') or ''
    is_admin_mode = (
        is_admin or
        request.GET.get('role') == 'admin' or
        request.POST.get('role') == 'admin' or
        'dashboard' in next_url or
        'admin' in next_url or
        request.path == '/admin-login/'
    )

    if request.method == 'POST':
        post_data = request.POST.copy()
        raw_username = post_data.get('username', '').strip()
        matching_user = User.objects.filter(username__iexact=raw_username).first() or User.objects.filter(email__iexact=raw_username).first()
        if matching_user:
            post_data['username'] = matching_user.username

        form = AuthenticationForm(request, data=post_data)
        if form.is_valid():
            user = form.get_user()

            if user.is_staff:
        
                auth_login(request, user)
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard')
            else:
                if is_admin_mode:
                    messages.error(
                        request,
                        'This account does not have administrator privileges. Please use Student Login.'
                    )
                    return render(request, 'reports/login.html', {
                        'form': form,
                        'next': next_url,
                        'is_admin_mode': is_admin_mode,
                    })

                auth_login(request, user)
                if next_url:
                    return redirect(next_url)
                return redirect('home')
    else:
        form = AuthenticationForm(request)

    return render(request, 'reports/login.html', {
        'form': form,
        'next': next_url,
        'is_admin_mode': is_admin_mode,
    })



def student_login_verify_otp(request):

    user_id = request.session.get('student_login_user_id')
    email = request.session.get('student_login_email')
    otp = request.session.get('student_login_otp')
    expiry = request.session.get('student_login_expiry', 0)

    if not user_id or not otp or not email:
        return redirect('login')

    now = time.time()
    remaining_seconds = max(0, int(expiry - now))
    is_expired = remaining_seconds <= 0

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()

        if now > expiry:
            is_expired = True
            remaining_seconds = 0
            messages.error(
                request,
                'Your OTP has expired! Please click "Resend OTP" below to receive a new code.'
            )
        elif entered_otp != str(otp):
            messages.error(
                request,
                'Invalid OTP code. Please check your email and try again.'
            )
        else:
            user = get_object_or_404(User, id=user_id)
            auth_login(request, user)
            student_profile = getattr(user, 'student_profile', None)
            if student_profile:
                StudentOTP.objects.filter(student=student_profile, otp=entered_otp, is_used=False).update(is_used=True)
            next_url = request.session.get('student_login_next')
            for key in [
                'student_login_user_id',
                'student_login_email',
                'student_login_otp',
                'student_login_expiry',
                'student_login_next',
                'student_login_resend_after',
            ]:
                request.session.pop(key, None)
            if next_url:
                return redirect(next_url)
            return redirect('profile')

    resend_seconds = max(
        0,
        int(
            request.session.get('student_login_resend_after', 0)
            - time.time()
        )
    )

    return render(
        request,
        'reports/student_login_verify_otp.html',
        {
            'email': email,
            'remaining_seconds': remaining_seconds,
            'is_expired': is_expired,
            'resend_seconds': resend_seconds,
        }
    )



def student_login_resend_otp(request):
    
    if request.method != 'POST':
        return redirect('student_login_verify_otp')

    user_id = request.session.get('student_login_user_id')
    email = request.session.get('student_login_email')

    if not user_id or not email:
        return redirect('login')

    user = User.objects.filter(
        id=user_id,
        email__iexact=email
    ).first()
    if not user:
        return redirect('login')

    now = time.time()
    resend_after = request.session.get('student_login_resend_after', 0)
    remaining = int(resend_after - now)

    if remaining > 0:
        messages.warning(
            request,
            f'Please wait {remaining} seconds before requesting another OTP.'
        )
        return redirect('student_login_verify_otp')

    new_otp = f"{random.randint(100000, 999999)}"

    try:
        send_mail(
            subject='Quizopedia - New Student Login OTP',
            message=(
                f'Hello {user.username},\n\n'
                'Here is your new OTP for signing into Quizopedia:\n\n'
                f'    {new_otp}\n\n'
                'This OTP is valid for 2 minutes.\n\n'
                'Best regards,\n'
                'The Quizopedia Team'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        now = time.time()
        request.session['student_login_otp'] = new_otp
        request.session['student_login_expiry'] = now + 120
        request.session['student_login_resend_after'] = now + OTP_RESEND_COOLDOWN

        student_profile = getattr(user, 'student_profile', None)
        if student_profile:
            StudentOTP.objects.create(
                student=student_profile,
                otp=new_otp,
                expires_at=timezone.now() + timedelta(seconds=120),
                is_used=False
            )

        messages.success(request, f'A new login OTP has been sent to {email}.')

    except Exception:
        messages.error(
            request,
            'Failed to send new OTP. Please try again later.'
        )

    return redirect('student_login_verify_otp')



def user_logout(request):
    
    auth_logout(request)
    return redirect('home')

@login_required
def delete_question(request, question_id):
    if not request.user.is_staff:
        return redirect('home')

    if request.method != 'POST':
        return redirect('question_bank')

    question = get_object_or_404(Question, pk=question_id)
    question.delete()

    messages.success(
        request,
        'Question and its options deleted successfully!'
    )
    return redirect('question_bank')
