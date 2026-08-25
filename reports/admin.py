from django.contrib import admin
from .models import Admin, Student, Subject, Question

admin.site.register(Admin)
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'email', 'phone')

admin.site.register(Question)    
admin.site.register(Subject)