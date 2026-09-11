from __future__ import annotations
import logging, sqlite3
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator
try:
    from domain.project import utc_now_iso
except Exception:
    from datetime import datetime,timezone
    def utc_now_iso(): return datetime.now(timezone.utc).isoformat()
from storage.migrations import MIGRATIONS

class DatabaseMigrationError(RuntimeError): pass

class SQLiteDatabase:
    """Central SQLite manager with tested WAL resilience and transactional migrations."""
    def __init__(self,path:Path,logger:logging.Logger|None=None)->None:self.path=Path(path);self.logger=logger or logging.getLogger('sp_video_studio.database');self.journal_mode='unknown'
    def initialize(self)->None:
        self.path.parent.mkdir(parents=True,exist_ok=True)
        try:
            with self.connect() as c:
                try:
                    row=c.execute('PRAGMA journal_mode=WAL').fetchone();self.journal_mode=str(row[0] if row else 'unknown').lower();c.execute('PRAGMA synchronous=NORMAL');c.execute('PRAGMA wal_autocheckpoint=1000')
                    if self.journal_mode!='wal':self.logger.warning('SQLite WAL unavailable; continuing with journal mode %s',self.journal_mode)
                except sqlite3.Error:
                    self.logger.warning('SQLite WAL could not be enabled; continuing with default journal mode',exc_info=True)
                c.execute('''CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL)''');c.commit()
                applied={int(r['version']) for r in c.execute('SELECT version FROM schema_migrations')}
                for m in sorted(MIGRATIONS,key=lambda x:x.version):
                    if m.version in applied:continue
                    try:
                        c.execute('BEGIN IMMEDIATE');m.apply(c);c.execute('INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)',(m.version,m.name,utc_now_iso()));c.commit();self.logger.info('Applied database migration %03d_%s',m.version,m.name)
                    except Exception as exc:
                        c.rollback();self.logger.exception('Database migration %03d_%s failed',m.version,m.name);raise DatabaseMigrationError(f'Could not apply database migration {m.version}.') from exc
        except DatabaseMigrationError:raise
        except sqlite3.Error as exc:
            self.logger.exception('Database initialization failed at %s',self.path);raise DatabaseMigrationError('Could not initialize the application database.') from exc
    @contextmanager
    def connect(self)->Iterator[sqlite3.Connection]:
        c=sqlite3.connect(self.path,timeout=10.0);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA busy_timeout=5000')
        try:yield c
        finally:c.close()
    def current_version(self)->int:
        if not self.path.exists():return 0
        with self.connect() as c:
            try:r=c.execute('SELECT MAX(version) AS version FROM schema_migrations').fetchone();return int(r['version'] or 0) if r else 0
            except sqlite3.Error:return 0
    def backup_to(self,target:Path)->Path:
        """Consistent SQLite backup API; never raw-copies a live WAL database."""
        target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
        source=sqlite3.connect(self.path,timeout=10.0);dest=sqlite3.connect(target)
        try:source.backup(dest);dest.commit()
        finally:dest.close();source.close()
        return target
