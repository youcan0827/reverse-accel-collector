"""
鮮度スコアリング・鮮度フィルタ

スコア計算:
  +10: 掲載日または更新日が7日以内
  +5:  優先ソース（eiicon/peatix/creww）
  +3:  応募期限が30日以内
スコア降順でソートして返す

鮮度フィルタ:
  掲載日・更新日がSTALENESS_MAX_DAYS以上古く、かつ期限日不明 → 除外
"""
from urllib.parse import urlparse

from src.config import FRESHNESS_DAYS, PRIORITY_SOURCES, STALENESS_MAX_DAYS
from src.crawl.parse import ParsedPage
from src.utils.dates import days_from_today
from src.utils.logger import get_logger

logger = get_logger()

_DEADLINE_NEAR_DAYS = 30


def _calc_score(page: ParsedPage) -> int:
    score = 0

    # 鮮度スコア（掲載日 or 更新日が7日以内）
    pub_delta = days_from_today(page.published_date)
    upd_delta = days_from_today(page.updated_date)

    if pub_delta is not None and 0 <= pub_delta <= FRESHNESS_DAYS:
        score += 10
    elif upd_delta is not None and 0 <= upd_delta <= FRESHNESS_DAYS:
        score += 10

    # 優先ソーススコア
    host = urlparse(page.url).hostname or ""
    if any(src in host for src in PRIORITY_SOURCES):
        score += 5

    # 期限近接スコア（30日以内）
    dl_delta = days_from_today(page.deadline_date)
    if dl_delta is not None and 0 <= dl_delta <= _DEADLINE_NEAR_DAYS:
        score += 3

    return score


def filter_stale_pages(pages: list[ParsedPage]) -> tuple[list[ParsedPage], list[ParsedPage]]:
    """
    掲載日・更新日がSTALENESS_MAX_DAYS以上古く、かつ期限日が不明なページを除外する。

    Returns:
        (通過ページリスト, 除外ページリスト)
    """
    passed: list[ParsedPage] = []
    removed: list[ParsedPage] = []

    for page in pages:
        # 期限日が明確な場合は除外しない（deadline_filterで処理される）
        if page.deadline_date is not None:
            passed.append(page)
            continue

        pub_delta = days_from_today(page.published_date)
        upd_delta = days_from_today(page.updated_date)

        # 最新の日付を選択
        best_delta = None
        if pub_delta is not None and upd_delta is not None:
            best_delta = min(pub_delta, upd_delta)
        elif pub_delta is not None:
            best_delta = pub_delta
        elif upd_delta is not None:
            best_delta = upd_delta

        if best_delta is not None and best_delta > STALENESS_MAX_DAYS:
            logger.debug(f"鮮度フィルタ除外（{best_delta}日前・期限不明）: {page.url}")
            removed.append(page)
        else:
            passed.append(page)

    if removed:
        logger.info(f"鮮度フィルタ: {len(removed)}件除外（掲載{STALENESS_MAX_DAYS}日超・期限不明）")

    return passed, removed


def sort_by_freshness(pages: list[ParsedPage]) -> list[ParsedPage]:
    """スコア降順にソートしたページリストを返す"""
    scored = [(page, _calc_score(page)) for page in pages]
    scored.sort(key=lambda x: x[1], reverse=True)

    for page, score in scored:
        logger.debug(f"鮮度スコア {score:+d}: {page.url}")

    return [page for page, _ in scored]
