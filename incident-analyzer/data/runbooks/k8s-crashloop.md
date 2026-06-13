# Runbook: Kubernetes CrashLoopBackOff

## Symptoms
- Pod status shows `CrashLoopBackOff`
- Container repeatedly starts and exits
- `kubectl get events` shows BackOff warnings

## Root Cause Categories
1. Application crash on startup (misconfiguration, missing env vars, bad entrypoint)
2. Liveness probe too aggressive (killing healthy containers)
3. OOMKilled — container exceeding memory limits
4. Missing ConfigMap or Secret dependency

## Diagnostic Steps
1. Check pod logs: `kubectl logs <pod> --previous`
2. Describe pod: `kubectl describe pod <pod>`
3. Check exit code: `kubectl get pod <pod> -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}'`
   - Exit 1: App error (check logs)
   - Exit 137: OOMKilled (increase memory limits)
   - Exit 143: SIGTERM (check graceful shutdown)

## Remediation Steps
1. **Check last crash logs**: `kubectl logs <pod-name> --previous -n <namespace>`
2. **Inspect environment variables**: `kubectl exec <pod> -- env | grep -i <relevant_var>`
3. **Verify ConfigMaps/Secrets exist**: `kubectl get cm,secret -n <namespace>`
4. **Adjust liveness probe** if exit code is 0 but pod keeps restarting — increase `initialDelaySeconds`
5. **Increase memory limits** if OOMKilled: edit deployment → `resources.limits.memory`
6. **Restart cleanly**: `kubectl rollout restart deployment/<name> -n <namespace>`
7. **Monitor rollout**: `kubectl rollout status deployment/<name>`

## Prevention
- Set appropriate resource requests and limits
- Use `initialDelaySeconds` ≥ 30s for slow-starting apps
- Add readiness probes separate from liveness probes
