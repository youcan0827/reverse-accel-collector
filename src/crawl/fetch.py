"""
httpxによる並行HTMLフェッチ
concurrency=3、リクエスト間1.5秒遅延
失敗した場合はNoneを返し、全体を止めない
"""
import asyncio
from typing import Optional

import httpx

from src.config import (
    FETCH_CONCURRENCY,
    FETCH_DELAY_SEC,
    FETCH_TIMEOUT_SEC,
    USER_AGENT,
)
from src.utils.logger import get_logger

logger = get_logger()


async def _fetch_one(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> tuple[str, Optional[str]]:
    """
    1件のURLをフェッチしてHTMLテキストを返す。
    失敗した場合は (url, None) を返す。
    """
    async with semaphore:
        try:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            logger.debug(f"Fetched: {url} ({resp.status_code})")
            return url, resp.text
        except Exception as exc:
            logger.warning(f"Fetch failed [{url}]: {exc}")
            return url, None
        finally:
            await asyncio.sleep(FETCH_DELAY_SEC)


async def fetch_all(urls: list[str]) -> dict[str, Optional[str]]:
    """
    URLリストを並行フェッチし、{url: html | None} を返す。
    """
    semaphore = asyncio.Semaphore(FETCH_CONCURRENCY)
    headers = {"User-Agent": USER_AGENT}
    timeout = httpx.Timeout(FETCH_TIMEOUT_SEC)

    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        tasks = [_fetch_one(client, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)

    return dict(results)


def fetch_all_sync(urls: list[str]) -> dict[str, Optional[str]]:
    """同期版ラッパー（main.pyから呼び出しやすいよう提供）"""
    return asyncio.run(fetch_all(urls))
