"""Model adapter implementations — Phase 3.5."""

from __future__ import annotations

import json
from pathlib import Path

from case_core.ml.training_abstraction import InferenceEngine, ModelAdapter


class MockAdapter(ModelAdapter):
    """Mock adapter for testing and development."""

    def __init__(self, adapter_id: str = "mock", base_model: str = "mock-model"):
        self._adapter_id = adapter_id
        self._base_model = base_model
        self._loaded = False
        self._responses: dict[str, str] = {}

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    @property
    def base_model(self) -> str:
        return self._base_model

    def load(self, adapter_path: str | None = None) -> None:
        if adapter_path and Path(adapter_path).exists():
            with open(adapter_path) as f:
                self._responses = json.load(f)
        self._loaded = True

    def save(self, output_path: str) -> None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(self._responses, f)

    def predict(self, input_text: str) -> str:
        if not self._loaded:
            raise RuntimeError("Adapter not loaded. Call load() first.")
        return self._responses.get(input_text, f"Mock prediction for: {input_text}")

    def predict_batch(self, input_texts: list[str]) -> list[str]:
        return [self.predict(text) for text in input_texts]


class NullAdapter(ModelAdapter):
    """Null adapter that returns empty predictions (baseline)."""

    @property
    def adapter_id(self) -> str:
        return "null"

    @property
    def base_model(self) -> str:
        return "null"

    def load(self, adapter_path: str | None = None) -> None:
        pass

    def save(self, output_path: str) -> None:
        pass

    def predict(self, input_text: str) -> str:
        return ""

    def predict_batch(self, input_texts: list[str]) -> list[str]:
        return [""] * len(input_texts)


class NullInferenceEngine(InferenceEngine):
    """Null inference engine for baseline testing."""

    def __init__(self) -> None:
        self._adapter: ModelAdapter | None = None

    def initialize(self, adapter: ModelAdapter) -> None:
        self._adapter = adapter
        adapter.load()

    def infer(self, input_text: str) -> str:
        if self._adapter is None:
            raise RuntimeError("Engine not initialized")
        return self._adapter.predict(input_text)

    def infer_batch(self, input_texts: list[str]) -> list[str]:
        if self._adapter is None:
            raise RuntimeError("Engine not initialized")
        return self._adapter.predict_batch(input_texts)

    def health_check(self) -> bool:
        return self._adapter is not None
