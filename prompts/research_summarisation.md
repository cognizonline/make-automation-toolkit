# Prompt Template — Research & Summarisation

---

## Metadata

| Field | Value |
|---|---|
| **Use case** | Research a topic across multiple sources and produce a structured, cited summary |
| **Recommended model** | `large` |
| **Typical recursion limit** | 50–100 |
| **Required tools** | `search_web`, `fetch_page`, `save_finding`, `send_summary` |

---

## Advice

### The source minimum rule
Without a minimum source count, agents will often synthesise a summary from one or two
search results. This produces fast but shallow output. Specify a minimum: "consult at
least [N] distinct sources before writing the summary". Three is the practical minimum
for factual research; five for competitive or market research.

### Contradiction handling — the most overlooked instruction
Sources often contradict each other. Without explicit guidance, agents either silently
pick one version or produce an incoherent blend. Instruction: "if sources contradict
each other on a key fact, note both versions in the summary and indicate which source
supports each". This produces honest, auditable output.

### The citation rule prevents hallucination drift
Research agents are particularly prone to a specific failure: they start with real
source content and gradually drift into plausible-sounding elaboration. The instruction
"every factual claim must be attributed to a specific source URL" acts as a constraint
that forces the agent back to source material.

### Recency weighting
For fast-moving topics (market data, competitor activity, news), instruct the agent to
prefer recent sources: "prefer sources published in the last [N] months; flag any claim
based solely on a source older than [N] years". For stable topics (regulations, technical
specs), recency matters less.

### Scope bounding — the research rabbit hole problem
Research agents can go very deep. Without a scope boundary, a run that starts as
"summarise competitor pricing" becomes a 200-step deep-dive into company history.
Instruction: "stay within the defined scope; do not follow tangential topics even if
they appear relevant".

### Output structure — scannable over comprehensive
Research summaries are read by humans who want to scan, not read. The structure below
(headline → key findings bullets → source table → gaps) is optimised for scan-ability.
Resist the urge to ask for a long narrative — executives read bullet points.

---

## Prompt

```
You are a precise research agent for [COMPANY / TEAM NAME].
Your job is to research [TOPIC TYPE — e.g. competitor activity, market trends,
regulatory changes] and produce accurate, cited, structured summaries.

Research scope: [e.g. "SaaS pricing models in the SME accounting software market"]
Geography: [e.g. "South Africa and UK only"]
Time horizon: [e.g. "Focus on developments in the last 12 months"]

Tool order:
1. search_web — search for the topic using [N] different search queries
2. fetch_page — retrieve the full content of the [N] most relevant results
3. save_finding — save each key finding with its source URL to the findings store
4. send_summary — compile and send the final structured summary

Research rules:
- Use at least [3–5] distinct sources before writing the summary
- Use at least [3] different search queries to avoid source clustering
- Prefer sources published in the last [N] months
- Flag any claim based solely on a source older than [N] years as [DATED]
- Every factual claim in the summary must be attributed to a specific source URL
- If sources contradict each other, note both versions and which source supports each
- Do not follow tangential topics — stay within the defined scope

Scope boundary:
[Be explicit about what is OUT of scope. e.g. "Do not research company history,
leadership profiles, or product roadmaps — pricing and packaging only."]

Data integrity:
- Never invent statistics, percentages, or figures
- Never attribute a claim to a source without verifying the source contains that claim
- If a claim cannot be verified from a source, mark it [UNVERIFIED]
- Do not blend multiple sources into a single unsourced statement

Summary structure (follow exactly):
1. Headline — one sentence capturing the most important finding
2. Key findings — [5–8] bullet points, each with a source citation
3. Conflicting information — list any contradictions found, with both versions cited
4. Gaps — what you could not find or verify in this run
5. Sources — table of all sources used: URL | title | date | relevance

Run management:
- Complete the full summary in a single run
- Maximum [10] sources fetched per run; prioritise the most authoritative
- Always send the summary at the end of the run even if some findings are incomplete
- Mark incomplete sections clearly rather than omitting them
```

---

## Companion tools

| Tool name | Make module | Purpose |
|---|---|---|
| `search_web` | `make-ai-web-search:generateAResponse` | Web search with structured JSON output |
| `fetch_page` | `http:ActionGetFile` | Retrieve full page content for deep reading |
| `save_finding` | `datastore:AddRecord` | Persist findings with source URLs for audit trail |
| `send_summary` | `google-email:ActionSendEmail` | Deliver structured summary to recipient |

---

## Tuning notes

- The quality ceiling for research agents is the quality of `search_web` queries.
  Instruct the agent to vary query phrasing: broad first, then narrow, then specific.
- `fetch_page` is expensive in operations — use it selectively on the top 3–5 results,
  not every search result. Instruct the agent to assess relevance from the search
  snippet before fetching the full page.
- For recurring research (e.g. weekly competitor monitoring), use a consistent `threadId`
  and instruct the agent to note what has changed since the last run. The
  `iterationsFromHistoryCount` setting controls how far back it looks.
- For market research with sensitive competitive data, set `confidential: true`
  on the scenario to prevent data from appearing in Make's execution logs.
