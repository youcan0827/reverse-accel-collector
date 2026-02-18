"""
data-model.json → Notion API プロパティ変換

Notionプロパティタイプ対応表:
  タイトル      → title
  主催          → rich_text
  目的・狙い    → rich_text
  企画の概要    → rich_text
  企画のキモ    → rich_text
  実現可能性    → rich_text
  ROI           → rich_text
  体制          → rich_text
  スケジュール  → rich_text
  リスク        → rich_text
  相性評価      → number
  参照URL       → url
  ステータス    → select
  掲載日        → date
  更新日        → date
"""
from typing import Any


def _title(text: str) -> dict:
    return {"title": [{"text": {"content": text[:2000]}}]}


def _rich_text(text: str) -> dict:
    return {"rich_text": [{"text": {"content": str(text)[:2000]}}]}


def _number(val: Any) -> dict:
    try:
        return {"number": float(val)}
    except (TypeError, ValueError):
        return {"number": None}


def _url(val: str) -> dict:
    return {"url": val or None}


def _select(val: str) -> dict:
    return {"select": {"name": val} if val else None}


def _date(val: str) -> dict:
    """val は "YYYY-MM-DD" または空文字列"""
    return {"date": {"start": val} if val else None}


def to_notion_properties(record: dict) -> dict:
    """
    LLMが返した整形済みJSONレコードをNotion API形式のpropertiesに変換する。

    Args:
        record: data-model.md で定義されたJSONスキーマに準拠した辞書

    Returns:
        Notion pages.create API の properties フィールドに渡せる辞書
    """
    props: dict = {}

    # Title (必須)
    title = str(record.get("タイトル", "") or "（タイトル不明）")
    props["タイトル"] = _title(title)

    # rich_text フィールド
    text_fields = [
        "主催",
        "目的・狙い",
        "企画の概要",
        "企画のキモ",
        "実現可能性",
        "ROI",
        "体制",
        "スケジュール",
        "リスク",
    ]
    for field in text_fields:
        props[field] = _rich_text(str(record.get(field, "") or "不明"))

    # number
    props["相性評価"] = _number(record.get("相性評価", 1))

    # url
    props["参照URL"] = _url(str(record.get("参照URL", "") or ""))

    # select
    status = str(record.get("ステータス", "候補") or "候補")
    if status not in ("候補", "要確認"):
        status = "候補"
    props["ステータス"] = _select(status)

    # date (任意)
    pub = str(record.get("掲載日", "") or "")
    upd = str(record.get("更新日", "") or "")
    if pub:
        props["掲載日"] = _date(pub)
    if upd:
        props["更新日"] = _date(upd)

    return props
