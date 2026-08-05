from tunegraph.schemas import ContractEvaluateRequest, ContractGate
from tunegraph.services.contracts import ContractEngine


def test_metric_and_json_schema_contracts_pass() -> None:
    gates = [
        ContractGate(
            id="accuracy",
            evaluator="metric_threshold",
            metric="accuracy",
            operator=">=",
            threshold=0.9,
        ),
        ContractGate(
            id="schema",
            evaluator="json_schema",
            config={
                "schema": {
                    "type": "object",
                    "required": ["category"],
                    "properties": {"category": {"type": "string"}},
                }
            },
        ),
    ]
    result = ContractEngine().evaluate(
        gates,
        ContractEvaluateRequest(metrics={"accuracy": 0.94}, output={"category": "billing"}),
    )
    assert result.passed is True
    assert all(item.passed for item in result.results)


def test_non_blocking_failure_does_not_fail_suite() -> None:
    gate = ContractGate(
        id="latency",
        evaluator="latency",
        operator="<=",
        threshold=100,
        blocking=False,
    )
    result = ContractEngine().evaluate([gate], ContractEvaluateRequest(latency_ms=120))
    assert result.passed is True
    assert result.results[0].passed is False
