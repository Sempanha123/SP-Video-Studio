class DirectorError(RuntimeError):
    user_message = "SP Video Studio could not create this production plan."

class DirectorInvalidRequest(DirectorError): pass
class DirectorUnsupportedWorkflow(DirectorError): pass
class DirectorUnsupportedPlatform(DirectorError): pass
class DirectorInvalidDuration(DirectorError): pass
class DirectorSourceMissing(DirectorError): pass
class DirectorPlanValidationError(DirectorError): pass
class DirectorApplyConflict(DirectorError): pass
