# Make.com Automation Skill

This skill gives you complete working knowledge to deploy, manage, and orchestrate
Make.com automations programmatically — including the REST API, both AI Agent
deployment patterns, MCP integration, and the make-automation-toolkit SDK.

**Core capabilities:**
- Deploy scenarios from version-controlled JSON blueprints via REST API
- Build and deploy Make AI Agents using both the scenario-embedded and standalone patterns
- Expose scenarios as callable tools via the Make MCP Server
- Manage data stores, webhooks, connections, organisations, and permissions
- Use the `MakeClient` / `MakeDeployer` Python SDK from this repository

---

## Quick start

```bash
# 1. Set environment variables
export MAKE_API_TOKEN="your-api-token"
export MAKE_ZONE="eu1.make.com"   # eu1 | eu2 | us1 | us2
export MAKE_TEAM_ID="123"
export MAKE_ORG_ID="456"          # optional

# 2. Test connectivity
curl -X GET "https://${MAKE_ZONE}/api/v2/ping" \
  -H "Authorization: Token ${MAKE_API_TOKEN}"
# Expected: {"code":"OK"}

# 3. SDK quick start
pip install -r requirements.txt
python src/examples/01_deploy_scenario.py
```

---

## Authentication

### API token
```
Authorization: Token your-api-token
```
Generated at: **Profile > API > Add token**

Common scopes:

| Scope | Operations |
|---|---|
| `scenario:read` | list, get, blueprint |
| `scenario:write` | create, update, delete |
| `scenario:execute` | run on-demand |
| `datastore:read/write` | stores and records |
| `hook:read/write` | webhooks |
| `connection:read` | list connections |
| `team:read` | list teams |

### MCP token
Separate from the API token. Generated at: **Profile > API/MCP access > Add token > MCP Token**

MCP Server URL: `https://<MAKE_ZONE>/mcp/u/<MCP_TOKEN>/sse`
OAuth alternative: `https://mcp.make.com/sse`

### Zone endpoints

| Zone | Base URL |
|---|---|
| EU1 | `https://eu1.make.com/api/v2` |
| EU2 | `https://eu2.make.com/api/v2` |
| US1 | `https://us1.make.com/api/v2` |
| US2 | `https://us2.make.com/api/v2` |
| Celonis EU1 | `https://eu1.make.celonis.com/api/v2` |
| Celonis US1 | `https://us1.make.celonis.com/api/v2` |

---

## SDK — MakeClient and MakeDeployer

This repository provides a typed Python SDK. Always prefer the SDK over raw curl
in Python scripts.

```python
from src.make_client import MakeClient, MakeDeployer

client = MakeClient(
    api_token="your-token",
    zone="eu1.make.com",
    team_id=123,
    org_id=456,        # optional
)
deployer = MakeDeployer(client)
```

The `_request()` method handles:
- Exponential backoff retry on 429 and 5xx
- `Retry-After` header — if present on a 429, sleeps the specified duration
- Automatic JSON serialisation/deserialisation

### Pagination
All list endpoints support pagination via `paginate()`:

```python
# Yield all scenarios without manual offset management
for scenario in client.paginate_scenarios():
    print(scenario["id"], scenario["name"])

# Yield all records from a data store
for record in client.paginate_records(store_id=106):
    print(record["key"], record["data"])

# Generic paginator for any list endpoint
for item in client.paginate("/scenarios", "scenarios", teamId=client.team_id):
    print(item)
```

---

## Scenario management

### Create from blueprint
```python
import json
from pathlib import Path

blueprint = json.loads(Path("src/blueprints/basic_webhook.json").read_text())

scenario_id = client.create_scenario(
    blueprint=blueprint,
    scheduling={"type": "indefinitely", "interval": 900},  # or "on-demand"
    folder_id=None,
)
client.activate_scenario(scenario_id)
```

### Run on-demand
```python
result = client.run_scenario(
    scenario_id=123,
    data={"customer_email": "test@example.com", "order_id": "ORD-001"},
    responsive=True,   # waits up to 40 s for completion
)
print(result["status"], result.get("executionId"))
```

