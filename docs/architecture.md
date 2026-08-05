# Architecture

TuneGraph separates behavior governance from model execution.

## Control plane

The FastAPI control plane owns authoritative metadata in PostgreSQL. It manages identity, datasets, training jobs, contract suites, immutable patch releases, capability graphs, policies, approvals, deployments, audit events, traces, and removal requests.

The initial implementation is a modular monolith. Training workers and the inference gateway remain independently scalable. This avoids premature distributed-system complexity while preserving domain boundaries.

## Data plane

The inference path resolves a deployment and graph, validates dependencies and conflicts, applies deterministic authorization after candidate selection, creates a patch plan, invokes an OpenAI-compatible backend, and records an inference trace.

The reference implementation routes one LoRA adapter directly through vLLM. Multi-patch graphs require an approved merged composition or a backend plugin that implements the selected composition algorithm.

## Immutability

Dataset versions, patch releases, graph releases, contract suites, training specifications, and evaluation evidence are immutable. Promotion is represented by deployment pointers and explicit state transitions.

## Storage

- PostgreSQL is the metadata source of truth.
- Object storage or OCI registries store weights and large evidence bundles.
- Redis may be added for temporary caches, never authoritative state.
- OPA evaluates deployment and inference policies.
- OpenTelemetry is the target observability protocol.

## Extension interfaces

The code isolates the following extension points:

- Training backends
- Artifact stores
- Contract evaluators
- Policy engines
- Router algorithms
- Inference backends
- Influence estimators
- Removal and unlearning strategies
