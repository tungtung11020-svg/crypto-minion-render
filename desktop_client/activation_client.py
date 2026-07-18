import httpx
class ActivationClient:
    def __init__(self,base_url,timeout=10): self.base_url=base_url.rstrip('/'); self.timeout=timeout
    async def activate(self,key,device_id,version='1.0.0'):
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r=await c.post(self.base_url+'/v1/licenses/activate',json={'license_key':key,'device_id':device_id,'app_version':version,'platform':'windows'})
            if r.is_error:
                try: raise ValueError(r.json()['detail']['message'])
                except (KeyError,TypeError): raise ValueError('Сервер временно недоступен')
            return r.json()
