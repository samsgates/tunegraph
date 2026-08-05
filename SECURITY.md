# Security Policy

## Supported versions

Security fixes are provided for the latest minor release on the active branch.

## Reporting a vulnerability

Do not create a public issue for a suspected vulnerability. Send a private report to the security contact configured by the repository owner. Include affected version, impact, reproduction steps, logs with secrets removed, and a proposed mitigation when available.

The maintainers should acknowledge a valid report within three business days, provide a remediation plan, coordinate disclosure, and publish a security advisory after patched releases are available.

## Security boundaries

TuneGraph manages highly sensitive model, dataset, adapter, and tenant metadata. Deploy it only behind authenticated network boundaries. The project does not make untrusted model weights safe, determine whether training data is legally usable, or prove complete machine unlearning.

## Mandatory production controls

- PostgreSQL, not SQLite
- TLS and private networking
- External secrets manager
- Signed immutable artifacts
- Default-deny OPA policies
- Least-privilege service accounts
- Restricted worker egress
- Centralized audit export
- Tested backup, restore, rollback, and revocation
- Dependency and container scanning

See `docs/security-deployment.md` and `docs/threat-model.md`.