### Set inputs/outputs (required for MCP tools)
```python
client.set_scenario_interface(
    scenario_id=123,
    inputs=[
        {"name": "query", "label": "Search Query", "type": "text", "required": True}
    ],
    outputs=[
        {"name": "results", "label": "Results", "type": "text"},
        {"name": "count",   "label": "Count",   "type": "number"},
    ],
)
```

### Common operations
```python
scenarios  = client.list_scenarios(folder_id=None)
scenario   = client.get_scenario(scenario_id)
blueprint  = client.get_blueprint(scenario_id)
client.update_scenario(scenario_id, new_blueprint)
client.deactivate_scenario(scenario_id)
client.delete_scenario(scenario_id)
logs       = client.get_scenario_logs(scenario_id, status="error")
executions = client.list_executions(scenario_id, limit=50)
```

### Scheduling options
```python
{"type": "on-demand"}                              # manual / MCP / agent trigger
{"type": "indefinitely", "interval": 900}          # every 15 minutes
{"type": "indefinitely", "interval": 3600}         # hourly
{"type": "cron", "cron": "0 9 * * 1-5"}           # 09:00 Mon–Fri
```

---

## Blueprint structure

Blueprints are JSON files in `src/blueprints/`. Validate before deploying:

```bash
python src/validate_blueprint.py src/blueprints/my_blueprint.json
```

Minimal valid blueprint:
```json
{
  "name": "My Scenario",
  "flow": [
    {
      "id": 1,
      "module": "gateway:CustomWebhook",
      "version": 1,
      "parameters": {},
      "mapper": {},
      "metadata": { "designer": { "x": 0, "y": 0 } }
    }
  ],
  "metadata": {
    "version": 1,
    "scenario": {
      "roundtrips": 1,
      "maxErrors": 3,
      "autoCommit": true,
      "autoCommitTriggerLast": true,
      "sequential": false,
      "confidential": false,
      "dataloss": false,
      "dlq": false
    }
  }
}
```

Available blueprints in this repo:
- `src/blueprints/basic_webhook.json` — webhook trigger → HTTP action
- `src/blueprints/ecommerce_order_processing.json` — router + error handler
- `src/blueprints/customer_tracking.json` — webhook → datastore upsert
- `src/blueprints/ai_local_agent.json` — scenario-embedded AI Agent template

---

## Make AI Agents — two distinct patterns

There are two fundamentally different ways to deploy AI Agents in Make. Choose the
right one before building.

### Pattern comparison

| | Scenario-embedded agent | Standalone AI Agent |
|---|---|---|
| **Module** | `ai-local-agent:RunLocalAIAgent` | `POST /api/v2/ai-agents/v1/agents` |
| **Structure** | One scenario, one module, tools nested inside | Separate entity; scenarios-as-tools |
| **Tool definition** | Inline `flow[]` of real Make modules | Existing active on-demand scenarios |
| **Execution trigger** | Scenario scheduling (webhook, interval, on-demand) | API call or MCP Server |
| **LLM orchestration** | Built-in — the module IS the LLM loop | Configured via agent entity |
| **Conversation memory** | `threadId` on the scenario run | `threadId` on the agent run |
| **MCP exposure** | No direct MCP exposure | Yes — if agent is configured for it |
| **Best for** | Self-contained agentic pipelines | AI assistants calling Make as a tool |

**Rule of thumb:** If the agent is the product, use the scenario-embedded pattern.
If the agent is a capability inside another product (Claude, Cursor, a chatbot),
use the standalone pattern.

---

### Pattern 1 — Scenario-embedded agent (`ai-local-agent:RunLocalAIAgent`)

The entire scenario is a **single module**. Tools are nested inside that module as
a `tools[]` array. Each tool has a `name`, `description`, and `flow[]` of real Make
modules. The LLM receives the input and system prompt, then decides which tools to
call, in what order, and how many times — all at runtime.

```
Scenario
  └─ ai-local-agent:RunLocalAIAgent   ← one module, owns the execution loop
       ├─ tool: search_places          ← has its own flow[] of Make modules
       ├─ tool: check_record
       ├─ tool: add_record
       └─ tool: send_email
```

