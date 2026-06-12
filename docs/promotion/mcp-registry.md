# Submitting LETHE to MCP discovery channels

Two channels, in order of impact.

---

## 1. Official MCP Registry (registry.modelcontextprotocol.io)

This is the registry Claude Code and other clients can pull from. Submission is done with the
`mcp-publisher` CLI, authenticated via your GitHub account (namespace
`io.github.jesusgarcia9009/...`).

**Prerequisites already done in this repo:**
- `server.json` at the repo root (the registry manifest, version 0.6.1).
- `mcp-name: io.github.jesusgarcia9009/lethe` annotation in `README.md` — proves you own the
  PyPI package `lethe-llm-context`. **This must be present in the published PyPI README**, so
  publish 0.6.1 to PyPI *before* submitting (see step 0).

**Step 0 — publish 0.6.1 to PyPI** (the registry validates against the live package):
```bash
python -m twine upload dist/*       # uploads lethe_llm_context 0.6.1
```

**Step 1 — install the publisher CLI** (Go-based; one option):
```bash
# macOS/Linux (Homebrew)
brew install mcp-publisher
# or download a release binary from:
# https://github.com/modelcontextprotocol/registry/releases
```

**Step 2 — authenticate with GitHub:**
```bash
mcp-publisher login github
```

**Step 3 — publish the server:**
```bash
mcp-publisher publish      # reads ./server.json
```

The registry fetches `lethe-llm-context` from PyPI, finds the `mcp-name` annotation in its
README, confirms ownership, and lists the server. Re-run `publish` whenever you ship a new
version (bump `version` in `server.json`).

> If you don't want to install the CLI, this step can be done later — the package is already
> installable from PyPI; the registry just improves discovery.

---

## 2. awesome-mcp-servers (community list)

A simple PR to a popular curated list — high visibility, no CLI needed.

- Repo: https://github.com/punkpeye/awesome-mcp-servers
- Fork it, add this line under an appropriate category (e.g. "📊 Memory / Context"), keep the
  list alphabetical:

```markdown
- [LETHE](https://github.com/JesusGarcia9009/lethe-engineering) - Context garbage collector for LLM agents: offload large tool outputs and recall them on demand to save tokens. Works in Claude Code & Codex.
```

- Open the PR with a one-line description. Done.

---

## 3. After listing

- Bump `server.json` `version` on every release and re-`publish`.
- Add the registry badge to the README once accepted.
