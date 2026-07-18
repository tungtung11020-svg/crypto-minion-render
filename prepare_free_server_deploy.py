from pathlib import Path
from datetime import datetime
import py_compile
import re
import shutil

root = Path.cwd()
required = [root / "start.py", root / "requirements.txt", root / "database" / "session.py", root / "api" / "main.py"]
for path in required:
    if not path.exists():
        raise SystemExit(f"Не найден {path}. Запустите updater из корня проекта «тг бот».")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = root / f"server_deploy_backup_{stamp}"
for path in required:
    dst = backup / path.relative_to(root)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)

# PostgreSQL driver for Neon.
requirements_path = root / "requirements.txt"
requirements = requirements_path.read_text(encoding="utf-8")
if not re.search(r"(?mi)^asyncpg\b", requirements):
    requirements = requirements.rstrip() + "\nasyncpg>=0.30,<1\n"
requirements_path.write_text(requirements, encoding="utf-8")

# SQLite locally, PostgreSQL on Render/Neon.
session_code = '''from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.config import get_settings

settings = get_settings()
database_url = settings.database_url.strip()
if database_url.startswith("postgresql://"):
    database_url = "postgresql+asyncpg://" + database_url[len("postgresql://"):]
if database_url.startswith("postgres://"):
    database_url = "postgresql+asyncpg://" + database_url[len("postgres://"):]
database_url = database_url.replace("sslmode=require", "ssl=require")

engine = create_async_engine(database_url, pool_pre_ping=True)

if database_url.startswith("sqlite"):
    @event.listens_for(engine.sync_engine, "connect")
    def sqlite_pragmas(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with SessionLocal() as session:
        yield session
'''
(root / "database" / "session.py").write_text(session_code, encoding="utf-8")

# Render exposes the port through PORT and requires 0.0.0.0.
start_path = root / "start.py"
start = start_path.read_text(encoding="utf-8")
if "import os" not in start:
    start = "import os\n" + start
start = start.replace(
    "server=uvicorn.Server(uvicorn.Config('api.main:app',host=cfg.api_host,port=cfg.api_port,log_level='info'))",
    "host=os.getenv('API_HOST','0.0.0.0' if os.getenv('PORT') else cfg.api_host); port=int(os.getenv('PORT',str(cfg.api_port))); server=uvicorn.Server(uvicorn.Config('api.main:app',host=host,port=port,log_level='info'))",
)
start = start.replace(
    'server = uvicorn.Server(uvicorn.Config("api.main:app", host=cfg.api_host, port=cfg.api_port, log_level="info"))',
    'host = os.getenv("API_HOST", "0.0.0.0" if os.getenv("PORT") else cfg.api_host)\n    port = int(os.getenv("PORT", str(cfg.api_port)))\n    server = uvicorn.Server(uvicorn.Config("api.main:app", host=host, port=port, log_level="info"))',
)
if "os.getenv('PORT'" not in start and 'os.getenv("PORT"' not in start:
    raise SystemExit("Не удалось найти создание Uvicorn в start.py. Backup уже создан.")
start_path.write_text(start, encoding="utf-8")

# Automatically create schema in a fresh Neon database.
api_path = root / "api" / "main.py"
api = api_path.read_text(encoding="utf-8")
api = api.replace("from database.session import get_session", "from database.session import get_session, engine")
if "from database.models import Base" not in api:
    insert_at = api.find("app=FastAPI(")
    if insert_at < 0:
        insert_at = api.find("app = FastAPI(")
    if insert_at < 0:
        raise SystemExit("Не найден объект FastAPI в api/main.py")
    api = api[:insert_at] + "from database.models import Base\n" + api[insert_at:]
if "async def create_database_schema" not in api:
    marker = "@app.get('/v1/health')"
    if marker not in api:
        marker = '@app.get("/v1/health")'
    if marker not in api:
        raise SystemExit("Не найден /v1/health в api/main.py")
    startup = "@app.on_event('startup')\nasync def create_database_schema():\n    async with engine.begin() as connection:\n        await connection.run_sync(Base.metadata.create_all)\n\n"
    api = api.replace(marker, startup + marker, 1)
api_path.write_text(api, encoding="utf-8")

