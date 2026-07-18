from fastapi import Depends,FastAPI,HTTPException,Request,Header
from sqlalchemy.ext.asyncio import AsyncSession
from api.schemas import DeactivateRequest,LicenseRequest,TokenValidateRequest
from database.session import get_session, engine
from services.activation import ActivationError,activate,deactivate,validate_token,validate
from database.models import Base
app=FastAPI(title='Крипто Миньон — API лицензирования',version='1.0.0',docs_url='/docs')
def client_id(request:Request)->str: return request.client.host if request.client else 'unknown'
@app.on_event('startup')
async def create_database_schema():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

@app.get('/v1/health')
async def health(): return {'status':'ok','service':'crypto-minion-licensing'}
async def run_activate(body:LicenseRequest,request:Request,session:AsyncSession):
    try: return await activate(session,body.license_key,body.device_id,body.app_version,body.platform,client_id(request))
    except ActivationError as e: await session.rollback(); raise HTTPException(429 if e.code=='rate_limited' else 400,detail={'code':e.code,'message':str(e),'force_logout':e.code in {'LICENSE_BLOCKED','LICENSE_REVOKED','LICENSE_EXPIRED','DEVICE_RESET','REFUNDED'}})
@app.post('/v1/licenses/activate')
async def activate_route(body:LicenseRequest,request:Request,session:AsyncSession=Depends(get_session)): return await run_activate(body,request,session)
@app.post('/v1/licenses/validate')
async def validate_route(body:TokenValidateRequest,request:Request,authorization:str=Header(...),session:AsyncSession=Depends(get_session)):
    if not authorization.startswith('Bearer '): raise HTTPException(401,detail={'code':'INVALID_TOKEN','message':'Требуется Bearer token'})
    try: return await validate_token(session,authorization[7:].strip(),body.device_id,body.app_version,body.platform,client_id(request))
    except ActivationError as e:
        await session.rollback(); status=403 if e.code in {'LICENSE_BLOCKED','LICENSE_REVOKED','LICENSE_EXPIRED','DEVICE_RESET','REFUNDED'} else 401
        raise HTTPException(status,detail={'code':e.code,'message':str(e),'force_logout':e.code in {'LICENSE_BLOCKED','LICENSE_REVOKED','LICENSE_EXPIRED','DEVICE_RESET','REFUNDED'}})
@app.post('/v1/licenses/deactivate')
async def deactivate_route(body:DeactivateRequest,request:Request,session:AsyncSession=Depends(get_session)):
    try: return await deactivate(session,body.license_key,body.device_id,client_id(request))
    except ActivationError as e: await session.rollback(); raise HTTPException(429 if e.code=='rate_limited' else 400,detail={'code':e.code,'message':str(e),'force_logout':e.code in {'LICENSE_BLOCKED','LICENSE_REVOKED','LICENSE_EXPIRED','DEVICE_RESET','REFUNDED'}})
