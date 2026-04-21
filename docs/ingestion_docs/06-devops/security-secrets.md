# Security and Secrets Requirements

## Secrets Policy

- No secrets committed to git.
- `.env.example` contains placeholders only.
- Production secrets provided by secure secret manager or server runtime injection.

## Container Security Baseline

- Minimal base images.
- Non-root containers where supported.
- Read-only filesystem when possible.
- Drop unnecessary Linux capabilities.
- Pin dependencies and scan regularly.

## Access and Network

- Least-privilege credentials per service.
- Separate credentials per environment.
- Internal-only networking for non-public services.
- TLS termination strategy documented for production ingress.

## Audit Requirements

- Deployment actions must be traceable.
- Configuration changes must be reviewable.
- Security incidents and response steps must be documented.
