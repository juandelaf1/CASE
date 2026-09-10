import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class DatasetItem(BaseModel):
    case_id: str
    report_text: str
    domain: str
    expected_decision: str
    expected_urgency: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Dataset(BaseModel):
    name: str
    version: str
    description: str = ""
    items: list[DatasetItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetLoader:
    def load_from_file(self, path: str | Path) -> Dataset:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Dataset not found: {p}")

        with open(p) as f:
            data = json.load(f)

        return Dataset(
            name=data.get("name", p.stem),
            version=data.get("version", "0.0.0"),
            description=data.get("description", ""),
            items=[DatasetItem(**item) for item in data.get("items", [])],
            metadata=data.get("metadata", {}),
        )

    def load_from_dict(self, data: dict) -> Dataset:
        return Dataset(
            name=data.get("name", "unnamed"),
            version=data.get("version", "0.0.0"),
            description=data.get("description", ""),
            items=[DatasetItem(**item) for item in data.get("items", [])],
            metadata=data.get("metadata", {}),
        )

    def save_to_file(self, dataset: Dataset, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            json.dump(dataset.model_dump(), f, indent=2)
