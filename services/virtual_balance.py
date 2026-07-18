from decimal import Decimal
from sqlalchemy import func,select
from sqlalchemy.exc import IntegrityError
from database.models import License,VirtualBalanceLedger
async def add_event(session,license_id:str,result_id:str,amount:Decimal,event_type='simulation_find'):
    lic=await session.get(License,license_id)
    if not lic or lic.status!='active': raise ValueError('Лицензия не активна')
    row=VirtualBalanceLedger(license_id=license_id,result_id=result_id,amount=amount,currency='VIRTUAL',event_type=event_type); session.add(row)
    try: await session.commit()
    except IntegrityError: await session.rollback(); raise ValueError('Результат уже начислен')
    return row
async def get_balance(session,license_id:str)->Decimal:
    value=(await session.execute(select(func.coalesce(func.sum(VirtualBalanceLedger.amount),0)).where(VirtualBalanceLedger.license_id==license_id))).scalar_one(); return Decimal(value)
