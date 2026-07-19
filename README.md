# TROHUB Skills

Agent Skills for the [TROHUB API](https://open.trohub.com/) — an IP (intellectual property) risk-checking service for cross-border e-commerce sellers. Covers US/EU design patent search, US word-trademark conflict checks, graphic trademark image search, global copyright/artwork tracing, and TRO (Temporary Restraining Order) lawsuit monitoring.

> **🌐 中文版文档** — 如果你更习惯阅读中文，请查看 [README_zh.md](./README_zh.md)。
> **📖 Chinese version** — If you prefer reading in Chinese, check out [README_zh.md](./README_zh.md).

Built on the open [Agent Skills](https://agentskills.io) standard (`SKILL.md` + optional `scripts/`/`references/`), so the same skill folder works across Claude Code, Codex CLI, Cursor, and other compatible AI coding tools — install once, no rewriting needed per tool.

## What's included

```
trohub-ip-check/
├── SKILL.md                  — main skill instructions (read this first)
├── scripts/
│   ├── trohub_client.py      — ready-to-run Python client + CLI
│   ├── requirements.txt
│   └── README.md             — client usage examples
└── references/
    ├── tro-cases.md          — TRO lawsuit monitoring
    ├── infringement-tasks.md — combined image-search task lifecycle
    ├── patents.md            — design patent search + citation lookup
    ├── trademarks.md         — word-mark + graphic trademark search
    ├── copyright.md          — global copyright/artwork search
    └── errors.md             — error codes & rate limits
```

## Prerequisites

You need a TROHUB account and API key before any tool can actually call the API (the skill only teaches the agent *how* to call it — it doesn't include credentials).

1. Sign up / log in at [app.trohub.com](https://app.trohub.com)
2. Get your API key from **Account → API Keys**: `https://app.trohub.com/account/api-keys`

Keep both handy — every tool below needs them as environment variables:

```bash
export TROHUB_API_KEY="your_api_key_here"
export TROHUB_BASE_URL="https://api.trohub.com/v1"
```

Add these two lines to your shell profile (`~/.zshrc`, `~/.bashrc`, etc.) so you don't have to re-set them every session.

---

## Install & use in Claude Code

**Install**

```bash
git clone https://github.com/easyamz/trohub-skills.git

# Personal — available in every project
cp -r trohub-skills/trohub-ip-check ~/.claude/skills/

# Project-only — commit it to a specific repo so your team gets it too
mkdir -p .claude/skills
cp -r trohub-skills/trohub-ip-check .claude/skills/
```

**Verify**

Start (or restart) Claude Code, then ask:
```
what skills do you have available?
```
`trohub-ip-check` should appear in the list.

**Use it**

Just describe what you need in plain language — Claude Code matches your request against the skill's description and loads it automatically:
```
check this product photo for design patent risk before I list it: https://example.com/product.jpg, it's a wireless headphone
```
```
scan this listing title for trademark conflicts: "Ergonomic Chair"
```

---

## Install & use in Codex CLI

**Install**

```bash
git clone https://github.com/easyamz/trohub-skills.git

# Personal — available in every project
cp -r trohub-skills/trohub-ip-check ~/.codex/skills/

# Project-only — commit it so teammates who clone the repo get it too
mkdir -p .codex/skills
cp -r trohub-skills/trohub-ip-check .codex/skills/
```

Codex looks these up in priority order: current-directory `.codex/skills/` → repo-root `.codex/skills/` → `~/.codex/skills/` (personal) → system-wide.

**Verify**

Start a new Codex session (skills are loaded at session start, so restart if Codex was already running), then run:
```
/skills
```
`trohub-ip-check` should be listed with its description.

**Use it**

Either let it trigger automatically from a plain-language request, or reference the skill by name if you want to be explicit:
```
using the trohub-ip-check skill, check whether this logo conflicts with any registered US graphic trademark: https://example.com/logo.png
```

---

## Install & use in Cursor

Cursor supports Agent Skills natively (Cursor ≥ 2.4). Cursor currently discovers skills at the **project level**, so commit the folder into the repo you're working in:

```bash
git clone https://github.com/easyamz/trohub-skills.git

mkdir -p .cursor/skills
cp -r trohub-skills/trohub-ip-check .cursor/skills/
```

**Verify**

Restart Cursor (or reload the window) so it re-scans skill directories, then in the Agent chat type `/` and search for `trohub-ip-check` — it should show up in the picker.

**Use it**

- Automatic: just describe the task in Agent chat and Cursor will pull the skill in when relevant.
- Manual: type `/` in the Agent input and select `trohub-ip-check` from the menu, then add your request.

---

## Other Agent-Skills-compatible tools

The Agent Skills format is also supported (with varying degrees of maturity as of mid-2026) by tools like Windsurf, Cline, OpenCode, Gemini CLI, and others. The general pattern is the same everywhere:

1. Find the tool's skill directory (usually something like `~/.<tool>/skills/` or `.<tool>/skills/` in the project root — check that tool's own docs, since exact paths and whether personal vs. project-level installs are supported still varies by tool).
2. Copy `trohub-ip-check/` (the whole folder, not just `SKILL.md`) into that directory.
3. Restart the tool so it re-scans for skills.
4. Describe your task in plain language, or invoke the skill explicitly if the tool supports that.

If a tool doesn't yet support Agent Skills at all, you can usually still get value out of this repo by manually pasting the contents of `trohub-ip-check/SKILL.md` into that tool's own "custom instructions"/"rules" file (e.g. `.cursorrules`, `AGENTS.md`, a system prompt) — you'll lose automatic discovery, but the instructions themselves still apply.

---

## Configuration reference

| Env var | Required | Description |
|---|---|---|
| `TROHUB_API_KEY` | yes | From `https://app.trohub.com/account/api-keys` |
| `TROHUB_BASE_URL` | yes | Always `https://api.trohub.com/v1` — set it and forget it |

The bundled `scripts/trohub_client.py` reads both from the environment automatically — see `trohub-ip-check/scripts/README.md` for full CLI and library usage.

## Troubleshooting

- **Skill doesn't show up after copying it in.** Most tools only scan for skills at startup — fully restart the tool (not just open a new chat/tab).
- **Folder is in the right place but still not detected.** Double-check the nesting: you should end up with `.../skills/trohub-ip-check/SKILL.md`, not `.../skills/SKILL.md` or `.../skills/trohub-skills/trohub-ip-check/SKILL.md`.
- **API calls fail with an auth error.** Confirm `TROHUB_API_KEY` is set in the same shell/session the tool is running from — a variable exported in one terminal tab won't be visible to a GUI app opened separately.
- **`VALIDATION_BAD_REQUEST` or similar 400s.** See `trohub-ip-check/references/errors.md` for the full error-code table and common causes.

## License

MIT — see [LICENSE](./LICENSE).
