class RenderError(RuntimeError):
    user_message = "SP Video Studio could not render this video."

class RenderFFmpegMissing(RenderError): pass
class RenderValidationError(RenderError): pass
class RenderMissingAsset(RenderValidationError): pass
class RenderEncoderUnavailable(RenderValidationError): pass
class RenderInsufficientDisk(RenderValidationError): pass
class RenderProcessError(RenderError): pass
class RenderCancelled(RenderError): pass
class RenderOutputInvalid(RenderError): pass
class RenderFontError(RenderValidationError): pass
