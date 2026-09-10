from enum import Enum


class ProcessingLifecycle(str, Enum):
    RECEIVED = "received"
    PARSING = "parsing"
    PARSED = "parsed"
    VALIDATING = "validating"
    VALIDATED = "validated"
    PROMPT_BUILDING = "prompt_building"
    PROMPT_BUILT = "prompt_built"
    PROVIDING = "providing"
    PROVIDED = "provided"
    PARSING_RESPONSE = "parsing_response"
    RESPONSE_PARSED = "response_parsed"
    VALIDATING_RESPONSE = "validating_response"
    RESPONSE_VALIDATED = "response_validated"
    DECIDING = "deciding"
    DECIDED = "decided"
    AUDITING = "auditing"
    AUDITED = "audited"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINAL_FAILURE = "terminal_failure"


class DecisionLifecycle(str, Enum):
    AI_PROPOSED = "ai_proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    MODIFIED = "modified"
    OVERRIDDEN = "overridden"
    ARCHIVED = "archived"
