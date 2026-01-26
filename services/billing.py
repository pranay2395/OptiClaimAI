"""
Stripe Billing Integration
Subscription management, webhooks, payment processing
"""

import stripe
import os
from typing import Optional, Dict, Any
from services.database import SessionLocal, User, Subscription, SubscriptionTier
from datetime import datetime

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_ENDPOINT_SECRET = os.getenv("STRIPE_ENDPOINT_SECRET", STRIPE_WEBHOOK_SECRET)

# Pricing
STRIPE_PRICES = {
    SubscriptionTier.BASIC: os.getenv("STRIPE_PRICE_BASIC", "price_basic"),
    SubscriptionTier.PRO: os.getenv("STRIPE_PRICE_PRO", "price_pro"),
}


class BillingService:
    """Stripe billing service"""
    
    @staticmethod
    def create_checkout_session(user_id: int, tier: str, success_url: str, cancel_url: str) -> Optional[str]:
        """
        Create a Stripe Checkout session.
        
        Returns: checkout session URL
        """
        try:
            db = SessionLocal()
            user = db.query(User).filter(User.id == user_id).first()
            db.close()
            
            if not user:
                return None
            
            price_id = STRIPE_PRICES.get(tier)
            if not price_id:
                return None
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                customer_email=user.email,
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": user_id,
                    "tier": tier,
                }
            )
            
            return session.url
        
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e}")
            return None
    
    @staticmethod
    def get_subscription_status(user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's subscription status"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.subscription:
                return None
            
            return {
                "tier": user.subscription.tier,
                "status": user.subscription.status,
                "is_active": user.subscription.is_active(),
                "days_until_renewal": user.subscription.days_until_renewal(),
                "current_period_end": user.subscription.current_period_end,
            }
        finally:
            db.close()
    
    @staticmethod
    def handle_webhook(event: Dict[str, Any]) -> bool:
        """
        Handle Stripe webhook events.
        
        Returns: True if handled successfully
        """
        event_type = event["type"]
        
        try:
            if event_type == "checkout.session.completed":
                return BillingService._handle_checkout_completed(event["data"]["object"])
            
            elif event_type == "customer.subscription.updated":
                return BillingService._handle_subscription_updated(event["data"]["object"])
            
            elif event_type == "customer.subscription.deleted":
                return BillingService._handle_subscription_deleted(event["data"]["object"])
            
            elif event_type == "invoice.payment_failed":
                return BillingService._handle_payment_failed(event["data"]["object"])
            
            return True  # Other events don't need handling
        
        except Exception as e:
            print(f"Webhook error: {e}")
            return False
    
    @staticmethod
    def _handle_checkout_completed(session: Dict[str, Any]) -> bool:
        """Handle checkout.session.completed"""
        db = SessionLocal()
        try:
            user_id = session.get("metadata", {}).get("user_id")
            tier = session.get("metadata", {}).get("tier")
            customer_id = session.get("customer")
            subscription_id = session.get("subscription")
            
            if not user_id or not tier:
                return False
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Get subscription details from Stripe
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Create or update subscription
            subscription = user.subscription or Subscription(user_id=user_id)
            subscription.tier = tier
            subscription.stripe_customer_id = customer_id
            subscription.stripe_subscription_id = subscription_id
            subscription.status = "active"
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
            
            db.add(subscription)
            db.commit()
            return True
        
        except Exception as e:
            print(f"Error handling checkout: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def _handle_subscription_updated(subscription: Dict[str, Any]) -> bool:
        """Handle customer.subscription.updated"""
        db = SessionLocal()
        try:
            subscription_obj = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription["id"]
            ).first()
            
            if not subscription_obj:
                return False
            
            subscription_obj.status = subscription["status"]
            subscription_obj.current_period_start = datetime.fromtimestamp(subscription["current_period_start"])
            subscription_obj.current_period_end = datetime.fromtimestamp(subscription["current_period_end"])
            subscription_obj.updated_at = datetime.utcnow()
            
            db.commit()
            return True
        
        except Exception as e:
            print(f"Error updating subscription: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def _handle_subscription_deleted(subscription: Dict[str, Any]) -> bool:
        """Handle customer.subscription.deleted (cancellation)"""
        db = SessionLocal()
        try:
            subscription_obj = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription["id"]
            ).first()
            
            if not subscription_obj:
                return False
            
            subscription_obj.status = "canceled"
            subscription_obj.updated_at = datetime.utcnow()
            
            db.commit()
            return True
        
        except Exception as e:
            print(f"Error deleting subscription: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def _handle_payment_failed(invoice: Dict[str, Any]) -> bool:
        """Handle invoice.payment_failed"""
        db = SessionLocal()
        try:
            subscription_obj = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == invoice["subscription"]
            ).first()
            
            if not subscription_obj:
                return False
            
            subscription_obj.status = "past_due"
            subscription_obj.updated_at = datetime.utcnow()
            
            db.commit()
            # TODO: Send email to user about payment failure
            return True
        
        except Exception as e:
            print(f"Error handling payment failure: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def cancel_subscription(user_id: int) -> bool:
        """Cancel user's subscription"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.subscription:
                return False
            
            # Cancel on Stripe
            stripe.Subscription.delete(user.subscription.stripe_subscription_id)
            
            # Update local status
            user.subscription.status = "canceled"
            user.subscription.updated_at = datetime.utcnow()
            db.commit()
            
            return True
        
        except Exception as e:
            print(f"Error canceling subscription: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def get_billing_portal_url(user_id: int) -> Optional[str]:
        """Get Stripe customer portal URL for managing subscription"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.subscription or not user.subscription.stripe_customer_id:
                return None
            
            session = stripe.billing_portal.Session.create(
                customer=user.subscription.stripe_customer_id,
                return_url="http://localhost:8501",
            )
            
            return session.url
        
        except Exception as e:
            print(f"Error creating portal session: {e}")
            return None
        finally:
            db.close()
