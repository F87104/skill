# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is

Python CLI toolkit for AI-agent "skills" (SNS automation, Investor F content generation). There is no web server, Docker Compose, or npm workspace. See root `README.md` for the skill index.

### Dependency refresh (automatic)

On VM startup, dependencies are refreshed via the update script (`pip3 install …` + `playwright install chromium`). No manual install step is required after a fresh pull unless you add new packages to `skills/pyson_x_auto_tool/requirements.txt`.

### PATH

`pip3 install --user` puts CLI tools (`playwright`, etc.) in `~/.local/bin`. Add to PATH if a command is not found:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Running tools

| Goal | Command |
|------|---------|
| X auto-like (Selenium, repo root) | `python3 auto_like_selenium.py --loop --daemon` |
| X auto-like (Playwright, recommended) | `python3 skills/pyson_x_auto_tool/auto_like_v11.3_smart_follow.py --loop` |
| Generate tweet drafts from news | `OPENAI_API_KEY=... python3 skills/investor_f/trend_oracle_v2.8.0_pro_news_triple_choice.py` |
| Substack auto-like | Unzip `skills/substack_auto_tool/substack-auto-like-safe.zip`, configure `config.json`, then `python3 main.py` |

Daemon status/stop for root Selenium tool: `--status` / `--stop`.

### Secrets and first-run setup

Copy `skills/pyson_x_auto_tool/.env.example` → `skills/pyson_x_auto_tool/.env` for X API + OpenAI keys. Browser-based X tools require a **one-time manual X login** on first run (`--setup` for Playwright tools); session is stored under `~/.prometheus_*`.

Substack needs a `substack.sid` cookie in `config.json` (see `skills/substack_auto_tool/SKILL.md`).

### Lint / tests

No pytest suite or linter config in the repo. Practical checks:

- Syntax: `python3 -m compileall -q skills auto_like_selenium.py` (note: `skills/pyson_x_auto_tool/auto_follow.py` has a pre-existing syntax error)
- Smoke: import `fetch_pro_news` from the trend_oracle script, or run `--help` on CLI entry points

### Known gaps

- `skills/pyson_x_auto_tool/prometheus.py` is incomplete (`core/` missing modules); use individual scripts instead.
- `prometheus_dashboard.py` needs extra deps: `pip3 install pandas plotly` (not in `requirements.txt`).
- Trend Oracle full flow needs `OPENAI_API_KEY`; news fetch alone works without it.
