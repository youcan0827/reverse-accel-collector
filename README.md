# リバース型アクセラ 自動収集システム

毎日10:00（JST）に日本国内のリバース型アクセラレーター・共創プログラムを自動収集し、Notionに登録してメール通知を送るPythonシステムです。

## 機能

- **自動検索** — OpenRouter（Perplexity Sonar）で6クエリを実行し、最大35件のURLを収集
- **スマートフィルタ** — 期限切れ・90日超・重複を除外し、鮮度スコア順で上位5件に絞り込み
- **AI構造化** — Gemini 2.0 FlashでONESTRUCTION目線のJSON評価を自動生成
- **Notion登録** — 15プロパティのデータベースへ重複なく登録
- **メール通知** — 0件でも必ず結果レポートをGmail送信

## ディレクトリ構成

```
docs/
├── src/
│   ├── main.py                  # エントリーポイント（8ステップ統合）
│   ├── config.py                # 環境変数・定数管理
│   ├── search/
│   │   └── openrouter_search.py # OpenRouter検索（最大35件）
│   ├── crawl/
│   │   ├── fetch.py             # httpx 並行フェッチ
│   │   └── parse.py             # eiicon/peatix/creww + 汎用パーサー
│   ├── filter/
│   │   ├── deadline.py          # 期限フィルタ
│   │   ├── freshness.py         # 鮮度スコアリング
│   │   └── dedupe.py            # 重複排除
│   ├── llm/
│   │   └── formatter.py         # LLM構造化整形
│   ├── notion/
│   │   ├── client.py            # Notion API CRUD
│   │   └── mapper.py            # Notionプロパティ変換
│   ├── notify/
│   │   └── emailer.py           # Gmail SMTP通知
│   ├── utils/
│   │   ├── logger.py            # ファイル+コンソール二重出力
│   │   └── dates.py             # JST日付処理
│   └── logs/                    # 実行ログ（YYYY-MM-DD.log）
├── .env.example                 # 環境変数テンプレート
├── requirements.txt
└── run.sh                       # cron実行ラッパー
```

## セットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/YOUR_USERNAME/reverse-accel-collector.git
cd reverse-accel-collector
```

### 2. 仮想環境を作成・依存パッケージをインストール

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 環境変数を設定

```bash
cp .env.example .env
```

`.env` を開いて以下の4種類のキーを入力してください。

| 変数名 | 取得方法 |
|---|---|
| `OPENROUTER_API_KEY` | [openrouter.ai/keys](https://openrouter.ai/keys) |
| `NOTION_TOKEN` | [notion.so/my-integrations](https://www.notion.so/my-integrations) でインテグレーション作成 |
| `NOTION_DATABASE_ID` | 後述の「Notionセットアップ」を参照 |
| `EMAIL_APP_PASSWORD` | Googleアカウント → セキュリティ → アプリパスワード |

### 4. Notionセットアップ

#### 4-1. インテグレーションの作成

1. [notion.so/my-integrations](https://www.notion.so/my-integrations) でインテグレーションを新規作成
2. 発行された **Internal Integration Secret** を `NOTION_TOKEN` に設定

#### 4-2. データベースの作成

以下のスクリプトで、指定したNotionページ内にデータベースを自動作成できます。

```bash
# 親ページIDを引数として実行（NotionページURLの末尾32文字）
python3 - <<'EOF'
import httpx, os, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path('.env'))
TOKEN = os.environ['NOTION_TOKEN']
PAGE_ID = input('NotionページIDを入力: ').strip().replace('-', '')

headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
}

body = {
    'parent': {'type': 'page_id', 'page_id': PAGE_ID},
    'title': [{'type': 'text', 'text': {'content': 'リバース型アクセラ 収集DB'}}],
    'properties': {
        'タイトル': {'title': {}},
        '主催': {'rich_text': {}},
        '目的・狙い': {'rich_text': {}},
        '企画の概要': {'rich_text': {}},
        '企画のキモ': {'rich_text': {}},
        '実現可能性': {'rich_text': {}},
        'ROI': {'rich_text': {}},
        '体制': {'rich_text': {}},
        'スケジュール': {'rich_text': {}},
        'リスク': {'rich_text': {}},
        '相性評価': {'number': {'format': 'number'}},
        '参照URL': {'url': {}},
        'ステータス': {'select': {'options': [
            {'name': '候補', 'color': 'blue'},
            {'name': '要確認', 'color': 'yellow'},
        ]}},
        '掲載日': {'date': {}},
        '更新日': {'date': {}},
    }
}

r = httpx.post('https://api.notion.com/v1/databases', headers=headers, json=body, timeout=15)
data = r.json()
if r.status_code == 200:
    db_id = data['id'].replace('-', '')
    print(f'\n✅ DB作成成功!')
    print(f'NOTION_DATABASE_ID={db_id}')
    print('\n.envのNOTION_DATABASE_IDをこの値に更新してください。')
else:
    print('エラー:', json.dumps(data, ensure_ascii=False))
EOF
```

#### 4-3. インテグレーションをページに接続

1. Notionで対象のページを開く
2. 右上「**…**」→「**接続**」→ 作成したインテグレーションを選択

### 5. 動作確認

```bash
# 手動実行
python -m src.main

# ログ確認
cat src/logs/$(date +%Y-%m-%d).log
```

### 6. cronで自動実行（毎日10:00 JST）

```bash
crontab -e
```

以下を追加：

```
0 10 * * * /Users/YOUR_USERNAME/docs/run.sh >> /Users/YOUR_USERNAME/docs/src/logs/cron.log 2>&1
```

## 処理フロー

```
[OpenRouter検索] 6クエリ → 最大35件URL
        ↓
[HTML取得] httpx 並行フェッチ（concurrency=3）
        ↓
[重複排除] Notion既登録URLと照合
        ↓
[期限フィルタ] 過去・90日超を除外
        ↓
[鮮度ソート] 7日以内+優先ソースを上位に
        ↓
[LLM整形] 上位5件をGeminiでJSON構造化
        ↓
[Notion登録] 15プロパティで登録
        ↓
[メール通知] 結果レポートを送信（0件でも必ず送信）
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
| 検索（6クエリ） | perplexity/sonar | ~0.03円/日 |
| LLM整形（最大5件） | google/gemini-2.0-flash-001 | ~0.19円/日 |
| **合計** | | **~0.22円/日** |

## トラブルシューティング

### 検索結果が0件

- `OPENROUTER_API_KEY` が有効か確認
- [openrouter.ai/models](https://openrouter.ai/models) でモデルが利用可能か確認

### Notion登録が失敗する

- `NOTION_TOKEN` とインテグレーションの接続を確認
- `NOTION_DATABASE_ID` がページIDでなくデータベースIDであることを確認

### メールが届かない

- Googleの2段階認証が有効になっているか確認
- `EMAIL_APP_PASSWORD` がアプリパスワード（16文字）であることを確認（通常のGmailパスワードは不可）

## ライセンス

MIT