This is the **new** agent pattern introduced in 2025–2026. Unlike the old linear chain
(trigger → module A → module B → output), the agent can loop, branch, and retry based
on intermediate results without any explicit routing configured in the designer.

#### Deploy via SDK
```python
tools = [
    {
        "name": "search_web",
        "description": "Search the web and return structured JSON results.",
        "flow": [
            {
                "id": 10,
                "module": "make-ai-web-search:generateAResponse",
                "version": 1,
                "mapper": {"input": "{{1.input}}", "parseJson": True},
                "parameters": {},
                "metadata": {"designer": {"x": 0, "y": 0}},
            }
        ],
    },
    {
        "name": "send_email",
        "description": "Send a summary email.",
        "flow": [
            {
                "id": 20,
                "module": "google-email:sendAnEmail",
                "version": 4,
                "mapper": {
                    "to": "{{1.to}}",
                    "subject": "{{1.subject}}",
                    "bodyType": "collection",
                    "contents": "{{1.contents}}",
                },
                "parameters": {"__IMTCONN__": YOUR_CONNECTION_ID},
                "metadata": {"designer": {"x": 0, "y": 200}},
            }
        ],
    },
]

scenario_id = deployer.deploy_scenario_agent(
    system_prompt="You are a research assistant...",
    tools=tools,
    model="large",          # "large" | "medium" | "small"
    reasoning_effort="low", # only valid value currently
    recursion_limit=100,    # max LLM steps per execution
    history_count=10,       # conversation turns retained
    output_type="text",     # "text" | "make-schema"
    scheduling={"type": "on-demand"},
)
```

#### Key parameters

| Parameter | Description | Guidance |
|---|---|---|
| `model` | `"large"` / `"medium"` / `"small"` | Use `large` for complex multi-tool reasoning, `medium` for bounded tasks |
| `reasoningEffort` | Always `"low"` | Only valid value currently |
| `recursionLimit` | Max LLM steps | Start at 50, increase only if runs terminate early |
| `iterationsFromHistoryCount` | Conversation turns retained | 0 for stateless, 5–10 for multi-turn |
| `threadId` | Conversation continuity | Same ID = continued conversation; new ID = fresh start |
| `outputType` | `"text"` or `"make-schema"` | Use `"make-schema"` when downstream modules need structured fields |

#### Tool structure rules
- `name`: used by the LLM to call the tool — make it a clear verb-noun: `search_web`, `add_record`
- `description`: the LLM reads this to decide when to call the tool — be specific about what it returns
- `flow[]`: standard Make module objects, same structure as a scenario flow
- Module IDs inside tools should be unique integers (e.g. 10, 20, 30 — not 1, 2, 3 which conflict with the agent module itself)

#### System prompt structure for scenario-embedded agents
See `prompts/` for full templates. Every production agent prompt needs these six sections:
1. **Identity & mission** — who the agent is and what it does
2. **Tool order** — explicit sequence (LLM will deviate without this)
3. **Decision rules** — when to skip, branch, update vs insert, stop early
4. **Data integrity rules** — what to never invent or guess
5. **Output format** — exact shape of the result
6. **Run management** — batch size cap, final action, error behaviour

---

### Pattern 2 — Standalone AI Agent (REST API)

A separate entity created via REST API. Backed by a list of existing active on-demand
scenarios used as tools. Exposed via MCP Server or called directly via API.

```python
agent_config = {
    "name": "Customer Support Agent",
    "systemPrompt": "You are a helpful customer support assistant...",
    "defaultModel": "gpt-4o-mini",
    "llmConfig": {
        "maxTokens": 2000,
        "temperature": 0.7,
        "topP": 1.0,
    },
    "invocationConfig": {
        "recursionLimit": 10,
        "timeout": 60000,       # milliseconds
    },
    "scenarios": [
        {"makeScenarioId": 123, "approvalMode": "auto-run"},
        {"makeScenarioId": 456, "approvalMode": "manual-approval"},
    ],
    "historyConfig": {"iterationsFromHistoryCount": 5},
    "outputParserFormat": {
        "type": "make-schema",
        "schema": [
            {"name": "response",     "type": "text", "label": "Agent Response", "required": True},
            {"name": "action_taken", "type": "text", "label": "Action Taken",   "required": False},
        ],
    },
}

agent_id = deployer.deploy_ai_agent_stack(agent_config)

# Run the agent
result = client.run_agent(
    agent_id=agent_id,
    messages=[{"role": "user", "content": "Check order #ORD-999"}],
    thread_id="thread-abc-123",
)
```

