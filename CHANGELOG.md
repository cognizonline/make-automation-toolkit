# Changelog

All notable changes to this project follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

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
