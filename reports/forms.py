import re
from django import forms
from .models import Student


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'email', 'phone']
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'form-input',
                    'placeholder': 'Enter full legal name (e.g., Savan Bharvadiya)',
                    'autocomplete': 'name',
                    'required': True,
                }
            ),
            'email': forms.EmailInput(
                attrs={
                    'class': 'form-input',
                    'placeholder': 'Enter active email address (e.g., student@example.com)',
                    'autocomplete': 'email',
                    'required': True,
                }
            ),
            'phone': forms.TextInput(
                attrs={
                    'class': 'form-input',
                    'placeholder': 'Enter contact phone number (e.g., +91 9876543210)',
                    'autocomplete': 'tel',
                    'required': True,
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise forms.ValidationError('Full name must be at least 2 characters long.')
        return name

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError('A valid email address is required.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise forms.ValidationError('A contact phone number is required.')
        
        digits_only = re.sub(r'[\s\-\+\(\)]', '', phone)
        if len(digits_only) < 7:
            raise forms.ValidationError('Please enter a valid phone number with at least 7 digits.')
        return phone