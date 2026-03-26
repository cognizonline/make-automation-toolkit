# Prompt Template — Document & Media Processing

---

## Metadata

| Field | Value |
|---|---|
| **Use case** | Extract structured data from documents, images, and audio files using Make's built-in AI extractors — no external API key required |
| **Recommended model** | `large` |
| **Typical recursion limit** | 30–80 |
| **Required tools** | `read_file`, `extract_document` / `describe_image` / `transcribe_audio`, `validate_record`, `save_record`, `notify` |

---

## Advice

### Why Make built-in extractors change the architecture

Traditional document processing agents call an external LLM to perform extraction.
Make's built-in extractors (`make-ai-extractors`) perform extraction as a **dedicated
module step** — before the agent's LLM even sees the data. This means:

- The agent receives **already-extracted structured output**, not raw file bytes
- The LLM's job shifts from extraction to **validation, routing, and decision-making**
- Credit costs are predictable and fixed (10 credits/page for documents, 2 credits for images)
- No external connection or API key is needed — privacy-preserving by design

Design your agent around this: extraction modules are tools the agent *calls*, but the
agent's reasoning layer focuses on what to do with the extracted data.

### Document extraction vs invoice/receipt extraction

`make-ai-extractors` has three document modules with different trade-offs:

| Module | Best for | Credits |
|---|---|---|
| `extractADocument` | General documents (contracts, reports, forms) | 10/page |
| `extractInvoice` | Invoices with line items, totals, dates | 10/op |
| `extractReceipt` | Point-of-sale receipts, expense claims | 10/op |

Use the specialised invoice/receipt modules when you know the document type in advance —
they return more reliably structured fields. Use `extractADocument` with a custom prompt
when document types are mixed or unknown.

### Image extraction strategy

For images, choose the module that matches the data you need:

- `extractTextFromAnImage` (OCR) — when you need the text content of a scanned document or photo
- `extractInvoice` / `extractReceipt` — when the image IS an invoice or receipt (these accept images)
- `generateCaption` / `describeImage` — when you need to understand what is depicted
- `generateImageTags` / `detectObjects` — when you need metadata for search or categorisation
- `generateCaptionsAdvanced` — for alt-text generation for accessibility pipelines

Use `describeImage` (not `generateCaption`) when you need a custom prompt — e.g.
"describe only the table visible in this image" or "list all text visible in this screenshot".

### Audio: transcription vs translation

`transcribeAudio` preserves the original language; `translateAudio` always outputs English.
For multilingual support teams, run both in sequence:
1. `transcribeAudio` — original language transcript for compliance/audit
2. `translateAudio` — English for downstream processing

Speaker diarization (who said what) is a `transcribeAudio` parameter — enable it for
meeting recordings, support calls, and interviews.

### The validation gap that extractors leave open

Extractors are accurate but not infallible. A blurry scan, a non-standard invoice format,
or a very long document will produce imperfect extraction. The agent must always run a
validation step after extraction:
- Are all required fields present and non-null?
- Do totals match line item sums (within rounding tolerance)?
- Is the date format consistent and parseable?

Without this step, extraction errors propagate silently to downstream systems.

### Credit cost awareness in the prompt

At 10 credits per page, a 50-page PDF costs 500 credits. Build the agent to check file
size and page count before calling `extractADocument` on large files, and to alert when
a batch run will exceed a threshold. Instruct the agent: "if a document exceeds [N] pages,
send a cost-approval request before extracting".

---

## Prompt

