from pathlib import Path
import sqlite3
from database.backup import backup_database
def test_sqlite_backup(tmp_path,monkeypatch):
 src=tmp_path/'a.db'; con=sqlite3.connect(src); con.execute('create table x(v int)'); con.execute('insert into x values(1)'); con.commit(); con.close()
 monkeypatch.setattr('database.backup._path',lambda:src); dst=backup_database(tmp_path/'b.db'); con=sqlite3.connect(dst); assert con.execute('select v from x').fetchone()[0]==1; con.close()
