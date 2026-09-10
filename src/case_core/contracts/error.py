from enum import Enum
from typing import Any

from pydantic import BaseModel


class ErrorCategory(str, Enum):
    PARSING = "parsing"
    SCHEMA_VALIDATION = "schema_validation"
    SEMANTIC_VALIDATION = "semantic_validation"
    DOMAIN_VALIDATION = "domain_validation"
    TRANSIENT = "transient"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    SYSTEM = "system"


class CASEError(BaseModel):
    category: ErrorCategory
    message: str
    recoverable: bool = False
    retryable: bool = False
    context: dict[str, Any] = {}
    details: Any = None
