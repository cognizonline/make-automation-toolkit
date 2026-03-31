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

**Decision guide — pick one before building:**

```
Q1: Is the LLM reasoning loop inside Make?
    YES → scenario-embedded agent (ai-local-agent:RunLocalAIAgent)
          deploy with: deployer.deploy_scenario_agent()
          example: src/examples/06_deploy_scenario_agent.py

    NO → the AI client lives outside Make (Claude, Cursor, ChatGPT, etc.)

Q2: Does the external AI need autonomous multi-step reasoning?
    YES → standalone AI Agent (REST API)
          deploy with: deployer.deploy_ai_agent_stack()
          example: src/examples/03_configure_agent.py

    NO → deterministic workflow the AI can trigger

Q3: Is this a production deployment needing access control + audit?
    YES → MCP Toolbox (governed, scoped, logged)
          deploy with: deployer.deploy_mcp_tool() → add to Toolbox in Make UI
          example: src/examples/08_mcp_toolbox_workflow.py

    NO → raw MCP endpoint (development / personal use)
          deploy with: deployer.deploy_mcp_tool()
          example: src/examples/04_setup_mcp.py
```

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
- `"tools": []` sits at the **module root** level alongside `"mapper"` — not inside `"mapper"`

#### Tool input mapping — two observed conventions

**1. Make UI (module tool auto-generated):** uses `{{agent_module_id.param_name}}`

When you add a module tool via the Make canvas, Make generates mapper references using the agent module's own `id`:
```json
"mapper": {
  "key":    "{{94.key}}",
  "upsert": "{{94.upsert}}",
  "data": {
    "risk_level":    "{{94.data.risk_level}}",
    "input_summary": "{{94.data.input_summary}}"
  }
}
```
Where `94` is the `"id"` of the `ai-local-agent:RunLocalAIAgent` module in the scenario blueprint.

**2. SDK / programmatic:** uses `{{parameters.param_name}}`

The `make-automation-toolkit` SDK and the `src/blueprints/ai_local_agent.json` template use a `{{parameters.*}}` namespace:
```json
"mapper": {
  "query": "{{parameters.query}}",
  "to":    "{{parameters.to}}"
}
```
Both forms are valid. Use `{{agent_id.*}}` when writing blueprints by hand or via MCP; use `{{parameters.*}}` when using `deploy_scenario_agent()` from the SDK.

#### `aiHelp` annotations — guide the agent's parameter choices

Inside each tool module's `metadata.restore.expect`, you can add `aiHelp` strings that the agent reads to understand what each parameter means:

```json
"restore": {
  "expect": {
    "key": {
      "extra": { "aiHelp": "The record key — use the execution ID provided in the input." }
    },
    "upsert": {
      "mode": "edit",
      "extra": { "aiHelp": "Set to true to insert the record if it does not already exist." }
    }
  }
}
```

Missing or vague `aiHelp` = agent passes wrong values or skips parameters entirely. Write `aiHelp` strings as if briefing a junior developer: what the field is, what value format is expected, and any default assumption.

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

### MCP Toolboxes — production-grade governed access

The raw MCP endpoint exposes your entire active scenario library. **MCP Toolboxes**
are team-level curated collections with dedicated server URLs, scoped auth keys,
per-tool access control, and invocation audit logs.

| | Raw MCP endpoint | MCP Toolbox |
|---|---|---|
| Scenarios exposed | All active on-demand | Only those you add |
| Server URL | Shared team endpoint | **Unique URL per Toolbox** |
| Auth keys | One team token | **Multiple keys per Toolbox** |
| Access control | All-or-nothing | **Read-only or read-write per tool** |
| Audit log | None | **Every invocation logged** |

**Create:** Make sidebar → MCP Toolboxes → Create toolbox → add scenarios → copy unique URL + key

**Connect Claude Code** (`.claude/settings.json`):
```json
{
  "mcpServers": {
    "make-toolbox": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://<TOOLBOX_URL>/sse"],
      "env": { "MCP_TOKEN": "<TOOLBOX_KEY>" }
    }
  }
}
```

**The single-tool wrapping pattern:**
Instead of exposing each step as a separate tool, wrap the entire workflow in one
scenario and expose that as one tool. The LLM makes one call; Make runs the full
deterministic chain internally.

```
Expose this:  onboard_customer(name, email, company, deal_value)
Not this:     validate_customer + create_contact + create_deal + send_notification
```

Generate one key per AI client — revoke individually without affecting others.
Set read-only for lookup tools; read-write for tools that create, update, or delete.

See full guide: `docs/mcp-toolboxes.md` and `src/examples/08_mcp_toolbox_workflow.py`

