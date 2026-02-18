#!/bin/bash
# リバース型アクセラ収集システム cron実行ラッパー
# cron設定例（毎日10:00 JST）:
#   0 10 * * * /Users/yoshinomukanou/docs/run.sh >> /Users/yoshinomukanou/docs/src/logs/cron.log 2>&1

set -e

# タイムゾーンを明示（cronは環境変数が引き継がれないため）
export TZ=Asia/Tokyo

# プロジェクトルートの絶対パス
PROJECT_DIR="/Users/yoshinomukanou/docs"

# 仮想環境のPython（存在すれば使用、なければシステムPython3）
VENV_PYTHON="${PROJECT_DIR}/.venv/bin/python"
if [ -f "$VENV_PYTHON" ]; then
    PYTHON="$VENV_PYTHON"
else
    PYTHON="$(which python3)"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 実行開始: $PYTHON"

# プロジェクトルートで実行（import パス解決のため）
cd "$PROJECT_DIR"
"$PYTHON" -m src.main

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 実行完了"
