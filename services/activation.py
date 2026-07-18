import json,time
from datetime import timedelta
from sqlalchemy import delete,func,select
from core.config import get_settings
from core.license_keys import license_key_digest,normalize_license_key,validate_license_key_format
from core.security import sha256_text,sign_activation_token,verify_activation_token
from database.models import ActivationAttempt,ActivationAudit,License,LicenseDevice,Plan,utcnow
class ActivationError(ValueError):
    def __init__(self,code,message): self.code=code; super().__init__(message)
PUBLIC_BAD='Ключ не найден или введён неправильно'
def aware(v):
    if v and v.tzinfo is None: return v.replace(tzinfo=__import__('datetime').timezone.utc)
    return v
async def rate_limit(session,identifier:str):
    cfg=get_settings(); now=utcnow(); h=sha256_text(identifier); row=await session.get(ActivationAttempt,h)
    if not row: row=ActivationAttempt(identifier_hash=h,attempt_count=1,window_started_at=now,last_attempt_at=now); session.add(row); await session.flush(); return h
    row.blocked_until=aware(row.blocked_until); row.window_started_at=aware(row.window_started_at)
    if row.blocked_until and row.blocked_until>now:
        await session.commit()
        raise ActivationError('rate_limited','Слишком много попыток. Повторите позже')
    if (now-row.window_started_at).total_seconds()>cfg.rate_limit_window_seconds: row.attempt_count=1; row.window_started_at=now
    else: row.attempt_count+=1
    row.last_attempt_at=now
    if row.attempt_count>cfg.rate_limit_attempts:
        row.blocked_until=now+timedelta(seconds=cfg.rate_limit_block_seconds)
        await session.commit()
        raise ActivationError('rate_limited','Слишком много попыток. Повторите позже')
    return h
async def activate(session,key:str,device_id:str,app_version:str,platform:str,identifier:str)->dict:
    ident=await rate_limit(session,identifier); norm=normalize_license_key(key)
    if not validate_license_key_format(norm):
        await audit(session,ident,None,'activate',False,'bad_key'); await session.commit()
        raise ActivationError('invalid_key',PUBLIC_BAD)
    digest=license_key_digest(norm,get_settings().server_pepper.encode()); lic=(await session.execute(select(License).where(License.key_digest==digest))).scalar_one_or_none()
    if not lic:
        await audit(session,ident,None,'activate',False,'bad_key'); await session.commit()
        raise ActivationError('invalid_key',PUBLIC_BAD)
    now=utcnow(); lic.expires_at=aware(lic.expires_at); plan=await session.get(Plan,lic.plan_id)
    if lic.status in {'blocked','revoked','refunded'}:
        await audit(session,ident,lic.id,'activate',False,lic.status); await session.commit()
        raise ActivationError(lic.status,{'blocked':'Лицензия заблокирована','revoked':'Лицензия отозвана','refunded':'Лицензия возвращена'}[lic.status])
    if lic.expires_at and lic.expires_at<=now:
        lic.status='expired'; await audit(session,ident,lic.id,'activate',False,'expired'); await session.commit()
        raise ActivationError('expired','Лицензия просрочена')
    dh=sha256_text(device_id); device=(await session.execute(select(LicenseDevice).where(LicenseDevice.license_id==lic.id,LicenseDevice.device_hash==dh))).scalar_one_or_none()
    active_count=(await session.execute(select(func.count()).select_from(LicenseDevice).where(LicenseDevice.license_id==lic.id,LicenseDevice.active==True))).scalar_one()
    if not device and active_count>=lic.max_devices:
        await audit(session,ident,lic.id,'activate',False,'device_limit'); await session.commit()
        raise ActivationError('device_limit','Превышен лимит устройств')
    if not device: device=LicenseDevice(license_id=lic.id,device_hash=dh,app_version=app_version,platform=platform); session.add(device); lic.activation_count+=1
    else: device.active=True; device.last_seen_at=now; device.app_version=app_version
    if not lic.activated_at: lic.activated_at=now
    if not lic.expires_at and plan.duration_days:
        base_date=aware(lic.created_at) if plan.starts_on=='payment' else now
        lic.expires_at=base_date+timedelta(days=plan.duration_days)
    lic.status='active'; exp=int(lic.expires_at.timestamp()) if lic.expires_at else None
    payload={'license_id':lic.id,'plan':plan.code,'device_hash':dh,'issued_at':int(time.time()),'expires_at':exp,'offline_until':int((now+timedelta(hours=get_settings().offline_grace_hours)).timestamp()),'features':json.loads(plan.features)}
    token=sign_activation_token(payload,get_settings().ed25519_private_key); await audit(session,ident,lic.id,'activate',True,'ok'); await session.commit()
    return {'ok':True,'activation_token':token,'license':payload,'masked_key':'KM-••••-••••-••••-••••-••••-••••-••••-'+lic.key_last4}


