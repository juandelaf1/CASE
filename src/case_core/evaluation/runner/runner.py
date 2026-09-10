from typing import Any

from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_core.evaluation.datasets.loader import Dataset, DatasetItem
from case_core.evaluation.runner.results import EvaluationResult, EvaluationRun
from case_core.ports.llm import LLMProvider


class EvaluationRunner:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def run_single(
        self,
        item: DatasetItem,
        pipeline: Any,
        domain_policy: Any,
    ) -> EvaluationResult:
        evidence = [
            EvidenceItem(
                id=e.get("id", f"ev-{i}"),
                type=EvidenceType(e.get("type", "text")),
                content=e.get("content", ""),
                source=e.get("source", "dataset"),
                confidence=e.get("confidence", 0.9),
                extracted_at=e.get("extracted_at", ""),
            )
            for i, e in enumerate(item.evidence)
        ]

        case = OperationalCase(
            case_id=item.case_id,
            report_text=item.report_text,
            domain=item.domain,
            urgency=UrgencyLevel.MEDIUM,
            evidence=evidence,
        )

        from case_core.prompts.builder import PromptBuilder
        builder = PromptBuilder(domain_policy=domain_policy)
        llm_request = builder.build(case)

        try:
            llm_response = await self._provider.complete(llm_request)
            decision, err = await pipeline.run(
                llm_response.raw_output,
                case,
                provider=self._provider,
                llm_request=llm_request,
            )

            if err:
                return EvaluationResult(
                    case_id=item.case_id,
                    expected_decision=item.expected_decision,
                    actual_decision="error",
                    expected_urgency=item.expected_urgency,
                    actual_urgency="unknown",
                    confidence=0.0,
                    correct_decision=False,
                    correct_urgency=False,
                    processing_time_ms=0.0,
                    provider=self._provider.name,
                    model=self._provider.model,
                    error=err.message,
                )

            return EvaluationResult(
                case_id=item.case_id,
                expected_decision=item.expected_decision,
                actual_decision=decision.action,
                expected_urgency=item.expected_urgency,
                actual_urgency=decision.urgency,
                confidence=decision.confidence,
                correct_decision=decision.action == item.expected_decision,
                correct_urgency=decision.urgency == item.expected_urgency,
                processing_time_ms=decision.processing_time_ms,
                provider=self._provider.name,
                model=self._provider.model,
            )
        except Exception as e:
            return EvaluationResult(
                case_id=item.case_id,
                expected_decision=item.expected_decision,
                actual_decision="error",
                expected_urgency=item.expected_urgency,
                actual_urgency="unknown",
                confidence=0.0,
                correct_decision=False,
                correct_urgency=False,
                processing_time_ms=0.0,
                provider=self._provider.name,
                model=self._provider.model,
                error=str(e),
            )

    async def run_dataset(
        self,
        dataset: Dataset,
        pipeline: Any,
        domain_registry: Any,
    ) -> EvaluationRun:
        results = []

        for item in dataset.items:
            domain_policy = domain_registry.get(item.domain)
            if not domain_policy:
                results.append(EvaluationResult(
                    case_id=item.case_id,
                    expected_decision=item.expected_decision,
                    actual_decision="error",
                    expected_urgency=item.expected_urgency,
                    actual_urgency="unknown",
                    confidence=0.0,
                    correct_decision=False,
                    correct_urgency=False,
                    processing_time_ms=0.0,
                    provider=self._provider.name,
                    model=self._provider.model,
                    error=f"Unknown domain: {item.domain}",
                ))
                continue

            result = await self.run_single(item, pipeline, domain_policy)
            results.append(result)

        successful = sum(1 for r in results if r.error is None)
        failed = len(results) - successful
        avg_time = sum(r.processing_time_ms for r in results) / len(results) if results else 0
        decision_acc = sum(1 for r in results if r.correct_decision) / len(results) if results else 0
        urgency_acc = sum(1 for r in results if r.correct_urgency) / len(results) if results else 0

        return EvaluationRun(
            dataset_name=dataset.name,
            dataset_version=dataset.version,
            provider=self._provider.name,
            model=self._provider.model,
            results=results,
            total_cases=len(results),
            successful_cases=successful,
            failed_cases=failed,
            avg_processing_time_ms=avg_time,
            decision_accuracy=decision_acc,
            urgency_accuracy=urgency_acc,
        )
