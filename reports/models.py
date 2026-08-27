from django.db import models
from django.contrib.auth.models import User


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

class Subject(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Question(models.Model):
    subject = models.ForeignKey(Subject,on_delete=models.CASCADE)
    question_text = models.TextField()

    def __str__(self):
        return self.question_text