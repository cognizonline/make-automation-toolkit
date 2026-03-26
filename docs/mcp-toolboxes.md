# MCP Toolboxes

MCP Toolboxes are team-level curated MCP servers you create inside Make.
Each Toolbox exposes a specific subset of your scenarios as callable tools
to external AI clients — with its own server URL, dedicated auth keys,
per-tool access control, and a centralized audit log.

They are the production-grade alternative to connecting an AI client directly
to the raw Make MCP Server endpoint.

---

## The problem with raw MCP connections

Connecting an AI client directly to `https://eu1.make.com/mcp/u/TOKEN/sse`
exposes your entire scenario library:

- **No scope control** — the AI can call any active on-demand scenario
- **Token waste** — the LLM reads every tool spec to find what it needs
- **Hallucination risk** — multi-step workflows exposed as separate tools force
  the LLM to infer the correct call sequence
- **One key controls everything** — revoke it and every client loses access

MCP Toolboxes fix all four problems.

---

## How Toolboxes differ from the raw MCP endpoint

| | Raw MCP endpoint | MCP Toolbox |
|---|---|---|
| Scenarios exposed | All active on-demand scenarios | Only those you explicitly add |
| Server URL | Shared team endpoint | **Unique URL per Toolbox** |
| Auth keys | One team token | **Multiple keys per Toolbox** |
| Access control | All-or-nothing | **Read-only or read-write per tool** |
| Audit log | None | **Centralized invocation log** |
| UI | API only | Make sidebar dashboard |
| Revoking access | Affects all clients | Revoke one key, others unaffected |

---

## Setup

### 1. Build and activate your scenario(s)

