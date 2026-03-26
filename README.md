# Make Automation Toolkit

> A professional Python SDK and reference guide for deploying, managing, and orchestrating Make.com automations — including REST API, MCP Server, and AI Agents.

[![CI](https://github.com/cognizonline/make-automation-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/cognizonline/make-automation-toolkit/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org)
[![Make.com](https://img.shields.io/badge/Make.com-API%20v2-6200ea.svg)](https://make.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Demo

https://github.com/cognizonline/make-automation-toolkit/assets/make_skills.mp4

---

## What this is

Make.com is a no-code automation platform. This toolkit exposes its full power
as **code** — letting engineers:

- Deploy production scenarios from version-controlled JSON blueprints
- Manage data stores, webhooks, and connections via a typed Python client
- Configure AI Agents with LLM providers and tool approval policies
- Expose scenarios as callable tools to any MCP-compatible AI assistant

---

## Features

| Capability | Description |
|---|---|
| **Scenario SDK** | Create, update, activate, run, and monitor scenarios programmatically |
| **Blueprint system** | Version-controlled JSON blueprints for reproducible deployments |
| **Data stores** | Full CRUD API for typed key-value storage with schema validation |
| **Webhooks** | Create and manage inbound webhook triggers with HMAC auth |
| **AI Agents** | Deploy LLM agents that call your scenarios as tools |
| **MCP integration** | Expose on-demand scenarios to Claude, Cursor, and any MCP client |
| **Retry logic** | Exponential backoff with rate-limit awareness baked in |
| **CI pipeline** | GitHub Actions validates blueprints and lints on every push |

---

## Repository structure

```
make-automation-toolkit/
├── src/
│   ├── make_client.py          # MakeClient + MakeDeployer SDK
│   ├── blueprints/
│   │   ├── basic_webhook.json
│   │   ├── ecommerce_order_processing.json
│   │   └── customer_tracking.json
│   └── examples/
│       ├── 01_deploy_scenario.py
│       ├── 02_manage_data_store.py
│       ├── 03_configure_agent.py
│       ├── 04_setup_mcp.py
│       └── 05_full_deployment.py
├── prompts/
│   ├── README.md
│   ├── lead_generation.md
│   ├── customer_support.md
│   ├── document_processing.md
│   ├── research_summarisation.md
│   ├── data_enrichment.md
│   └── _template.md
├── docs/
│   ├── quickstart.md
│   ├── authentication.md
│   ├── mcp-integration.md
│   ├── ai-agents.md
│   └── best-practices.md
├── assets/
│   └── make_skills.mp4
├── .github/workflows/ci.yml
├── requirements.txt
└── README.md
```

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/cognizonline/make-automation-toolkit.git
cd make-automation-toolkit
pip install -r requirements.txt

# 2. Set credentials
export MAKE_API_TOKEN="your-token"
export MAKE_ZONE="eu1.make.com"
export MAKE_TEAM_ID="123"

# 3. Run any example
python src/examples/01_deploy_scenario.py
```

See [docs/quickstart.md](docs/quickstart.md) for full setup.

---

## SDK usage

### Client

```python
from src.make_client import MakeClient

client = MakeClient(
    api_token="your-token",
    zone="eu1.make.com",
    team_id=123,
)

# Scenarios
scenarios  = client.list_scenarios()
scenario_id = client.create_scenario(blueprint, scheduling={"type": "on-demand"})
client.activate_scenario(scenario_id)
result = client.run_scenario(scenario_id, data={"key": "value"})

# Data stores
structure_id = client.create_data_structure("Orders", spec)
store_id     = client.create_data_store("Order Store", structure_id)
client.add_record(store_id, {"order_id": "ORD-001", "status": "pending"})
records = client.list_records(store_id)

# Webhooks
hook = client.create_hook("Inbound Events")
print(hook["url"])  # send events here

# AI Agents
agent_id = client.create_agent(config)
reply    = client.run_agent(agent_id, messages=[{"role": "user", "content": "..."}])
```

### High-level deployer

```python
from src.make_client import MakeClient, MakeDeployer

deployer = MakeDeployer(client)

# Deploy a scenario as an MCP tool in one call
scenario_id = deployer.deploy_mcp_tool(blueprint, inputs, outputs, activate=True)

# Deploy a scenario + data store together
result = deployer.deploy_with_datastore(blueprint, "My Store", structure_spec)
```

---

## Blueprints

Blueprints are plain JSON files under `src/blueprints/`. Each blueprint
describes the full scenario flow including modules, mappers, filters, and
error handlers.

```json
{
  "name": "Basic Webhook Trigger",
  "flow": [
    { "id": 1, "module": "gateway:CustomWebhook", ... },
    { "id": 2, "module": "http:ActionSendData",   ... }
  ],
  "metadata": {
    "version": 1,
    "scenario": {
      "roundtrips": 1,
      "maxErrors": 3,
      "autoCommit": true,
      ...
    }
  }
}
```

Blueprints are validated in CI on every push.

---

## MCP integration

Expose any Make scenario as a tool callable by Claude, Cursor, or any MCP
client. Three requirements: on-demand scheduling, active, typed I/O.

```python
scenario_id = deployer.deploy_mcp_tool(blueprint, inputs, outputs)
```

Then add to your Claude config:

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

See [docs/mcp-integration.md](docs/mcp-integration.md) for the full guide.

---

## Documentation

| Doc | Contents |
|---|---|
| [Quick Start](docs/quickstart.md) | Installation, env vars, first run |
| [Authentication](docs/authentication.md) | Token types, scopes, zones |
| [MCP Integration](docs/mcp-integration.md) | Expose scenarios as AI tools |
| [AI Agents](docs/ai-agents.md) | LLM agents, approval modes, output schemas |
| [Best Practices](docs/best-practices.md) | Security, performance, monitoring |

---

## Error handling & retry

All SDK methods include built-in exponential backoff for `429 Too Many Requests`
and transient `5xx` errors:

```python
# Configurable per-call
result = client._request("GET", "/scenarios", max_retries=5)
```

Common status codes and their meaning: [docs/best-practices.md](docs/best-practices.md).

---

## License

MIT — see [LICENSE](LICENSE).

---

## Acknowledgements

Built on top of the [Make.com REST API v2](https://www.make.com/en/api-documentation)
and the [Make MCP Server](https://www.make.com/en/integrations/mcp).
