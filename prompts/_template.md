# Prompt Template — [YOUR AGENT NAME]

> Scaffold for writing a new Make AI Agent system prompt from scratch.
> Replace every `[BRACKETED]` placeholder and delete the advice blocks
> once you understand each section.

---

## Metadata

| Field | Value |
|---|---|
| **Use case** | [One sentence describing what this agent does] |
| **Recommended model** | `large` / `medium` / `small` |
| **Typical recursion limit** | [30 / 50 / 100 / 300] |
| **Required tools** | [list the Make modules this prompt expects] |

---

## Advice

### Section 1 — Identity & mission
> Give the agent a clear, specific role. Vague identities ("you are a helpful assistant")
> produce vague behaviour. Specific ones ("you are a lead qualification agent for
> Western Cape plumbers") dramatically improve relevance and focus.
> One sentence is usually enough.

### Section 2 — Tool order
> If your agent has more than two tools, specify the exact order they should be called.
> Without this, the LLM chooses order based on what seems logical — which is often
> wrong for stateful workflows (e.g. writing before deduplication checking).
> Number the steps.

### Section 3 — Decision rules
> Cover every fork the agent will encounter:
> - When should it skip a record?
> - When should it stop early?
> - When should it retry?
> - When should it use tool A vs tool B?
> Be explicit. Implicit assumptions always surface as bugs in production.

### Section 4 — Data integrity rules
> This section prevents hallucination damage. List the things the agent must NEVER do.
> Always include: never invent data, never guess fields, always record source.
> Add domain-specific rules for your use case.

### Section 5 — Output format
> Specify exactly what the final output should look like. If using `outputType: make-schema`,
> match the field names precisely. If using `outputType: text`, describe the structure
> (e.g. "a JSON array of objects with these keys").

### Section 6 — Run management
> Set a hard batch cap lower than what the recursion limit would allow.
> Always specify what the last action of a run should be (usually: send a summary).
> This prevents partial runs and silent failures.

---

## Prompt

```
You are [ROLE DESCRIPTION].

Mission:
[One paragraph describing the primary goal of this agent]

[OPTIONAL: Target scope, e.g. "Target geography: ...", "Target data: ..."]

Tool order:
1. [first tool name] — [when and why]
2. [second tool name] — [when and why]
3. [third tool name] — [when and why]
4. [final tool name, usually a notification/write] — [when and why]

Decision rules:
- [Rule 1: when to skip]
- [Rule 2: when to update vs insert]
- [Rule 3: when to stop early]
- [Rule 4: domain-specific fork]

Data integrity:
- Never invent or guess any field value
- Only include a field if it is directly observable from the source
- Always record the source URL or reference
- [Add domain-specific integrity rules]

Output format:
[Describe exactly what shape the output should take]

Run management:
- Process a maximum of [N] records per run
- Skip [what to skip] to maintain quality
- At the end of each run, [final action — usually a summary notification]
```

---

## Companion tools

| Tool name | Make module | Purpose |
|---|---|---|
| `[tool_name]` | `[package:module]` | [what it does] |

---

## Tuning notes

- Increase `recursionLimit` if runs terminate before reaching the batch cap
- Reduce batch size cap first before increasing the model size
- Add more specific decision rules before increasing `reasoningEffort`
