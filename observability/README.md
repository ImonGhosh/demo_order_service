# Observability Setup

This folder contains the Grafana Alloy configuration for shipping local demo order service logs to Grafana Cloud Loki.

## Files

- `alloy/demo-order-service.alloy`: Alloy pipeline for tailing the backend JSON log file and writing to Grafana Cloud Loki.
- `alloy/.env.example`: Safe placeholder values for required environment variables.
- `alloy/run-alloy.ps1`: PowerShell runner that loads `alloy/.env` and starts Alloy.

## One-Time Setup

Create a local Alloy env file from the example:

```powershell
Copy-Item .\observability\alloy\.env.example .\observability\alloy\.env
```

Edit this file with your real Grafana Cloud Loki values:

```text
observability/alloy/.env
```

Expected keys:

```env
GRAFANA_LOKI_URL=https://logs-prod-000.grafana.net/loki/api/v1/push
GRAFANA_LOKI_USERNAME=000000
GRAFANA_LOKI_TOKEN=glc_xxx
DEMO_ORDER_SERVICE_LOG_PATH=C:/IMON/Masters/Self-Learning/ai-ops-incident-automation/demo_order_service/backend/logs/demo-order-service.log
```

The real `.env` file is ignored by git. Do not commit real Grafana credentials.

Validate that the local `.env` file can be loaded:

```powershell
.\observability\alloy\run-alloy.ps1 -CheckOnly
```

This prints only whether required variables were loaded. It does not print secret values.

## Run The Pipeline

Use three terminals.

### Terminal 1: Start FastAPI

```powershell
cd C:\IMON\Masters\Self-Learning\ai-ops-incident-automation\demo_order_service\backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

The backend writes structured JSON logs to stdout and to:

```text
demo_order_service/backend/logs/demo-order-service.log
```

Check local file logging:

```powershell
Get-Content .\logs\demo-order-service.log -Tail 5
```

### Terminal 2: Start Alloy

Run Alloy through the repo script so values are loaded from `observability/alloy/.env`:

```powershell
cd C:\IMON\Masters\Self-Learning\ai-ops-incident-automation\demo_order_service
.\observability\alloy\run-alloy.ps1
```

Keep Alloy running while you generate traffic.

### Terminal 3: Generate Logs

Run a finite verification burst:

```powershell
python scripts\generate_traffic.py --base-url http://127.0.0.1:8000 --requests-per-minute 60 --error-rate 0.3 --duration-seconds 120
```

Run continuous log generation:

```powershell
python scripts\generate_traffic.py --base-url http://127.0.0.1:8000 --requests-per-minute 30 --error-rate 0.25
```

The continuous command keeps running until you stop it with `Ctrl+C`.

### Optional Terminal 4: Run The Demo UI

If manual testing is useful, run the React/Vite demo UI:

```powershell
cd C:\IMON\Masters\Self-Learning\ai-ops-incident-automation\demo_order_service\frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Keep the API field set to:

```text
/api
```

Use the normal-flow buttons to create `INFO` logs, such as user creation, product listing, order creation, and payment simulation. Use the error-injection buttons to manually create `ERROR` logs for categories such as payment timeout, database slow query, runtime exception, and background job failure.

## Check Logs In Grafana Cloud

Open your Grafana Cloud stack in the browser.

Go to:

```text
Left sidebar -> Explore
```

Then:

1. Select the Loki data source (grafanacloud-jumboanemone3581-logs) from the data source dropdown.
2. Set the time range to `Last 15 minutes`.
3. Go to code mode, then run the queries below and run "Live Stream your logs"

If nothing appears, open the label browser in Explore and check whether labels such as `service`, `environment`, `app`, `level`, or `error_category` are visible.

Use these LogQL queries in Grafana Explore:

```logql
{service="demo-order-service", environment="local"}
```

```logql
{service="demo-order-service", environment="local", level="ERROR"}
```

```logql
{service="demo-order-service", environment="local", error_category!="", level="ERROR"}
```

```logql
{service="demo-order-service", environment="local", error_category="payment_timeout"}
```

For live verification, use the `Live` option in Grafana Explore while clicking UI buttons or running the traffic generator.

## Troubleshooting

If local logs exist but Grafana shows no logs:

- Confirm Alloy is still running.
- Confirm `.\observability\alloy\run-alloy.ps1 -CheckOnly` passes.
- Confirm `DEMO_ORDER_SERVICE_LOG_PATH` points to the exact local log file.
- Check the Alloy terminal for authentication, permission, or HTTP errors.
- Confirm the Grafana Cloud token has Loki write permission.
- Confirm Explore is using the correct Loki data source and a recent time range.

## Notes

The Alloy config intentionally keeps high-cardinality values such as `request_id`, `trace_id`, `user_id`, and `order_id` inside the JSON log body instead of promoting them to Loki labels.
