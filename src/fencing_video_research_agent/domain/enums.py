"""Domain enumerations for fencing-video research workflows."""

from enum import StrEnum


class ReviewStatus(StrEnum):
    """Manual review state for a stored video."""

    UNREVIEWED = "unreviewed"
    REVIEWED = "reviewed"
