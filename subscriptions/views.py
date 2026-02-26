from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib import messages
import stripe
from .models import Subscription, Payment
from django.utils import timezone

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def subscription_page(request):
    """Subscription checkout page"""
    subscription, created = Subscription.objects.get_or_create(user=request.user)
    
    context = {
        'subscription': subscription,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'stripe_price_id': settings.STRIPE_PRICE_ID,
    }
    return render(request, 'subscriptions/subscription.html', context)


@login_required
def create_checkout_session(request):
    """Create Stripe Checkout session"""
    if request.method == 'POST':
        try:
            subscription = Subscription.objects.get(user=request.user)
            
            # Create or get Stripe customer
            if not subscription.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=request.user.email,
                    metadata={'user_id': request.user.id}
                )
                subscription.stripe_customer_id = customer.id
                subscription.save()
            
            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=subscription.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': settings.STRIPE_PRICE_ID,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=request.build_absolute_uri('/subscriptions/success/'),
                cancel_url=request.build_absolute_uri('/subscriptions/cancel/'),
            )
            
            return redirect(checkout_session.url)
            
        except Exception as e:
            messages.error(request, f'Error creating checkout session: {str(e)}')
            return redirect('subscriptions:subscription_page')
    
    return redirect('subscriptions:subscription_page')


@login_required
def subscription_success(request):
    """Subscription successful"""
    messages.success(request, 'Subscription activated! You now have access to the air quality dashboard.')
    return render(request, 'subscriptions/success.html')


@login_required
def subscription_cancel(request):
    """Subscription canceled"""
    messages.info(request, 'Subscription was canceled. You can try again anytime.')
    return render(request, 'subscriptions/cancel.html')


@login_required
def manage_subscription(request):
    """Manage existing subscription"""
    try:
        subscription = Subscription.objects.get(user=request.user)
    except Subscription.DoesNotExist:
        return redirect('subscriptions:subscription_page')
    
    context = {
        'subscription': subscription,
    }
    return render(request, 'subscriptions/manage.html', context)


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session(session)
    
    elif event['type'] == 'customer.subscription.updated':
        subscription_data = event['data']['object']
        handle_subscription_update(subscription_data)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription_data = event['data']['object']
        handle_subscription_deleted(subscription_data)
    
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        handle_payment_succeeded(invoice)
    
    return HttpResponse(status=200)


def handle_checkout_session(session):
    """Handle successful checkout"""
    customer_id = session.get('customer')
    subscription_id = session.get('subscription')
    
    try:
        subscription = Subscription.objects.get(stripe_customer_id=customer_id)
        subscription.stripe_subscription_id = subscription_id
        subscription.status = 'active'
        subscription.save()
        
        # Get subscription details from Stripe
        stripe_sub = stripe.Subscription.retrieve(subscription_id)
        subscription.current_period_start = timezone.datetime.fromtimestamp(
            stripe_sub.current_period_start, tz=timezone.utc
        )
        subscription.current_period_end = timezone.datetime.fromtimestamp(
            stripe_sub.current_period_end, tz=timezone.utc
        )
        subscription.save()
        
    except Subscription.DoesNotExist:
        pass


def handle_subscription_update(subscription_data):
    """Handle subscription status changes"""
    subscription_id = subscription_data['id']
    
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        subscription.status = subscription_data['status']
        subscription.current_period_start = timezone.datetime.fromtimestamp(
            subscription_data['current_period_start'], tz=timezone.utc
        )
        subscription.current_period_end = timezone.datetime.fromtimestamp(
            subscription_data['current_period_end'], tz=timezone.utc
        )
        subscription.save()
    except Subscription.DoesNotExist:
        pass


def handle_subscription_deleted(subscription_data):
    """Handle subscription cancellation"""
    subscription_id = subscription_data['id']
    
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        subscription.status = 'canceled'
        subscription.save()
    except Subscription.DoesNotExist:
        pass


def handle_payment_succeeded(invoice):
    """Record successful payment"""
    customer_id = invoice.get('customer')
    amount = invoice.get('amount_paid', 0) / 100  # Convert cents to pounds
    payment_intent_id = invoice.get('payment_intent')
    
    try:
        subscription = Subscription.objects.get(stripe_customer_id=customer_id)
        Payment.objects.create(
            subscription=subscription,
            stripe_payment_intent_id=payment_intent_id,
            amount=amount,
            currency='gbp',
            status='succeeded'
        )
    except Subscription.DoesNotExist:
        pass

# Create your views here.
