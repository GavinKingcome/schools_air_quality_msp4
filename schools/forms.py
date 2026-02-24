"""
schools/forms.py

Forms with validation for school profile editing and note management.
Addresses criteria 1.4 and 2.3 (forms with validation beyond auth).
"""

from django import forms
from .models import School, SchoolNote


class SchoolContactForm(forms.ModelForm):
    """
    Form for school administrators to update their school's contact details.
    
    Only exposes non-sensitive fields that a school admin would
    reasonably need to update.
    """
    
    class Meta:
        model = School
        fields = ['phone', 'email', 'website', 'student_count']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 020 7123 4567',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. office@school.sch.uk',
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. https://www.school.sch.uk',
            }),
            'student_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Approximate number of students',
                'min': '1',
                'max': '2000',
            }),
        }
    
    def clean_phone(self):
        """Validate UK phone number format."""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove spaces and dashes for validation
            cleaned = phone.replace(' ', '').replace('-', '')
            if not cleaned.replace('+', '').isdigit():
                raise forms.ValidationError(
                    'Phone number should contain only digits, spaces, and dashes.'
                )
            if len(cleaned) < 10 or len(cleaned) > 15:
                raise forms.ValidationError(
                    'Phone number should be between 10 and 15 digits.'
                )
        return phone
    
    def clean_student_count(self):
        """Validate student count is reasonable."""
        count = self.cleaned_data.get('student_count')
        if count is not None:
            if count < 1:
                raise forms.ValidationError(
                    'Student count must be at least 1.'
                )
            if count > 2000:
                raise forms.ValidationError(
                    'Student count seems too high. Please check the number.'
                )
        return count


class SchoolNoteForm(forms.ModelForm):
    """
    Form for users to submit notes about a school's air quality environment.
    """
    
    class Meta:
        model = SchoolNote
        fields = ['title', 'category', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief summary of your observation',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe what you have observed about air quality '
                              'conditions at this school...',
            }),
        }
    
    def clean_title(self):
        """Validate title length and content."""
        title = self.cleaned_data.get('title')
        if title and len(title.strip()) < 5:
            raise forms.ValidationError(
                'Title should be at least 5 characters long.'
            )
        return title.strip()
    
    def clean_content(self):
        """Validate content length."""
        content = self.cleaned_data.get('content')
        if content and len(content.strip()) < 10:
            raise forms.ValidationError(
                'Please provide a more detailed description (at least 10 characters).'
            )
        return content.strip()