### Make a scenario appear as an MCP tool
Three requirements, all must be met:
1. Scheduling: `{"type": "on-demand"}`
2. Active: `client.activate_scenario(scenario_id)`
3. Typed outputs: `client.set_scenario_interface(scenario_id, inputs, outputs)`

```python
scenario_id = deployer.deploy_mcp_tool(blueprint, inputs, outputs, activate=True)
```

### Make Tools vs AI Agents vs MCP Toolboxes

| | Make Tools | MCP Toolbox tool | AI Agent |
|---|---|---|---|
| **Created via** | MCP `tools_create` or REST | Make sidebar + `deploy_mcp_tool()` | REST API only |
| **Structure** | Single module wrapper | Scenario with defined I/O, in a curated Toolbox | LLM + scenario tools |
| **Called from** | MCP clients, agents, scenarios | External AI clients via unique Toolbox URL | API, MCP (standalone), scenario (embedded) |
| **Auth** | Team MCP token | Dedicated Toolbox key (multiple per Toolbox) | API token |
| **Access control** | None | Read-only or read-write per tool | None |
| **Audit log** | None | Yes — every invocation logged | None |
| **LLM reasoning** | None | None (deterministic scenario) | Core feature |
| **Use case** | Simple callable action | Governed, audited workflow exposed to external AI | Multi-step autonomous task |

---

## Make built-in AI modules

Make provides three families of built-in AI apps that require **no external connection
or API key**. They are privacy-focused, beta, and available to all Make plans.

| App | Connection required | Best for |
|---|---|---|
| `make-ai-web-search` | None | Live web search with JSON output |
| `make-ai-extractors` | None | Document, image, and audio extraction |
| `ai-tools` v2 | Make AI Provider (free) or custom OpenAI/Anthropic | Text analysis, translation, summarisation |

---

### `make-ai-web-search` — Web search with structured output

Single module: `generateAResponse`

Performs a live web search and returns a natural-language answer, optionally as
structured JSON. Location-aware: pass city, country, region, and timezone to get
geographically relevant results.

**Credit cost:** 1 credit per 900 tokens + 1 operation credit

**Example — web search in an agent tool:**
```json
{
  "name": "search_web",
  "type": "builtin",
  "connection": null,
  "module": "make-ai-web-search:generateAResponse",
  "parameters": {
    "query": "{{agent.input.search_query}}",
    "parseJson": true,
    "city": "Cape Town",
    "country": "ZA",
    "timezone": "Africa/Johannesburg"
  }
}
```

**Key parameters:**

| Parameter | Type | Notes |
|---|---|---|
| `query` | string | The search question or instruction |
| `parseJson` | boolean | Parse the response as JSON (default false) |
| `city` | string | Optional — improves local result relevance |
| `country` | string | ISO 3166-1 alpha-2 code |
| `region` | string | State/province |
| `timezone` | string | IANA timezone (e.g. `Europe/London`) |

**When to use over HTTP search API calls:**
- No external API key — privacy-preserving, works on all plans
- The model synthesises results into a single answer (not raw snippets)
- Location-aware results without building custom query strings

---

### `make-ai-extractors` — Document, image, and audio extraction

No connection required. All modules are privacy-focused.

#### Document modules

| Module | Input | Output | Credits |
|---|---|---|---|
| `extractADocument` | PDF, DOCX, XLSX, PPTX, HTML, images (up to 2000 pages / 500 MB) | Custom JSON via prompt | 10/page |
| `extractInvoice` | PDF, DOCX, images | Fixed invoice schema | 10/op |
| `extractReceipt` | PDF, DOCX, images | Fixed receipt schema | 10/op |

**`extractInvoice` output schema:**
`invoiceNumber`, `invoiceDate`, `dueDate`, `vendorName`, `vendorAddress`, `buyerName`,
`buyerAddress`, `lineItems[]`, `subtotal`, `taxRate`, `taxAmount`, `total`, `currency`

**`extractADocument` example with custom prompt:**
```json
{
  "module": "make-ai-extractors:extractADocument",
  "parameters": {
    "file": "{{download.data}}",
    "filename": "{{download.name}}",
    "prompt": "Extract: company name, contract start date, contract end date, total value, and payment terms. Return as JSON.",
    "parseJson": true
  }
}
```

#### Image modules

| Module | Purpose | Credits |
|---|---|---|
| `generateCaption` | One-sentence image caption | 2/op |
| `generateCaptionsAdvanced` | Detailed caption for accessibility/alt-text | 2/op |
| `describeImage` | Custom-prompted description (has `temperature` param) | 2/op |
| `extractTextFromAnImage` | OCR — returns all text visible in the image | 2/op |
| `generateImageTags` | Returns keyword tags for search/categorisation | 2/op |
| `detectObjects` | Returns list of objects detected in the image | 2/op |

