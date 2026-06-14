# AWS Rate Limiting / Throttling (429) Runbook

AWS APIs and load balancers return 429 / ThrottlingException when request
rates exceed account or service limits.

## Remediation
1. Implement exponential backoff with jitter on the client SDK.
2. Batch requests and cache responses where possible.
3. Request a service quota increase via Service Quotas if sustained.
4. Spread load across regions or partitions to avoid hot keys.
5. Validate the throttling errors stop in CloudWatch metrics.

# AWS DNS Resolution Failure Runbook

`name or service not known` / SERVFAIL indicates DNS resolution problems.

## Remediation
1. Confirm Route 53 / resolver returns the record: `dig <host>`.
2. Check VPC DNS settings (`enableDnsSupport`, `enableDnsHostnames`).
3. Verify the service endpoint and that the record has not expired.
4. Flush local resolver caches if stale.
5. Validate resolution and downstream connectivity.

# TLS / Certificate Error Runbook

`x509` / `certificate` errors indicate an invalid, expired, or untrusted cert.

## Remediation
1. Inspect the certificate: `openssl s_client -connect host:443`.
2. Renew or rotate expired certificates (ACM / cert-manager).
3. Ensure the full chain is served, not just the leaf cert.
4. Confirm clients trust the issuing CA.
5. Validate the handshake succeeds end to end.
