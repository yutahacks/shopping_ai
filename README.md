# Amazon Fresh Japan Shopping Assistant

自然言語で買い物リクエストを入力すると、AIが家族構成・ルール・予算を考慮してショッピングリストを生成し、Playwright で Amazon Fresh Japan のカートに自動追加する Web アプリ。

> **重要**: アプリは絶対に購入を行いません。カートへの追加のみ実施し、最終的な購入はユーザー自身が行います。

## 主な機能

- **AI 買い物プランニング** — 「カレー4人分」「今週の晩ご飯」などの自然言語から買い物リストを自動生成
- **家族プロファイル** — 家族人数・年齢層・アレルギー・苦手食材・予算を設定し、AI が自動考慮
- **ショッピングルール** — 除外食材、ブランド優先、価格戦略（最安値/コスパ/プレミアム）を管理
- **カート自動追加** — Playwright でAmazon Fresh を操作し、商品検索→ルール適用→カート追加を自動化
- **リアルタイム進捗** — SSE で実行状況をフロントエンドにストリーミング
- **履歴管理** — 過去の買い物セッションを保存・参照

## 技術スタック

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI, Pydantic v2, Playwright |
| AI | OpenAI Agents SDK (gpt-5.4-mini) |
| Package Manager | UV |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS 4, shadcn/ui |
| Storage | YAML (rules), JSON (cookies, profile), SQLite (history) |
| Container | Docker, docker-compose |
| Cloud | Azure Container Apps + App Gateway WAF (IP制限) |

## セットアップ

### 前提条件

- Python 3.12+
- Node.js 20+
- [UV](https://docs.astral.sh/uv/) (Python パッケージマネージャ)
- Docker & docker-compose (コンテナ実行時)

### ローカル開発

```bash
# 環境変数の設定
cp .env.example .env
# OPENAI_API_KEY を設定

# バックエンド
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000

# フロントエンド (別ターミナル)
cd frontend
npm install
npm run dev

# Git hooks のインストール (初回のみ・必須)
bash scripts/setup-hooks.sh
```

### Docker

```bash
OPENAI_API_KEY=sk-xxx docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API ドキュメント: http://localhost:8000/docs

## 開発

### コマンド一覧

```bash
# --- バックエンド ---
cd backend
uv run pytest                                     # テスト実行
uv run pytest -m "not integration"                # ユニットテストのみ
uv run pytest --cov=app --cov-report=term-missing # カバレッジ付きテスト
uv run ruff check .                               # Lint
uv run ruff format .                              # フォーマット
uv run mypy app/                                  # 型チェック (strict)

# --- フロントエンド ---
cd frontend
npm run lint                                      # ESLint
npm run typecheck                                 # TypeScript チェック (tsc --noEmit)
npm run test                                      # テスト実行 (vitest)
npm run build                                     # プロダクションビルド
```

### Git Hooks

`bash scripts/setup-hooks.sh` で以下の hooks がインストールされます：

**pre-commit** — コミット前に自動実行（全7チェック）:
1. `ruff check` — Python lint
2. `ruff format --check` — Python フォーマット確認
3. `mypy app/` — Python 型チェック (strict)
4. `pytest` — Backend ユニットテスト (40件)
5. `eslint` — TypeScript lint
6. `tsc --noEmit` — TypeScript 型チェック
7. `vitest run` — Frontend テスト (13件)

**commit-msg** — コミットメッセージの形式を強制:
```
<type>(<scope>): <description>

# 例:
feat: add shopping cart API
fix(planner): handle empty item list
docs: update README with setup instructions
```
使用可能な type: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `ci`, `perf`, `style`, `build`, `revert`

### CI/CD

GitHub Actions が push / PR 時に自動実行:
- **Backend**: ruff check → ruff format → mypy → pytest (カバレッジ付き)
- **Frontend**: ESLint → tsc → build → vitest

### Branch Protection

- `main` への直接 push は禁止
- CI が全てパスしないとマージ不可
- Force push は無効化

### Claude Code Hooks

`.claude/settings.json` で Claude Code 使用時に自動 lint:
- Python ファイル編集後 → `ruff check --fix` + `ruff format` を自動実行
- TypeScript ファイル編集後 → `eslint` を自動実行

## プロジェクト構成

```
shopping_ai/
├── backend/            # Python FastAPI
│   ├── app/
│   │   ├── api/        # エンドポイント
│   │   ├── models/     # Pydantic モデル
│   │   ├── services/   # ビジネスロジック
│   │   ├── automation/ # Playwright 自動化
│   │   ├── middleware/  # 認証ミドルウェア
│   │   └── storage/    # SQLite 永続化
│   └── tests/          # pytest テスト (unit/ + integration/)
├── frontend/           # Next.js TypeScript
│   ├── app/            # App Router ページ
│   ├── components/     # React コンポーネント
│   ├── hooks/          # カスタムフック
│   ├── lib/            # API クライアント・型定義
│   └── __tests__/      # vitest テスト
├── scripts/            # 開発スクリプト
│   ├── hooks/          # Git hooks (pre-commit, commit-msg)
│   └── setup-hooks.sh  # Hook インストーラー
├── .claude/            # Claude Code 設定 (auto-lint hooks)
├── .github/            # GitHub Actions CI, Issue/PR テンプレート
├── config/             # デフォルト設定テンプレート
├── data/               # ランタイムデータ (gitignored)
├── infra/              # Azure Bicep IaC
└── docker-compose.yml
```

## ライセンス

個人・家庭用途のみ。Amazon 利用規約の範囲内での利用を想定しています。
