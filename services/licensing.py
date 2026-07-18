import json
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from core.config import get_settings
from core.license_keys import generate_license_key,license_key_digest
from core.security import encrypt_delivery_secret
from database.models import License,Order,Payment,Plan,TelegramUser,utcnow

class PaymentError(ValueError): pass
async def create_order(session,tg_id:int,username:str|None,full_name:str|None,plan_id:str)->Order:
    user=(await session.execute(select(TelegramUser).where(TelegramUser.telegram_id==tg_id))).scalar_one_or_none()
    if not user: user=TelegramUser(telegram_id=tg_id,username=username,full_name=full_name); session.add(user); await session.flush()
    plan=await session.get(Plan,plan_id)
    if not plan or not plan.is_active: raise PaymentError('Тариф недоступен')
    order=Order(user_id=user.id,plan_id=plan.id,amount=plan.price,currency=plan.currency,invoice_payload=f'km:{__import__("uuid").uuid4()}')
    session.add(order); await session.commit(); return order
async def process_successful_payment(session,*,order_id:str,tg_id:int,amount:int,currency:str,payload:str,payment_id:str)->tuple[License,str,bool]:
    existing=(await session.execute(select(Payment).where(Payment.provider_payment_id==payment_id))).scalar_one_or_none()
    if existing:
        lic=(await session.execute(select(License).where(License.order_id==existing.order_id))).scalar_one(); return lic,'',True
    order=await session.get(Order,order_id)
    if not order or order.invoice_payload!=payload: raise PaymentError('Некорректный заказ')
    user=await session.get(TelegramUser,order.user_id); plan=await session.get(Plan,order.plan_id)
    if user.telegram_id!=tg_id or order.amount!=amount or order.currency!=currency or order.status!='pending': raise PaymentError('Параметры платежа не совпадают')
    for _ in range(5):
        key=generate_license_key(); digest=license_key_digest(key,get_settings().server_pepper.encode())
        found=(await session.execute(select(License.id).where(License.key_digest==digest))).first()
        if not found: break
    else: raise RuntimeError('Не удалось создать уникальный ключ')
    now=utcnow(); expires=now+timedelta(days=plan.duration_days) if plan.duration_days and plan.starts_on=='payment' else None
    status='active' if plan.starts_on=='payment' else 'pending'
    payment=Payment(order_id=order.id,provider_payment_id=payment_id,amount=amount,currency=currency,status='paid')
    lic=License(key_digest=digest,key_last4=key[-4:],key_delivery_ciphertext=encrypt_delivery_secret(key,get_settings().server_pepper),purchaser_telegram_id=tg_id,plan_id=plan.id,order_id=order.id,status=status,expires_at=expires,max_devices=plan.max_devices)
    order.status='paid'; session.add_all([payment,lic]); await session.commit(); return lic,key,False
