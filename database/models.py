from __future__ import annotations
import enum, uuid
from datetime import datetime, timezone
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def utcnow(): return datetime.now(timezone.utc)
def uid(): return str(uuid.uuid4())
class Base(DeclarativeBase): pass
class TimestampMixin:
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,nullable=False)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow,nullable=False)
class TelegramUser(Base,TimestampMixin):
    __tablename__='telegram_users'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    telegram_id:Mapped[int]=mapped_column(BigInteger,unique=True,index=True); username:Mapped[str|None]=mapped_column(String(64)); full_name:Mapped[str|None]=mapped_column(String(255)); phone_number:Mapped[str|None]=mapped_column(String(32),index=True)
class Plan(Base,TimestampMixin):
    __tablename__='plans'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); code:Mapped[str]=mapped_column(String(50),unique=True)
    name:Mapped[str]=mapped_column(String(100)); description:Mapped[str]=mapped_column(Text); price:Mapped[int]=mapped_column(Integer); currency:Mapped[str]=mapped_column(String(3),default='XTR')
    duration_days:Mapped[int|None]=mapped_column(Integer); starts_on:Mapped[str]=mapped_column(String(20),default='activation'); max_devices:Mapped[int]=mapped_column(Integer,default=1)
    features:Mapped[str]=mapped_column(Text,default='[]'); is_active:Mapped[bool]=mapped_column(Boolean,default=True)
class Order(Base,TimestampMixin):
    __tablename__='orders'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); user_id:Mapped[str]=mapped_column(ForeignKey('telegram_users.id'))
    plan_id:Mapped[str]=mapped_column(ForeignKey('plans.id')); amount:Mapped[int]=mapped_column(Integer); currency:Mapped[str]=mapped_column(String(3)); invoice_payload:Mapped[str]=mapped_column(String(255),unique=True); status:Mapped[str]=mapped_column(String(20),default='pending',index=True)
class Payment(Base,TimestampMixin):
    __tablename__='payments'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); order_id:Mapped[str]=mapped_column(ForeignKey('orders.id'),unique=True)
    provider_payment_id:Mapped[str]=mapped_column(String(255),unique=True,index=True); amount:Mapped[int]=mapped_column(Integer); currency:Mapped[str]=mapped_column(String(3)); status:Mapped[str]=mapped_column(String(20),default='paid')
class License(Base,TimestampMixin):
    __tablename__='licenses'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); key_digest:Mapped[str]=mapped_column(String(64),unique=True,index=True); key_last4:Mapped[str]=mapped_column(String(4))
    purchaser_telegram_id:Mapped[int]=mapped_column(BigInteger,index=True); plan_id:Mapped[str]=mapped_column(ForeignKey('plans.id')); order_id:Mapped[str]=mapped_column(ForeignKey('orders.id'),unique=True)
    status:Mapped[str]=mapped_column(String(20),default='pending',index=True); status_reason:Mapped[str|None]=mapped_column(Text,nullable=True); status_changed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); status_changed_by:Mapped[int|None]=mapped_column(BigInteger,nullable=True); key_delivery_ciphertext:Mapped[str|None]=mapped_column(Text); activated_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); expires_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); max_devices:Mapped[int]=mapped_column(Integer); activation_count:Mapped[int]=mapped_column(Integer,default=0)
class LicenseDevice(Base,TimestampMixin):
    __tablename__='license_devices'; __table_args__=(UniqueConstraint('license_id','device_hash'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); license_id:Mapped[str]=mapped_column(ForeignKey('licenses.id',ondelete='CASCADE'),index=True); device_hash:Mapped[str]=mapped_column(String(64),index=True); app_version:Mapped[str]=mapped_column(String(32)); platform:Mapped[str]=mapped_column(String(32)); active:Mapped[bool]=mapped_column(Boolean,default=True); last_seen_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class ActivationAttempt(Base):
    __tablename__='activation_attempts'; identifier_hash:Mapped[str]=mapped_column(String(64),primary_key=True); attempt_count:Mapped[int]=mapped_column(Integer,default=0); window_started_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow); blocked_until:Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); last_attempt_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class ActivationAudit(Base):
    __tablename__='activation_audit'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); identifier_hash:Mapped[str]=mapped_column(String(64),index=True); license_id:Mapped[str|None]=mapped_column(String(36),index=True); action:Mapped[str]=mapped_column(String(30)); success:Mapped[bool]=mapped_column(Boolean); reason:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
class VirtualBalanceLedger(Base):
    __tablename__='virtual_balance_ledger'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); license_id:Mapped[str]=mapped_column(ForeignKey('licenses.id'),index=True); result_id:Mapped[str]=mapped_column(String(64),unique=True,index=True); amount:Mapped[float]=mapped_column(Numeric(18,8)); currency:Mapped[str]=mapped_column(String(10),default='VIRTUAL'); event_type:Mapped[str]=mapped_column(String(30)); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class AdminAction(Base):
    __tablename__='admin_actions'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); admin_telegram_id:Mapped[int]=mapped_column(BigInteger,index=True); action:Mapped[str]=mapped_column(String(50)); target_id:Mapped[str|None]=mapped_column(String(64)); details:Mapped[str]=mapped_column(Text,default='{}'); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
