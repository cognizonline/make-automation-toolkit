# Skill — AI Assistant Context File

`make-automation-skill.md` is a single-file reference document designed to be loaded
into an AI assistant's context window, giving it complete working knowledge of the
Make.com REST API, both AI Agent deployment patterns, MCP integration, and this
toolkit's SDK.

---

## How to load it

### Claude Code (project-level)
Add to `.claude/settings.json` in this repo:
```json
{
  "contextFiles": ["skill/make-automation-skill.md"]
}
```
Or reference it manually at the start of a session:
```
/read skill/make-automation-skill.md
```

### Claude Desktop — Project Knowledge
1. Open your Claude project
2. Project Settings → Add Content → Upload file
3. Upload `skill/make-automation-skill.md`

The skill will be available in every conversation in that project.

### Cursor
Add to `.cursorrules` or reference via `@file`:
```
@skill/make-automation-skill.md
```

### Any MCP-compatible client
Reference as a resource or include in the system prompt context.

---

## What the skill covers

- Make.com REST API v2 — full reference with curl and Python examples
- Both AI Agent deployment patterns (scenario-embedded and standalone)
- The MCP toolset — what it can and cannot do (AI Agent gap documented)
- Make Tools vs AI Agents — when to use each
- Data stores, webhooks, connections, organisations, analytics
- SDK usage (`MakeClient` and `MakeDeployer` from this repo)
- Prompt template library reference
- Error handling, retry logic, rate limiting
- Best practices and security

---

## Difference from `docs/`

| `skill/make-automation-skill.md` | `docs/*.md` |
|---|---|
| One file, loaded whole into AI context | Multiple files, browsed by humans |
| Optimised for AI comprehension and task execution | Optimised for human navigation |
| Complete self-contained reference | Topic-specific deep dives |
| Use when asking an AI to build with Make.com | Use when you need to read the details yourself |
