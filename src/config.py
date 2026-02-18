"""
環境変数・定数管理
cronから実行されても確実に.envを読み込めるよう絶対パスで指定
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# cronはカレントディレクトリが不定のため、__file__基準で絶対パスを解決
_BASE_DIR = Path(__file__).resolve().parent.parent  # /docs/
_ENV_FILE = _BASE_DIR / ".env"
load_dotenv(dotenv_path=_ENV_FILE)

# ── OpenRouter ──────────────────────────────────────────────────
OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL_SEARCH: str = os.environ.get(
    "OPENROUTER_MODEL_SEARCH", "google/gemini-flash-1.5"
)
OPENROUTER_MODEL_EXTRACT: str = os.environ.get(
    "OPENROUTER_MODEL_EXTRACT", "google/gemini-flash-1.5"
)
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

# ── Notion ───────────────────────────────────────────────────────
NOTION_TOKEN: str = os.environ.get("NOTION_TOKEN", "")
NOTION_DATABASE_ID: str = os.environ.get("NOTION_DATABASE_ID", "")
NOTION_API_VERSION: str = "2022-06-28"

# ── Email (Gmail SMTP SSL) ────────────────────────────────────────
EMAIL_FROM: str = os.environ.get("EMAIL_FROM", "")
EMAIL_TO: str = os.environ.get("EMAIL_TO", "")
EMAIL_APP_PASSWORD: str = os.environ.get("EMAIL_APP_PASSWORD", "")
SMTP_HOST: str = "smtp.gmail.com"
SMTP_PORT: int = 465

# ── 収集設定 ─────────────────────────────────────────────────────
PRIORITY_SOURCES: list[str] = [
    "auba.eiicon.net",
    "peatix.com",
    "growth.creww.me",
]
MAX_URLS: int = 35          # 検索で取得する最大URL数
MAX_REGISTER: int = 5       # Notionに登録する最大件数
DEADLINE_MAX_DAYS: int = 90 # 期限がこの日数より先は除外
FRESHNESS_DAYS: int = 7     # 鮮度スコアの基準日数

# ── クロール設定 ──────────────────────────────────────────────────
FETCH_CONCURRENCY: int = 3
FETCH_DELAY_SEC: float = 1.5
FETCH_TIMEOUT_SEC: int = 15
USER_AGENT: str = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ── LLM設定 ──────────────────────────────────────────────────────
LLM_MAX_TOKENS: int = 1200
LLM_TEMPERATURE: float = 0.1
SEARCH_MAX_TOKENS: int = 800
BODY_EXCERPT_CHARS: int = 2000  # LLMに渡す本文の最大文字数

# ── パス ─────────────────────────────────────────────────────────
LOG_DIR: Path = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
