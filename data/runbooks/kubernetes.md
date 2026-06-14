# Kubernetes Pod CrashLoopBackOff Runbook

A pod in CrashLoopBackOff is starting, crashing, and being restarted repeatedly.

## Diagnosis
- Inspect the previous container logs: `kubectl logs <pod> --previous`.
- Describe the pod to see the exit code and reason: `kubectl describe pod <pod>`.
- Common causes: bad config/secret, failing liveness probe, missing dependency, application panic on boot, or an image that exits immediately.

## Remediation
1. Identify the crash reason from logs and the `Last State` in `describe`.
2. If a liveness/readiness probe is too aggressive, increase `initialDelaySeconds`.
3. If a ConfigMap/Secret is wrong, patch it and let the pod restart.
4. Roll out the fix: `kubectl rollout restart deploy/<name>`.
5. Watch recovery: `kubectl get pods -w`.

# Kubernetes OOMKilled Runbook

A container was killed by the kernel OOM killer because it exceeded its memory limit.

## Diagnosis
- `kubectl get events --field-selector reason=OOMKilling`.
- Check `kubectl describe pod <pod>` for `Last State: Terminated, Reason: OOMKilled`.
- Review memory requests/limits in the deployment spec.

## Remediation
1. Increase the container memory `limits` and `requests` if the workload genuinely needs more.
2. If there is a memory leak, capture a heap profile and fix the application.
3. Add or tune a Horizontal Pod Autoscaler if load-driven.
4. Apply changes and `kubectl rollout restart deploy/<name>`.
5. Validate steady-state memory with `kubectl top pod`.

# Kubernetes Disk Pressure / Pod Evicted Runbook

Nodes under DiskPressure evict pods to reclaim space.

## Remediation
1. Check node conditions: `kubectl describe node <node>`.
2. Clear unused images on the node: `crictl rmi --prune` or `docker image prune`.
3. Rotate or ship large container logs.
4. Expand the node disk or add nodes.
5. Confirm the node leaves `DiskPressure` and pods reschedule.
