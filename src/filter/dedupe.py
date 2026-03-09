"""
重複排除
第一キー: URL完全一致（ローカルJSONファイルで管理）
第二キー: タイトル + 期限日（同一セッション内）
"""
import json

from src.config import SEEN_URLS_FILE
from src.crawl.parse import ParsedPage
from src.utils.dates import format_date_iso
from src.utils.logger import get_logger

logger = get_logger()


def load_seen_urls() -> set[str]:
    """送信済みURLをローカルファイルから読み込む"""
    if not SEEN_URLS_FILE.exists():
        return set()
    try:
        data = json.loads(SEEN_URLS_FILE.read_text(encoding="utf-8"))
        return set(data) if isinstance(data, list) else set()
    except Exception as e:
        logger.warning(f"seen_urls読み込み失敗: {e}")
        return set()


def save_seen_urls(urls: set[str]) -> None:
    """送信済みURLをローカルファイルに保存する"""
    try:
        SEEN_URLS_FILE.write_text(
            json.dumps(sorted(urls), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning(f"seen_urls保存失敗: {e}")


def dedupe_pages(
    pages: list[ParsedPage],
    existing_urls: set[str],
) -> tuple[list[ParsedPage], list[str]]:
    """
    Args:
        pages: フィルタ後のページリスト
        existing_urls: 送信済みURLセット（ローカルファイルから読み込み済み）

    Returns:
        (重複除外後のページリスト, 除外されたURLリスト)
    """
    seen_urls: set[str] = set(existing_urls)
    seen_keys: set[str] = set()
    passed: list[ParsedPage] = []
    duplicates: list[str] = []

    for page in pages:
        # 第一キー: URL
        if page.url in seen_urls:
            logger.debug(f"重複スキップ（URL）: {page.url}")
            duplicates.append(page.url)
            continue

        # 第二キー: タイトル + 期限
        key = f"{page.title}|{format_date_iso(page.deadline_date)}"
        if key in seen_keys and page.title:
            logger.debug(f"重複スキップ（タイトル+期限）: {page.url}")
            duplicates.append(page.url)
            continue

        seen_urls.add(page.url)
        if page.title:
            seen_keys.add(key)
        passed.append(page)

    logger.info(
        f"重複排除: {len(pages)}件 → {len(passed)}件残存 / {len(duplicates)}件除外"
    )
    return passed, duplicates
