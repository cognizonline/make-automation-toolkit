# Contributing to Make Automation Toolkit

Thank you for considering a contribution. This guide covers everything you need to submit safely and effectively.

---

## Ground rules

- **Never commit secrets.** No API tokens, MCP tokens, passwords, or real IDs in any file — ever.
- Keep examples generic (use `"your-token"`, `os.environ["MAKE_API_TOKEN"]`, placeholder IDs like `123`).
- One change per PR — blueprints, examples, docs, and SDK changes should each get their own PR.
- All CI checks must pass before a PR will be reviewed.

---

## What you can contribute

| Type | Where |
|---|---|
| New blueprint | `src/blueprints/<name>.json` |
| New example script | `src/examples/<NN>_<description>.py` |
| SDK bug fix / new method | `src/make_client.py` |
| Documentation | `docs/<topic>.md` |
| Bug report | GitHub Issues |

---

## Setup

```bash
git clone https://github.com/cognizonline/make-automation-toolkit.git
cd make-automation-toolkit
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install flake8
```

---

## Submitting a pull request

1. **Fork** the repo on GitHub.
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feat/my-blueprint
   ```
3. **Make your changes** (see rules per type below).
4. **Validate locally** before pushing:
   ```bash
   # Lint Python
   flake8 src/ --max-line-length=120

   # Validate JSON blueprints
   for f in src/blueprints/*.json; do
     python -c "import json; json.load(open('$f'))" && echo "$f OK"
   done
   ```
5. **Commit** with a clear message:
   ```
   feat(blueprints): add Slack notification blueprint
   fix(client): handle 503 in retry loop
   docs(mcp): clarify approval mode behaviour
   ```
6. **Push** and open a PR against `main`.

---

## Blueprint guidelines

A valid blueprint must:

- Pass `json.load()` without errors (validated in CI)
- Have a descriptive `"name"` field
- Use placeholder values for any IDs: `"{{DATASTORE_ID}}"`, `"YOUR_URL"`
- Include a `metadata.scenario` block with sensible defaults
- Not reference real webhook URLs, credentials, or account IDs

```json
{
  "name": "My Blueprint",
  "flow": [ ... ],
  "metadata": {
    "version": 1,
    "scenario": {
      "roundtrips": 1,
      "maxErrors": 3,
      "autoCommit": true,
      "autoCommitTriggerLast": true,
      "sequential": false,
      "confidential": false,
      "dataloss": false,
      "dlq": false
    }
  }
}
```

---

## Example script guidelines

- Read credentials **only** from environment variables (`os.environ`)
- Include a docstring at the top with usage (`export MAKE_API_TOKEN=...`)
- Use `sys.path.insert` to import from `src/` (see existing examples)
- Number files sequentially (`06_`, `07_`, ...) if adding to the sequence

---

## Reporting a bug

Open a [GitHub Issue](https://github.com/cognizonline/make-automation-toolkit/issues/new) with:

- Python version
- Which example or method triggered the bug
- Full error traceback (redact any real IDs or tokens)
- What you expected vs what happened

---

## Code of conduct

Be respectful. Focus feedback on code, not people. Keep discussions constructive.
