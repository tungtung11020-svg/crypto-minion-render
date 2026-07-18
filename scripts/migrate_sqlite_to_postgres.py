import argparse
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
