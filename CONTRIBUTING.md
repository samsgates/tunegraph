# Contributing

Thank you for improving TuneGraph.

## Development

1. Fork the repository and create a focused branch.
2. Install `uv` and run `uv sync --extra dev`.
3. Add tests for every behavior change.
4. Run `ruff`, `mypy`, and `pytest`.
5. Update migrations, API documentation, and operational guidance when applicable.
6. Submit a pull request with the problem, design, risks, tests, and rollback considerations.

## Design requirements

- Preserve tenant isolation.
- Fail closed for privileged or production operations.
- Never log secrets, raw credentials, or model prompts by default.
- Keep immutable releases immutable.
- Represent influence as an estimate, not exact causality.
- Do not claim complete unlearning without evidence.
- Place optional integrations behind stable interfaces and extras.

Major schema, routing, policy, training, or lifecycle changes require an RFC.
