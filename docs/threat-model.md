# Threat Model

## Assets

- Training data and labels
- Model and adapter weights
- Signing keys
- Tenant metadata
- Graph and deployment configuration
- Credentials and API keys
- Inference traces
- Audit evidence

## Trust boundaries

- Browser to console
- Console to API
- API to PostgreSQL, OPA, and artifact storage
- Worker to datasets, models, and artifact storage
- Gateway to inference backend
- Tenant to tenant
- CI builder to registry

## Primary threats

### Poisoned data

An attacker inserts examples that create hidden triggers or unsafe behavior. Mitigations include quarantine, ownership metadata, quality gates, duplicate detection, human approval, contract suites, red-team evaluation, and source-level lineage.

### Malicious model or adapter

An artifact contains unsafe serialization or backdoored behavior. Mitigations include safetensors, immutable digests, signatures, scanning, restricted loading, and isolated evaluation.

### Unauthorized patch selection

A request attempts to activate a patch outside its tenant or profile. Candidate routing never grants authorization. The deterministic resolver and policy layer enforce organization, state, dependency, conflict, and environment restrictions.

### Artifact substitution

A registry object is replaced after approval. Content hashes and signatures make substitution detectable. Runtime loaders must verify both.

### Tenant leakage

Metadata, adapters, cache entries, or prompts cross tenant boundaries. Mitigations include tenant IDs on records, organization-scoped queries, separate credentials, cache namespaces, network policies, and isolation tests.

### Prompt injection

A user attempts to bypass application rules or invoke unauthorized tools. TuneGraph governs patches, but applications still need tool authorization, input isolation, output validation, and least-agency design.

### Removal overclaim

An operator mistakes graph exclusion for complete erasure. TuneGraph labels impact and influence as evidence with limitations and requires retain-set and forget-set evaluation before making stronger claims.
