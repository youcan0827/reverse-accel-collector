"""
JST日付処理ユーティリティ
"""
import re
from datetime import datetime, date, timedelta, timezone
from typing import Optional

JST = timezone(timedelta(hours=9), name="JST")


def now_jst() -> datetime:
    """現在のJST日時を返す"""
    return datetime.now(tz=JST)


def today_jst() -> date:
    """今日のJST日付を返す"""
    return now_jst().date()


def days_from_today(d: Optional[date]) -> Optional[int]:
    """
    指定日付が今日から何日後かを返す（負の値は過去）。
    Noneを渡した場合はNoneを返す。
    """
    if d is None:
        return None
    return (d - today_jst()).days


# ── 日本語日付パターン ─────────────────────────────────────────────
_JP_FULL = re.compile(r"(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})日?")
_JP_SHORT = re.compile(r"(\d{1,2})[月/](\d{1,2})日?")
_SLASH_DATE = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})")


def parse_japanese_date(text: Optional[str]) -> Optional[date]:
    """
    日本語・スラッシュ形式の日付文字列をdateオブジェクトに変換する。
    対応フォーマット:
      - 2024年3月15日 / 2024年03月15日
      - 2024/3/15 / 2024-03-15
      - 3月15日（年を省略した場合は今年を補完）
    解析できない場合はNoneを返す。
    """
    if not text:
        return None
    text = text.strip()

    m = _JP_FULL.search(text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    m = _SLASH_DATE.search(text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    m = _JP_SHORT.search(text)
    if m:
        try:
            today = today_jst()
            return date(today.year, int(m.group(1)), int(m.group(2)))
        except ValueError:
            pass

    return None


def format_date_iso(d: Optional[date]) -> str:
    """date → "YYYY-MM-DD" 文字列。Noneなら空文字列を返す。"""
    return d.isoformat() if d else ""
