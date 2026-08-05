from __future__ import annotations

import operator
import re
from typing import Any, Callable

from jsonschema import ValidationError, validate

from tunegraph.schemas import (
    ContractEvaluateRequest,
    ContractEvaluationResult,
    ContractGate,
    ContractGateResult,
)

OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    ">=": operator.ge,
    ">": operator.gt,
    "<=": operator.le,
    "<": operator.lt,
    "=": operator.eq,
    "!=": operator.ne,
}


class ContractEngine:
    def evaluate(
        self, gates: list[ContractGate], request: ContractEvaluateRequest
    ) -> ContractEvaluationResult:
        results = [self._evaluate_gate(gate, request) for gate in gates]
        passed = all(result.passed or not result.blocking for result in results)
        return ContractEvaluationResult(passed=passed, results=results)

    def _evaluate_gate(
        self, gate: ContractGate, request: ContractEvaluateRequest
    ) -> ContractGateResult:
        if gate.evaluator == "metric_threshold":
            observed = request.metrics.get(gate.metric or "")
            if observed is None:
                return self._result(gate, False, None, "Required metric is missing")
            compare = OPERATORS[gate.operator]
            passed = compare(observed, gate.threshold)
            return self._result(gate, passed, observed, f"{observed} {gate.operator} {gate.threshold}")

        if gate.evaluator == "latency":
            observed = request.latency_ms
            if observed is None:
                return self._result(gate, False, None, "Latency value is missing")
            compare = OPERATORS[gate.operator]
            passed = compare(observed, gate.threshold)
            return self._result(gate, passed, observed, f"{observed}ms {gate.operator} {gate.threshold}ms")

        if gate.evaluator == "json_schema":
            schema = gate.config.get("schema")
            if not isinstance(schema, dict):
                return self._result(gate, False, request.output, "JSON schema is missing")
            try:
                validate(instance=request.output, schema=schema)
            except ValidationError as exc:
                return self._result(gate, False, request.output, exc.message)
            return self._result(gate, True, request.output, "Output matches JSON schema")

        if gate.evaluator == "regex":
            pattern = gate.config.get("pattern")
            if not isinstance(pattern, str):
                return self._result(gate, False, request.output, "Regex pattern is missing")
            text = request.output if isinstance(request.output, str) else str(request.output)
            passed = re.search(pattern, text) is not None
            return self._result(gate, passed, text, "Regex matched" if passed else "Regex did not match")

        if gate.evaluator == "required_fields":
            required = gate.config.get("fields", [])
            if not isinstance(request.output, dict):
                return self._result(gate, False, request.output, "Output is not an object")
            missing = [field for field in required if field not in request.output]
            return self._result(
                gate,
                not missing,
                request.output,
                "All required fields present" if not missing else f"Missing fields: {missing}",
            )

        return self._result(gate, False, None, f"Unsupported evaluator: {gate.evaluator}")

    @staticmethod
    def _result(
        gate: ContractGate, passed: bool, observed: Any, message: str
    ) -> ContractGateResult:
        return ContractGateResult(
            id=gate.id,
            passed=passed,
            blocking=gate.blocking,
            observed=observed,
            message=message,
        )
