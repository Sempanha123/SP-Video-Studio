from __future__ import annotations

class AssetError(RuntimeError): pass
class AssetNotFound(AssetError): pass
class AssetImportFailed(AssetError): pass
class AssetDuplicate(AssetError): pass
class AssetMissing(AssetError): pass
class AssetPathUnsafe(AssetError): pass
class AssetInUse(AssetError): pass
class AssetRelinkMismatch(AssetError): pass
class AssetStorageError(AssetError): pass
class AssetUnsupportedFormat(AssetError): pass
