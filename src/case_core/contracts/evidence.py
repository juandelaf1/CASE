from enum import Enum

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    METRIC = "metric"
    RULE = "rule"


class EvidenceItem(BaseModel):
    id: str
    type: EvidenceType
    content: str
    source: str
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "extracted_at": self.extracted_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EvidenceItem":
        return cls(
            id=data["id"],
            type=EvidenceType(data["type"]),
            content=data["content"],
            source=data["source"],
            confidence=data["confidence"],
            extracted_at=data["extracted_at"],
        )
