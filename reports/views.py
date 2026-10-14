from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count
from django.db import transaction
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
import random
import time
from .models import Admin, Student, Question, Subject, Option
from .forms import StudentProfileForm

OTP_RESEND_COOLDOWN = 30

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

def user_login(request):
   
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('dashboard')
        return redirect('profile')

    next_url = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()

            if user.is_staff:
        
                auth_login(request, user)
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard')
            else:
                
                student_profile = getattr(user, 'student_profile', None)
                student_email = getattr(student_profile, 'email', None) or user.email

                if not student_email:
                    messages.error(
                        request,
                        'No email address is linked with this student account. Please contact an administrator.'
                    )
                    return render(request, 'reports/login.html', {'form': form, 'next': next_url})

                otp = f"{random.randint(100000, 999999)}"
                expiry = time.time() + 120  

                request.session['student_login_user_id'] = user.id
                request.session['student_login_email'] = student_email
                request.session['student_login_otp'] = otp
                request.session['student_login_expiry'] = expiry
                request.session['student_login_next'] = next_url

                try:
                    send_mail(
                        subject='Quizopedia - Student Login OTP',
                        message=(
                            f'Hello {user.username},\n\n'
                            'A login attempt was made for your Quizopedia student account.\n\n'
                            f'Your One-Time Password (OTP) is:\n\n'
                            f'    {otp}\n\n'
                            'This OTP is valid for 2 minutes. Please enter it to complete your sign in.\n\n'
                            'If you did not attempt to sign in, please contact support or change your password.\n\n'
                            'Best regards,\n'
                            'The Quizopedia Team'
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[student_email],
                        fail_silently=False,
                    )
                    request.session['student_login_resend_after'] = time.time() + OTP_RESEND_COOLDOWN
                    return redirect('student_login_verify_otp')
                except Exception as e:
                    messages.error(request, 'Unable to send OTP email at this moment. Please try again.')
    else:
        form = AuthenticationForm(request)

    return render(request, 'reports/login.html', {'form': form, 'next': next_url})



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
            return redirect('student_list')

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
        id=usrer_id,
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


