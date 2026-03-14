# リバース型アクセラ 自動収集システム

毎日10:00（JST）に日本国内のリバース型アクセラレーター・共創プログラムを自動収集し、Notionに登録してメール通知を送るPythonシステムです。

## 機能

- **自動検索** — OpenRouter（Perplexity Sonar）で複数クエリを実行し、最大35件のURLを収集
- **スマートフィルタ** — 期限切れ・90日超・重複を除外し、鮮度スコア順で上位5件に絞り込み
- **AI評価** — LLMでONESTRUCTION目線の参加お勧め度（1〜5）を自動スコアリング
- **Notion登録** — 3カラム（タイトル・参加お勧め度・参照URL）のデータベースへ重複なく登録
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

---

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

`.env` ファイルをプロジェクトルートに作成します：

```env
OPENROUTER_API_KEY=sk-or-xxxxxxxx
NOTION_TOKEN=secret_xxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EMAIL_FROM=your@gmail.com
EMAIL_TO=your@gmail.com
EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

| 変数名 | 説明 | 取得方法 |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter APIキー | [openrouter.ai/keys](https://openrouter.ai/keys) |
| `NOTION_TOKEN` | Notion インテグレーションシークレット | [notion.so/my-integrations](https://www.notion.so/my-integrations) でインテグレーション作成 |
| `NOTION_DATABASE_ID` | NotionデータベースのID | 後述「Notionセットアップ」を参照 |
| `EMAIL_FROM` | 送信元Gmailアドレス | 例: `yourname@gmail.com` |
| `EMAIL_TO` | 送信先メールアドレス | 例: `yourname@gmail.com` |
| `EMAIL_APP_PASSWORD` | Gmailアプリパスワード（16文字） | Googleアカウント → セキュリティ → アプリパスワード |

### 4. Notionセットアップ

#### 4-1. インテグレーションの作成

1. [notion.so/my-integrations](https://www.notion.so/my-integrations) でインテグレーションを新規作成
2. 発行された **Internal Integration Secret** を `NOTION_TOKEN` に設定

#### 4-2. データベースの作成

以下のスクリプトで、指定したNotionページ内にデータベースを自動作成できます。

```bash
python3 - <<'EOF'
import httpx, os, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path('.env'))
TOKEN = os.environ['NOTION_TOKEN']
PAGE_ID = input('NotionページIDを入力（URLの末尾32文字）: ').strip().replace('-', '')

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
        '参加お勧め度': {'number': {'format': 'number'}},
        '参照URL': {'url': {}},
    }
}

r = httpx.post('https://api.notion.com/v1/databases', headers=headers, json=body, timeout=15)
data = r.json()
if r.status_code == 200:
    db_id = data['id'].replace('-', '')
    print(f'\nDB作成成功!')
    print(f'NOTION_DATABASE_ID={db_id}')
    print('\n.envのNOTION_DATABASE_IDをこの値に更新してください。')
else:
    print('エラー:', json.dumps(data, ensure_ascii=False))
EOF
```

> **既存のDBを使う場合：** NotionのDBページを開き、URLの末尾にある32文字の英数字が `NOTION_DATABASE_ID` です。

#### 4-3. インテグレーションをページに接続

1. Notionで対象のページ（またはDBのある親ページ）を開く
2. 右上「**…**」→「**接続**」→ 作成したインテグレーションを選択

#### 4-4. Notionデータベースのカラム構成

| カラム名 | 型 | 説明 |
|---|---|---|
| タイトル | タイトル | プログラム名 |
| 参加お勧め度 | 数値（1〜5） | ONESTRUCTIONとの親和性スコア |
| 参照URL | URL | 元ページのURL |

### 5. 動作確認

```bash
# 仮想環境を有効化
source .venv/bin/activate

# 手動実行
python -m src.main

# ログ確認
cat src/logs/$(date +%Y-%m-%d).log
```

実行後、登録件数・除外件数・エラーがメールで届きます。

### 6. cronで自動実行（毎日10:00 JST）

```bash
crontab -e
```

以下を追加（パスは実際の配置場所に変更してください）：

```
0 10 * * * /path/to/reverse-accel-collector/run.sh >> /path/to/reverse-accel-collector/src/logs/cron.log 2>&1
```

> `run.sh` 内の `PROJECT_DIR` も実際のパスに変更してください。

---

## 処理フロー

```
[OpenRouter検索] 複数クエリ → 最大35件URL
        ↓
[HTML取得] httpx 並行フェッチ（concurrency=3）
        ↓
[重複排除] 送信済みURL（seen_urls.json）と照合
        ↓
[期限フィルタ] 過去・90日超を除外
        ↓
[鮮度フィルタ] 掲載日古すぎを除外
        ↓
[鮮度ソート] 上位5件に絞り込み
        ↓
[LLM評価] 参加お勧め度（1-5）・is_active判定
        ↓
[Notion登録] タイトル・参加お勧め度・参照URLの3カラムで登録
        ↓
[メール通知] 結果レポートを送信（0件でも必ず送信）
```

---

## 優先収集ソース

| ソース | URL |
|---|---|
| AUBA（eiicon） | https://auba.eiicon.net/ |
| Peatix | https://peatix.com/ |
| creww Growth | https://growth.creww.me/ |

---

## コスト目安

| フェーズ | モデル | 概算 |
|---|---|---|
| 検索（複数クエリ） | perplexity/sonar | ~0.03円/日 |
| LLM評価（最大5件） | google/gemini-2.0-flash-001 | ~0.19円/日 |
| **合計** | | **~0.22円/日** |

---

## トラブルシューティング

### 解析失敗が多い

```bash
pip install lxml
```

`lxml` が未インストールの場合、HTML解析が全件失敗します。

### 検索結果が0件

- `OPENROUTER_API_KEY` が `.env` に設定されているか確認
- [openrouter.ai/activity](https://openrouter.ai/activity) でAPIの疎通を確認

### Notion登録が失敗する（400 Bad Request）

- `NOTION_TOKEN` とインテグレーションのページ接続を確認
- `NOTION_DATABASE_ID` がページIDではなく**データベースID**であることを確認
- NotionのDBカラムが「タイトル」「参加お勧め度」「参照URL」の3カラムになっているか確認（旧フォーマットのカラムが残っているとエラーになります）

### メールが届かない

- Googleの2段階認証が有効になっているか確認
- `EMAIL_APP_PASSWORD` はアプリパスワード（16文字）を使用（通常のパスワード不可）

### cronで実行されない

- `run.sh` に実行権限があるか確認：`chmod +x run.sh`
- `run.sh` 内の `PROJECT_DIR` が正しい絶対パスになっているか確認
- cronのログを確認：`src/logs/cron.log`

---

## ライセンス

MIT
