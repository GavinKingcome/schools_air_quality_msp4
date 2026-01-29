from django.contrib import admin
from .models import Subscription, Payment


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'current_period_end', 'is_active', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'user__email', 'stripe_customer_id']
    readonly_fields = ['stripe_customer_id', 'stripe_subscription_id', 'created_at', 'updated_at']
    
    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'amount', 'currency', 'status', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['subscription__user__username', 'stripe_payment_intent_id']
    readonly_fields = ['stripe_payment_intent_id', 'created_at']

