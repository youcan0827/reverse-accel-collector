"""
リバース型アクセラ自動収集システム v1.0
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
from src.filter.dedupe import dedupe_pages
from src.filter.freshness import sort_by_freshness
from src.llm.formatter import format_pages
from src.notion.client import create_page, fetch_existing_urls
from src.notion.mapper import to_notion_properties
from src.notify.emailer import send_report
from src.search.openrouter_search import fetch_candidate_urls
from src.utils.dates import today_jst
from src.utils.logger import get_logger

logger = get_logger()


def main() -> None:
    today = today_jst().isoformat()
    logger.info(f"========== 実行開始: {today} ==========")

    # 集計用変数（finallyブロックで参照するためスコープを外に出す）
    registered_records: list[dict] = []
    excluded_count: int = 0
    duplicate_count: int = 0
    errors: list[str] = []

    try:
        # ── Step 1: OpenRouter検索 → 候補URL取得（最大35件）─────────────
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

        # ── Step 2: Notion既登録URL取得（重複チェック用）─────────────────
        logger.info("Step 2: Notion既登録URL取得")
        try:
            existing_urls = fetch_existing_urls()
        except Exception as e:
            errors.append(f"Step2 Notion取得エラー: {e}")
            logger.error(f"Step2 失敗: {e}")
            existing_urls = set()

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

        # ── Step 5: 重複排除 → 期限フィルタ → 鮮度ソート ────────────────
        logger.info("Step 5: フィルタリング")

        # 5a: 重複排除（Notion既登録URLとの照合）
        pages, dups = dedupe_pages(pages, existing_urls)
        duplicate_count = len(dups)

        # 5b: 期限フィルタ
        pages, excluded = apply_deadline_filter(pages)
        excluded_count = len(excluded)

        # 5c: 鮮度スコア降順ソート → 上位MAX_REGISTER件に絞る
        pages = sort_by_freshness(pages)
        pages = pages[:MAX_REGISTER]
        logger.info(f"フィルタ後: {len(pages)}件（最大{MAX_REGISTER}件）")

        if not pages:
            logger.info("登録対象が0件。メール通知のみ実行します。")
            return

        # ── Step 6: LLMによる構造化整形 ──────────────────────────────
        logger.info(f"Step 6: LLM整形 ({len(pages)}件)")
        records, llm_errors = format_pages(pages)
        errors.extend(llm_errors)
        logger.info(f"整形成功: {len(records)}件")

        # ── Step 7: Notionへ登録 ─────────────────────────────────────
        logger.info(f"Step 7: Notion登録 ({len(records)}件)")
        for record in records:
            title = record.get("タイトル", "（不明）")
            url = record.get("参照URL", "")
            try:
                props = to_notion_properties(record)
                create_page(props)
                registered_records.append(record)
                logger.info(f"  登録: {title[:40]}")
            except Exception as e:
                err_msg = f"Notion登録失敗 [{title[:30]}]: {e}"
                errors.append(err_msg)
                logger.error(err_msg)

    except Exception as e:
        err_msg = f"予期せぬエラー: {e}"
        errors.append(err_msg)
        logger.exception(err_msg)

    finally:
        # ── Step 8: メール通知（必ず実行）───────────────────────────
        logger.info(
            f"Step 8: メール通知 "
            f"(登録{len(registered_records)}件 / 除外{excluded_count}件 "
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
