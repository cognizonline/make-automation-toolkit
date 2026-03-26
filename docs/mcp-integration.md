# MCP Server Integration

Make.com's MCP (Model Context Protocol) Server lets AI assistants — including
Claude, Cursor, and any MCP-compatible client — discover and call your Make
scenarios as native tools.

## How it works

```
AI Assistant  ──MCP──▶  Make MCP Server  ──▶  Your Scenarios
```

Each active, on-demand scenario with defined inputs/outputs is automatically
exposed as a callable tool. The AI sees the scenario name as the tool name and
the input schema as the argument spec.

## Requirements for a scenario to appear as an MCP tool

1. **Scheduling**: must be `on-demand`
2. **Active**: scenario must be activated
3. **Inputs/Outputs**: must have at least one defined output
4. **MCP token scope**: `scenario:run` (execution) or `scenario:read` (discovery)

## Setup

### 1. Generate an MCP token

**Profile > API/MCP access > Add token > MCP Token**

### 2. Configure your MCP client

**Claude Desktop** (`~/.config/claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "make": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://eu1.make.com/mcp/u/YOUR_MCP_TOKEN/sse"
      ]
    }
  }
}
```

**Claude Code** (`.claude/settings.json`):

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

**OAuth-based (no token management)**:

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

## Deploy a scenario as an MCP tool

```python
from src.make_client import MakeClient, MakeDeployer

client = MakeClient(api_token, zone, team_id)
deployer = MakeDeployer(client)

inputs = [
    {"name": "query", "label": "Search Query", "type": "text", "required": True}
]
outputs = [
    {"name": "results", "label": "Results",     "type": "text"},
    {"name": "count",   "label": "Total Count", "type": "number"},
]

scenario_id = deployer.deploy_mcp_tool(blueprint, inputs, outputs, activate=True)
```

Or use `example 04`:

```bash
python src/examples/04_setup_mcp.py
```

## Tool naming

The scenario **name** becomes the tool name the AI sees. Keep names:

- Descriptive: `"Search Product Catalog"` not `"Scenario 42"`
- Action-oriented: verb + noun
- Under 56 characters (configurable via `maxToolNameLength` 32–160)

## Approval modes

When using scenarios inside an AI Agent, you control whether the agent can
call the tool automatically or must ask for approval:

| Mode | Behaviour |
|---|---|
| `auto-run` | Agent calls the tool without confirmation |
| `manual-approval` | Agent pauses and presents the call for a human to approve |

Use `manual-approval` for any scenario that writes data, sends emails, or
charges money.
