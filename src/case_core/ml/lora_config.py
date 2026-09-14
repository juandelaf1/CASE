"""LoRA/QLoRA configuration and support — Phase 3.4."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AdaptationMethod(str, Enum):
    """Supported adaptation methods."""

    LORA = "lora"
    QLORA = "qlora"
    FULL_FINETUNE = "full_finetune"
    PROMPT_TUNING = "prompt_tuning"


class LoRAConfig(BaseModel):
    """Configuration for LoRA/QLoRA adaptation."""

    method: AdaptationMethod = AdaptationMethod.LORA
    rank: int = Field(default=8, ge=1, le=256)
    alpha: int = Field(default=16, ge=1, le=512)
    dropout: float = Field(default=0.1, ge=0.0, le=1.0)
    target_modules: list[str] = Field(default_factory=lambda: ["q_proj", "v_proj"])
    base_model_name: str = "meta-llama/Llama-2-7b-hf"
    base_model_path: str | None = None
    adapter_path: str | None = None
    max_seq_length: int = Field(default=512, ge=32, le=4096)
    learning_rate: float = Field(default=2e-4, ge=1e-6, le=1e-1)
    batch_size: int = Field(default=4, ge=1, le=256)
    num_epochs: int = Field(default=3, ge=1, le=100)
    warmup_steps: int = Field(default=100, ge=0)
    weight_decay: float = Field(default=0.01, ge=0.0, le=1.0)
    gradient_accumulation_steps: int = Field(default=1, ge=1, le=64)
    lora_dropout: float = Field(default=0.05, ge=0.0, le=1.0)
    bias: str = "none"
    task_type: str = "CAUSAL_LM"
    quantization_bits: int | None = Field(default=None, ge=2, le=16)

    def get_target_modules(self) -> list[str]:
        return self.target_modules

    def validate_config(self) -> list[str]:
        errors = []
        if self.method == AdaptationMethod.QLORA and self.quantization_bits is None:
            errors.append("QLoRA requires quantization_bits to be set")
        if self.method == AdaptationMethod.QLORA and self.quantization_bits not in (4, 8):
            errors.append("QLoRA typically uses 4-bit or 8-bit quantization")
        if self.rank > self.alpha:
            errors.append("rank should be <= alpha for stable training")
        if self.learning_rate > 1e-2:
            errors.append("learning_rate too high, may cause instability")
        return errors


class TrainingConfig(BaseModel):
    """Complete training configuration."""

    lora_config: LoRAConfig = Field(default_factory=LoRAConfig)
    output_dir: str = "./output"
    logging_dir: str = "./logs"
    save_strategy: str = "epoch"
    evaluation_strategy: str = "epoch"
    load_best_model_at_end: bool = True
    metric_for_best_model: str = "accuracy"
    greater_is_better: bool = True
    fp16: bool = False
    bf16: bool = False
    dataloader_num_workers: int = 0
    remove_unused_columns: bool = False
    report_to: str = "none"
    seed: int = 42

    def get_training_args(self) -> dict[str, Any]:
        return {
            "output_dir": self.output_dir,
            "logging_dir": self.logging_dir,
            "save_strategy": self.save_strategy,
            "evaluation_strategy": self.evaluation_strategy,
            "load_best_model_at_end": self.load_best_model_at_end,
            "metric_for_best_model": self.metric_for_best_model,
            "greater_is_better": self.greater_is_better,
            "fp16": self.fp16,
            "bf16": self.bf16,
            "dataloader_num_workers": self.dataloader_num_workers,
            "remove_unused_columns": self.remove_unused_columns,
            "report_to": self.report_to,
            "seed": self.seed,
        }


class AdapterMetadata(BaseModel):
    """Metadata for a trained adapter."""

    adapter_id: str
    base_model: str
    method: AdaptationMethod
    rank: int
    alpha: int
    target_modules: list[str]
    training_dataset_id: str | None = None
    training_examples: int = 0
    training_epochs: int = 0
    final_loss: float | None = None
    final_accuracy: float | None = None
    created_at: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
