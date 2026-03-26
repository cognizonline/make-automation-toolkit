# Make AI Agents

This document covers both ways to deploy AI Agents in Make.com, how to choose
between them, and the limits of what the Make MCP toolset can do.

---

## 1. Two agent deployment patterns

### Old pattern — linear scenario chain

Before AI Agents existed, "automation" meant a sequence of discrete modules
wired together in a fixed order:

```
Trigger → Module A → Module B → Module C → Output
```

Execution is deterministic: every run follows the same path.  There is no
reasoning layer — the scenario cannot decide to skip a step or repeat one based
on intermediate output.  This pattern is still correct for simple, predictable
workflows.

### New pattern — scenario-embedded agent (`ai-local-agent:RunLocalAIAgent`)

The entire scenario is a **single module**: `ai-local-agent:RunLocalAIAgent`.
Tools (each with their own `flow[]` of real Make modules) are nested **inside**
that one module.  At runtime, the LLM receives the input message and your
system prompt, then decides which tools to call, in what order, and how many
times — all within a single scenario execution.

```
Scenario
  └─ ai-local-agent:RunLocalAIAgent   ← one module, owns the execution loop
       ├─ tool: web_search             ← has its own flow[] of Make modules
       ├─ tool: write_to_datastore
       └─ tool: send_email
```

Key differences from the old pattern:

| | Old linear chain | Scenario-embedded agent |
|---|---|---|
| Execution order | Fixed at design time | LLM decides at runtime |
| Branching | Filters/routers only | Arbitrary tool re-use and chaining |
| LLM involvement | None (unless you add an AI module manually) | Built-in — the whole module IS the LLM loop |
| Scenario complexity | N modules visible in designer | 1 module visible; tools are nested |

### Standalone AI Agent (REST API)

A separate entity created via `POST /api/v2/ai-agents/v1/agents`.  It has its
own LLM config, system prompt, and a list of Make scenarios as callable tools.
You interact with it via `POST /ai-agents/v1/agents/{id}/run`.  It can be
surfaced via the Make MCP Server if configured.

---

## 2. Scenario-embedded agent — `deploy_scenario_agent()`

Use `MakeDeployer.deploy_scenario_agent()` to create a scenario whose sole
module is `ai-local-agent:RunLocalAIAgent`.

```python
from make_client import MakeClient, MakeDeployer

client = MakeClient(
    api_token="YOUR_TOKEN",
    zone="eu1.make.com",
    team_id=123,
)
deployer = MakeDeployer(client)

tools = [
    {
        "name": "search_web",
        # make-ai-web-search requires no external connection or API key.
        # It performs a live web search and returns a synthesised answer.
        # Credit cost: 1 credit per 900 tokens + 1 operation credit.
        "description": "Search the web for current information. Returns a synthesised answer.",
        "flow": [
            {
                "id": 10,
                "module": "make-ai-web-search:generateAResponse",
                "version": 1,
                "mapper": {
                    "query": "{{parameters.query}}",
                    "parseJson": False,
                },
                "parameters": {},
                "metadata": {"designer": {"x": 0, "y": 0}},
            }
        ],
    },
    {
        "name": "send_email",
        "description": "Send an email notification to a recipient.",
        "flow": [
            {
                "id": 20,
                "module": "gmail:ActionSendEmail",
                "version": 1,
                "mapper": {
                    "connectionId": 0,          # replace with real connection ID
                    "to": "{{parameters.to}}",
                    "subject": "{{parameters.subject}}",
                    "content": "{{parameters.body}}",
                },
                "parameters": {"accountId": 0},  # replace with real account ID
                "metadata": {"designer": {"x": 0, "y": 150}},
            }
        ],
    },
]

scenario_id = deployer.deploy_scenario_agent(
    system_prompt="You are a research assistant. Search for information and email summaries on request.",
    tools=tools,
    model="large",           # "large" | "medium" | "small"
    reasoning_effort="low",  # only valid value currently
    recursion_limit=50,      # max LLM steps per execution
    history_count=10,        # conversation turns retained
    output_type="text",      # "text" | "make-schema"
)
print(f"Agent scenario ID: {scenario_id}")
```

### Tool structure

Each entry in `tools` must have:

| Field | Type | Description |
|---|---|---|
| `name` | string | Identifier the LLM uses to call the tool |
| `description` | string | Natural-language description the LLM reads to decide when to call it |
| `flow` | array | Standard Make module objects (same structure as a scenario `flow[]`) |

