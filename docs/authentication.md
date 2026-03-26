# Authentication & Authorization

## API Token

Generate from **Profile > API > Add token**. Tokens are scoped — request only what you need.

### Common scopes

| Scope | Operations |
|---|---|
| `scenario:read` | List, get, get blueprint |
| `scenario:write` | Create, update, delete |
| `scenario:execute` | Run on-demand |
| `datastore:read` | List stores and records |
| `datastore:write` | Create stores, CRUD records |
| `hook:read` | List webhooks |
| `hook:write` | Create, delete webhooks |
| `connection:read` | List connections |
| `team:read` | List teams |
| `organization:read` | Get org details |

### Request header

```http
Authorization: Token your-api-token-here
```

## MCP Token

Used exclusively for Make MCP Server access. Generated separately:

**Profile > API/MCP access > Add token > MCP Token**

### MCP Server URL

```
https://<MAKE_ZONE>/mcp/u/<MCP_TOKEN>/sse
```

Or with OAuth:

```
https://mcp.make.com/sse
```

## Zone Endpoints

| Zone | Base URL |
|---|---|
| EU1 | `https://eu1.make.com/api/v2` |
| EU2 | `https://eu2.make.com/api/v2` |
| US1 | `https://us1.make.com/api/v2` |
| US2 | `https://us2.make.com/api/v2` |
| Celonis EU1 | `https://eu1.make.celonis.com/api/v2` |
| Celonis US1 | `https://us1.make.celonis.com/api/v2` |

## Security recommendations

- Rotate tokens regularly
- Use scoped tokens — never a master token in automation code
- Store tokens in environment variables or a secrets manager (never in source code)
- Enable `confidential: true` on scenarios that handle PII
- Use HMAC signatures on inbound webhooks
