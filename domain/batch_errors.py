from __future__ import annotations


class BatchError(RuntimeError):
    user_message = "Batch Factory could not complete this action."


class BatchInvalidInput(BatchError):
    user_message = "One or more Batch rows are invalid."


class BatchMappingError(BatchError):
    user_message = "Batch placeholder mapping is incomplete or invalid."


class BatchTemplateError(BatchError):
    user_message = "The selected template is not compatible with this Batch."


class BatchLanguageUnsupported(BatchError):
    user_message = "A requested Batch language is not supported by the selected workflow."


class BatchVoiceMissing(BatchError):
    user_message = "A required voice is missing or incompatible."


class BatchAssetMissing(BatchError):
    user_message = "A required reusable Asset could not be resolved."


class BatchVariantError(BatchError):
    user_message = "Batch variant settings are invalid."


class BatchOutputConflict(BatchError):
    user_message = "A Batch output path conflicts with an existing output."


class BatchInsufficientDisk(BatchError):
    user_message = "Batch processing paused because available disk space is too low."


class BatchItemFailed(BatchError):
    user_message = "This Batch item failed."


class BatchCancelled(BatchError):
    user_message = "Batch processing was cancelled."


class BatchLocked(BatchError):
    user_message = "This Batch is already owned by an active scheduler."
