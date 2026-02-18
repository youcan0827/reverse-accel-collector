"""
期限フィルタ
- 応募期限が過去 → 除外
- 応募期限が今日から90日以上先 → 除外
- 期限不明 → deadline_status="要確認" として通過
"""
from src.config import DEADLINE_MAX_DAYS
from src.crawl.parse import ParsedPage
from src.utils.dates import days_from_today, today_jst
from src.utils.logger import get_logger

logger = get_logger()


def apply_deadline_filter(
    pages: list[ParsedPage],
) -> tuple[list[ParsedPage], list[str]]:
    """
    Returns:
        (通過したページリスト, 除外理由メッセージリスト)
    """
    passed: list[ParsedPage] = []
    excluded: list[str] = []

    for page in pages:
        delta = days_from_today(page.deadline_date)

        if delta is None:
            # 期限不明 → 要確認として通過
            logger.debug(f"期限不明（要確認）: {page.url}")
            passed.append(page)
            continue

        if delta < 0:
            reason = f"期限切れ（{page.deadline_date}）: {page.url}"
            logger.debug(f"除外 - {reason}")
            excluded.append(reason)
            continue

        if delta > DEADLINE_MAX_DAYS:
            reason = f"期限{delta}日後（90日超）: {page.url}"
            logger.debug(f"除外 - {reason}")
            excluded.append(reason)
            continue

        passed.append(page)

    logger.info(
        f"期限フィルタ: {len(pages)}件 → 通過{len(passed)}件 / 除外{len(excluded)}件"
    )
    return passed, excluded
