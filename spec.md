# Amazon Fresh Japan Shopping Assistant — 仕様書

## 概要


ユーザーが自然言語（例：「カレーを作りたい」「今週1週間分の晩ご飯の食材」）を入力すると、AIが家族構成・ルール・予算を考慮して買い物リストを生成し、PlaywrightでAmazon Fresh Japanのカートに自動追加するWebアプリ。

**重要な制約**: アプリは絶対に購入を行わない。カートへの追加のみ実施し、最終的な購入はユーザー自身が行う。

## 主な機能

### 1. 買い物プランニング
- 自然言語でリクエストを入力（例：「カレー4人分」「今週の晩ご飯の食材」「来週分の朝食と昼食」）
- AIが以下を考慮してショッピングリストを生成：
  - 家族構成（人数・年齢層・食事制限）
  - ルール設定（除外品・ブランド・価格・メモ）
  - 予算制限
  - 過去の購入履歴（定期購入品の提案）
- ユーザーはリスト確認・**個別アイテムの編集/削除/追加**・修正後に実行
- **合計金額の概算表示**

### 2. 家族プロファイル（世帯設定）
- 家族人数（大人/子供の内訳）
- 各メンバーの食事制限・アレルギー
- 食の好み（和食中心、洋食多めなど）
- 設定画面からいつでも変更可能
- AIプランニング時に自動的に考慮

### 3. ルール管理
- `data/rules.yaml`でショッピングルールを管理
- 避けたい食材・商品（理由付き、例外キーワードあり）
- ブランド優先設定（例：シャンプーはパンテーン）
- 価格戦略（最安値/コスパ重視/プレミアム）
- 自由記述のメモ（有機野菜を優先など）
- **すべてUI画面から追加・編集・削除が可能**

### 4. カート自動追加
- Playwright（headless Chromium）でAmazon Fresh Japanを操作
- Amazon Cookieを使用してログイン状態を維持
- 商品検索 → ルール適用でフィルタ → カート追加
- SSEでリアルタイム進捗をフロントエンドに配信
- **実行前の確認ダイアログ**

### 5. Cookie管理
- Amazonセッションクッキーを安全にアップロード・管理
- Cookie有効性の確認機能

### 6. 履歴管理
- 過去の買い物セッションをSQLiteで保存
- セッション詳細（リクエスト・生成プラン・実行結果）の参照
- 過去のプランの再利用

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
| Backend | Python 3.12+, FastAPI, Pydantic v2, Playwright |
| AI | OpenAI API (gpt-5.4-mini) via Agents SDK |
| Package manager | UV |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS 4, shadcn/ui |
| Storage | YAML (rules), JSON (cookies, profile), SQLite (history) |
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
| GET | `/api/profile` | 家族プロファイル取得 |
| PUT | `/api/profile` | 家族プロファイル更新 |
| GET | `/api/settings/cookies/status` | Cookie有効性確認 |
| POST | `/api/settings/cookies` | Cookie JSON アップロード |
| DELETE | `/api/settings/cookies` | Cookie削除 |

## UX要件

- 初回アクセス時にセットアップガイド（Cookie設定 → 家族構成 → ルール設定）
- プラン生成後に個別アイテムの編集・削除・追加が可能
- 合計金額の概算を常に表示
- カート実行前に確認ダイアログを表示
- 日本語UIを徹底
- レスポンシブデザイン（モバイル対応）
