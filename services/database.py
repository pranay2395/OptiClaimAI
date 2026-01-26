"""
Database Models for OptiClaimAI SaaS
User accounts, subscriptions, usage tracking, claims storage
"""

from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import bcrypt
import os
from enum import Enum as PyEnum

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///opticlaimai.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class SubscriptionTier(str, PyEnum):
    """Subscription tier types"""
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class User(Base):
    """User account"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(255))
    last_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")
    claims = relationship("ClaimStorage", back_populates="user", cascade="all, delete-orphan")
    
    def set_password(self, password: str):
        """Hash and set password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Subscription(Base):
    """User subscription"""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    tier = Column(String(50), default=SubscriptionTier.BASIC)
    stripe_customer_id = Column(String(255), unique=True)
    stripe_subscription_id = Column(String(255), unique=True)
    status = Column(String(50), default="active")  # active, past_due, canceled
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        if self.status != "active":
            return False
        if self.current_period_end and datetime.utcnow() > self.current_period_end:
            return False
        return True
    
    def days_until_renewal(self) -> int:
        """Days until next renewal"""
        if not self.current_period_end:
            return -1
        delta = self.current_period_end - datetime.utcnow()
        return max(0, delta.days)
    
    def to_dict(self):
        return {
            "tier": self.tier,
            "status": self.status,
            "is_active": self.is_active(),
            "days_until_renewal": self.days_until_renewal(),
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
        }


class UsageLog(Base):
    """Usage tracking for metering"""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # claim_created, claim_validated, edi_generated, ai_called
    count = Column(Integer, default=1)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metadata = Column(Text)  # JSON string with additional info
    
    # Relationships
    user = relationship("User", back_populates="usage_logs")
    
    def to_dict(self):
        return {
            "action": self.action,
            "count": self.count,
            "timestamp": self.timestamp.isoformat(),
        }


class ClaimStorage(Base):
    """Encrypted claim storage"""
    __tablename__ = "claims"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    claim_id = Column(String(255), unique=True, nullable=False)
    encrypted_data = Column(Text, nullable=False)  # Encrypted JSON
    claim_summary = Column(Text)  # Plain text summary for search
    status = Column(String(50), default="pending")  # pending, validated, exported, denied
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="claims")
    
    def to_dict(self):
        return {
            "claim_id": self.claim_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# Create all tables
def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============= SUBSCRIPTION TIER LIMITS =============

TIER_LIMITS = {
    SubscriptionTier.BASIC: {
        "claims_per_month": 10,
        "ai_explanations_per_month": 5,
        "features": ["cms1500_form", "validation", "edi_generation"],
    },
    SubscriptionTier.PRO: {
        "claims_per_month": None,  # Unlimited
        "ai_explanations_per_month": None,  # Unlimited
        "features": ["cms1500_form", "validation", "edi_generation", "edi_upload", "nppes_lookup", "ai_full"],
    },
    SubscriptionTier.ENTERPRISE: {
        "claims_per_month": None,  # Unlimited
        "ai_explanations_per_month": None,  # Unlimited
        "features": ["all"],
    },
}


def get_tier_limits(tier: str) -> dict:
    """Get feature limits for tier"""
    return TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.BASIC])


# ============= USAGE TRACKING HELPERS =============

def log_usage(user_id: int, action: str, count: int = 1, metadata: str = None):
    """Log a usage event"""
    db = SessionLocal()
    try:
        usage = UsageLog(user_id=user_id, action=action, count=count, metadata=metadata)
        db.add(usage)
        db.commit()
    finally:
        db.close()


def get_monthly_usage(user_id: int, action: str) -> int:
    """Get usage count for current month"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        result = db.query(UsageLog).filter(
            UsageLog.user_id == user_id,
            UsageLog.action == action,
            UsageLog.timestamp >= month_start
        ).all()
        
        return sum(log.count for log in result)
    finally:
        db.close()


def has_feature(user_id: int, feature: str) -> bool:
    """Check if user has access to feature"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.subscription or not user.subscription.is_active():
            return False
        
        limits = get_tier_limits(user.subscription.tier)
        
        # Enterprise has all features
        if "all" in limits.get("features", []):
            return True
        
        # Check if feature is in tier's feature list
        return feature in limits.get("features", [])
    finally:
        db.close()


def check_usage_limit(user_id: int, action: str) -> tuple[bool, str]:
    """
    Check if user has exceeded monthly limit for action.
    
    Returns: (is_allowed, message)
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.subscription:
            return False, "No active subscription"
        
        if not user.subscription.is_active():
            return False, "Subscription inactive"
        
        limits = get_tier_limits(user.subscription.tier)
        limit = limits.get(f"{action}_per_month")
        
        # No limit = unlimited
        if limit is None:
            return True, "OK"
        
        current_usage = get_monthly_usage(user_id, action)
        
        if current_usage >= limit:
            return False, f"Monthly limit of {limit} {action}s exceeded. Upgrade to Pro."
        
        # Warn at 80%
        if current_usage >= (limit * 0.8):
            return True, f"Warning: {limit - current_usage} {action}s remaining this month"
        
        return True, "OK"
    finally:
        db.close()
