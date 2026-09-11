from __future__ import annotations


class TemplateError(RuntimeError):
    user_message="MMO Video Studio could not complete this template action."

class TemplateNotFound(TemplateError): user_message="This template could not be found."
class TemplateReadOnly(TemplateError): user_message="Built-in templates are read-only. Duplicate it to create an editable copy."
class TemplateValidationError(TemplateError): user_message="This template is invalid or incomplete."
class TemplateCompatibilityError(TemplateError): user_message="This template is not compatible with the selected project settings."
class TemplatePackageError(TemplateError): user_message="This template package is invalid."
class TemplatePackageUnsafe(TemplatePackageError): user_message="This template package contains an unsafe file or path."
class TemplateChecksumError(TemplatePackageError): user_message="A template package checksum did not match."
class TemplateVersionTooNew(TemplatePackageError): user_message="This template was created with a newer MMO Video Studio version."
class TemplatePlaceholderUnresolved(TemplateError): user_message="A required template placeholder still needs setup."
class TemplateApplyError(TemplateError): user_message="The template could not be applied safely; created changes were rolled back."
