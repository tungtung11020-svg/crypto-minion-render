import asyncio,json
from sqlalchemy import select
from database.models import Plan
from database.session import SessionLocal
PLANS=[('30_days','30 дней',99,30),('90_days','90 дней',249,90),('365_days','365 дней',699,365),('lifetime','Бессрочная лицензия',1499,None)]
async def main():
 async with SessionLocal() as s:
  for code,name,price,days in PLANS:
   if not (await s.execute(select(Plan).where(Plan.code==code))).scalar_one_or_none(): s.add(Plan(code=code,name=name,description='Доступ к программе «Крипто Миньон»',price=price,currency='XTR',duration_days=days,starts_on='payment',max_devices=1,features=json.dumps(['scanner_simulation','virtual_balance','personal_account'])))
  await s.commit()
if __name__=='__main__': asyncio.run(main())
