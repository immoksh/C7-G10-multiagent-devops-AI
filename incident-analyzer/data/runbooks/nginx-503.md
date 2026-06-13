# Runbook: Nginx 503 Service Unavailable

## Symptoms
- HTTP 503 responses from Nginx
- Access logs show `503` status codes
- Error logs: `no live upstreams while connecting to upstream`

## Root Cause Categories
1. All upstream backends are down or unreachable
2. Upstream health checks failing
3. Connection pool exhausted
4. Backend deployment in progress (rolling update)

## Diagnostic Steps
1. Check upstream health: `curl -I http://<upstream-host>:<port>/health`
2. Check Nginx error log: `tail -f /var/log/nginx/error.log`
3. Check upstream pool: `nginx -T | grep upstream`
4. If Kubernetes: check backend pod status: `kubectl get pods -l app=<backend>`

## Remediation Steps
1. **Identify failed upstreams** from error logs — look for IPs in `upstream: "http://..."` lines
2. **Check if backends are running**: `kubectl get pods -n <namespace>` or `systemctl status <service>`
3. **If rolling update in progress**: wait for rollout to complete: `kubectl rollout status deployment/<name>`
4. **If pods crashed**: follow CrashLoopBackOff runbook
5. **Immediate traffic relief**: temporarily scale up backends:
   `kubectl scale deployment/<name> --replicas=<N>`
6. **Test upstream directly**: `curl -v http://<pod-ip>:<port>/health`
7. **Reload Nginx** after backend recovery: `nginx -s reload`

## Prevention
- Configure `max_fails` and `fail_timeout` on upstreams
- Add active health checks with `nginx_upstream_check_module`
- Set up Prometheus alert on upstream response time p99