```
You are a document and media processing agent for [COMPANY NAME].
Your job is to extract structured data from inbound files — documents, images, and audio
— using Make's built-in AI extractors, validate the output, and route it to the correct
destination.

Supported file types:
- Documents: PDF, DOCX, XLSX, PPTX, HTML (up to 2000 pages, 500 MB)
- Images: PNG, JPG, WEBP, GIF, BMP, TIFF
- Audio: MP3, WAV, M4A, FLAC, OGG (up to 2 hours / 300 MB for transcription; 25 MB for translation)

Tool order:
1. read_file — retrieve the file from [Google Drive / S3 / HTTP source]
2. classify_file — identify the file type and document subtype (invoice / receipt / contract / image / audio / other)
3. extract — call the appropriate extractor based on file type and subtype:
   - Invoice (doc or image): extract_invoice — returns invoice_number, vendor, line_items, totals, dates
   - Receipt (doc or image): extract_receipt — returns merchant, items, total, payment_method, date
   - General document: extract_document with prompt: "[describe what fields to extract]"
   - Image (content): describe_image with prompt: "[what you want to know about the image]"
   - Image (text): ocr_image — returns raw text content
   - Audio: transcribe_audio (preserves language) or translate_audio (outputs English)
4. validate_record — verify required fields are present, non-null, and correctly typed
5. save_record — write the validated record to [datastore / Google Sheets / CRM]
6. notify — send a processing confirmation or flag-for-review notification

Required fields by document subtype:

Invoice:
- invoice_number (text, required)
- invoice_date (date ISO 8601, required)
- vendor_name (text, required)
- line_items (array of {description, quantity, unit_price, amount}, required)
- subtotal (number, required)
- tax (number, required)
- total (number, required)
- currency (text, required)
- due_date (date ISO 8601, optional)
- po_number (text, optional)

Receipt:
- merchant_name (text, required)
- transaction_date (date ISO 8601, required)
- items (array, required)
- total (number, required)
- payment_method (text, optional)

Audio transcription:
- transcript (text, required)
- language (text, required)
- duration_seconds (number, required)
- speaker_segments (array, optional — only if diarization enabled)

[Add additional subtypes and fields here]

Extraction rules:
- Never invent values — extract only what is explicitly present in the source
- If a required field is absent or unreadable, mark it null and add [NEEDS_REVIEW]
- Normalise all dates to ISO 8601 (YYYY-MM-DD)
- Normalise currency amounts to plain numbers (no symbols or commas)
- If extraction confidence for a required field is below 90%, append [NEEDS_REVIEW]

Cost guardrail:
- If a document exceeds [N] pages, do NOT call extract_document immediately
- Instead, call notify to request cost approval, then stop
- Resume extraction only after approval is confirmed

Routing rules:
- Invoice, total > [APPROVAL_THRESHOLD]: route to approval_queue
- Invoice, total <= [APPROVAL_THRESHOLD]: route to auto_process_queue
- Receipt: route to expense_queue
- Audio transcript: route to [transcript_store / CRM note]
- Any record with [NEEDS_REVIEW]: route to manual_review_queue
- Unknown file type: route to manual_review_queue

Data integrity:
- Never calculate totals — extract them from the source
- Never correct errors in the source — extract as-is and flag
- Duplicate check: if invoice_number already exists in the store, flag as DUPLICATE and do not overwrite

Run management:
- Process one file per run
- Always complete the notify step regardless of outcome
- If validation fails, route to manual_review_queue and include the error detail in the notification
- Report format: file_name | subtype | fields_extracted | fields_flagged | route_destination
```

---

## Companion tools

| Tool name | Make module | Purpose |
|---|---|---|
| `read_file` | `google-drive:DownloadFile` or `http:ActionGetFile` | Retrieve file from storage |
| `extract_document` | `make-ai-extractors:extractADocument` | General document extraction (10 credits/page) |
| `extract_invoice` | `make-ai-extractors:extractInvoice` | Invoice-specific structured extraction (10 credits/op) |
| `extract_receipt` | `make-ai-extractors:extractReceipt` | Receipt-specific structured extraction (10 credits/op) |
| `describe_image` | `make-ai-extractors:describeImage` | Custom-prompted image description (2 credits/op) |
| `ocr_image` | `make-ai-extractors:extractTextFromAnImage` | OCR — extract all text from an image (2 credits/op) |
| `generate_tags` | `make-ai-extractors:generateImageTags` | Image tagging for search/categorisation (2 credits/op) |
| `transcribe_audio` | `make-ai-extractors:transcribeAudio` | Full transcript with optional diarization (20 credits/min) |
| `translate_audio` | `make-ai-extractors:translateAudio` | Audio to English transcript (20 credits/min, max 25 MB) |
| `save_record` | `datastore:AddRecord` or `google-sheets:addRow` | Persist extracted record |
| `notify` | `slack:ActionPostMessage` or `google-email:sendAnEmail` | Confirmation or flag-for-review alert |

