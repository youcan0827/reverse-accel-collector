"""
data-model.json → Notion API プロパティ変換

Notionプロパティタイプ対応表:
  タイトル      → title
  参加お勧め度  → number
  参照URL       → url
"""
from typing import Any


def _title(text: str) -> dict:
    return {"title": [{"text": {"content": text[:2000]}}]}


def _number(val: Any) -> dict:
    try:
        return {"number": float(val)}
    except (TypeError, ValueError):
        return {"number": None}


def _url(val: str) -> dict:
    return {"url": val or None}


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

    # number（「参加お勧め度」優先、なければ旧フィールド「相性評価」でフォールバック）
    score = record.get("参加お勧め度", record.get("相性評価", 3))
    props["参加お勧め度"] = _number(score)

    # url
    props["参照URL"] = _url(str(record.get("参照URL", "") or ""))

    return props
