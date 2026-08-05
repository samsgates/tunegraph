# Operations Runbooks

## Revoke a patch

1. Identify the immutable patch release.
2. Record the incident reason.
3. Transition the patch to `revoked`.
4. Confirm policy decisions reject it.
5. Remove or replace affected graph releases.
6. Roll back deployments.
7. Evict adapter caches in the serving backend.
8. Review affected inference traces and tenants.

## Roll back a deployment

1. Confirm the previous graph release is signed and available.
2. Call the deployment rollback endpoint.
3. Verify traffic and health metrics.
4. Confirm new inference traces use the expected graph release.
5. Open an incident or regression investigation.

## Suspected dataset poisoning

1. Quarantine the dataset version.
2. Stop queued and running jobs that use it.
3. Run removal impact analysis.
4. Revoke affected patches when risk is material.
5. Preserve the source, hashes, logs, and approvals.
6. Retrain from approved retained data.
7. Run target, regression, safety, and trigger evaluations.

## Database restore

1. Stop writes.
2. Restore PostgreSQL to the selected recovery point.
3. Verify migration revision.
4. Verify artifact and graph references.
5. Verify signing keys and policy bundles.
6. Start one API replica and run readiness checks.
7. Reconcile deployments and then scale out.
