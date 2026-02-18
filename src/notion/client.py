"""
Notion API クライアント
- fetch_existing_urls(): ページネーション対応でDB内の参照URLを全件取得
- create_page(): 新規ページ登録
"""
from typing import Optional

import httpx

from src.config import NOTION_API_VERSION, NOTION_DATABASE_ID, NOTION_TOKEN
from src.utils.logger import get_logger

logger = get_logger()

_BASE = "https://api.notion.com/v1"
_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_API_VERSION,
    "Content-Type": "application/json",
}


def _get_headers() -> dict:
    """トークンを毎回評価するよう遅延生成"""
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def fetch_existing_urls() -> set[str]:
    """
    NotionデータベースからすべてのページのURLプロパティを取得して返す。
    ページネーション（100件/ページ）に対応。
    """
    urls: set[str] = set()
    has_more = True
    start_cursor: Optional[str] = None

    with httpx.Client(timeout=30) as client:
        while has_more:
            body: dict = {
                "page_size": 100,
                "filter": {
                    "property": "参照URL",
                    "url": {"is_not_empty": True},
                },
            }
            if start_cursor:
                body["start_cursor"] = start_cursor

            resp = client.post(
                f"{_BASE}/databases/{NOTION_DATABASE_ID}/query",
                headers=_get_headers(),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

            for page in data.get("results", []):
                props = page.get("properties", {})
                url_prop = props.get("参照URL", {})
                url_val = url_prop.get("url", "")
                if url_val:
                    urls.add(url_val)

            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

    logger.info(f"Notion既登録URL: {len(urls)}件")
    return urls


def create_page(properties: dict) -> str:
    """
    Notionページを作成してページIDを返す。

    Args:
        properties: mapper.py が返す Notion API 形式の properties dict

    Returns:
        作成されたページのID
    """
    body = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties,
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{_BASE}/pages",
            headers=_get_headers(),
            json=body,
        )
        resp.raise_for_status()
        page_id = resp.json().get("id", "")
        logger.debug(f"Notion登録完了: {page_id}")
        return page_id