### Model sizes

| Value | Approximate equivalent |
|---|---|
| `"large"` | Most capable, slowest, highest cost |
| `"medium"` | Balanced |
| `"small"` | Fastest, cheapest, less capable |

### See also

- `src/blueprints/ai_local_agent.json` — a schema-valid JSON template showing this pattern with two tools
- `src/examples/06_deploy_scenario_agent.py` — runnable example

---

## 3. Standalone AI Agent — `deploy_ai_agent_stack()`

Use `MakeDeployer.deploy_ai_agent_stack()` to create a standalone agent entity
via the REST API.  Each scenario listed in `agent_config["scenarios"]` must
already exist and be active.

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
    "historyConfig": {
        "iterationsFromHistoryCount": 5,
    },
    "outputParserFormat": {
        "type": "make-schema",
        "schema": [
            {"name": "response",     "type": "text", "label": "Agent Response", "required": True},
            {"name": "action_taken", "type": "text", "label": "Action Taken",   "required": False},
        ],
    },
}

agent_id = deployer.deploy_ai_agent_stack(agent_config)
```

### Running the agent

```python
result = client.run_agent(
    agent_id=agent_id,
    messages=[{"role": "user", "content": "Check order #ORD-999 status"}],
    thread_id="thread-abc-123",   # same ID continues a conversation
)
```

---

## 4. MCP toolset gap — what the MCP server cannot do

The Make MCP Server exposes tools for scenarios, data stores, hooks, and
connections.  **It has no endpoint to create or configure AI Agents of either
type.**

The tools named `tools_create`, `tools_get`, and `tools_update` in the MCP
server are for **Make Tools** — single-module wrappers that surface one Make
module as an MCP-callable function.  They are an entirely different feature
from AI Agents and cannot be used as a substitute.

Consequence: `create_agent` and `run_agent` (and `deploy_ai_agent_stack`) can
**only** be called via the REST API.  There is no MCP path.

Similarly, `deploy_scenario_agent()` calls `create_scenario` under the hood,
which the MCP server *does* support — but the LLM tooling configuration inside
`ai-local-agent:RunLocalAIAgent` is blueprint-level detail that you provide
yourself; the MCP server does not validate or interpret it.

---

## 5. Choosing between patterns

| Concern | Scenario-embedded agent | Standalone AI Agent |
|---|---|---|
| How it is deployed | `deploy_scenario_agent()` → `create_scenario` | `deploy_ai_agent_stack()` → REST `POST /ai-agents/v1/agents` |
| Trigger | Scenario scheduling (webhook, interval, on-demand) | `POST /ai-agents/v1/agents/{id}/run` or MCP Server |
| Tool definition | Inline `flow[]` inside the scenario blueprint | Existing active scenarios listed by ID |
| Conversation continuity | `threadId` in the module mapper | `threadId` in the run payload |
| MCP Server exposure | Not directly (scenario can be used as an MCP tool, but agent config is not surfaced) | Yes, if the team has MCP Server enabled |
| API access | Create via `POST /scenarios`; run via `POST /scenarios/{id}/run` | Create via `POST /ai-agents/v1/agents`; run via `POST /ai-agents/v1/agents/{id}/run` |
| Best for | Self-contained agents where tools are new flows built alongside the agent | Agents that orchestrate existing, already-deployed scenarios |
| Reasoning model config | `defaultModel`, `reasoningEffort`, `recursionLimit` in blueprint | `llmConfig`, `invocationConfig` in agent config |

---

## 6. Make built-in AI modules as agent tools

Make provides built-in AI modules that work inside a tool `flow[]` with **no
external connection or API key**.  They are the recommended default for web
search and document/media extraction in agent tools.

### `make-ai-web-search:generateAResponse`

```python
{
    "name": "search_web",
    "description": "Search the web for current information on a topic.",
    "flow": [
        {
            "id": 10,
            "module": "make-ai-web-search:generateAResponse",
            "version": 1,
            "mapper": {
                "query": "{{parameters.query}}",
                "parseJson": False,     # set True to get a structured JSON response
                # Optional location parameters for geo-relevant results:
                # "city": "London", "country": "GB", "timezone": "Europe/London",
            },
            "parameters": {},
            "metadata": {"designer": {"x": 0, "y": 0}},
        }
    ],
}
```

**Credit cost:** 1 credit per 900 tokens + 1 operation credit

### `make-ai-extractors:extractInvoice`

```python
{
    "name": "extract_invoice",
    "description": "Extract structured fields from an invoice file (PDF, DOCX, or image).",
    "flow": [
        # Step 1 — download the file
        {
            "id": 10,
            "module": "http:ActionGetFile",
            "version": 3,
            "mapper": {"url": "{{parameters.file_url}}"},
            "parameters": {},
            "metadata": {"designer": {"x": 0, "y": 0}},
        },
        # Step 2 — extract with the built-in extractor (no connection needed)
        {
            "id": 20,
            "module": "make-ai-extractors:extractInvoice",
            "version": 1,
            "mapper": {
                "file": "{{10.data}}",
                "filename": "{{parameters.filename}}",
            },
            "parameters": {},
            "metadata": {"designer": {"x": 0, "y": 150}},
        },
    ],
}
```

**Returns:** `invoiceNumber`, `invoiceDate`, `dueDate`, `vendorName`, `lineItems[]`,
`subtotal`, `taxAmount`, `total`, `currency`

**Credit cost:** 10 credits per operation

### `make-ai-extractors:extractADocument`

For general documents (contracts, reports, forms) where you define the fields:

```python
{
    "id": 20,
    "module": "make-ai-extractors:extractADocument",
    "version": 1,
    "mapper": {
        "file": "{{10.data}}",
        "filename": "{{parameters.filename}}",
        "prompt": "Extract: party names, effective date, termination date, and total contract value. Return as JSON.",
        "parseJson": True,
    },
    "parameters": {},
    "metadata": {"designer": {"x": 0, "y": 150}},
}
```

**Credit cost:** 10 credits per page (up to 2000 pages / 500 MB)

### `make-ai-extractors:transcribeAudio`

```python
{
    "name": "transcribe_call",
    "description": "Transcribe an audio recording. Returns transcript with optional speaker labels.",
    "flow": [
        {
            "id": 10,
            "module": "http:ActionGetFile",
            "version": 3,
            "mapper": {"url": "{{parameters.audio_url}}"},
            "parameters": {},
            "metadata": {"designer": {"x": 0, "y": 0}},
        },
        {
            "id": 20,
            "module": "make-ai-extractors:transcribeAudio",
            "version": 1,
            "mapper": {
                "file": "{{10.data}}",
                "filename": "{{parameters.filename}}",
                "language": "{{parameters.language}}",
                "diarization": True,   # set False for single-speaker content
            },
            "parameters": {},
            "metadata": {"designer": {"x": 0, "y": 150}},
        },
    ],
}
```

**Credit cost:** 20 credits per minute of audio (up to 2 hrs / 300 MB)

### Built-in module quick reference

| Task | Module | Credits | Notes |
|---|---|---|---|
| Web search | `make-ai-web-search:generateAResponse` | ~1/search | No API key; `parseJson` for structured output |
| Invoice extraction | `make-ai-extractors:extractInvoice` | 10/op | Fixed schema; best for known invoice formats |
| General document | `make-ai-extractors:extractADocument` | 10/page | Custom prompt; `parseJson: true` recommended |
| Image description | `make-ai-extractors:describeImage` | 2/op | Has `temperature` param; use low (0.1–0.3) for facts |
| OCR | `make-ai-extractors:extractTextFromAnImage` | 2/op | Returns raw text; no prompt needed |
| Image tags | `make-ai-extractors:generateImageTags` | 2/op | Structured tag list for search/categorisation |
| Audio transcription | `make-ai-extractors:transcribeAudio` | 20/min | `diarization: true` for speaker attribution |
| Audio → English | `make-ai-extractors:translateAudio` | 20/min | Max 25 MB; always outputs English |

---

## See also

- [`src/examples/03_configure_agent.py`](../src/examples/03_configure_agent.py) — standalone agent example
- [`src/examples/06_deploy_scenario_agent.py`](../src/examples/06_deploy_scenario_agent.py) — scenario-embedded agent with placeholder tools
- [`src/examples/07_builtin_ai_tools.py`](../src/examples/07_builtin_ai_tools.py) — agent using Make built-in AI modules (no API keys)
- [`src/blueprints/ai_local_agent.json`](../src/blueprints/ai_local_agent.json) — blueprint template
- [MCP Integration](mcp-integration.md)
- [Prompt Templates](../prompts/README.md) — includes `document_and_media_processing.md` for extractor-based agents
