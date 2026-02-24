"""
Registration view for Early Years Schools Pollution Monitor.

Provides user registration with email, redirecting authenticated
users away from the registration page (criterion 3.2).
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from django.shortcuts import render, redirect


class RegistrationForm(UserCreationForm):
    """Extended registration form with required email field."""

    email = forms.EmailField(
        required=True,
        help_text='Required. Enter a valid email address.'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        """Validate that the email is not already registered."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'An account with this email address already exists.'
            )
        return email


def register_view(request):
    """
    Handle user registration.

    - Redirects authenticated users to the map (criterion 3.2)
    - Creates account and logs user in on success
    - Shows validation errors on failure
    """
    if request.user.is_authenticated:
        return redirect('maps:map')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f'Welcome, {user.username}! Your account has been created.'
            )
            return redirect('maps:map')
    else:
        form = RegistrationForm()

    return render(request, 'registration/register.html', {'form': form})