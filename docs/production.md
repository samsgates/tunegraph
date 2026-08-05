# Production Guide

## Readiness checklist

Before production traffic:

1. Use managed or highly available PostgreSQL with encrypted storage, backups, point-in-time recovery, and tested restores.
2. Put all credentials and signing keys in an external secrets manager.
3. Generate separate keys for staging and production.
4. Configure TLS at the ingress and private TLS or mTLS between sensitive services.
5. Replace the example OPA policy with organization-specific default-deny policy bundles.
6. Use immutable base-model, tokenizer, container, dataset, and adapter revisions.
7. Run Alembic migrations as a controlled deployment job, not concurrently from every replica.
8. Set `TUNEGRAPH_RUN_MIGRATIONS=false` on ordinary API pods after introducing a dedicated migration job.
9. Configure an externally managed object store or OCI registry for artifacts.
10. Install centralized logs, traces, metrics, alerts, and audit export.
11. Create patch revocation and graph rollback runbooks.
12. Run tenant-isolation, security, load, restore, and disaster-recovery tests.

## Database

Use `postgresql+psycopg://` with TLS parameters appropriate to your provider. Give the migration job DDL permissions. Give application pods only required DML permissions where practical.

Recommended controls:

- Connection pooling
- Statement timeouts
- Idle transaction timeouts
- Row-level security for high-isolation deployments
- Automated vacuum monitoring
- Slow-query alerts

## Artifact storage

The included local artifact store is for development and single-node installations. Production deployments should implement the artifact-store interface with S3, GCS, Azure Blob, or OCI and require:

- Versioning
- Object lock where needed
- Server-side encryption
- Content digests
- Signed manifests
- Malware and serialization scanning
- Short-lived workload credentials

## Scaling

Scale API replicas horizontally. Keep training workers in a dedicated GPU pool. Scale inference separately according to model memory, adapter cache behavior, and latency targets.

Use a queue or scheduler instead of the reference polling worker for large installations. Preserve idempotent job state transitions and immutable outputs.

## Upgrades

1. Back up PostgreSQL and verify the backup.
2. Review migrations and release notes.
3. Deploy migrations to staging.
4. Run API and graph compatibility tests.
5. Create a canary API deployment.
6. Apply the migration job.
7. Roll out API replicas.
8. Verify health, audit, and inference traces.
9. Keep the previous image and graph release available for rollback.

## Disaster recovery

Recovery order:

1. PostgreSQL metadata
2. Signing and encryption keys
3. Artifact registry or object storage
4. Policy bundles
5. API and workers
6. Inference backends
7. Deployment health reconciliation

Do not restore mutable aliases without validating that their referenced immutable releases exist and pass signature verification.