#### Approval modes

| Mode | Behaviour | Use for |
|---|---|---|
| `"auto-run"` | Agent calls the scenario without confirmation | Read-only lookups, safe queries |
| `"manual-approval"` | Pauses for human approval before executing | Writes, sends, charges, deletes |

---

## MCP Server integration

### What the Make MCP Server CAN do
- List active on-demand scenarios as callable tools
- Execute scenarios via `scenario:run` scope
- Manage scenarios, data stores, hooks, connections, and organisations
- Expose standalone AI Agents as tools (if configured)

### What the Make MCP Server CANNOT do ⚠️
- Create or configure AI Agents of either type (no `/ai-agents` endpoint in MCP)
- Manage the `ai-local-agent:RunLocalAIAgent` module or its tools

**The `tools_create/get/update` MCP endpoints are NOT AI Agents.** They create
"Make Tools" — single-module wrappers callable from MCP or agents. Completely
different feature. Use the REST API to create/configure AI Agents.

### Configure MCP client

Claude Desktop / Claude Code (`.claude/settings.json`):
```json
{
  "mcpServers": {
    "make": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://eu1.make.com/mcp/u/YOUR_MCP_TOKEN/sse"]
    }
  }
}
```

OAuth alternative:
```json
{
  "mcpServers": {
    "make": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.make.com/sse"]
    }
  }
}
```

### Make a scenario appear as an MCP tool
Three requirements, all must be met:
1. Scheduling: `{"type": "on-demand"}`
2. Active: `client.activate_scenario(scenario_id)`
3. Typed outputs: `client.set_scenario_interface(scenario_id, inputs, outputs)`

```python
scenario_id = deployer.deploy_mcp_tool(blueprint, inputs, outputs, activate=True)
```

### Make Tools vs AI Agents

| | Make Tools | AI Agents |
|---|---|---|
| **Created via** | MCP `tools_create` or REST | REST API only |
| **Structure** | Single module wrapper | LLM + scenario tools |
| **Called from** | MCP clients, agents, scenarios | API, MCP (standalone), scenario (embedded) |
| **LLM reasoning** | None | Core feature |
| **Use case** | Simple callable action | Multi-step autonomous task |

---

## Data store management

### Full setup
```python
# 1. Create typed structure
structure_id = client.create_data_structure(
    name="Customer Records",
    spec=[
        {"name": "customer_id",    "type": "text",   "label": "Customer ID",    "required": True},
        {"name": "email",          "type": "email",  "label": "Email",          "required": True},
        {"name": "tier",           "type": "text",   "label": "Tier",           "required": False},
        {"name": "lifetime_value", "type": "number", "label": "Lifetime Value", "required": False},
    ],
    strict=True,   # enforce validation on write
)

# 2. Create store
store_id = client.create_data_store("Customer Database", structure_id, max_size_mb=100)
```

### CRUD
```python
# Create
client.add_record(store_id, {"customer_id": "CUST-001", "email": "a@b.com"}, key="CUST-001")

# Read (paginated — never truncates)
for record in client.paginate_records(store_id):
    print(record["key"], record["data"])

# Partial update
client.update_record(store_id, "CUST-001", {"tier": "premium"})

# Full replace
client.replace_record(store_id, "CUST-001", {"customer_id": "CUST-001", "email": "new@b.com", "tier": "enterprise"})

# Delete
client.delete_records(store_id, ["CUST-001", "CUST-002"])
```

### Data types reference

| Type | Use for |
|---|---|
| `text` | Strings, IDs, URLs |
| `email` | Email addresses (validated) |
| `number` | Integers and floats |
| `boolean` | True/false flags |
| `date` | ISO 8601 dates |
| `array` | Lists of values |
| `collection` | Nested objects |

