"""
重複排除
第一キー: URL完全一致
第二キー: タイトル + 期限日
"""
from src.crawl.parse import ParsedPage
from src.utils.dates import format_date_iso
from src.utils.logger import get_logger

logger = get_logger()


def dedupe_pages(
    pages: list[ParsedPage],
    existing_urls: set[str],
) -> tuple[list[ParsedPage], list[str]]:
    """
    Args:
        pages: フィルタ後のページリスト
        existing_urls: Notionに既登録のURLセット

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
