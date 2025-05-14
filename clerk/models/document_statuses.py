from enum import Enum


class DocumentStatuses(str, Enum):
    SUBMITTED = "submitted"
    FAILED = "failed"
    EXTRACTED = "extracted"
    REVIEWED_POSITIVE = "reviewed_positive"
    REVIEWED_NEGATIVE = "reviewed_negative"
    EXAMPLE = "example"
    SUPERSEDED = "superseded"
