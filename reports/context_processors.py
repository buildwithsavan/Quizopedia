from .models import Student, Question, Subject, Admin, PendingProfileUpdate, StudentOTP

def admin_sidebar_context(request):

    if not (request.user.is_authenticated and request.user.is_staff):
        return {}

    try:
        total_students = Student.objects.count()
        total_questions = Question.objects.count()
        total_subjects = Subject.objects.count()
        total_admins = Admin.objects.count()
        pending_count = PendingProfileUpdate.objects.filter(status='pending').count()
        recent_otps_count = StudentOTP.objects.count()

        return {
            'total_students': total_students,
            'total_questions': total_questions,
            'total_subjects': total_subjects,
            'total_admins': total_admins,
            'pending_count': pending_count,
            'recent_otps_count': recent_otps_count,
        }
    except Exception:
        return {}