render_yaml = '''services:
  - type: web
    name: crypto-minion-licensing
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python start.py
    healthCheckPath: /v1/health
    autoDeploy: true
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.8
      - key: API_HOST
        value: 0.0.0.0
      - key: BOT_TOKEN
        sync: false
      - key: BOT_USERNAME
        sync: false
      - key: ADMIN_IDS
        sync: false
      - key: DATABASE_URL
        sync: false
      - key: SERVER_PEPPER
        sync: false
      - key: ED25519_PRIVATE_KEY
        sync: false
      - key: ED25519_PUBLIC_KEY
        sync: false
      - key: PAYMENT_MODE
        value: test
      - key: PAYMENT_PROVIDER_TOKEN
        sync: false
      - key: APP_DOWNLOAD_URL
        sync: false
      - key: SUPPORT_URL
        sync: false
      - key: API_PUBLIC_URL
        sync: false
      - key: OFFLINE_GRACE_HOURS
        value: 72
      - key: RATE_LIMIT_ATTEMPTS
        value: 8
'''
(root / "render.yaml").write_text(render_yaml, encoding="utf-8")

runtime = "python-3.12.8\n"
(root / "runtime.txt").write_text(runtime, encoding="utf-8")

# Never publish local secrets or SQLite files.
gitignore_path = root / ".gitignore"
gitignore = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
for line in [".env", "data/*.db", "data/*.db-*", "data/backups/", "*_backup_*/", "server_deploy_backup_*/"]:
    if line not in gitignore.splitlines():
        gitignore = gitignore.rstrip() + "\n" + line + "\n"
gitignore_path.write_text(gitignore, encoding="utf-8")

migration_code = r'''import argparse
import asyncio
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Boolean, DateTime, Numeric
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import create_async_engine

from database.models import Base


def normalize_url(value: str) -> str:
    value = value.strip()
    if value.startswith("postgresql://"):
        value = "postgresql+asyncpg://" + value[len("postgresql://"):]
    elif value.startswith("postgres://"):
        value = "postgresql+asyncpg://" + value[len("postgres://"):]
    return value.replace("sslmode=require", "ssl=require")


def convert(column, value):
    if value is None:
        return None
    if isinstance(column.type, Boolean):
        return bool(value)
    if isinstance(column.type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(column.type, Numeric):
        return Decimal(str(value))
    return value


async def migrate(sqlite_path: Path, database_url: str):
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite не найден: {sqlite_path}")
    source = sqlite3.connect(sqlite_path)
    source.row_factory = sqlite3.Row
    engine = create_async_engine(normalize_url(database_url), pool_pre_ping=True)
    try:
        async with engine.begin() as target:
            await target.run_sync(Base.metadata.create_all)
            for table in Base.metadata.sorted_tables:
                exists = source.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table.name,)
                ).fetchone()
                if not exists:
                    continue
                source_columns = {row[1] for row in source.execute(f'PRAGMA table_info("{table.name}")')}
                common = [column for column in table.columns if column.name in source_columns]
                rows = source.execute(f'SELECT * FROM "{table.name}"').fetchall()
                copied = 0
                for row in rows:
                    values = {column.name: convert(column, row[column.name]) for column in common}
                    await target.execute(pg_insert(table).values(**values).on_conflict_do_nothing())
                    copied += 1
                print(f"{table.name}: {copied}")
    finally:
        source.close()
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default="data/licensing.db")
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    asyncio.run(migrate(Path(args.sqlite), args.database_url))


if __name__ == "__main__":
    main()
'''
scripts = root / "scripts"
scripts.mkdir(exist_ok=True)
(scripts / "migrate_sqlite_to_postgres.py").write_text(migration_code, encoding="utf-8")

readme = '''# Бесплатный сервер: Render + Neon

1. Создайте бесплатную PostgreSQL-базу в Neon и скопируйте connection string.
2. Не добавляйте `.env` и `data/licensing.db` в GitHub.
3. Загрузите проект в приватный GitHub-репозиторий.
4. В Render выберите New → Blueprint и подключите репозиторий.
5. Заполните секретные переменные из локального `.env`; для DATABASE_URL используйте строку Neon.
6. После первого deploy установите API_PUBLIC_URL равным HTTPS-адресу Render.
7. Проверьте `/v1/health`.
8. В UptimeRobot добавьте HTTPS monitor на `/v1/health` с интервалом 5 минут.

Локальная SQLite продолжает работать. На сервере используется Neon PostgreSQL.
Никогда не публикуйте BOT_TOKEN, SERVER_PEPPER, приватный Ed25519-ключ или `.env`.
'''
(root / "SERVER_DEPLOY_FREE.md").write_text(readme, encoding="utf-8")

for path in [start_path, root / "database" / "session.py", api_path, scripts / "migrate_sqlite_to_postgres.py"]:
    py_compile.compile(str(path), doraise=True)

print("Готово: проект подготовлен для Render + Neon.")
print("Backup:", backup)
print("Дальше: загрузите проект в приватный GitHub-репозиторий.")
