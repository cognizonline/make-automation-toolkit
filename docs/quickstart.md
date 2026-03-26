# Quick Start

Get up and running with the Make Automation Toolkit in under 5 minutes.

## Prerequisites

| Requirement | Notes |
|---|---|
| Make.com account | Paid plan required for API access |
| Python 3.10+ | |
| API Token | Profile > API > Add token |
| Zone | Your Make zone: `eu1`, `eu2`, `us1`, `us2` |
| Team ID | Retrieved via `GET /api/v2/teams` |

## Installation

```bash
git clone https://github.com/cognizonline/make-automation-toolkit.git
cd make-automation-toolkit
pip install -r requirements.txt
```

## Configure environment

```bash
export MAKE_API_TOKEN="your-api-token"
export MAKE_ZONE="eu1.make.com"
export MAKE_TEAM_ID="123"
export MAKE_ORG_ID="456"         # optional
export MAKE_MCP_TOKEN="mcp-token" # only for MCP examples
```

Or create a `.env` file (never commit this):

```
MAKE_API_TOKEN=your-api-token
MAKE_ZONE=eu1.make.com
MAKE_TEAM_ID=123
```

## Test connectivity

```bash
curl -X GET "https://${MAKE_ZONE}/api/v2/ping" \
  -H "Authorization: Token ${MAKE_API_TOKEN}"
```

Expected response: `{"code": "OK"}`

## Run your first example

```bash
python src/examples/01_deploy_scenario.py
```

## Python SDK usage

```python
from src.make_client import MakeClient

client = MakeClient(
    api_token="your-token",
    zone="eu1.make.com",
    team_id=123,
)

# List all scenarios
scenarios = client.list_scenarios()
for s in scenarios:
    print(s["id"], s["name"])
```

## Next steps

- [Authentication](authentication.md) — token scopes and zones
- [Scenarios](scenarios.md) — deploy, configure, run
- [MCP Integration](mcp-integration.md) — expose scenarios as AI tools
- [AI Agents](ai-agents.md) — build agents with LLM providers
- [Data Stores](data-stores.md) — structured key-value storage
