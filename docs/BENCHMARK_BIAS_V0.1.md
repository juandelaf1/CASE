# BIAS EVALUATION BENCHMARK V0.1

## Objective

Evaluate if CASE maintains consistent decisions when two cases are substantially equivalent and only one attribute changes that shouldn't affect the decision.

## Methodology

1. Create counterfactual pairs
2. Measure invariance across dimensions
3. Document findings

## Dataset

Small, controlled, synthetic dataset in `evaluation/scenarios/bias/`

## Dimensions Evaluated

1. Client name changes
2. Provider changes
3. Text wording changes
4. Irrelevant information changes
5. Synthetic demographic attributes
6. Neutral logistics attributes

## Metrics

- Pair consistency rate
- Decision invariance rate
- Classification invariance
- Urgency invariance
- Routing invariance
- Recommendation invariance
- Automation invariance
- HITL consistency

## Limitations

- Small, controlled dataset
- Synthetic cases only
- Offline evaluation
- Uses MockProvider
- Not production fairness guarantee
- Doesn't represent global bias absence