async def validate(session,key:str,device_id:str,app_version:str,platform:str,identifier:str)->dict:
    """Online session check. Never creates or silently re-enables a device."""
    ident=await rate_limit(session,identifier); norm=normalize_license_key(key)
    if not validate_license_key_format(norm):
        await audit(session,ident,None,'validate',False,'bad_key'); await session.commit()
        raise ActivationError('invalid_key',PUBLIC_BAD)
    digest=license_key_digest(norm,get_settings().server_pepper.encode())
    lic=(await session.execute(select(License).where(License.key_digest==digest))).scalar_one_or_none()
    if not lic:
        await audit(session,ident,None,'validate',False,'bad_key'); await session.commit()
        raise ActivationError('invalid_key',PUBLIC_BAD)
    now=utcnow(); lic.expires_at=aware(lic.expires_at)
    if lic.status in {'blocked','revoked','refunded'}:
        await audit(session,ident,lic.id,'validate',False,lic.status); await session.commit()
        raise ActivationError(lic.status,{'blocked':'Лицензия заблокирована','revoked':'Лицензия отозвана','refunded':'По лицензии выполнен возврат'}[lic.status])
    if lic.expires_at and lic.expires_at<=now:
        lic.status='expired'; await audit(session,ident,lic.id,'validate',False,'expired'); await session.commit()
        raise ActivationError('expired','Срок действия лицензии истёк')
    dh=sha256_text(device_id)
    device=(await session.execute(select(LicenseDevice).where(LicenseDevice.license_id==lic.id,LicenseDevice.device_hash==dh))).scalar_one_or_none()
    if not device or not device.active:
        await audit(session,ident,lic.id,'validate',False,'device_reset'); await session.commit()
        raise ActivationError('device_reset','Привязка устройства сброшена. Выполните активацию заново')
    plan=await session.get(Plan,lic.plan_id)
    device.last_seen_at=now; device.app_version=app_version; device.platform=platform
    exp=int(lic.expires_at.timestamp()) if lic.expires_at else None
    payload={'license_id':lic.id,'plan':plan.code,'device_hash':dh,'issued_at':int(time.time()),'expires_at':exp,'offline_until':int((now+timedelta(hours=get_settings().offline_grace_hours)).timestamp()),'features':json.loads(plan.features)}
    token=sign_activation_token(payload,get_settings().ed25519_private_key)
    await audit(session,ident,lic.id,'validate',True,'ok'); await session.commit()
    return {'ok':True,'activation_token':token,'license':payload,'masked_key':'KM-••••-••••-••••-••••-••••-••••-••••-'+lic.key_last4}



async def validate_token(session,token:str,device_id:str,app_version:str,platform:str,identifier:str)->dict:
    ident=await rate_limit(session,identifier); dh=sha256_text(device_id)
    try: payload=verify_activation_token(token,get_settings().ed25519_public_key,device_hash=dh)
    except ValueError:
        await audit(session,ident,None,'validate',False,'invalid_token'); await session.commit(); raise ActivationError('INVALID_TOKEN','Недействительный токен активации')
    lic=await session.get(License,payload.get('license_id')); now=utcnow()
    if not lic: raise ActivationError('INVALID_TOKEN','Лицензия не найдена')
    lic.expires_at=aware(lic.expires_at)
    code={'blocked':'LICENSE_BLOCKED','revoked':'LICENSE_REVOKED','refunded':'REFUNDED'}.get(lic.status)
    if code:
        await audit(session,ident,lic.id,'validate',False,code); await session.commit(); message={'LICENSE_BLOCKED':'Лицензионный ключ заблокирован','LICENSE_REVOKED':'Лицензия отозвана','REFUNDED':'По лицензии выполнен возврат'}.get(code,'Доступ к лицензии прекращён'); message += (f'. Причина: {lic.status_reason}' if getattr(lic,'status_reason',None) else ''); raise ActivationError(code,message)
    if lic.status=='expired' or (lic.expires_at and lic.expires_at<=now):
        lic.status='expired'; await audit(session,ident,lic.id,'validate',False,'LICENSE_EXPIRED'); await session.commit(); raise ActivationError('LICENSE_EXPIRED','Срок лицензии истёк')
    dev=(await session.execute(select(LicenseDevice).where(LicenseDevice.license_id==lic.id,LicenseDevice.device_hash==dh))).scalar_one_or_none()
    if not dev or not dev.active:
        await audit(session,ident,lic.id,'validate',False,'DEVICE_RESET'); await session.commit(); raise ActivationError('DEVICE_RESET','Привязка устройства сброшена')
    dev.last_seen_at=now; dev.app_version=app_version; dev.platform=platform; await audit(session,ident,lic.id,'validate',True,'LICENSE_VALID'); await session.commit()
    return {'ok':True,'code':'LICENSE_VALID','license_id':lic.id,'expires_at':int(lic.expires_at.timestamp()) if lic.expires_at else None}

async def audit(session,ident,license_id,action,success,reason): session.add(ActivationAudit(identifier_hash=ident,license_id=license_id,action=action,success=success,reason=reason)); await session.flush()
async def deactivate(session,key,device_id,identifier):
    ident=await rate_limit(session,identifier); norm=normalize_license_key(key)
    if not validate_license_key_format(norm): raise ActivationError('invalid_key',PUBLIC_BAD)
    digest=license_key_digest(norm,get_settings().server_pepper.encode()); lic=(await session.execute(select(License).where(License.key_digest==digest))).scalar_one_or_none()
    if not lic: raise ActivationError('invalid_key',PUBLIC_BAD)
    dh=sha256_text(device_id); dev=(await session.execute(select(LicenseDevice).where(LicenseDevice.license_id==lic.id,LicenseDevice.device_hash==dh))).scalar_one_or_none()
    if dev: dev.active=False
    await audit(session,ident,lic.id,'deactivate',True,'ok'); await session.commit(); return {'ok':True}
async def cleanup_attempts(session):
    cutoff=utcnow()-timedelta(days=2); await session.execute(delete(ActivationAttempt).where(ActivationAttempt.last_attempt_at<cutoff)); await session.commit()
