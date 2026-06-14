# Nginx Runbook: 503 Service Unavailable / Upstream Timeout

## Description
Nginx is returning a 503 Service Unavailable or 504 Gateway Timeout error.

## Root Causes
1. **Upstream Service Down:** The application server (e.g., Node.js, Python, Java) that Nginx proxies to is down or crashed.
2. **Upstream Timeout:** The application server is taking too long to respond, exceeding Nginx's `proxy_read_timeout`.
3. **Connection Refused:** Nginx cannot establish a TCP connection to the backend service.
4. **Resource Exhaustion:** The backend service is out of memory or CPU and cannot accept new requests.

## Remediation Steps
1. **Check Nginx Error Logs:** Identify which upstream server is failing.
   `tail -f /var/log/nginx/error.log`
2. **Verify Backend Health:** Check if the backend application process is running.
   `systemctl status backend-service` or `docker ps`
3. **Check Backend Logs:** Look for application errors, memory leaks, or slow queries.
4. **Restart Backend:** If the backend is hung or crashed, restart it.
   `systemctl restart backend-service`
5. **Increase Timeout (Temporary):** If the application is just slow and it is a known heavy query, temporarily increase `proxy_read_timeout` in `nginx.conf` and reload Nginx:
   `nginx -s reload`
