# Changelog

All notable changes to this project follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## [1.3.2] — 2026-03-27

### Fixed
- `src/make_client.py` — `_request()` now passes `timeout=30` to every request (no more indefinite hangs); 4xx errors now raise immediately without retry (only 429 and network errors are retried); imported `HTTPError` explicitly for the guard
- `src/make_client.py` — `paginate_records()` was delegating to `paginate()` which sends `pg[limit]/pg[offset]`; data-store records endpoint requires plain `limit/offset`; fixed by delegating to `list_records()` which already uses the correct params
- `src/make_client.py` — `deploy_with_datastore()` docstring claimed `"webhook": dict | None` return key that was never populated; removed phantom key
- `pyproject.toml` — switched build backend from `setuptools.backends.legacy:build` to standard `setuptools.build_meta`; added `[tool.setuptools.packages.find]` with `include = ["src*"]` to make `pip install .` reliable
- `requirements.txt` — removed dev-only packages (`responses`, `jsonschema`) which belong in `pyproject.toml [dev]` extras only; runtime install is now minimal
- `README.md` — webhook feature description now accurately states HMAC is configured in Make UI, not via SDK
- `skill/make-automation-skill.md` — HMAC section now clarifies SDK scope (create hook) vs Make UI scope (configure secret); shows `compare_digest` for timing-safe verification
- `src/make_client.py` — `_request()` 5xx retry regression fixed: previous fix accidentally re-raised 5xx HTTPErrors immediately; now discriminates in `except HTTPError` by checking `exc.response.status_code`; 5xx retries with backoff, 4xx raises immediately
- `src/make_client.py` — `MakeDeployer` class docstring corrected to reflect actual methods
- `pyproject.toml` — version bumped to 1.3.2; added `[tool.setuptools.package-data]` so `src/blueprints/*.json` (including `schema.json`) is included in wheel/sdist installs
- `src/__init__.py` — version bumped to 1.3.2
- `.gitattributes` — added to enforce LF line endings on all text files, preventing mojibake on Windows
- `tests/test_make_client.py` — added 4 new tests: 401 no-retry, 403 no-retry, 503 retry-then-succeed, `paginate_records` uses `limit`/`offset` not `pg[...]`; suite now 19 tests, all passing

---

## [1.3.1] — 2026-03-27

### Fixed
- `src/examples/06_deploy_scenario_agent.py`, `07_builtin_ai_tools.py`, `08_mcp_toolbox_workflow.py` — broken import pattern (used `parent.parent` + `from make_client import`). Aligned with examples 01–05: `resolve().parents[2]` (absolute repo root) + `from src.make_client import`
- `.github/workflows/ci.yml` — install now uses `pip install -e ".[dev]"` instead of separate `requirements.txt` + dev tools installs; CI now matches `pyproject.toml` package structure
- `.github/workflows/ci.yml` — documented why `ai_local_agent.json` and `schema.json` are excluded from blueprint validation
- `skill/make-automation-skill.md` — expanded AI Agent decision guide to include MCP Toolboxes as a third option (with example references); added `_request()` usage note in Organisation section

---

## [1.3.0] — 2026-03-26

### Added
- `docs/mcp-toolboxes.md` — full guide to MCP Toolboxes: setup, access control, the single-tool wrapping pattern, multi-client key isolation, audit logging, and naming conventions
- `src/examples/08_mcp_toolbox_workflow.py` — runnable example deploying a 4-step "Onboard Customer" workflow as a single governed MCP Toolbox tool
- `skill/make-automation-skill.md` — MCP Toolboxes subsection with comparison table, connection config, and single-tool wrapping pattern
- `docs/mcp-integration.md` — Toolboxes callout section with link to full guide

### Changed
- `skill/make-automation-skill.md` — expanded "Make Tools vs AI Agents" to three-way comparison including MCP Toolboxes (auth, access control, audit log columns added)

---

## [1.2.0] — 2026-03-26

### Added
- `prompts/document_and_media_processing.md` — new prompt template for document, image, and audio extraction using Make's built-in AI extractors (`make-ai-extractors`)
- `skill/make-automation-skill.md` — new "Make built-in AI modules" section covering `make-ai-web-search`, `make-ai-extractors` (all 11 modules with JSON examples), and `ai-tools` v2
- Module reference with credit costs, parameter tables, and usage guidance for all extraction modules

### Changed
- `prompts/README.md` — added `document_and_media_processing.md` to template index
- `docs/ai-agents.md` — updated `web_search` tool example to use `make-ai-web-search:generateAResponse`; added section 6 "Make built-in AI modules as agent tools" with copy-paste `flow[]` examples for web search, invoice extraction, document extraction, and audio transcription; updated See also
- `src/examples/07_builtin_ai_tools.py` — new runnable example: accounts payable agent using `make-ai-web-search` + `make-ai-extractors:extractInvoice` + `datastore:AddRecord`

---

## [1.1.0] — 2026-03-26

### Added
- `tests/` directory with unit tests covering client methods, retry logic, and pagination
- `src/validate_blueprint.py` — schema-based blueprint validator
- `src/blueprints/schema.json` — JSON Schema for Make.com blueprints
- `src/blueprints/ai_local_agent.json` — template blueprint for the scenario-embedded AI Agent pattern (`ai-local-agent:RunLocalAIAgent`)
- `MakeDeployer.deploy_ai_agent_stack()` — implements previously documented but missing method
- `MakeDeployer.deploy_scenario_agent()` — new method for the scenario-embedded agent pattern
- `MakeClient.paginate()` — generator for paginated list endpoints
- `MakeClient.paginate_scenarios()` and `paginate_records()` convenience wrappers
- `pyproject.toml` — proper packaging config; installable via `pip install .`
- `CHANGELOG.md`

### Fixed
- `_request()` now reads `Retry-After` response header on 429 instead of always using exponential backoff
- `requirements.txt` cleaned — removed unused `pydantic`, `click`, `rich`; added `responses` and `jsonschema`
- CI blueprint validation now uses schema validator instead of bare `json.load()`
- `pytest` no longer uses `|| true` — failures are real failures; coverage gate at 60%

### Docs
- `docs/ai-agents.md` updated to cover both deployment patterns and the MCP toolset gap
