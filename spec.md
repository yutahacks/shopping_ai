# Amazon Fresh Japan Shopping Assistant — 仕様書

## 概要

ユーザーが自然言語（例：「カレーを作りたい」）を入力すると、AIが買い物リストを生成し、PlaywrightでAmazon Fresh Japanのカートに自動追加するWebアプリ。

**重要な制約**: アプリは絶対に購入を行わない。カートへの追加のみ実施し、最終的な購入はユーザー自身が行う。

## 主な機能

### 1. 買い物プランニング
- 自然言語でリクエストを入力（例：「今週の晩ご飯の食材」「カレー4人分の材料」）
- Claudeが現在の`rules.yaml`設定を考慮してショッピングリストを生成
- ユーザーはリスト確認・修正後に実行

### 2. ルール管理
- `data/rules.yaml`でショッピングルールを管理
- 避けたい食材・商品（例：アレルギー食材）
- ブランド優先設定（例：シャンプーはパンテーン）
- 価格戦略（最安値/コスパ重視/プレミアム）
- 自由記述のメモ（有機野菜を優先など）

### 3. カート自動追加
- Playwright（headless Chromium）でAmazon Fresh Japanを操作
- Amazon Cookieを使用してログイン状態を維持
- 商品検索 → ルール適用でフィルタ → カート追加
- SSEでリアルタイム進捗をフロントエンドに配信

### 4. Cookie管理
- Amazonセッションクッキーを安全にアップロード・管理
- Cookie有効性の確認機能

### 5. 履歴管理
- 過去の買い物セッションをSQLiteで保存
- セッション詳細（リクエスト・生成プラン・実行結果）の参照

## セキュリティ要件

- Azure App Gateway WAF v2でIPホワイトリスト制限（自宅IPのみ許可）
- APIキーはAzure Key Vaultに保存
- CookieはログやAPIレスポンスに含めない
- コンテナはVNet内部のみ（外部から直接アクセス不可）

## 制約

- **購入禁止**: 決済・購入ページへの遷移は絶対に行わない
- Amazon利用規約の範囲内での利用を想定
- 個人・家庭用途のみ

## 技術スタック

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI, Pydantic v2, Playwright, Anthropic SDK |
| Package manager | UV |
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| AI | Claude claude-sonnet-4-6 (structured output) |
| Storage | YAML (rules), JSON (cookies), SQLite (history) |
| Container | Docker, docker-compose |
| Cloud | Azure Container Apps + App Gateway WAF (IP制限) |

## API概要

| Method | Path | Description |
|---|---|---|
| POST | `/api/shopping/plan` | 自然言語 → ShoppingPlan生成 |
| GET | `/api/shopping/sessions` | 過去セッション一覧 |
| GET | `/api/shopping/sessions/{id}` | セッション詳細 |
| POST | `/api/cart/execute` | プランをカートに追加実行 |
| GET | `/api/cart/status/{id}` | SSEで進捗ストリーム |
| GET | `/api/rules` | ルール取得 |
| PUT | `/api/rules` | ルール全体更新 |
| PATCH | `/api/rules/avoid` | 避けるリスト更新 |
| PATCH | `/api/rules/brands` | ブランドルール更新 |
| PATCH | `/api/rules/preferences` | 価格設定更新 |
| GET | `/api/settings/cookies/status` | Cookie有効性確認 |
| POST | `/api/settings/cookies` | Cookie JSON アップロード |
| DELETE | `/api/settings/cookies` | Cookie削除 |
