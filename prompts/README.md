# System Prompt Templates

Ready-to-use system prompts for Make AI Agents — each with annotated advice explaining
*why* each section is written the way it is, so you can adapt them confidently.

---

## Anatomy of an effective Make agent prompt

A well-structured Make agent system prompt has six sections, always in this order:

```
1. Identity & mission       — who the agent is and what it exists to do
2. Tool order               — which tools to call in which sequence
3. Decision rules           — when to branch, skip, repeat, or stop
4. Data integrity rules     — what to accept, reject, and never invent
5. Output format            — exactly what shape the result must take
6. Run management           — batch limits, error behaviour, end-of-run actions
```

Skipping any section is fine for simple agents. For production agents, all six matter.

### Why tool order matters

Unlike the old linear chain — where the scenario designer defines execution order —
the agent decides which tools to call at runtime. This is powerful but means the LLM
can make suboptimal choices (e.g. writing to the datastore before checking for duplicates).
An explicit tool order instruction overrides this and makes runs deterministic.

### Why data integrity rules matter

LLMs hallucinate. Without explicit rules like *"never invent contact names"* or
*"only include WhatsApp if explicitly shown"*, agents will confidently fabricate
plausible-looking data. Every production prompt needs a short list of things the
agent must never do.

### Why run management matters

Agents run inside a scenario with a `recursionLimit`. Without explicit batch caps
(e.g. *"max 50 records per run"*), the agent will optimise for thoroughness and
regularly hit the limit mid-task, leaving partial work in an inconsistent state.

---

## Templates

| File | Use case | Recommended model |
|---|---|---|
| [lead_generation.md](lead_generation.md) | Discover, qualify, and store business leads | `large` |
| [customer_support.md](customer_support.md) | Triage inbound requests, look up records, respond | `medium` |
| [document_processing.md](document_processing.md) | Extract, validate, and route structured data from documents | `large` |
| [research_summarisation.md](research_summarisation.md) | Research a topic across sources and produce a structured summary | `large` |
| [data_enrichment.md](data_enrichment.md) | Fill gaps in existing records using external lookups | `medium` |
| [document_and_media_processing.md](document_and_media_processing.md) | Extract data from PDFs, images, and audio using Make's built-in AI extractors | `large` |
| [_template.md](_template.md) | Scaffold for writing your own prompt | — |

---

## Quick start

1. Pick the template closest to your use case
2. Read the **Advice** section — understand *why* each block is there before editing
3. Replace the bracketed placeholders `[LIKE THIS]` with your specifics
4. Pair with the suggested tools in the **Companion tools** section
5. Start with `recursionLimit: 50` and tune up only if runs terminate early

---

## Tuning reference

| Setting | Conservative | Balanced | Aggressive |
|---|---|---|---|
| `recursionLimit` | 30 | 50–100 | 200–300 |
| `iterationsFromHistoryCount` | 3 | 5–10 | 15+ |
| `defaultModel` | `small` | `medium` | `large` |
| `reasoningEffort` | `low` | `low` | `low` |
| Batch size cap in prompt | 10 | 25–50 | 100+ |

> `reasoningEffort: low` is the only currently valid value. Do not change it.
