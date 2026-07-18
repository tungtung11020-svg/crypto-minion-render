import json
from decimal import Decimal
import pytest
from sqlalchemy import func,select
from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine
from database.models import Base,Plan,TelegramUser,Order,License,utcnow
from services.licensing import create_order,process_successful_payment,PaymentError
from services.activation import activate,ActivationError
from services.virtual_balance import add_event,get_balance
@pytest.fixture
async def session():
 e=create_async_engine('sqlite+aiosqlite:///:memory:');
 async with e.begin() as c: await c.run_sync(Base.metadata.create_all)
 S=async_sessionmaker(e,expire_on_commit=False)
 async with S() as s: yield s
 await e.dispose()
async def plan(session,devices=1,days=30):
 p=Plan(code='p'+str(devices)+str(days),name='Тест',description='Тест',price=10,currency='XTR',duration_days=days,starts_on='activation',max_devices=devices,features='[]'); session.add(p); await session.commit(); return p
@pytest.mark.asyncio
async def test_payment_idempotency_and_validation(session):
 p=await plan(session); o=await create_order(session,123,None,'User',p.id)
 order_id, payload=o.id, o.invoice_payload
 with pytest.raises(PaymentError): await process_successful_payment(session,order_id=order_id,tg_id=123,amount=11,currency='XTR',payload=payload,payment_id='bad')
 await session.rollback(); lic,key,dup=await process_successful_payment(session,order_id=order_id,tg_id=123,amount=10,currency='XTR',payload=payload,payment_id='pay1'); assert key and not dup
 lic2,key2,dup=await process_successful_payment(session,order_id=order_id,tg_id=123,amount=10,currency='XTR',payload=payload,payment_id='pay1'); assert dup and lic2.id==lic.id and not key2
@pytest.mark.asyncio
async def test_wrong_currency_and_no_license_before_payment(session):
 p=await plan(session); o=await create_order(session,555,None,'User',p.id)
 assert await session.scalar(select(func.count()).select_from(License))==0
 with pytest.raises(PaymentError): await process_successful_payment(session,order_id=o.id,tg_id=555,amount=10,currency='USD',payload=o.invoice_payload,payment_id='wrong-currency')
 await session.rollback(); assert await session.scalar(select(func.count()).select_from(License))==0
@pytest.mark.asyncio
async def test_activation_device_limit_and_ledger(session):
 p=await plan(session); o=await create_order(session,123,None,'User',p.id); lic,key,_=await process_successful_payment(session,order_id=o.id,tg_id=123,amount=10,currency='XTR',payload=o.invoice_payload,payment_id='pay2')
 lic_id=lic.id
 first=await activate(session,key,'a'*32,'1.0','windows','ip1'); second=await activate(session,key,'a'*32,'1.0','windows','ip2'); assert first['license']['license_id']==second['license']['license_id']
 with pytest.raises(ActivationError) as e: await activate(session,key,'b'*32,'1.0','windows','ip3')
 assert e.value.code=='device_limit'; await session.rollback(); await add_event(session,lic_id,'r1',Decimal('2.5')); assert await get_balance(session,lic_id)==Decimal('2.50000000')
 with pytest.raises(ValueError): await add_event(session,lic_id,'r1',Decimal('2.5'))
@pytest.mark.asyncio
@pytest.mark.parametrize('status',['blocked','revoked','refunded'])
async def test_rejected_statuses(session,status):
 p=await plan(session); o=await create_order(session,123,None,'User',p.id); lic,key,_=await process_successful_payment(session,order_id=o.id,tg_id=123,amount=10,currency='XTR',payload=o.invoice_payload,payment_id='pay'+status); lic.status=status; await session.commit()
 with pytest.raises(ActivationError) as e: await activate(session,key,'a'*32,'1','windows','x'+status)
 assert e.value.code==status
@pytest.mark.asyncio
async def test_expired_license(session):
 from datetime import timedelta
 p=await plan(session); o=await create_order(session,777,None,'User',p.id); lic,key,_=await process_successful_payment(session,order_id=o.id,tg_id=777,amount=10,currency='XTR',payload=o.invoice_payload,payment_id='expired-pay')
 lic.status='active'; lic.expires_at=utcnow()-timedelta(seconds=1); await session.commit()
 with pytest.raises(ActivationError) as e: await activate(session,key,'a'*32,'1','windows','expired-ip')
 assert e.value.code=='expired'
@pytest.mark.asyncio
async def test_rate_limiting(session):
 from core.config import get_settings
 cfg=get_settings(); old=cfg.rate_limit_attempts; cfg.rate_limit_attempts=1
 try:
  with pytest.raises(ActivationError):
   await activate(session,'KM-AAAA-AAAA-AAAA-AAAA-AAAA-AAAA-AAAA-AAAA','a'*32,'1','windows','same-ip')
  await session.rollback()
  with pytest.raises(ActivationError) as e: await activate(session,'KM-AAAA-AAAA-AAAA-AAAA-AAAA-AAAA-AAAA-AAAA','a'*32,'1','windows','same-ip')
  assert e.value.code=='rate_limited'
 finally: cfg.rate_limit_attempts=old
