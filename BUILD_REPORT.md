# TuneGraph 0.1.0 Build Report

## Release scope

This repository is a production-oriented alpha implementation of the TuneGraph PRD. It provides a runnable control plane and reference data plane with the following completed paths:

- Organization-scoped authentication, API keys, Argon2 hashing, JWT tokens, and RBAC
- Immutable base-model, dataset, capability, contract, training, patch, graph, deployment, trace, and removal records
- Dataset validation and approval lifecycle
- PEFT training specifications and an optional Hugging Face PEFT worker
- Executable quality and output contracts
- Patch lifecycle enforcement, dependencies, conflicts, evaluation, provenance, and diffing
- Signed graph releases and patch-manifest verification
- Graph validation, canary rollout, graph update, promotion, rollback, and revocation support
- OPA-compatible policy decisions with a local default-deny fallback
- OpenAI-compatible inference proxy with request-to-patch tracing
- Removal impact analysis with explicit limitations for approximate unlearning
- Alembic migrations, Docker images, Docker Compose, Helm, CI, security workflows, SDK, CLI, and console

## Validation performed in the build environment

- Python bytecode compilation completed for `src`, `tests`, and `alembic`.
- Unit test result: 20 passed.
- API lifecycle test: included but skipped locally because the isolated build environment did not contain `aiosqlite` and had no package-registry access.
- Coverage result: 32.54 percent, above the repository's alpha threshold of 25 percent.
- Archive contents are checked using `unzip -t` before delivery.
- Source files are recorded in `SOURCE_MANIFEST.sha256`.

GitHub Actions installs all declared dependencies and runs Python 3.11, 3.12, and 3.13 tests, Ruff, MyPy, PostgreSQL migration checks, console builds, dependency audits, and CodeQL.

## Explicit extension boundaries

The following PRD areas are represented by interfaces, schemas, or safe workflow scaffolding, but are not claimed as completed scientific guarantees:

- Exact record-level machine unlearning
- Token-level LoRA routing
- Mathematically guaranteed provenance separation
- Automated causal influence attribution
- Automatic patch consolidation
- Cross-base-model adapter conversion
- Fully autonomous production promotion

Production teams must independently benchmark model quality, privacy, security, latency, infrastructure sizing, and regulatory controls for their own models and data before enabling customer traffic.
