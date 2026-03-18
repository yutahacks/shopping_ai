# CLAUDE.md — Shopping AI Project

## Overview

Amazon Fresh Japan Shopping Assistant: 自然言語 → AI買い物リスト生成 → Playwrightでカート自動追加

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI, Pydantic v2, Playwright |
| AI | OpenAI API (GPT-4o) |
| Package manager | UV |
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS 4, shadcn/ui |
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
├── data/              # Runtime data (rules.yaml, cookies.json, profile.json)
└── infra/             # Azure Bicep IaC
```

## Development Commands

### Backend
```bash
cd backend
uv sync                          # Install dependencies
uv sync --extra dev              # Install with dev dependencies
uv run uvicorn app.main:app --reload --port 8000  # Start dev server
uv run pytest                    # Run tests
uv run pytest -m "not integration"  # Skip integration tests
uv run ruff check .              # Lint
uv run ruff format .             # Format
uv run mypy app/                 # Type check
```

### Frontend
```bash
cd frontend
npm install                      # Install dependencies
npm run dev                      # Start dev server (port 3000)
npm run build                    # Production build
npm run lint                     # ESLint
```

### Docker
```bash
docker compose up --build        # Start full stack
docker compose up backend        # Backend only
```

## Conventions

### Python (Backend)
- Google-style docstrings on all classes and public methods
- Pydantic v2 models for all data structures
- Async-first: all I/O operations are async
- Type annotations on all function signatures
- ruff for linting & formatting, mypy strict mode for type checking
- Tests: pytest + pytest-asyncio, `tests/unit/` and `tests/integration/`

### TypeScript (Frontend)
- Strict TypeScript — no `any` types
- All API types defined in `lib/types.ts`
- Custom hooks for API state management (`hooks/use*.ts`)
- shadcn/ui for UI components
- Japanese UI text throughout

### Git
- Issue-driven development: create issue first, then branch `feature/{issue-number}-short-description`
- Pre-commit hooks enforce linting and type checking
- Commit messages in English, imperative mood

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

## Critical Safety Constraint

**The app MUST NEVER navigate to checkout/purchase pages.** Cart addition only — the user completes the purchase manually.
