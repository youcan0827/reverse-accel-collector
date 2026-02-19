"""
OpenRouter API を使った検索
6クエリ実行、優先ソース(eiicon/peatix/creww)URLを先頭に配置、最大35件返却
コスト最適化: max_tokens=800, temperature=0.1
"""
import json
import re
from urllib.parse import urlparse

import httpx

from src.config import (
    MAX_URLS,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL_SEARCH,
    PRIORITY_SOURCES,
    SEARCH_MAX_TOKENS,
)
from src.utils.dates import today_jst
from src.utils.logger import get_logger

logger = get_logger()


def _build_search_queries() -> list[str]:
    year = today_jst().year
    return [
        f"リバース型アクセラレーター 日本 {year} 応募受付中",
        f"共創プログラム 企業 スタートアップ 募集 {year}",
        "site:auba.eiicon.net リバース型 共創 募集",
        "site:growth.creww.me アクセラ 参加企業 募集",
        f"オープンイノベーション 協業 プログラム 建設 BIM AI {year}",
        f"コーポレートアクセラレーター 日本 {year} 応募",
    ]


def _build_system_prompt() -> str:
    year = today_jst().year
    return (
        f"あなたはリバース型アクセラレーター・共創プログラムの情報収集専門家です。"
        f"{year}年現在も募集受付中のプログラムのみを対象としてください。"
        f"応募期限が過去のものや既に終了したプログラムは除外してください。"
        "日本語のWebページURLのリストをJSON配列として出力してください。"
        "形式: [\"https://...\", \"https://...\"]"
        "URLのみを出力し、説明文は一切不要です。"
    )


def _extract_urls_from_text(text: str) -> list[str]:
    """LLMレスポンスからURLを抽出する"""
    # JSON配列として解析を試みる
    try:
        start = text.index("[")
        end = text.rindex("]") + 1
        arr = json.loads(text[start:end])
        if isinstance(arr, list):
            return [u for u in arr if isinstance(u, str) and u.startswith("http")]
    except (ValueError, json.JSONDecodeError):
        pass

    # 正規表現フォールバック
    return re.findall(r"https?://[^\s\"\'\]\)]+", text)


def _is_priority(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return any(src in host for src in PRIORITY_SOURCES)


def fetch_candidate_urls() -> list[str]:
    """
    6クエリを実行してURLを収集し、優先ソースを先頭に配置して最大35件返す。
    """
    all_urls: list[str] = []
    seen: set[str] = set()

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/reverse-accel-collector",
        "X-Title": "Reverse Accel Collector",
    }

    queries = _build_search_queries()
    system_prompt = _build_system_prompt()

    with httpx.Client(timeout=60) as client:
        for i, query in enumerate(queries):
            logger.info(f"検索クエリ {i+1}/{len(queries)}: {query[:50]}...")
            try:
                resp = client.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json={
                        "model": OPENROUTER_MODEL_SEARCH,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": query},
                        ],
                        "max_tokens": SEARCH_MAX_TOKENS,
                        "temperature": 0.1,
                    },
                )
                resp.raise_for_status()
                content = (
                    resp.json()
                    .get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                urls = _extract_urls_from_text(content)
                new_urls = [u for u in urls if u not in seen]
                seen.update(new_urls)
                all_urls.extend(new_urls)
                logger.debug(f"  → {len(new_urls)}件取得（累計{len(all_urls)}件）")

            except Exception as exc:
                logger.warning(f"検索クエリ失敗 [{query[:30]}]: {exc}")

    # 優先ソースを先頭へ
    priority = [u for u in all_urls if _is_priority(u)]
    others = [u for u in all_urls if not _is_priority(u)]
    result = (priority + others)[:MAX_URLS]

    logger.info(
        f"URL収集完了: 優先{len(priority)}件 + その他{len(others)}件 → {len(result)}件"
    )
    return result
