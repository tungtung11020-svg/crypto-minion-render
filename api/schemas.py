from pydantic import BaseModel,Field
class LicenseRequest(BaseModel):
    license_key:str=Field(min_length=3,max_length=80); device_id:str=Field(min_length=32,max_length=256); app_version:str=Field(min_length=1,max_length=32); platform:str=Field(default='windows',max_length=32)
class DeactivateRequest(BaseModel): license_key:str=Field(max_length=80); device_id:str=Field(min_length=32,max_length=256)

class TokenValidateRequest(BaseModel):
    device_id:str=Field(min_length=32,max_length=256)
    app_version:str=Field(min_length=1,max_length=32)
    platform:str=Field(default='windows',max_length=32)