---

## Make built-in extractor module reference

### `make-ai-extractors:extractADocument`

Extracts structured content from PDF, DOCX, XLSX, PPTX, HTML, and image files.

```json
{
  "module": "make-ai-extractors:extractADocument",
  "parameters": {
    "file": "{{read_file.data}}",
    "filename": "{{read_file.name}}",
    "prompt": "Extract the following fields: vendor name, invoice number, invoice date, line items (description, quantity, unit price), subtotal, tax, and total. Return as JSON.",
    "parseJson": true
  }
}
```

**Key parameters:**
- `file` — binary file data (from HTTP download or Drive module)
- `filename` — required for format detection
- `prompt` — custom extraction instruction (what fields to extract and how to format them)
- `parseJson: true` — returns output as a parsed JSON object instead of raw text
- Supports up to 2000 pages / 500 MB; costs 10 credits per page

### `make-ai-extractors:extractInvoice`

Pre-trained on invoice formats. Returns a fixed schema including line items, totals, and payment terms.

```json
{
  "module": "make-ai-extractors:extractInvoice",
  "parameters": {
    "file": "{{read_file.data}}",
    "filename": "{{read_file.name}}"
  }
}
```

Returns: `invoiceNumber`, `invoiceDate`, `dueDate`, `vendorName`, `vendorAddress`,
`buyerName`, `buyerAddress`, `lineItems[]`, `subtotal`, `taxRate`, `taxAmount`, `total`, `currency`

### `make-ai-extractors:describeImage`

LLM-powered image description with a custom prompt.

```json
{
  "module": "make-ai-extractors:describeImage",
  "parameters": {
    "file": "{{image_download.data}}",
    "filename": "{{image_download.name}}",
    "prompt": "Describe the damage visible in this image in 2-3 sentences. Note the affected area, severity, and any visible part numbers.",
    "temperature": 0.2
  }
}
```

Use low `temperature` (0.1–0.3) for factual extraction; higher (0.5–0.8) for creative descriptions.

### `make-ai-extractors:transcribeAudio`

Full audio transcript with optional speaker diarization.

```json
{
  "module": "make-ai-extractors:transcribeAudio",
  "parameters": {
    "file": "{{audio_download.data}}",
    "filename": "recording.mp3",
    "language": "en",
    "diarization": true
  }
}
```

- `language` — ISO 639-1 code (e.g. `en`, `fr`, `de`). Leave blank for auto-detect.
- `diarization: true` — identifies individual speakers (Speaker 1, Speaker 2...)
- Supports up to 2 hours / 300 MB; costs 20 credits per minute of audio

---

## Tuning notes

- For invoice/receipt extraction, use the specialised modules (`extractInvoice`,
  `extractReceipt`) rather than `extractADocument` with a prompt. They return a
  consistent schema regardless of invoice format variation.
- For `extractADocument`, the single biggest quality improvement is a specific prompt.
  "Extract all text" produces a wall of text; "Extract the following fields as JSON: ..."
  produces structured, usable output.
- Set `parseJson: true` on any extractor that has it — this eliminates all downstream
  JSON parsing steps and makes the output directly mappable.
- Audio diarization doubles processing time on long recordings. Enable it only when you
  need speaker attribution (support calls, meetings). Disable it for single-speaker
  content (voicemails, dictation).
- For high-volume document runs, batch by file type so you can use the right extractor
  module for each type rather than forcing all files through `extractADocument`.
- Credit cost at scale: 100 x 10-page PDFs = 10,000 credits for extraction alone.
  Add a counter to the agent and have it stop and report after [N] credits consumed
  per run.
