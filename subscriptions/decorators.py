from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def subscription_required(view_func):
    """Decorator to require active subscription"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Check if user has active subscription
        if hasattr(request.user, 'subscription') and request.user.subscription.is_active:
            return view_func(request, *args, **kwargs)
        
        messages.warning(request, 'You need an active subscription to access this page.')
        return redirect('subscriptions:subscription_page')
    
    return wrapper