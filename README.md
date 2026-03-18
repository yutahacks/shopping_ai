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
| AI | OpenAI Agents SDK (GPT-4o) |
| Package Manager | UV |
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS 4, shadcn/ui |
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
```

### Docker

```bash
OPENAI_API_KEY=sk-xxx docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API ドキュメント: http://localhost:8000/docs

## 開発

```bash
# テスト
cd backend
uv run pytest

# Lint & Format
uv run ruff check app/
uv run ruff format app/

# 型チェック
uv run mypy app/

# フロントエンド
cd frontend
npm run lint
npm run build
```

### Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

## プロジェクト構成

```
shopping_ai/
├── backend/            # Python FastAPI
│   ├── app/
│   │   ├── api/        # エンドポイント
│   │   ├── models/     # Pydantic モデル
│   │   ├── services/   # ビジネスロジック
│   │   ├── automation/ # Playwright 自動化
│   │   └── storage/    # SQLite 永続化
│   └── tests/
├── frontend/           # Next.js TypeScript
│   ├── app/            # App Router ページ
│   ├── components/     # React コンポーネント
│   ├── hooks/          # カスタムフック
│   └── lib/            # API クライアント・型定義
├── data/               # ランタイムデータ
├── infra/              # Azure Bicep IaC
└── docker-compose.yml
```

## ライセンス

個人・家庭用途のみ。Amazon 利用規約の範囲内での利用を想定しています。
