# Kubernetes Runbook: Pod CrashLoopBackOff

## Description
A pod is repeatedly crashing and being restarted by Kubernetes. This is indicated by the `CrashLoopBackOff` status.

## Root Causes
1. Application misconfiguration (e.g., missing environment variables, invalid configmap).
2. Missing dependencies (e.g., database is not reachable on startup).
3. Insufficient memory leading to `OOMKilled`.
4. Application panics or unhandled exceptions on startup.

## Remediation Steps
1. **Check Pod Logs:** View the logs of the previous container instance to find the panic or error stack trace:
   `kubectl logs <pod-name> -n <namespace> --previous`
2. **Describe Pod:** Check the events section for `OOMKilled` or Liveness probe failures:
   `kubectl describe pod <pod-name> -n <namespace>`
3. **Verify Configuration:** Ensure the ConfigMap and Secrets are correctly mounted and contain valid data.
4. **Restart Deployment:** If the issue was temporary (e.g., a database restart), try restarting the deployment:
   `kubectl rollout restart deployment <deployment-name> -n <namespace>`
5. **Scale Down and Up:** If necessary, scale to 0 and back up to force a fresh pull of secrets/configs.
