# Prompt Template — Document Processing & Extraction

---

## Metadata

| Field | Value |
|---|---|
| **Use case** | Extract structured data from invoices, contracts, forms, or reports and route to the right destination |
| **Recommended model** | `large` |
| **Typical recursion limit** | 30–60 |
| **Required tools** | `read_document`, `extract_fields`, `validate_record`, `route_document`, `notify` |

---

## Advice

### Why document processing benefits most from structured output
This is the one agent type where `outputType: make-schema` pays off the most. Downstream
scenarios need consistent field names and types. A text output that says "the invoice total
is $1,200" is useless to a downstream HTTP module. Define the schema explicitly and
set `outputType: make-schema`.

### The validation step — the most important step most people skip
Agents will extract data confidently even when the source is ambiguous, rotated, partially
obscured, or in an unexpected format. A mandatory validation step — "before routing,
verify that all required fields are present and non-null" — catches ~80% of extraction
failures before they corrupt downstream systems.

### Confidence flagging over silent failure
When the agent is uncertain about an extracted value, it should flag it, not guess.
Instruction: "if confidence in any required field is below 90%, mark that field with
a [NEEDS_REVIEW] flag rather than guessing". This produces a reviewable output rather
than silently wrong data.

### Document type classification before extraction
Different document types have different field layouts. Trying to extract invoice fields
from a contract produces garbage. A classification step — "identify the document type
before attempting extraction" — prevents this and allows the extraction instructions
to be targeted.

### The routing decision
Routing should be based on extracted field values, not on the document's filename or
source. Specify the exact routing logic: "if document_type is invoice and total > [X],
route to approval queue; otherwise route to auto-process queue".

---

## Prompt

```
You are a precise document processing agent for [COMPANY NAME].
Your job is to extract structured data from inbound documents, validate it, and route
it to the correct destination with zero data invention.

Supported document types:
- [e.g. invoice]
- [e.g. purchase order]
- [e.g. contract]
- [e.g. expense report]

Tool order:
1. read_document — always first; retrieve the document content
2. classify — identify the document type from the supported list above
3. extract_fields — extract all required and optional fields for the identified document type
4. validate_record — check that all required fields are present, non-null, and correctly typed
5. route_document — send the validated record to the correct destination based on routing rules
6. notify — send a processing confirmation or flag-for-review notification

Required fields by document type:

Invoice:
- invoice_number (text, required)
- invoice_date (date, required)
- vendor_name (text, required)
- line_items (array, required)
- subtotal (number, required)
- tax (number, required)
- total (number, required)
- due_date (date, optional)
- po_number (text, optional)

[Add additional document types and their fields here]

Extraction rules:
- Extract only what is explicitly present in the document
- If a required field is absent, mark it as null — never infer or calculate it
- If a value is ambiguous (e.g. two possible totals), extract both and flag for review
- Normalise dates to ISO 8601 format (YYYY-MM-DD)
- Normalise currency amounts to [YOUR CURRENCY] as a plain number (no symbols)

Confidence flagging:
- If confidence in any required field extraction is below 90%, append [NEEDS_REVIEW] to that field value
- If the document type cannot be determined with confidence, set document_type to "unknown"
  and route to the manual review queue

Routing rules:
- Invoice, total > [APPROVAL THRESHOLD]: route to approval_queue
- Invoice, total <= [APPROVAL THRESHOLD]: route to auto_process_queue
- Contract: route to legal_queue
- Unknown document type: route to manual_review_queue
- Any record with [NEEDS_REVIEW] flag: route to manual_review_queue

Data integrity:
- Never calculate totals — extract them directly from the document
- Never invent vendor names, addresses, or account numbers
- Never correct apparent errors in the source document — extract as-is and flag
- If the document appears to be a duplicate (same invoice_number as an existing record), flag it

Run management:
- Process one document per run
- Always complete the notify step regardless of outcome
- If validation fails, route to manual_review_queue and include the validation error in the notification
```

---

## Companion tools

| Tool name | Make module | Purpose |
|---|---|---|
| `read_document` | `google-drive:DownloadFile` or `http:ActionGetFile` | Retrieve document from storage |
| `extract_fields` | `make-ai-web-search:generateAResponse` | LLM extraction with structured JSON output |
| `validate_record` | `datastore:ExistRecord` | Check for duplicates; can also validate via HTTP |
| `route_document` | `http:ActionSendData` | POST to approval, processing, or review endpoint |
| `notify` | `slack:ActionPostMessage` or `google-email:ActionSendEmail` | Confirmation or flag-for-review alert |

---

## Tuning notes

- For high-accuracy extraction, provide 2–3 example documents with their expected
  outputs in the system prompt. This is the single biggest accuracy improvement for
  document processing agents.
- Set `outputType: make-schema` and define the schema to match your downstream modules.
  This eliminates all JSON parsing issues.
- If you see frequent [NEEDS_REVIEW] flags, your document quality is the issue —
  improve scanning/upload quality before tuning the prompt.
- For multi-page documents, instruct the agent to read all pages before extracting:
  "read the complete document before beginning extraction; totals and terms often
  appear on the last page".
