import os
import asyncio,uvicorn
from database.backup import backup_database_async
from bot.main import run_bot
from core.config import get_settings
from core.logging import configure_logging
async def main():
    cfg=get_settings(); cfg.validate_secrets(); configure_logging()
    host=os.getenv('API_HOST','0.0.0.0' if os.getenv('PORT') else cfg.api_host); port=int(os.getenv('PORT',str(cfg.api_port))); server=uvicorn.Server(uvicorn.Config('api.main:app',host=host,port=port,log_level='info'))
    async def maintenance():
        while True:
            await backup_database_async()
            await asyncio.sleep(24*60*60)
    tasks = [server.serve(), run_bot()]
    if cfg.database_url.strip().lower().startswith('sqlite'):
        tasks.append(maintenance())
    await asyncio.gather(*tasks)
if __name__=='__main__': asyncio.run(main())