---

## Webhook management

```python
# Create
hook = client.create_hook("Order Events", include_method=True, include_headers=True)
webhook_url = hook["url"]    # send events to this URL

# List
hooks = client.list_hooks()

# Delete
client.delete_hook(hook_id)
```

### Webhook authentication (HMAC)
```python
import hmac, hashlib, json

payload  = {"event": "order.created", "order_id": "12345"}
secret   = "your-webhook-secret"
sig      = hmac.new(secret.encode(), json.dumps(payload).encode(), hashlib.sha256).hexdigest()

requests.post(webhook_url, json=payload, headers={"X-Signature": sig})
```

---

## Connection management

```python
connections = client.list_connections()
connections = client.list_connections(connection_type="google")   # filter by type
is_valid    = client.verify_connection(connection_id)              # returns bool
```

Common connection type strings: `"google"`, `"google-email"`, `"slack"`, `"airtable2"`,
`"openai-gpt-3"`, `"anthropic-claude"`, `"ai-provider"`, `"google-maps"`

---

## Organisation & team management

```python
org  = client.get_organization(org_id)
teams = client.list_teams()         # requires org_id set on client
team  = client.get_team(team_id)

# Create organisation
response = client._request("POST", "/organizations", json={
    "name": "My Company",
    "regionId": 1,
    "timezoneId": 113,
    "countryId": 840,
})
```

### Configure LLM providers for a team
```python
client._request("PATCH", f"/teams/{client.team_id}/llm-configuration", json={
    "aiMappingAccountId":   123,                          # connection ID
    "aiMappingModelName":   "gpt-4o-mini",
    "aiToolkitAccountId":   456,
    "aiToolkitModelName":   "claude-sonnet-4-6",          # or any supported model
    "aiToolkitBuiltinTier": "large",
})
```

---

## Monitoring & analytics

```python
# Execution logs
logs = client.get_scenario_logs(scenario_id, status="error", limit=100)
# status options: "success" | "error" | "warning" | "incomplete"

# Specific execution detail
execution = client.get_execution(execution_id)

# Operations consumption
consumption = client.get_consumption(
    scenario_id=123,
    time_from="2026-01-01T00:00:00Z",
    time_to="2026-12-31T23:59:59Z",
)

# Organisation analytics (Enterprise plan)
analytics = client._request("GET", f"/analytics/{org_id}", params={
    "timeframe[dateFrom]": "2026-01-01",
    "timeframe[dateTo]":   "2026-12-31",
    "teamId[]":            [team_id],
    "sortBy":              "operations",
})
```

---

## Advanced scenario patterns

### Router with filters
```python
{
    "id": 2,
    "module": "builtin:BasicRouter",
    "version": 1,
    "routes": [
        {
            "flow": [...],
            "filter": {
                "name": "Standard Orders",
                "conditions": [[{"a": "{{1.order_type}}", "b": "standard", "o": "text:equal"}]]
            }
        },
        {
            "flow": [...],
            "filter": {
                "name": "Priority Orders",
                "conditions": [[{"a": "{{1.order_type}}", "b": "priority", "o": "text:equal"}]]
            }
        }
    ]
}
```

### Error handler
```python
{
    "id": 5,
    "module": "builtin:ErrorHandler",
    "version": 1,
    "handlers": [
        {
            "flow": [
                {
                    "id": 6,
                    "module": "slack:ActionPostMessage",
                    "version": 1,
                    "mapper": {"channel": "errors", "text": "Failed: {{5.error.message}}"}
                }
            ],
            "errorType": "*"   # catches all error types
        }
    ]
}
```

### Scenario metadata flags

| Flag | Default | When to change |
|---|---|---|
| `autoCommit` | `true` | Set false for transactional scenarios |
| `sequential` | `false` | Set true for order-dependent operations (counters, inventory) |
| `confidential` | `false` | Set true for scenarios handling PII or credentials |
| `maxErrors` | `3` | Increase for flaky external APIs; never set to 0 |
| `dlq` | `false` | Enable Dead Letter Queue for critical data pipelines |

---

