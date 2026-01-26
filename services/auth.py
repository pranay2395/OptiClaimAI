"""
Authentication & Session Management
Login, registration, session persistence
"""

from services.database import SessionLocal, User, Subscription, SubscriptionTier, init_db
from datetime import datetime
from typing import Optional, Tuple


class AuthService:
    """Authentication service"""
    
    @staticmethod
    def register(email: str, password: str, first_name: str = "", last_name: str = "") -> Tuple[bool, str]:
        """
        Register a new user.
        
        Returns: (success, message)
        """
        db = SessionLocal()
        try:
            # Check if email already exists
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                return False, "Email already registered"
            
            # Create user
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user.set_password(password)
            
            db.add(user)
            db.flush()  # Get user ID
            
            # Create default BASIC subscription
            subscription = Subscription(
                user_id=user.id,
                tier=SubscriptionTier.BASIC,
                status="pending"  # Pending payment
            )
            db.add(subscription)
            db.commit()
            
            return True, f"User registered. User ID: {user.id}"
        
        except Exception as e:
            db.rollback()
            return False, f"Registration error: {str(e)}"
        finally:
            db.close()
    
    @staticmethod
    def login(email: str, password: str) -> Tuple[bool, Optional[int], str]:
        """
        Authenticate user.
        
        Returns: (success, user_id, message)
        """
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            
            if not user:
                return False, None, "Invalid email or password"
            
            if not user.is_active:
                return False, None, "Account is inactive"
            
            if not user.verify_password(password):
                return False, None, "Invalid email or password"
            
            return True, user.id, "Login successful"
        
        except Exception as e:
            return False, None, f"Login error: {str(e)}"
        finally:
            db.close()
    
    @staticmethod
    def get_user(user_id: int) -> Optional[dict]:
        """Get user details"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            return {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "is_active": user.is_active,
            }
        finally:
            db.close()
    
    @staticmethod
    def get_user_with_subscription(user_id: int) -> Optional[dict]:
        """Get user with subscription details"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            user_data = {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "is_active": user.is_active,
            }
            
            if user.subscription:
                user_data["subscription"] = {
                    "tier": user.subscription.tier,
                    "status": user.subscription.status,
                    "is_active": user.subscription.is_active(),
                    "days_until_renewal": user.subscription.days_until_renewal(),
                }
            
            return user_data
        finally:
            db.close()
    
    @staticmethod
    def verify_subscription_active(user_id: int) -> bool:
        """Check if user has active subscription"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.subscription:
                return False
            return user.subscription.is_active()
        finally:
            db.close()
    
    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "User not found"
            
            if not user.verify_password(old_password):
                return False, "Current password is incorrect"
            
            user.set_password(new_password)
            user.updated_at = datetime.utcnow()
            db.commit()
            
            return True, "Password changed successfully"
        
        except Exception as e:
            db.rollback()
            return False, f"Error: {str(e)}"
        finally:
            db.close()


def ensure_db_initialized():
    """Ensure database is initialized"""
    try:
        init_db()
    except Exception as e:
        print(f"Database initialization error: {e}")
