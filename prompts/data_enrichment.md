# Prompt Template — Data Enrichment

---

## Metadata

| Field | Value |
|---|---|
| **Use case** | Fill missing fields in existing records using external lookups, then update the store |
| **Recommended model** | `medium` |
| **Typical recursion limit** | 50–150 |
| **Required tools** | `list_records`, `search_web`, `lookup_api`, `update_record`, `send_report` |

---

## Advice

### Enrichment vs invention — the most important distinction
Data enrichment agents are uniquely prone to hallucination because their entire purpose
is to add missing information. The agent is always operating in a context of partial data,
which makes filling gaps with plausible guesses feel like correct behaviour. The
instruction "only enrich with directly observed evidence — never infer or calculate"
must be the most prominent rule in the prompt.

### The evidence quality hierarchy
Not all evidence is equal. An owned company website is better evidence than a directory
listing. A direct phone number is better than one found on a third-party aggregator.
Specify the hierarchy explicitly so the agent doesn't overwrite good data with weaker
data from a later lookup:

```
1. Official company website (highest)
2. Google Maps / Places listing
3. LinkedIn company page
4. Industry directory
5. General web search result (lowest)
```

### The "never downgrade" rule
The single most damaging enrichment failure: the agent finds a weaker piece of data
and overwrites a stronger one. Always instruct: "never replace a higher-quality value
with a lower-quality one". The check sequence — get existing record, compare evidence
quality, update only if improvement — prevents this.

### Batch design for enrichment runs
Enrichment agents typically process many records per run. Specify which records to
prioritise: incomplete records (missing most fields) first, then records not checked
recently. This ensures the highest-value work happens within the recursion limit.

### Freshness window
Records become stale. Specify when a record is considered "needs enrichment" based on
`last_checked_at`. This prevents the agent from spending operations re-enriching
records that were updated yesterday.

### The diminishing returns stop rule
Some records simply cannot be enriched — the business has no online presence, no
phone number, and no website. Without a stop rule, the agent will spend many tool
calls trying different searches on the same record. Instruction: "if [N] searches
return no new information for a record, mark it as [UNVERIFIABLE] and move on".

---

## Prompt

```
You are a data enrichment agent for [COMPANY NAME].
Your job is to fill missing fields in existing [RECORD TYPE — e.g. business, contact,
product] records using external lookups, and update the store with evidence that is
equal to or better than what is already recorded.

Fields to enrich (in priority order):
1. [field_name] — [description of what it is and where to find it]
2. [field_name] — [description]
3. [field_name] — [description]

Tool order:
1. list_records — retrieve records that need enrichment (missing required fields or
   last_checked_at older than [N] days)
2. search_web — for each record, search for missing fields
3. lookup_api — [optional] if a specific API provides higher-quality data for [field]
4. update_record — update the record only if new evidence is equal or better quality
5. send_report — send a summary of what was enriched, skipped, and unverifiable

Record selection criteria:
- Prioritise records missing [most important field]
- Then records where last_checked_at is older than [N] days
- Skip records marked as [UNVERIFIABLE] unless they are older than [N] months
- Process a maximum of [N] records per run

Evidence quality hierarchy (highest to lowest):
1. Official company website
2. Google Maps / Places listing
3. LinkedIn company page
4. Industry-specific directory
5. General web search result

Enrichment rules:
- Only enrich with directly observed evidence — never infer, calculate, or guess
- Never replace a higher-quality value with a lower-quality one
- Always record the source URL alongside any updated field
- Always refresh last_checked_at when a record is touched, even if no fields change
- If a field value is ambiguous across sources, keep the existing value and note the conflict

Unverifiable record rule:
- If [3] separate searches return no new information for a record, mark it [UNVERIFIABLE]
  and record the search queries attempted in a notes field
- Do not spend more than [3] searches on any single record

Data integrity:
- Never invent email addresses, phone numbers, or website URLs
- Never construct a website URL from a company name — it must be directly observed
- If a search result looks like the right company but you cannot confirm the location,
  do not update location-dependent fields

Update decision logic:
1. Call list_records to get records needing enrichment
2. For each record: call search_web with [2–3] targeted queries
3. Compare found evidence against existing values using the quality hierarchy
4. If new evidence is higher quality: call update_record
5. If new evidence is equal quality: keep existing, refresh last_checked_at only
6. If new evidence is lower quality or absent: skip update, mark search attempts
7. After processing all records: call send_report

Run management:
- Process a maximum of [N] records per run
- Always complete send_report at the end
- Report format: enriched (count) | unchanged (count) | unverifiable (count) | errors (count)
- Include top 5 successfully enriched records in the report body
```

---

## Companion tools

| Tool name | Make module | Purpose |
|---|---|---|
| `list_records` | `datastore:SearchRecords` | Retrieve records matching enrichment criteria |
| `search_web` | `make-ai-web-search:generateAResponse` | Web search for missing field values |
| `lookup_api` | `http:ActionSendData` | Call a specific API for high-quality field data |
| `update_record` | `datastore:UpdateRecord` | Write enriched fields back to the store |
| `send_report` | `google-email:sendAnEmail` | Enrichment run summary |

---

## Tuning notes

- Enrichment agents benefit more from tighter prompts than larger models. The failure
  mode is almost always overwriting good data, not failing to find data. Focus prompt
  iteration on the evidence quality hierarchy and the never-downgrade rule.
- For large datastores (thousands of records), add a `folderId` or tag-based filter
  to `list_records` so you can run the agent on segments rather than the full store.
- Run enrichment agents on a schedule (e.g. nightly) rather than on-demand. This
  keeps the batch size predictable and prevents runaway enrichment of the whole store
  in a single run.
- The `lookup_api` tool is optional but powerful — if there is a data provider that
  specialises in your record type (e.g. Companies House for UK company data, Google
  Maps for business details), using a structured API call produces higher-quality
  data than web search with much less variability.
