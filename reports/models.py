from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class Admin(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='admin_profile'
    )

    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=50)
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.name


class Student(models.Model):

    APPROVAL_STATUS = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='student_profile'
    )

    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=50)
    phone = models.CharField(max_length=15)

    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS,
        default='approved'
    )

    pending_name = models.CharField(max_length=100, blank=True)
    pending_email = models.EmailField(max_length=50, blank=True)
    pending_phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.name

class PendingProfileUpdate(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='pending_profile_updates'
    )

    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=50)
    phone = models.CharField(max_length=15)

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    rejection_reason = models.TextField(blank=True, default='')
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    @property
    def requested_changes_display(self):
        changes = []
        if self.email and self.email.strip().lower() != (self.student.email or '').strip().lower():
            changes.append('Email address')
        if self.name and self.name.strip() != (self.student.name or '').strip():
            changes.append('Name')
        if self.phone and self.phone.strip() != (self.student.phone or '').strip():
            changes.append('Phone number')
        if not changes:
            return 'Email address'
        return ', '.join(changes)

    def __str__(self):
        return f"Profile update for {self.student.name} ({self.status})"

class Subject(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')

    def __str__(self):
        return self.name

class StudentOTP(models.Model):
    student = models.ForeignKey(
        'Student',
        on_delete=models.CASCADE,
        related_name='otps'
    )
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"OTP for {self.student.name}"


class Question(models.Model):
    subject = models.ForeignKey(Subject,on_delete=models.CASCADE)
    question_text = models.TextField()

    def __str__(self):
        return self.question_text

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    option_text = models.CharField(max_length=200)
    is_answer = models.BooleanField(default=False)

    def __str__(self):
        return self.option_text