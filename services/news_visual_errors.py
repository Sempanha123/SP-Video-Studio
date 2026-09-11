class NewsVisualError(RuntimeError): pass
class NewsVisualPresetNotFound(NewsVisualError): pass
class NewsVisualInvalidLayout(NewsVisualError): pass
class NewsVisualSourceMissing(NewsVisualError): pass
class NewsVisualClaimInvalid(NewsVisualError): pass
class NewsVisualFontError(NewsVisualError): pass
class NewsVisualOverflow(NewsVisualError): pass
class NewsVisualRenderUnsupported(NewsVisualError): pass