Each tool in a Toolbox is backed by one Make scenario. The scenario must be:
- **Active**
- **On-demand** scheduling (`{"type": "on-demand"}`)
- **Has defined inputs/outputs** (so the AI knows the tool's argument schema)

Deploy via the SDK:

```python
from make_client import MakeClient, MakeDeployer

client = MakeClient(api_token=API_TOKEN, zone=ZONE, team_id=TEAM_ID)
deployer = MakeDeployer(client)

scenario_id = deployer.deploy_mcp_tool(
    blueprint=YOUR_BLUEPRINT,
    inputs=[
        {"name": "customer_email", "label": "Customer email", "type": "email", "required": True},
    ],
    outputs=[
        {"name": "status", "label": "Result status", "type": "text"},
    ],
    activate=True,
)
```

Or see [`src/examples/08_mcp_toolbox_workflow.py`](../src/examples/08_mcp_toolbox_workflow.py)
for a complete example.

### 2. Create the Toolbox in Make

1. **Left sidebar → MCP Toolboxes → Create toolbox**
2. Name the Toolbox (e.g. `"CRM Tools — Sales Team"`)
3. Add your active on-demand scenarios as tools
4. For each tool, set **read-only** or **read-write** (see Access control below)
5. Click **Create**

### 3. Save the access key

Make shows the key once — copy and store it securely.
If you lose it, generate a new key; the old one cannot be recovered.

### 4. Copy the server URL

Close the key dialog. The Toolbox server URL is displayed under **MCP Server URL**.
Each Toolbox has a unique URL — this is what you give to the AI client.

### 5. Connect your AI client

**Claude Code** (`.claude/settings.json`):

```json
{
  "mcpServers": {
    "make-sales": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://<TOOLBOX_URL>/sse"],
      "env": {
        "MCP_TOKEN": "<TOOLBOX_KEY>"
      }
    }
  }
}
```

**Claude Desktop** (`~/.config/claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "make-sales": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://<TOOLBOX_URL>/sse", "--header", "Authorization: Bearer <TOOLBOX_KEY>"]
    }
  }
}
```

**Cursor** (`.cursorrules` or MCP settings):

```json
{
  "mcpServers": {
    "make-sales": {
      "url": "https://<TOOLBOX_URL>/sse",
      "headers": { "Authorization": "Bearer <TOOLBOX_KEY>" }
    }
  }
}
```

---

## Access control

### Read-only vs read-write

Set this per tool when adding it to the Toolbox:

| Setting | Use for |
|---|---|
| **Read-only** | Search, lookup, list, fetch — tools that never modify data |
| **Read-write** | Create, update, delete, send — tools that write to external systems |

Separate read-only and read-write tools into different Toolboxes when you need
to give a client read access without write access.

### Multiple keys per Toolbox

Generate one key per AI client or team:

```
Toolbox: "CRM Tools"
  ├── Key A  →  Claude (Sales team)
  ├── Key B  →  Cursor (Engineering)
  └── Key C  →  ChatGPT (Marketing)
```

Revoke Key B when the engineering project ends. Keys A and C are unaffected.
The scenario itself is never touched.

---

## The single-tool wrapping pattern

The most important design principle for MCP Toolboxes:

> **Wrap a complete workflow into a single tool — don't expose each step separately.**

### Wrong: exposing every step

```
Tools exposed:
  validate_customer(email)
  create_crm_contact(name, email, company)
  create_crm_deal(contact_id, value)
  send_slack_notification(deal_id)
```

The LLM must call all four in the right order. It can call them in the wrong
order, skip one, or hallucinate arguments between calls.

### Right: wrapping the workflow

```
Tools exposed:
  onboard_customer(name, email, company, deal_value)
```

Make executes the full 4-step sequence internally, deterministically.
The LLM makes one call. Business logic lives in Make.

### When to expose separate steps

Expose steps individually only when the AI legitimately needs to:
- Look up a value before deciding whether to write it
- Choose between multiple write operations based on lookup results
- Read data for the user without writing anything

In that case, expose the lookup as **read-only** and the write as **read-write**,
and document the correct call order in each tool's scenario name and description.

---

## Use cases

### Governed AI assistant for a team

Create one Toolbox per team (Sales, Support, Finance). Each Toolbox exposes
only the workflows that team's AI tools should be able to trigger.
Use separate keys for each AI client within the team.

### Multi-account routing

A single Toolbox can route actions to different accounts (e.g. different
Slack workspaces, Salesforce orgs) by having separate scenarios per account
— all exposed under logical tool names. The AI calls `notify_us_team` vs
`notify_eu_team` without knowing anything about the underlying connections.

### Testing sandbox

Expose a scenario as a Toolbox tool and use Claude or Cursor as a live test
harness. Call the tool directly from your IDE, inspect the Make execution log,
iterate on the scenario. Faster than manually triggering webhooks and reading
raw JSON responses.

```
Developer workflow:
  1. Edit scenario in Make designer
  2. In Cursor: call the MCP tool with test data
  3. Check the Toolbox audit log for the call
  4. Check the Make execution log for the full trace
  5. Repeat
```

### Cross-client isolation

Separate AI clients that need different tool sets:
```
Toolbox: "Customer Ops"    → Claude (support agents)
Toolbox: "Finance Ops"     → ChatGPT (finance team)
Toolbox: "Dev Tools"       → Cursor (engineering)
```

Each client sees only its Toolbox's tools. Credentials for each service
are managed by Make, not shared with any client.

---

## Audit log

Every tool invocation is logged in the Toolbox dashboard:
- Which tool was called
- What parameters were passed
- When it was called
- Which key was used (which client)

This is the primary compliance and debugging tool for governed AI deployments.
Check the audit log first when a client reports unexpected behaviour.

---

## Naming conventions for Toolbox tools

The scenario name becomes the tool name the AI sees. Follow these rules:

| Rule | Example |
|---|---|
| Verb + noun | `"Onboard Customer"` not `"Customer Onboarding"` |
| Describe the outcome | `"Send Invoice"` not `"Invoice Module"` |
| Be specific about scope | `"Search EU Contacts"` not `"Search"` |
| Include read/write signal | `"Fetch Order Status"` (read) vs `"Cancel Order"` (write) |
| Under 56 characters | Truncated names confuse the LLM |

---

## Toolboxes vs other MCP patterns

| Pattern | When to use |
|---|---|
| **MCP Toolbox** | Production: governed, audited, scoped access for external AI clients |
| **Raw MCP endpoint** | Development/prototyping: full scenario access for your own use |
| **Standalone AI Agent via MCP** | When the agent itself should be the MCP tool (agent-as-tool pattern) |
| **Scenario-embedded agent** | When the LLM reasoning loop lives inside Make, not in the external client |

---

## See also

- [`src/examples/04_setup_mcp.py`](../src/examples/04_setup_mcp.py) — deploy a single MCP tool scenario
- [`src/examples/08_mcp_toolbox_workflow.py`](../src/examples/08_mcp_toolbox_workflow.py) — full Toolbox pattern with multi-step scenario
- [`docs/mcp-integration.md`](mcp-integration.md) — raw MCP endpoint setup
- [`docs/ai-agents.md`](ai-agents.md) — agent deployment patterns
