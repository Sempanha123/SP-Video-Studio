from __future__ import annotations


class ShortsError(RuntimeError):
    user_message = "Shorts Maker could not complete this action."


class ShortSourceMissing(ShortsError):
    user_message = "The source video for this Short is unavailable."


class ShortInvalidRange(ShortsError):
    user_message = "Set an Out point after the In point."


class ShortCandidateInvalid(ShortsError):
    user_message = "This Short candidate is invalid."


class ShortReframeInvalid(ShortsError):
    user_message = "The Short reframe settings are invalid."


class ShortCaptionError(ShortsError):
    user_message = "Short captions could not be prepared."


class ShortSourceOutdated(ShortsError):
    user_message = "The source project changed after this Short was created."
