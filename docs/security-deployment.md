# Secure Deployment

## Identity

Integrate an enterprise identity provider before broad access. The included local user store supports initial deployment and development. Use separate service accounts for API, training, evaluation, migration, and inference workloads.

## Secrets

Never place secrets in Git, images, Helm values, training specifications, or logs. Rotate JWT secrets, API keys, database credentials, registry credentials, and signing keys through documented procedures.

## Signing

TuneGraph uses Ed25519 for reference signing. Protect private keys using KMS, HSM, or a dedicated signing service. API and runtime components should usually receive only the public verification key. The reference application can sign graph manifests locally, but external signing is preferable for high-assurance deployments.

## Model and dataset ingestion

Treat every external model, tokenizer, dataset, and adapter as hostile until reviewed.

- Disable remote code execution.
- Prefer `safetensors`.
- Scan archives and containers.
- Verify licenses and data-use permissions.
- Inspect tokenizers and templates.
- Run poisoning and hidden-trigger tests.
- Quarantine untrusted artifacts.

## Network

Training workers require the narrowest possible egress. Inference workers should not reach control-plane databases directly. Deny cross-tenant pod traffic unless required. Restrict OPA, PostgreSQL, registry, and object-store access by workload identity and network policy.

## Logging and privacy

The reference gateway stores request and response digests, not raw content. Organizations enabling raw-content storage must define purpose, access, encryption, retention, redaction, and deletion controls.

## Incident response

For a suspected malicious patch:

1. Revoke the patch.
2. Remove it from active graph plans.
3. Evict it from runtime caches.
4. Roll back affected deployments.
5. Preserve audit and build evidence.
6. Identify datasets, training jobs, graphs, tenants, and traces in the impact path.
7. Rotate credentials if the supply chain was compromised.
8. Publish a corrected signed release only after security review.
