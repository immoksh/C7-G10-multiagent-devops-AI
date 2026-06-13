# Runbook: Database Connection Refused

## Symptoms
- Application logs: `connection refused` to database port
- `dial tcp <db-ip>:<port>: connect: connection refused`
- Service returning 500 errors, health checks failing

## Root Cause Categories
1. Database pod/service is down
2. Database port not exposed or wrong port configured
3. Network policy blocking traffic
4. Database max_connections exhausted
5. Wrong DB host in application config (env var issue)

## Diagnostic Steps
1. Test connectivity: `nc -zv <db-host> <db-port>` or `telnet <db-host> <db-port>`
2. Check DB pod: `kubectl get pods -l app=postgres -n <namespace>`
3. Check DB service: `kubectl get svc -n <namespace>`
4. Check DB logs: `kubectl logs <db-pod> --tail=50`
5. Check connection count (Postgres): `SELECT count(*) FROM pg_stat_activity;`

## Remediation Steps
1. **Verify DB is running**: `kubectl get pods -n <namespace> | grep <db>`
2. **If DB pod is down**: `kubectl describe pod <db-pod>` — check for OOM or crash
3. **Restart DB if needed**: `kubectl rollout restart deployment/<db-deployment>`
4. **Check env vars**: `kubectl exec <app-pod> -- env | grep -i db`
5. **If max_connections hit** (Postgres): restart app pods to release idle connections
   `kubectl rollout restart deployment/<app>`
6. **Check network policy**: `kubectl get networkpolicy -n <namespace>`
7. **Verify service DNS**: `kubectl exec <app-pod> -- nslookup <db-service>`

## Prevention
- Use connection pooling (PgBouncer, HikariCP)
- Set `max_connections` alert at 80% utilization
- Run DB on persistent volume with appropriate storage class
