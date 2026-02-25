"""
URL configuration for schools_air_quality_msp4 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.views.generic import RedirectView

from .views import register_view  # NEW: import registration view

urlpatterns = [
    path('', RedirectView.as_view(url='/map/', permanent=False), name='home'),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True,  # NEW: criterion 3.2 - redirect logged-in users
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/map/'), name='logout'),
    path('register/', register_view, name='register'),  # NEW: registration page
    
    # Password reset URLs
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset_form.html',
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt',
         ),
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    
    path('map/', include('maps.urls')),
    path('schools/', include('schools.urls')),
    path('subscriptions/', include('subscriptions.urls')),
]