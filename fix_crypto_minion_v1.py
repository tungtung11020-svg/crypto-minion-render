from pathlib import Path

root = Path.cwd()
activation = root / "services" / "activation.py"
tests = root / "tests" / "test_integration.py"

if not activation.exists() or not tests.exists():
    raise SystemExit("Ошибка: запустите этот файл из корня проекта, где находятся services и tests.")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"Уже исправлено: {label}")
        return text
    if old not in text:
        raise SystemExit(f"Не найден ожидаемый фрагмент: {label}. Файл отличается от исходной версии.")
    print(f"Исправлено: {label}")
    return text.replace(old, new, 1)

text = activation.read_text(encoding="utf-8")
text = replace_once(
    text,
    "    if row.blocked_until and row.blocked_until>now: raise ActivationError('rate_limited','Слишком много попыток. Повторите позже')",
    "    if row.blocked_until and row.blocked_until>now:\n        await session.commit()\n        raise ActivationError('rate_limited','Слишком много попыток. Повторите позже')",
    "сохранение существующей блокировки rate limit",
)
text = replace_once(
    text,
    "    if row.attempt_count>cfg.rate_limit_attempts: row.blocked_until=now+timedelta(seconds=cfg.rate_limit_block_seconds); raise ActivationError('rate_limited','Слишком много попыток. Повторите позже')",
    "    if row.attempt_count>cfg.rate_limit_attempts:\n        row.blocked_until=now+timedelta(seconds=cfg.rate_limit_block_seconds)\n        await session.commit()\n        raise ActivationError('rate_limited','Слишком много попыток. Повторите позже')",
    "сохранение новой блокировки rate limit",
)
text = replace_once(
    text,
    "    if not validate_license_key_format(norm): await audit(session,ident,None,'activate',False,'bad_key'); raise ActivationError('invalid_key',PUBLIC_BAD)",
    "    if not validate_license_key_format(norm):\n        await audit(session,ident,None,'activate',False,'bad_key'); await session.commit()\n        raise ActivationError('invalid_key',PUBLIC_BAD)",
    "аудит неправильного формата ключа",
)
text = replace_once(
    text,
    "    if not lic: await audit(session,ident,None,'activate',False,'bad_key'); raise ActivationError('invalid_key',PUBLIC_BAD)",
    "    if not lic:\n        await audit(session,ident,None,'activate',False,'bad_key'); await session.commit()\n        raise ActivationError('invalid_key',PUBLIC_BAD)",
    "аудит неизвестного ключа",
)
text = replace_once(
    text,
    "    if lic.status in {'blocked','revoked','refunded'}: await audit(session,ident,lic.id,'activate',False,lic.status); raise ActivationError(lic.status,{'blocked':'Лицензия заблокирована','revoked':'Лицензия отозвана','refunded':'Лицензия возвращена'}[lic.status])",
    "    if lic.status in {'blocked','revoked','refunded'}:\n        await audit(session,ident,lic.id,'activate',False,lic.status); await session.commit()\n        raise ActivationError(lic.status,{'blocked':'Лицензия заблокирована','revoked':'Лицензия отозвана','refunded':'Лицензия возвращена'}[lic.status])",
    "аудит запрещённых статусов",
)
text = replace_once(
    text,
    "    if lic.expires_at and lic.expires_at<=now: lic.status='expired'; await audit(session,ident,lic.id,'activate',False,'expired'); raise ActivationError('expired','Лицензия просрочена')",
    "    if lic.expires_at and lic.expires_at<=now:\n        lic.status='expired'; await audit(session,ident,lic.id,'activate',False,'expired'); await session.commit()\n        raise ActivationError('expired','Лицензия просрочена')",
    "сохранение просроченного статуса",
)
text = replace_once(
    text,
    "    if not device and active_count>=lic.max_devices: await audit(session,ident,lic.id,'activate',False,'device_limit'); raise ActivationError('device_limit','Превышен лимит устройств')",
    "    if not device and active_count>=lic.max_devices:\n        await audit(session,ident,lic.id,'activate',False,'device_limit'); await session.commit()\n        raise ActivationError('device_limit','Превышен лимит устройств')",
    "аудит превышения устройств",
)
activation.write_text(text, encoding="utf-8")

text = tests.read_text(encoding="utf-8")
text = replace_once(
    text,
    " p=await plan(session); o=await create_order(session,123,None,'User',p.id)\n with pytest.raises(PaymentError): await process_successful_payment(session,order_id=o.id,tg_id=123,amount=11,currency='XTR',payload=o.invoice_payload,payment_id='bad')\n await session.rollback(); lic,key,dup=await process_successful_payment(session,order_id=o.id,tg_id=123,amount=10,currency='XTR',payload=o.invoice_payload,payment_id='pay1'); assert key and not dup\n lic2,key2,dup=await process_successful_payment(session,order_id=o.id,tg_id=123,amount=10,currency='XTR',payload=o.invoice_payload,payment_id='pay1'); assert dup and lic2.id==lic.id and not key2",
    " p=await plan(session); o=await create_order(session,123,None,'User',p.id)\n order_id, payload=o.id, o.invoice_payload\n with pytest.raises(PaymentError): await process_successful_payment(session,order_id=order_id,tg_id=123,amount=11,currency='XTR',payload=payload,payment_id='bad')\n await session.rollback(); lic,key,dup=await process_successful_payment(session,order_id=order_id,tg_id=123,amount=10,currency='XTR',payload=payload,payment_id='pay1'); assert key and not dup\n lic2,key2,dup=await process_successful_payment(session,order_id=order_id,tg_id=123,amount=10,currency='XTR',payload=payload,payment_id='pay1'); assert dup and lic2.id==lic.id and not key2",
    "тест идемпотентного платежа",
)
text = replace_once(
    text,
    " p=await plan(session); o=await create_order(session,123,None,'User',p.id); lic,key,_=await process_successful_payment(session,order_id=o.id,tg_id=123,amount=10,currency='XTR',payload=o.invoice_payload,payment_id='pay2')\n first=await activate",
    " p=await plan(session); o=await create_order(session,123,None,'User',p.id); lic,key,_=await process_successful_payment(session,order_id=o.id,tg_id=123,amount=10,currency='XTR',payload=o.invoice_payload,payment_id='pay2')\n lic_id=lic.id\n first=await activate",
    "сохранение license ID до rollback",
)
text = replace_once(
    text,
    " assert e.value.code=='device_limit'; await session.rollback(); await add_event(session,lic.id,'r1',Decimal('2.5')); assert await get_balance(session,lic.id)==Decimal('2.50000000')\n with pytest.raises(ValueError): await add_event(session,lic.id,'r1',Decimal('2.5'))",
    " assert e.value.code=='device_limit'; await session.rollback(); await add_event(session,lic_id,'r1',Decimal('2.5')); assert await get_balance(session,lic_id)==Decimal('2.50000000')\n with pytest.raises(ValueError): await add_event(session,lic_id,'r1',Decimal('2.5'))",
    "тест ledger после rollback",
)
tests.write_text(text, encoding="utf-8")

print("\nИсправление применено. Теперь выполните: python -m pytest -q")
