# Nginx 502 / 504 Upstream Timeout Runbook

Nginx returns 502 Bad Gateway or 504 Gateway Timeout when an upstream is
slow, unreachable, or returns an invalid response.

## Diagnosis
- Tail the error log: `tail -f /var/log/nginx/error.log`.
- Look for `upstream timed out`, `no live upstreams`, or `connect() failed`.
- Verify upstream health directly with `curl` from the proxy host.

## Remediation
1. Confirm the upstream service is up and within latency SLOs.
2. If the upstream is simply slow, raise `proxy_read_timeout` and
   `proxy_connect_timeout` in the relevant location block.
3. If an upstream is dead, remove it from the pool or fix its health check.
4. Reload nginx without dropping connections: `nginx -s reload`.
5. Validate with synthetic requests and watch p99 latency recover.

# Nginx 503 Service Unavailable Runbook

503 usually means no healthy upstreams are available or the server is
overloaded / rate limiting.

## Remediation
1. Check whether all upstreams are marked down (`no live upstreams`).
2. Scale the upstream service horizontally to add capacity.
3. Inspect `limit_req` / `limit_conn` directives for unintended throttling.
4. Reload nginx and confirm requests return 200.
