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
  "参加お勧め度": 3,
  "参照URL": "元ページURL（文字列）",
  "is_active": true
}

参加お勧め度は1（低）〜5（高）の整数で、ONESTRUCTIONとの親和性に基づいて設定してください。
is_activeはページの内容から募集が現在進行中かを判定してください。
期限切れ・終了済み・募集終了と読み取れる場合は false にしてください。
現在応募受付中、または判断できない場合は true にしてください。
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
        result.setdefault("is_active", True)

        # 参加お勧め度の型保証
        try:
            result["参加お勧め度"] = int(result.get("参加お勧め度", 3))
            result["参加お勧め度"] = max(1, min(5, result["参加お勧め度"]))
        except (TypeError, ValueError):
            result["参加お勧め度"] = 3

        # is_activeの型保証（文字列 "false" も考慮）
        raw_active = result.get("is_active", True)
        if isinstance(raw_active, str):
            result["is_active"] = raw_active.lower() not in ("false", "0", "no")
        else:
            result["is_active"] = bool(raw_active)

        logger.debug(f"LLM整形完了: {result.get('タイトル', '')[:30]} (is_active={result['is_active']})")
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
