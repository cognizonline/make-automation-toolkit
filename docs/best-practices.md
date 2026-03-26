# Best Practices

## Scenario design

- **Meaningful names** — name describes the action, not the trigger: `"Sync Customer to CRM"` not `"Webhook Scenario 1"`
- **Error handlers** — always attach a `builtin:ErrorHandler` on critical paths; alert via Slack or email
- **Filters on routers** — use `builtin:BasicRouter` + filters instead of multiple separate scenarios
- **Validate at the boundary** — check required fields in the first module; fail fast with a clear error message
- **Scheduling** — use `on-demand` for AI/MCP tools, `indefinitely` with a sensible interval for background jobs

## Performance

| Setting | Recommendation |
|---|---|
| `roundtrips` | Set to `1` unless you need multiple trigger reads |
| `sequential` | Enable for order-dependent ops (inventory updates, counters) |
| `maxErrors` | `3`–`5` is typically right; avoid `0` (unlimited) |
| Payload size | Keep data flowing between modules small; fetch only needed fields |
| Pagination | Always use `limit`/`offset` when listing records from data stores |

## Security

- **Token rotation** — rotate API tokens on a schedule (monthly or per-deployment)
- **Scoped tokens** — create a dedicated token per automation with minimal required scopes
- **Confidential flag** — set `"confidential": true` on scenarios that handle PII or credentials
- **Webhook auth** — protect inbound webhooks with an API key or HMAC signature
- **Secrets** — never hard-code tokens in blueprints; use Make's connection system

## MCP & AI Agent integration

- **Clear I/O schemas** — well-named inputs become the tool's parameter docs the LLM reads
- **Approval mode** — default to `manual-approval`; only move to `auto-run` after the scenario is battle-tested
- **Rate limiting** — implement throttling in scenarios exposed publicly via MCP
- **Structured errors** — return `{"error": "...", "code": "..."}` from outputs so agents can handle failures gracefully

## Data store management

- **Strict schemas** — always set `"strict": true` to catch type mismatches at write time
- **Meaningful keys** — use natural, stable keys (`customer_id`, `order_number`) not UUIDs when possible
- **Monitor size** — set `maxSizeMB` conservatively; alert when nearing 80 % capacity
- **Cleanup jobs** — schedule a nightly scenario to purge records older than your retention window
- **Periodic exports** — export critical data stores to external storage (S3, Google Sheets) for backup

## Monitoring

- Poll execution logs for `"error"` status after deployments
- Use `consumptions` endpoint to track operation usage against plan limits
- Set up a Slack/email error handler on every production scenario
- Review `X-RateLimit-*` response headers to stay within API limits
