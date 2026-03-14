# リバース型アクセラ 自動収集システム

毎日10:00（JST）に日本国内のリバース型アクセラレーター・共創プログラムを自動収集し、メールで通知するPythonシステムです。

## 機能

- **実ウェブ検索** — Perplexity Sonarで10クエリを実行し、最大80件のURLを収集
- **スマートフィルタ** — 期限切れ・古い掲載日・重複を除外し、鮮度スコア順で上位15件に絞り込み
- **AI評価** — LLMがONESTRUCTION目線で参加お勧め度（1〜5）と募集中判定（is_active）を付与
- **メール通知** — 参加お勧め度の高い順にURLをリスト送信（0件でも必ず送信）
- **重複管理** — 一度送信したURLはローカルファイルで管理し再送しない

## ディレクトリ構成

```
reverse-accel-collector/
├── src/
│   ├── main.py                  # エントリーポイント
│   ├── config.py                # 環境変数・定数管理
│   ├── search/
│   │   └── openrouter_search.py # Perplexity Sonar検索（最大80件）
│   ├── crawl/
│   │   ├── fetch.py             # httpx 並行フェッチ
│   │   └── parse.py             # eiicon/peatix/creww + 汎用パーサー
│   ├── filter/
│   │   ├── deadline.py          # 期限フィルタ
│   │   ├── freshness.py         # 鮮度スコアリング・鮮度フィルタ
│   │   └── dedupe.py            # 重複排除（ローカルファイル管理）
│   ├── llm/
│   │   └── formatter.py         # LLM評価・整形
│   ├── notify/
│   │   └── emailer.py           # Gmail SMTP通知
│   ├── utils/
│   │   ├── logger.py            # ファイル+コンソール二重出力
│   │   └── dates.py             # JST日付処理
│   ├── data/
│   │   └── seen_urls.json       # 送信済みURL管理
│   └── logs/                    # 実行ログ（YYYY-MM-DD.log）
├── docs/                        # 仕様ドキュメント
│   ├── api-specification.md
│   ├── data-model.md
│   ├── folder-structure.md
│   └── requirements.md
├── .env                         # 環境変数（要作成）
├── requirements.txt
└── run.sh                       # cron実行ラッパー
```

## セットアップ

### 1. リポジトリをクローン

```bash
git clone git@github.com:youcan0827/reverse-accel-collector.git
cd reverse-accel-collector
```

### 2. 仮想環境を作成・依存パッケージをインストール

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 環境変数を設定

`.env` ファイルをプロジェクトルートに作成：

```env
OPENROUTER_API_KEY=sk-or-xxxxxxxx
EMAIL_FROM=your@gmail.com
EMAIL_TO=your@gmail.com
EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

| 変数名 | 取得方法 |
|---|---|
| `OPENROUTER_API_KEY` | [openrouter.ai/keys](https://openrouter.ai/keys) |
| `EMAIL_APP_PASSWORD` | Googleアカウント → セキュリティ → アプリパスワード（16文字） |

### 4. 動作確認

```bash
python -m src.main

# ログ確認
cat src/logs/$(date +%Y-%m-%d).log
```

### 5. cronで自動実行（毎日10:00 JST）

```bash
crontab -e
```

以下を追加（パスは環境に合わせて変更）：

```
0 10 * * * /path/to/reverse-accel-collector/run.sh >> /path/to/reverse-accel-collector/src/logs/cron.log 2>&1
```

## 処理フロー

```
[Perplexity Sonar検索] 10クエリ → 最大80件URL
        ↓
[HTML取得] httpx 並行フェッチ（concurrency=5）
        ↓
[重複排除] 送信済みURL（seen_urls.json）と照合
        ↓
[期限フィルタ] 過去・90日超を除外
        ↓
[鮮度フィルタ] 掲載日120日超 & 期限不明を除外
        ↓
[鮮度ソート] 上位15件に絞り込み
        ↓
[LLM評価] 参加お勧め度（1-5）・is_active判定
        ↓
[メール通知] お勧め度順にURLをリスト送信
```

## メール形式

```
=== リバース型アクセラ収集レポート (2026-03-09) ===

【案件リスト】3件

1. https://auba.eiicon.net/projects/xxxxx
   参加お勧め度: ★★★★☆ (4/5)

2. https://growth.creww.me/...
   参加お勧め度: ★★★☆☆ (3/5)

除外: 期限切れ 2件 / 重複 5件
```

## 優先収集ソース

| ソース | URL |
|---|---|
| AUBA（eiicon） | https://auba.eiicon.net/ |
| Peatix | https://peatix.com/ |
| creww Growth | https://growth.creww.me/ |

## コスト目安

| フェーズ | モデル | 概算 |
|---|---|---|
| 検索（10クエリ） | perplexity/sonar | ~0.05円/日 |
| LLM評価（最大15件） | gemini-flash | ~0.6円/日 |
| **合計** | | **~0.65円/日** |

## トラブルシューティング

### 解析失敗が多い

```bash
pip install lxml
```

`lxml` が未インストールの場合、HTML解析が全件失敗します。

### 検索結果が0件

- `OPENROUTER_API_KEY` が `.env` に設定されているか確認
- [openrouter.ai/activity](https://openrouter.ai/activity) でAPIの疎通を確認

### メールが届かない

- Googleの2段階認証が有効になっているか確認
- `EMAIL_APP_PASSWORD` はアプリパスワード（16文字）を使用（通常のパスワード不可）

## ライセンス

MIT
