# Make AI Agents (Beta)

Make AI Agents are LLM-powered agents that can autonomously call your Make
scenarios as tools in response to natural-language prompts.

## Architecture

```
User message
    │
    ▼
AI Agent (LLM + system prompt)
    │
    ├──▶ Scenario A (auto-run)
    ├──▶ Scenario B (manual approval)
    └──▶ Response to user
```

## Create an agent

```python
agent_config = {
    "name": "Customer Support Agent",
    "systemPrompt": "You are a helpful customer support assistant...",
    "defaultModel": "gpt-4o-mini",
    "llmConfig": {
        "maxTokens": 2000,
        "temperature": 0.7,
        "topP": 1.0
    },
    "invocationConfig": {
        "recursionLimit": 10,
        "timeout": 60000        # ms
    },
    "scenarios": [
        {"makeScenarioId": 123, "approvalMode": "auto-run"},
        {"makeScenarioId": 456, "approvalMode": "manual-approval"}
    ],
    "historyConfig": {
        "iterationsFromHistoryCount": 5
    },
    "outputParserFormat": {
        "type": "make-schema",
        "schema": [
            {"name": "response",     "type": "text", "label": "Agent Response", "required": True},
            {"name": "action_taken", "type": "text", "label": "Action Taken",   "required": False}
        ]
    }
}

agent_id = client.create_agent(agent_config)
```

## Run an agent

```python
result = client.run_agent(
    agent_id=agent_id,
    messages=[
        {"role": "user", "content": "Check order #ORD-999 status"}
    ],
    thread_id="thread-abc-123"   # pass same ID to continue a conversation
)
```

## Configure LLM providers

Teams can have a default AI provider for the mapping assistant and for the
agent toolkit separately:

```python
llm_settings = {
    "aiMappingAccountId": 123,               # connection ID for OpenAI etc.
    "aiMappingModelName": "gpt-4o-mini",
    "aiToolkitAccountId": 456,               # connection ID for Anthropic etc.
    "aiToolkitModelName": "claude-sonnet-4-6"
}
```

## Best practices

| Concern | Guidance |
|---|---|
| System prompt | Be specific about capabilities and limitations |
| Tool selection | Only expose scenarios the agent needs |
| `recursionLimit` | Set to prevent runaway chains (5–15 typical) |
| `timeout` | 30–120 s depending on scenario complexity |
| Sensitive ops | Always use `manual-approval` mode |
| Structured output | Define `outputParserFormat` for consistent downstream parsing |

## See also

- [`src/examples/03_configure_agent.py`](../src/examples/03_configure_agent.py)
- [MCP Integration](mcp-integration.md)
