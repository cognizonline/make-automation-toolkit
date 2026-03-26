# Changelog

All notable changes to this project follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## [1.2.0] — 2026-03-26

### Added
- `prompts/document_and_media_processing.md` — new prompt template for document, image, and audio extraction using Make's built-in AI extractors (`make-ai-extractors`)
- `skill/make-automation-skill.md` — new "Make built-in AI modules" section covering `make-ai-web-search`, `make-ai-extractors` (all 11 modules with JSON examples), and `ai-tools` v2
- Module reference with credit costs, parameter tables, and usage guidance for all extraction modules

### Changed
- `prompts/README.md` — added `document_and_media_processing.md` to template index

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
