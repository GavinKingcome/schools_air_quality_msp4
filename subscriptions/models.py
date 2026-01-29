from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Subscription(models.Model):
    """
    User subscription model for accessing the air quality dashboard.
    
    For Phase 1: Simple single-tier subscription for basic access
    Future Phase 2: Tiered system (free for parents, paid for schools/admin)
    """
    
    SUBSCRIPTION_STATUS = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('past_due', 'Past Due'),
        ('trialing', 'Trialing'),
        ('incomplete', 'Incomplete'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    
    # Stripe fields
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Subscription details
    status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS,
        default='incomplete'
    )
    
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.status}"
    
    @property
    def is_active(self):
        """Check if subscription is currently active"""
        if self.status not in ['active', 'trialing']:
            return False
        
        if self.current_period_end and self.current_period_end < timezone.now():
            return False
        
        return True
    
    @property
    def days_remaining(self):
        """Calculate days remaining in current period"""
        if not self.current_period_end:
            return None
        
        delta = self.current_period_end - timezone.now()
        return max(0, delta.days)


class Payment(models.Model):
    """
    Track individual payments for audit trail and customer support.
    """
    
    PAYMENT_STATUS = [
        ('succeeded', 'Succeeded'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='gbp')
    
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='pending'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subscription.user.username} - £{self.amount} - {self.status}"

