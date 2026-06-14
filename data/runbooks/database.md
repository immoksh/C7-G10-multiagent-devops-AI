# Postgres "too many connections" Runbook

The database rejects new connections because `max_connections` is reached.

## Diagnosis
- `SELECT count(*) FROM pg_stat_activity;`
- Look for idle-in-transaction sessions holding connections.

## Remediation
1. Introduce or fix a connection pooler (PgBouncer) in transaction mode.
2. Lower per-service pool sizes so total stays under `max_connections`.
3. Terminate stuck sessions: `SELECT pg_terminate_backend(pid) ...`.
4. Increase `max_connections` only as a last resort (costs memory).
5. Validate new connections succeed and pool saturation drops.

# Database Deadlock Runbook

A deadlock occurs when two transactions wait on each other's locks.

## Remediation
1. Read the deadlock detail in the DB log to find the conflicting queries.
2. Ensure transactions acquire locks in a consistent order.
3. Keep transactions short; avoid user think-time inside a transaction.
4. Add appropriate indexes to reduce lock scope.
5. Retry the victim transaction with backoff in the application.

# Database Connection Refused Runbook

`connection refused` means nothing is listening on the DB host/port.

## Remediation
1. Confirm the database process is running and healthy.
2. Verify network policy / security group allows the client.
3. Check the connection string host, port, and credentials.
4. Restart the database service if it crashed, then validate connectivity.
