import asyncio, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from core.config import get_settings
def _path()->Path:
    url=get_settings().database_url; return Path(url.split('///',1)[1])
def backup_database(dest:Path|None=None)->Path:
    src=_path(); folder=Path('data/backups'); folder.mkdir(parents=True,exist_ok=True)
    dest=dest or folder/f"licensing_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.db"
    with sqlite3.connect(src) as s, sqlite3.connect(dest) as d: s.backup(d)
    backups=sorted(folder.glob('licensing_*.db'),reverse=True)
    for old in backups[7:]: old.unlink(missing_ok=True)
    return dest
async def backup_database_async()->Path: return await asyncio.to_thread(backup_database)
def restore_database(backup:Path,confirmation:str)->None:
    if confirmation!='ВОССТАНОВИТЬ': raise ValueError('Требуется подтверждение ВОССТАНОВИТЬ')
    backup_database(); src=_path()
    with sqlite3.connect(backup) as s, sqlite3.connect(src) as d: s.backup(d)
