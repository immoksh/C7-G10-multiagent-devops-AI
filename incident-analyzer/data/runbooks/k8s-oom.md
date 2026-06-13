# Runbook: Kubernetes OOMKilled

## Symptoms
- Pod status: `OOMKilled` or exit code 137
- Container repeatedly killed without application error in logs
- Node memory pressure events

## Root Cause Categories
1. Memory limit set too low for the workload
2. Memory leak in the application
3. Sudden traffic spike exceeding expected memory usage
4. JVM/Node.js heap not tuned to container limits

## Diagnostic Steps
1. Confirm OOM: `kubectl describe pod <pod> | grep -A5 "Last State"`
2. Check node pressure: `kubectl describe node <node> | grep -A10 "Conditions"`
3. Check current limits: `kubectl get pod <pod> -o jsonpath='{.spec.containers[0].resources}'`
4. Check historical metrics (if Prometheus available): `container_memory_working_set_bytes`

## Remediation Steps
1. **Immediate**: Increase memory limit in deployment:
   ```yaml
   resources:
     requests:
       memory: "256Mi"
     limits:
       memory: "512Mi"
   ```
2. **Apply change**: `kubectl apply -f deployment.yaml`
3. **For JVM apps**: Set `-Xmx` to ~75% of container limit
4. **For Node.js**: Set `--max-old-space-size` flag
5. **Restart and monitor**: `kubectl rollout restart deployment/<name>`
6. **Watch memory**: `kubectl top pods -n <namespace> --sort-by=memory`

## Prevention
- Always set both requests and limits
- Monitor memory usage trends over 7 days before setting limits
- Set up Prometheus alert at 80% memory utilization
