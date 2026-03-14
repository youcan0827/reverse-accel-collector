
---

# 📄 api-specification.md

```md
# API仕様書

---

# 環境変数

- OPENROUTER_API_KEY
- OPENROUTER_MODEL_SEARCH
- OPENROUTER_MODEL_EXTRACT
- EMAIL_FROM
- EMAIL_TO
- EMAIL_APP_PASSWORD

---

# 処理フロー

1. OpenRouterで検索実行
2. 候補URL最大80件取得
3. 送信済みURL（ローカルファイル）で重複確認
4. 期限フィルタ適用（期限切れ・90日以上先を除外）
5. 鮮度判定（7日以内優先）
6. 最大15件をAIで構造化
7. メール通知送信

---

# メール通知仕様

件名：
[ReverseAccel] YYYY-MM-DD 実行結果

本文内容：
- 送信件数
- 除外件数（期限切れ／90日超／重複）
- 案件タイトル＋URL
- エラー有無

---

# エラー処理

- 1URL失敗で全体停止しない
- 0件でもメール通知する
