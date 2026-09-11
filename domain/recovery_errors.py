class Phase27Error(RuntimeError): pass
class AutosaveFailed(Phase27Error): pass
class RecoverySnapshotFailed(Phase27Error): pass
class RecoverySnapshotCorrupt(Phase27Error): pass
class RecoveryRestoreFailed(Phase27Error): pass
class RecoveryVersionUnsupported(Phase27Error): pass
class RecoveryDiskFull(Phase27Error): pass
class ProjectIntegrityError(Phase27Error): pass