**`describeImage` example (damage assessment):**
```json
{
  "module": "make-ai-extractors:describeImage",
  "parameters": {
    "file": "{{photo.data}}",
    "filename": "damage.jpg",
    "prompt": "Describe visible damage: affected area, severity (minor/moderate/severe), and any part numbers visible.",
    "temperature": 0.2
  }
}
```

#### Speech modules

| Module | Output | Credits | Limits |
|---|---|---|---|
| `transcribeAudio` | Transcript in original language; optional speaker diarization | 20/min | 2 hrs / 300 MB |
| `translateAudio` | English-only transcript | 20/min | 25 MB |

**`transcribeAudio` example with diarization:**
```json
{
  "module": "make-ai-extractors:transcribeAudio",
  "parameters": {
    "file": "{{call_recording.data}}",
    "filename": "support-call.mp3",
    "language": "en",
    "diarization": true
  }
}
```

---

### `ai-tools` v2 — Text analysis toolkit

**Connection required:** Make AI Provider (free on all plans) or custom OpenAI / Anthropic
key (paid plans only).

| Module | Purpose |
|---|---|
| Simple Text Prompt | General-purpose LLM call |
| Extract information from text | Structured extraction from plain text |
| Categorize text | Assign to one or more categories |
| Translate text | Translate to any target language |
| Identify language | Detect source language |
| Summarize text | Condensed summary |
| Analyze sentiment | Positive / negative / neutral + score |
| Standardize text | Normalise formatting, casing, whitespace |
| Chunk text | Split long text into token-limited segments |

**Primary use in agent architectures:**
Use `ai-tools` modules as **pre-processing tools** before the agent's main LLM step —
e.g. translate an inbound support ticket to English before the agent reads it, or
chunk a long document before passing it to `extractADocument`.

---

### Choosing the right built-in AI module

| Task | Module | Reason |
|---|---|---|
| Web search in an agent tool | `make-ai-web-search:generateAResponse` | Single step, no API key, JSON output |
| Extract fields from a PDF | `make-ai-extractors:extractADocument` | Handles any document format with custom prompt |
| Process inbound invoices | `make-ai-extractors:extractInvoice` | Fixed schema, most reliable for invoices |
| Transcribe a support call | `make-ai-extractors:transcribeAudio` | Diarization support, 2-hour limit |
| Detect language of a message | `ai-tools:IdentifyLanguage` | Lightweight, requires Make AI Provider connection |
| Summarise a long article | `ai-tools:SummarizeText` | Token-efficient, handles chunking |
| Read text in a photo | `make-ai-extractors:extractTextFromAnImage` | OCR, 2 credits, no prompt needed |
| Tag product images | `make-ai-extractors:generateImageTags` | Returns structured tag list for search |


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

> **SDK scope:** `create_hook()` creates the webhook endpoint. The HMAC secret is
> configured in the Make UI (Webhook settings → Custom headers / IP restriction).
> The code below shows how to **verify** an incoming HMAC signature in your
> receiving endpoint — not how to configure Make to send one.

```python
import hmac, hashlib

def verify_make_webhook(payload_bytes: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

# In your Flask/FastAPI handler:
# sig = request.headers.get("X-Make-Signature", "")
# if not verify_make_webhook(request.get_data(), sig, WEBHOOK_SECRET):
#     abort(401)
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

> **Note on `_request()`:** Some operations (org creation, LLM config, analytics)
> are not yet wrapped in named public methods. Use `client._request(method, path, **kwargs)`
> directly for these — it gets the same retry/backoff and auth handling as all public methods.

```python
org  = client.get_organization(org_id)
teams = client.list_teams()         # requires org_id set on client
team  = client.get_team(team_id)

# Create organisation (no public method — use _request directly)
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

Pre-built, annotated system prompts for the six most common agent types are in
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
| `prompts/document_and_media_processing.md` | Extract from PDFs, images, and audio using Make's built-in AI extractors |
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
│   ├── blueprints/                 ← JSON blueprint templates + schema validator
│   └── examples/                   ← runnable Python examples (01–08)
├── prompts/                        ← six system prompt templates with advice
├── docs/                           ← human-readable topic docs (incl. mcp-toolboxes.md)
├── tests/                          ← unit tests (responses-mocked HTTP)
├── .github/workflows/ci.yml        ← lint + test + blueprint validation CI
├── pyproject.toml                  ← pip install . packaging config
└── requirements.txt
```