## Error handling and retry

### HTTP status codes

| Code | Meaning | Action |
|---|---|---|
| `200` | OK | — |
| `201` | Created | — |
| `400` | Bad request | Fix request parameters |
| `401` | Unauthorised | Check token and scopes |
| `403` | Forbidden | Check scopes and team membership |
| `404` | Not found | Verify resource ID |
| `409` | Conflict | Duplicate name or state conflict |
| `422` | Validation failed | Fix payload structure |
| `429` | Rate limited | Respect `Retry-After` header |
| `500` | Server error | Retry with backoff |

### Retry pattern (built into SDK `_request()`)
```python
# The SDK handles this automatically — for reference:
if resp.status_code == 429:
    wait = int(resp.headers.get("Retry-After", 2 ** attempt))
    time.sleep(wait)
    continue
```

Always read `Retry-After` on 429 — Make's API sends it. Ignoring it causes immediate
re-rate-limiting on the next attempt.

---

## System prompt templates

Pre-built, annotated system prompts for the five most common agent types are in
`prompts/`. Each template includes:
- Advice explaining *why* each section is structured the way it is
- The prompt itself with bracketed placeholders
- Companion tool list (Make modules that pair with this prompt)
- Tuning notes

| Template | Use case |
|---|---|
| `prompts/lead_generation.md` | Discover, qualify, deduplicate business leads |
| `prompts/customer_support.md` | Triage, lookup, respond, escalate |
| `prompts/document_processing.md` | Extract, validate, route structured doc data |
| `prompts/research_summarisation.md` | Multi-source research with citations |
| `prompts/data_enrichment.md` | Fill missing fields without overwriting good data |
| `prompts/_template.md` | Scaffold for new prompts |

See `prompts/README.md` for the full anatomy guide and tuning reference.

---

## Best practices

### Scenario design
- Name describes the action: `"Sync Customer to CRM"` not `"Webhook 1"`
- Always attach a `builtin:ErrorHandler` on production scenarios
- Use `sequential: true` for order-dependent operations (inventory, counters)
- Set `confidential: true` for scenarios handling PII

### Agent design
- Specify explicit tool order in the system prompt — the LLM will deviate without it
- Use `manual-approval` for any scenario that writes data, sends messages, or charges
- Set `recursionLimit` conservatively (50) and increase only when needed
- Use `outputType: "make-schema"` when downstream modules need structured fields
- Cap batch size in the prompt lower than `recursionLimit` allows — partial runs leave inconsistent state

### Security
- Rotate API tokens regularly; use scoped tokens (not master tokens) in automation code
- Protect inbound webhooks with HMAC signatures or API key headers
- Store tokens in environment variables — never in blueprints or source code
- Use `confidential: true` on scenarios that log sensitive data

### Performance
- `roundtrips: 1` unless you need multiple trigger reads
- Use `paginate_scenarios()` / `paginate_records()` — never assume list endpoints return all results
- For bulk datastore operations, batch deletes with `delete_records(store_id, [key1, key2, ...])`
- Monitor `X-RateLimit-*` response headers for approaching limits

### Data store design
- Always set `strict: true` — catches type mismatches at write time, not at query time
- Use natural stable keys (`customer_id`, order number) not UUIDs when possible
- Set `maxSizeMB` conservatively; alert at 80% capacity
- Schedule a nightly cleanup scenario for records past your retention window

---

## Repo structure reference

```
make-automation-toolkit/
├── skill/
│   ├── README.md                   ← how to load this skill
│   └── make-automation-skill.md    ← this file
├── src/
│   ├── make_client.py              ← MakeClient + MakeDeployer SDK
│   ├── validate_blueprint.py       ← blueprint schema validator
│   ├── blueprints/                 ← JSON blueprint templates
│   └── examples/                   ← runnable Python examples (01–06)
├── prompts/                        ← system prompt templates with advice
├── docs/                           ← human-readable topic docs
├── tests/                          ← unit tests (responses-mocked HTTP)
├── .github/workflows/ci.yml        ← lint + test + blueprint validation CI
├── pyproject.toml                  ← pip install . packaging config
└── requirements.txt
```
