from __future__ import annotations
from domain.recovery_errors import ProjectIntegrityError

class ProjectIntegrityService:
    def __init__(self,database,logger=None):self.database=database;self.logger=logger
    def lightweight_check(self)->dict:
        with self.database.connect() as c:
            quick=str(c.execute('PRAGMA quick_check(1)').fetchone()[0]);fk=c.execute('PRAGMA foreign_key_check').fetchmany(20)
        result={'quickCheck':quick,'foreignKeyIssues':len(fk),'ok':quick=='ok' and not fk}
        if not result['ok'] and self.logger:self.logger.error('Startup integrity check failed: %s',result)
        return result
    def require_ok(self):
        r=self.lightweight_check()
        if not r['ok']:raise ProjectIntegrityError('Project data needs repair before recovery can continue.')
        return r
