# フォルダ構成
project/
src/
main.py
config.py

search/
  openrouter_search.py

crawl/
  fetch.py
  parse.py

filter/
  freshness.py
  deadline.py
  dedupe.py

llm/
  formatter.py

notion/
  client.py
  mapper.py

notify/
  emailer.py

utils/
  logger.py
  dates.py

logs/
docs/
requirements.txt


---

# 各モジュールの責務

## main.py
cronから実行されるエントリーポイント

## search/
OpenRouter検索処理

## crawl/
ページ取得および本文・日付抽出

## filter/
鮮度・期限・重複フィルタ

## llm/
JSONスキーマ整形処理

## notion/
Notion API処理

## notify/
メール通知処理

## utils/
ログ・日付処理
