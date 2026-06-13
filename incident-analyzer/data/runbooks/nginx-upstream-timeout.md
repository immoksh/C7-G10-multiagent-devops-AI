# Runbook: Nginx Upstream Timeout

## Symptoms
- Nginx error log: `upstream timed out (110: Connection timed out)`
- Elevated response times
- 504 Gateway Timeout responses to clients

## Root Cause Categories
1. Backend processing too slow (CPU-bound or slow queries)
2. `proxy_read_timeout` set too low for the operation
3. Network latency between Nginx and upstream
4. Database or downstream dependency slow

## Diagnostic Steps
1. Check which upstream is timing out (IP in error log)
2. Measure backend response time directly: `time curl http://<upstream>/path`
3. Check backend CPU/memory: `kubectl top pods` or `top`
4. Check database query time if backend is DB-dependent
5. Check current timeout setting: `nginx -T | grep proxy_read_timeout`

## Remediation Steps
1. **Identify the slow endpoint** from the error log's `request:` field
2. **Measure backend directly**: `curl -w "@curl-format.txt" http://<upstream>/<path>`
3. **If backend is overloaded**: scale up replicas
   `kubectl scale deployment/<name> --replicas=<N>`
4. **If query is slow**: add DB index or optimize query (involves app team)
5. **Temporary relief** — increase timeout in Nginx config:
   ```nginx
   proxy_read_timeout 120s;
   proxy_connect_timeout 10s;
   ```
   Then reload: `nginx -s reload`
6. **Long term**: add circuit breaker in application layer

## Prevention
- Set `proxy_read_timeout` based on p99 latency + buffer
- Implement request timeout at application level
- Alert on p95 backend latency > 2s
