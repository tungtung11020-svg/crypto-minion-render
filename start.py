import os
import asyncio, uvicorn
from database.backup import backup_database_async
from bot.main import run_bot
from core.config import get_settings
from core.logging import configure_logging

async def main():
    cfg = get_settings()
    cfg.validate_secrets()
    configure_logging()

    host = os.getenv('API_HOST', '0.0.0.0' if os.getenv('PORT') else cfg.api_host)
    port = int(os.getenv('PORT', str(cfg.api_port)))

    server = uvicorn.Server(
        uvicorn.Config('api.main:app', host=host, port=port, log_level='info')
    )

    # Maintenance (SQLite-only backup) — skip on PostgreSQL/Neon
    db_url = cfg.database_url.strip().lower()
    maintenance_task = None
    if db_url.startswith('sqlite'):
        async def maintenance():
            while True:
                try:
                    await backup_database_async()
                except Exception:
                    pass
                await asyncio.sleep(24 * 60 * 60)
        maintenance_task = maintenance()

    tasks = [server.serve(), run_bot()]
    if maintenance_task:
        tasks.append(maintenance_task)
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
