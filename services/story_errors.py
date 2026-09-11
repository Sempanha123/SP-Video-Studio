class StoryError(RuntimeError):
    user_message="SP Video Studio could not complete this Story action."
class StoryInvalidSetup(StoryError): pass
class StoryOutlineMissing(StoryError): pass
class StoryBeatInvalid(StoryError): pass
class StoryApplyConflict(StoryError): pass
class StorySourceChanged(StoryError): pass
class StoryMappingError(StoryError): pass
