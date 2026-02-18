"""
鮮度スコアリング
スコア計算:
  +10: 掲載日または更新日が7日以内
  +5:  優先ソース（eiicon/peatix/creww）
  +3:  応募期限が30日以内
スコア降順でソートして返す
"""
from urllib.parse import urlparse

from src.config import FRESHNESS_DAYS, PRIORITY_SOURCES
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


def sort_by_freshness(pages: list[ParsedPage]) -> list[ParsedPage]:
    """スコア降順にソートしたページリストを返す"""
    scored = [(page, _calc_score(page)) for page in pages]
    scored.sort(key=lambda x: x[1], reverse=True)

    for page, score in scored:
        logger.debug(f"鮮度スコア {score:+d}: {page.url}")

    return [page for page, _ in scored]
