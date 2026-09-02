# Dev Setup Notes — code-quality guardrails for any project

My personal cheat-sheet: the basic barriers to set up so a project stays clean.
Keep it simple — pick the tool for each slot, wire up the two enforcement layers.

## The mental model: 5 slots + 2 enforcement layers

Every project has the same 5 "slots." Only the tool changes per language.

| # | Slot (what it guards) | Plain word |
|---|---|---|
| 1 | Environment & dependencies | the pantry — right libraries, right versions |
| 2 | Format + lint | spell-checker + tidier |
| 3 | Type check | fact-checker (value types line up) |
| 4 | Tests | quality tester (does it actually work) |
| 5 | Enforcement | the bouncer — auto-runs 2–4 |

**2 enforcement layers (always do both):**
- **Local** — runs at `git commit` on your machine (fast, catches early).
- **Remote (CI)** — runs on GitHub at push/PR (backstop; local hooks can be skipped).

## Tool per language

| Slot | Python | JavaScript / TypeScript | Rust | Go |
|---|---|---|---|---|
| 1 Env & deps | uv | pnpm / npm | cargo | go mod |
| 2 Format + lint | ruff | prettier + eslint | rustfmt + clippy | gofmt + go vet |
| 3 Types | ty (or mypy) | tsc | (compiler) | (compiler) |
| 4 Tests | pytest | vitest / jest | cargo test | go test |
| 5 Local enforce | prek / pre-commit | husky | pre-commit | pre-commit |
| 5 Remote enforce | GitHub Actions (CI) | GitHub Actions | GitHub Actions | GitHub Actions |

Config lives in text files: **pyproject.toml** (Python), **package.json** (JS),
**Cargo.toml** (Rust). Enforcement config: **.pre-commit-config.yaml** + a CI
file under **.github/workflows/**. (YAML/TOML/JSON are just formats, not tools.)

## Python quick-start (what I actually run)

```bash
uv init --python 3.12
uv add --dev ruff ty pytest prek
# add ruff + pytest config to pyproject.toml   (see Reference configs below)
# add .pre-commit-config.yaml  (local hooks)   (see Reference configs below)
# add .github/workflows/ci.yml (remote checks)
uv run prek install            # activate the local hook (once per clone)
```

Daily: `uv run pytest` · `uv run ruff check` · `uv run ruff format` · `uv run ty check`

## Reference configs (copy-paste)

**Where config goes is standardized** (ruff → `[tool.ruff]`, pytest →
`[tool.pytest.ini_options]`, pre-commit → `repos → hooks`). **What you put in** is
convention — these are solid, non-fussy defaults.

### `pyproject.toml` — ruff + pytest

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
# E/W pycodestyle, F pyflakes (bugs), I import-sort,
# B bug-prone, UP modern-Python, SIM simplifications
select = ["E", "W", "F", "I", "B", "UP", "SIM"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-q"
```

### `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1
    hooks:
      - id: gitleaks

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.5
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format

  - repo: local          # for tools already in the venv (uv run ...)
    hooks:
      - id: ty
        name: ty (type check)
        entry: uv run ty check
        language: system
        pass_filenames: false
        types: [python]
      - id: pytest
        name: pytest
        entry: uv run pytest
        language: system
        pass_filenames: false
        types: [python]
```

Notes: `repo` + `rev` + `hooks` is the fixed shape; **pin `rev` to a version tag**
(not a branch) so checks don't change silently. `repo: local` is the escape hatch
for tools already installed in your project. The ruff rule set is the main thing
people tune.

## Tier 1 add-ons (worth it on almost every project)

- **Secret scanning** (gitleaks) — blocks committing keys/passwords. Cheapest
  insurance against the worst mistake. Add as a hook + CI job.
- **Dependabot** (`.github/dependabot.yml`) — weekly PRs for dependency + security
  updates. Set-and-forget.
- **.editorconfig** — consistent indentation/line-endings across editors.
- **Branch protection** — require CI to pass before merging to `main`. Turns CI
  from advice into a hard gate. ⚠️ Free only on **public** repos; private needs
  paid GitHub Pro. On a free private repo, rely on CI signal + discipline instead.

## How much to set up (scale to the project)

- **Throwaway script:** slots 1–2 (uv + ruff). Done.
- **Real solo project:** all 5 slots + Tier 1. Tests + CI pay off when you return
  months later.
- **Team / shared:** all of the above, stricter, + branch protection as a gate.

## The honest limit

Tools catch *mechanical* problems — they're the floor, not the ceiling. Real
quality is **small changes, clear names, simplicity, honest error handling, and
reading your own diffs**. No tool checks those; they're on you.
