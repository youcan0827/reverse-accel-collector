"""
リバース型アクセラ自動収集システム v2.0
メール完結版
cronエントリーポイント: 8ステップを try/finally で統合

どのステップで例外が発生しても finally でメール通知を保証する。
"""
import sys
from pathlib import Path

# cron実行時のimportパス対策
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import MAX_REGISTER
from src.crawl.fetch import fetch_all_sync
from src.crawl.parse import parse_html
from src.filter.deadline import apply_deadline_filter
from src.filter.dedupe import dedupe_pages, load_seen_urls, save_seen_urls
from src.filter.freshness import filter_stale_pages, sort_by_freshness
from src.llm.formatter import format_pages
from src.notify.emailer import send_report
from src.search.openrouter_search import fetch_candidate_urls
from src.utils.dates import today_jst
from src.utils.logger import get_logger

logger = get_logger()


def main() -> None:
    today = today_jst().isoformat()
    logger.info(f"========== 実行開始: {today} ==========")

    registered_records: list[dict] = []
    excluded_count: int = 0
    duplicate_count: int = 0
    stale_count: int = 0
    inactive_count: int = 0
    errors: list[str] = []

    try:
        # ── Step 1: Perplexity Sonar検索 → 候補URL取得（最大80件）─────────
        logger.info("Step 1: URL検索")
        try:
            candidate_urls = fetch_candidate_urls()
        except Exception as e:
            errors.append(f"Step1 検索エラー: {e}")
            logger.error(f"Step1 失敗: {e}")
            candidate_urls = []

        if not candidate_urls:
            logger.warning("候補URLが0件。処理を終了します。")
            return

        # ── Step 2: 送信済みURL取得（重複チェック用）─────────────────────
        logger.info("Step 2: 送信済みURL取得")
        existing_urls = load_seen_urls()
        logger.info(f"送信済みURL: {len(existing_urls)}件")

        # ── Step 3: HTML並行取得 ───────────────────────────────────────
        logger.info(f"Step 3: HTML取得 ({len(candidate_urls)}件)")
        try:
            html_map = fetch_all_sync(candidate_urls)
        except Exception as e:
            errors.append(f"Step3 HTML取得エラー: {e}")
            logger.error(f"Step3 失敗: {e}")
            html_map = {}

        # ── Step 4: HTML解析 ──────────────────────────────────────────
        logger.info("Step 4: HTML解析")
        pages = []
        for url, html in html_map.items():
            if html is None:
                errors.append(f"取得失敗: {url}")
                continue
            page = parse_html(url, html)
            if page:
                pages.append(page)
            else:
                errors.append(f"解析失敗: {url}")

        logger.info(f"解析成功: {len(pages)}件")

        # ── Step 5: 重複排除 → 期限フィルタ → 鮮度フィルタ → 鮮度ソート ──
        logger.info("Step 5: フィルタリング")

        pages, dups = dedupe_pages(pages, existing_urls)
        duplicate_count = len(dups)

        pages, excluded = apply_deadline_filter(pages)
        excluded_count = len(excluded)

        pages, stale = filter_stale_pages(pages)
        stale_count = len(stale)

        pages = sort_by_freshness(pages)
        pages = pages[:MAX_REGISTER]
        logger.info(f"フィルタ後: {len(pages)}件（最大{MAX_REGISTER}件）")

        if not pages:
            logger.info("対象が0件。メール通知のみ実行します。")
            return

        # ── Step 6: LLMによる評価・整形 ──────────────────────────────
        logger.info(f"Step 6: LLM評価 ({len(pages)}件)")
        records, llm_errors = format_pages(pages)
        errors.extend(llm_errors)
        logger.info(f"評価成功: {len(records)}件")

        # is_active=false の案件を除外
        active_records = [r for r in records if r.get("is_active", True)]
        inactive_count = len(records) - len(active_records)
        if inactive_count:
            logger.info(f"is_active=false 除外: {inactive_count}件")
        records = active_records

        # 参加お勧め度の高い順にソート
        records.sort(key=lambda r: r.get("参加お勧め度", 0), reverse=True)

        registered_records = records

        # ── Step 7: 送信済みURLを保存 ────────────────────────────────
        if registered_records:
            new_urls = {r.get("参照URL", "") for r in registered_records if r.get("参照URL")}
            updated_seen = existing_urls | new_urls
            save_seen_urls(updated_seen)
            logger.info(f"送信済みURL保存: {len(new_urls)}件追加 → 累計{len(updated_seen)}件")

    except Exception as e:
        err_msg = f"予期せぬエラー: {e}"
        errors.append(err_msg)
        logger.exception(err_msg)

    finally:
        # ── Step 8: メール通知（必ず実行）───────────────────────────
        logger.info(
            f"Step 8: メール通知 "
            f"(送信{len(registered_records)}件 / 期限除外{excluded_count}件 "
            f"/ 鮮度除外{stale_count}件 / 非アクティブ除外{inactive_count}件 "
            f"/ 重複{duplicate_count}件 / エラー{len(errors)}件)"
        )
        send_report(
            registered=registered_records,
            excluded_count=excluded_count,
            duplicate_count=duplicate_count,
            errors=errors,
        )
        logger.info(f"========== 実行完了: {today_jst().isoformat()} ==========")


if __name__ == "__main__":
    main()
