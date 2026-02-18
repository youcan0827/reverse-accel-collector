"""
LLMによる情報構造化
ParsedPageの本文をdata-model.md定義のJSONスキーマに整形する
コスト最適化: 本文2000文字制限、max_tokens=1200/件
"""
import json
import re
from typing import Optional

import httpx

from src.config import (
    BODY_EXCERPT_CHARS,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL_EXTRACT,
)
from src.crawl.parse import ParsedPage
from src.utils.dates import format_date_iso
from src.utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """\
あなたはONESTRUCTION（建設×BIM×AIのスタートアップ）の視点で、
リバース型アクセラレーター・共創プログラムを評価する専門家です。

以下のJSONスキーマに従って情報を構造化し、JSONのみを出力してください。
説明文・マークダウン・コードブロックは不要です。

{
  "タイトル": "プログラム名（文字列）",
  "主催": "主催企業・団体名（不明なら「不明」、推測なら「（推定）社名」）",
  "目的・狙い": "ONESTRUCTION目線：建設/BIM/AIとの親和性・活用可能性",
  "企画の概要": "プログラムの内容・対象・特徴を200字以内で",
  "企画のキモ": "このプログラムの最も重要なポイントを100字以内で",
  "実現可能性": "ONESTRUCTIONの現状リソースで参加できるかの評価",
  "ROI": "参加した場合の期待リターン・ビジネス価値",
  "体制": "運営体制・支援内容（記載なければ「記載なし」）",
  "スケジュール": "日程・マイルストーン（不明なら「不明」）",
  "リスク": "参加・応募に際するリスク・注意点",
  "相性評価": 3,
  "参照URL": "元ページURL（文字列）",
  "掲載日": "YYYY-MM-DD または空文字列",
  "更新日": "YYYY-MM-DD または空文字列",
  "ステータス": "候補 または 要確認"
}

相性評価は1（低）〜5（高）の整数で、ONESTRUCTIONとの親和性に基づいて設定してください。
ステータスは「候補」（応募検討に値する）または「要確認」（情報不足・期限不明）を選択してください。
"""


def extract_body_excerpt(text: str, max_chars: int = BODY_EXCERPT_CHARS) -> str:
    """本文を最大文字数に切り詰める"""
    return text[:max_chars] if len(text) > max_chars else text


def _parse_llm_json(text: str) -> Optional[dict]:
    """LLMの出力テキストからJSONを抽出・パース"""
    # コードブロック除去
    text = re.sub(r"```(?:json)?", "", text).strip()

    # JSON オブジェクトを探す
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning(f"JSON解析失敗: {e} / テキスト先頭: {text[:100]}")
        return None


def format_page(page: ParsedPage) -> Optional[dict]:
    """
    ParsedPageをLLMで整形してdata-model.md準拠のdictを返す。
    失敗した場合はNoneを返す。
    """
    body = extract_body_excerpt(page.body_text)

    user_content = f"""
URL: {page.url}
タイトル（仮）: {page.title}
主催（仮）: {page.organizer}
掲載日: {format_date_iso(page.published_date)}
更新日: {format_date_iso(page.updated_date)}
締め切り日: {format_date_iso(page.deadline_date)}
締め切りテキスト: {page.raw_deadline_text}

本文（最大{BODY_EXCERPT_CHARS}文字）:
{body}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/reverse-accel-collector",
        "X-Title": "Reverse Accel Collector",
    }

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json={
                    "model": OPENROUTER_MODEL_EXTRACT,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "max_tokens": LLM_MAX_TOKENS,
                    "temperature": LLM_TEMPERATURE,
                },
            )
            resp.raise_for_status()
            content = (
                resp.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )

        result = _parse_llm_json(content)
        if result is None:
            return None

        # 必須フィールドの補完
        result.setdefault("参照URL", page.url)
        result.setdefault("タイトル", page.title or "（タイトル不明）")
        result.setdefault("ステータス", "候補")

        # 相性評価の型保証
        try:
            result["相性評価"] = int(result.get("相性評価", 3))
            result["相性評価"] = max(1, min(5, result["相性評価"]))
        except (TypeError, ValueError):
            result["相性評価"] = 3

        logger.debug(f"LLM整形完了: {result.get('タイトル', '')[:30]}")
        return result

    except Exception as exc:
        logger.warning(f"LLM整形失敗 [{page.url}]: {exc}")
        return None


def format_pages(pages: list[ParsedPage]) -> tuple[list[dict], list[str]]:
    """
    複数ページを順次整形する。

    Returns:
        (整形成功レコードリスト, エラーメッセージリスト)
    """
    records: list[dict] = []
    errors: list[str] = []

    for page in pages:
        logger.info(f"LLM整形: {page.url}")
        result = format_page(page)
        if result:
            records.append(result)
        else:
            errors.append(f"LLM整形失敗: {page.url}")

    return records, errors
