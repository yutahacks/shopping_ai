# CLAUDE.md — Shopping AI Project

## Overview

Amazon Fresh Japan Shopping Assistant: 自然言語 → AI買い物リスト生成 → Playwrightでカート自動追加

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI, Pydantic v2, Playwright |
| AI | OpenAI API (gpt-5.4-mini) via Agents SDK |
| Package manager | UV |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS 4, shadcn/ui |
| Storage | YAML (rules), JSON (cookies/profile), SQLite (history) |
| Container | Docker, docker-compose |
| Cloud | Azure Container Apps + App Gateway WAF |

## Project Structure

```
shopping_ai/
├── backend/           # Python FastAPI backend
│   ├── app/
│   │   ├── api/       # Route handlers
│   │   ├── models/    # Pydantic models
│   │   ├── services/  # Business logic
│   │   ├── automation/# Playwright browser automation
│   │   └── storage/   # SQLite & file persistence
│   └── tests/
├── frontend/          # Next.js TypeScript frontend
│   ├── app/           # App Router pages
│   ├── components/    # React components
│   ├── hooks/         # Custom React hooks
│   └── lib/           # API client, types, utils
├── scripts/           # Development scripts
│   ├── hooks/         # Git hooks (pre-commit, commit-msg)
│   └── setup-hooks.sh # Hook installer for new contributors
├── config/            # Default config templates (rules.yaml.default, profile.json.default)
├── data/              # Runtime data (gitignored — auto-populated from config/)
├── .claude/           # Claude Code settings (hooks for auto-linting)
└── infra/             # Azure Bicep IaC
```

## Initial Setup

```bash
# 1. Clone and install dependencies
cd backend && uv sync --extra dev
cd ../frontend && npm install

# 2. Install git hooks (required for all contributors)
bash scripts/setup-hooks.sh
```

## Development Commands

### Backend
```bash
cd backend
uv sync --extra dev                              # Install with dev dependencies
uv run uvicorn app.main:app --reload --port 8000 # Start dev server
uv run pytest                                    # Run all tests
uv run pytest -m "not integration"               # Unit tests only
uv run pytest --cov=app --cov-report=term-missing # Tests with coverage
uv run ruff check .                              # Lint
uv run ruff format .                             # Format
uv run mypy app/                                 # Type check (strict + pydantic plugin)
```

### Frontend
```bash
cd frontend
npm install                      # Install dependencies
npm run dev                      # Start dev server (port 3000)
npm run build                    # Production build
npm run lint                     # ESLint
npm run typecheck                # TypeScript strict check (tsc --noEmit)
npm run test                     # Run tests (vitest)
```

### Docker
```bash
docker compose up --build        # Start full stack
docker compose up backend        # Backend only
```

## Quality Gates

### Pre-commit Hook (7 checks, auto-runs on `git commit`)
| # | Check | Tool | Layer |
|---|---|---|---|
| 1 | Lint | `ruff check` | Backend |
| 2 | Format | `ruff format --check` | Backend |
| 3 | Type check | `mypy app/` (strict) | Backend |
| 4 | Unit tests | `pytest -m "not integration"` | Backend |
| 5 | Lint | `eslint` | Frontend |
| 6 | Type check | `tsc --noEmit` | Frontend |
| 7 | Unit tests | `vitest run` | Frontend |

### Commit-msg Hook
Enforces [Conventional Commits](https://www.conventionalcommits.org/):
```
<type>(<scope>): <description>
```
Allowed types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `ci`, `perf`, `style`, `build`, `revert`

### CI (GitHub Actions)
Runs on push to `main` and all PRs. Mirrors pre-commit checks plus `npm run build` and coverage reporting.

### Claude Code Hooks (`.claude/settings.json`)
- **PostToolUse (Edit/Write)**: Auto-runs `ruff check --fix` + `ruff format` on Python files
- **PostToolUse (Edit/Write)**: Auto-runs `eslint` on TypeScript/TSX files

### Branch Protection (main)
- Direct push to main is blocked
- CI status checks must pass before merge
- Force push is disabled

## Conventions

### Python (Backend)
- Google-style docstrings on all classes and public methods
- Pydantic v2 models for all data structures (mypy plugin: `pydantic.mypy`)
- Async-first: all I/O operations are async
- Type annotations on all function signatures
- ruff for linting & formatting, mypy strict mode for type checking
- Tests: pytest + pytest-asyncio + pytest-cov, `tests/unit/` and `tests/integration/`
- Coverage: `pytest-cov` with `--cov=app`, threshold enforced in CI

### TypeScript (Frontend)
- Strict TypeScript — no `any` types
- All API types defined in `lib/types.ts`
- Custom hooks for API state management (`hooks/use*.ts`)
- shadcn/ui for UI components
- Japanese UI text throughout
- Tests: vitest + @testing-library/react, `__tests__/` directory
- Coverage: `@vitest/coverage-v8` with v8 provider

### Git
- Issue-driven development: create issue first, then branch `feature/{issue-number}-short-description`
- Pre-commit hooks enforce: ruff check, ruff format, mypy, pytest, eslint, tsc, vitest (7 checks)
- Conventional commits enforced by commit-msg hook: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`, `ci:`, `perf:`, `style:`, `build:`, `revert:`
- Branch protection: main requires CI to pass, no force push
- New contributors: run `bash scripts/setup-hooks.sh` after cloning

### API Design
- RESTful endpoints under `/api/`
- Pydantic models for request/response validation
- SSE for real-time progress streaming
- Japanese error messages for user-facing errors

## Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `DATA_DIR` | Data directory path (default: `/data`) |
| `DATABASE_PATH` | SQLite DB path |
| `RULES_PATH` | Shopping rules YAML path |
| `COOKIES_PATH` | Amazon cookies JSON path |
| `BROWSER_HEADLESS` | Playwright headless mode (default: `true`) |
| `CONFIG_DIR` | Config templates directory (default: `/config`) |
| `LOG_LEVEL` | Logging level (default: `INFO`) |
| `API_SECRET_KEY` | Bearer token for API auth (empty = no auth) |

## Development Approach

This project follows **spec-driven development**: `spec.md` is the source of truth for features and requirements. All implementation should be validated against the spec.

## Critical Safety Constraint

**The app MUST NEVER navigate to checkout/purchase pages.** Cart addition only — the user completes the purchase manually.
