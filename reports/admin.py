from django.contrib import admin
from .models import Admin, Student, Subject, Question, Option

from django.core.mail import send_mail
from django.conf import settings

admin.site.register(Admin)
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'phone', 'approval_status', 'pending_name', 'pending_email')
    list_filter = ('approval_status',)
    actions = ['approve_profiles', 'reject_profiles']

    @admin.action(description='Approve selected student profile updates')
    def approve_profiles(self, request, queryset):
        count = 0
        for student in queryset.filter(approval_status='pending'):
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
                            'Your profile update request on Quizopedia has been APPROVED by an administrator.\n\n'
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
            count += 1
        self.message_user(request, f"{count} student profile(s) approved and notified.")

    @admin.action(description='Reject selected student profile updates')
    def reject_profiles(self, request, queryset):
        count = 0
        for student in queryset.filter(approval_status='pending'):
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
                            'Your profile update request was reviewed and declined by an administrator.\n\n'
                            'Your existing profile information remains in place.\n\n'
                            'Best regards,\n'
                            'The Quizopedia Team'
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[target_email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
            count += 1
        self.message_user(request, f"{count} student profile(s) rejected and notified.")


admin.site.register(Question)    
admin.site.register(Subject)
@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ('question', 'option_text', 'is_answer')