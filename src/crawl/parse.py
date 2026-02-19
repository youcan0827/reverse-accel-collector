"""
HTMLパーサー
eiicon / peatix / creww 専用パーサー + 汎用パーサー（OGP/JSON-LD/正規表現）
"""
import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.utils.dates import parse_japanese_date, today_jst
from src.utils.logger import get_logger

logger = get_logger()


@dataclass
class ParsedPage:
    url: str
    title: str = ""
    organizer: str = ""
    body_text: str = ""
    published_date: Optional[date] = None
    updated_date: Optional[date] = None
    deadline_date: Optional[date] = None
    raw_deadline_text: str = ""


# ── ヘルパー ──────────────────────────────────────────────────────

def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _og_meta(soup: BeautifulSoup, prop: str) -> str:
    tag = soup.find("meta", attrs={"property": prop}) or soup.find(
        "meta", attrs={"name": prop}
    )
    return (tag.get("content") or "") if tag else ""  # type: ignore[union-attr]


def _extract_jsonld(soup: BeautifulSoup) -> dict:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            if isinstance(data, list):
                data = data[0]
            return data
        except Exception:
            pass
    return {}


def _body_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())


def _find_deadline_text(text: str) -> str:
    """本文から応募締め切りっぽいテキストを抽出"""
    patterns = [
        r"応募.*?締[め切り]+[：:\s]*(.{5,30})",
        r"締[め切り]+[：:\s]*(.{5,30})",
        r"募集期間[：:\s]*(.{5,50})",
        r"期限[：:\s]*(.{5,30})",
        r"deadline[：:\s]*(.{5,30})",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def _parse_deadline(dl_text: str, reference_date: Optional[date]) -> Optional[date]:
    """
    締め切りテキストを日付に変換する。
    年省略の場合は reference_date の年を基準にする。
    reference_date が過去年なら、過去年で解釈することで期限切れとして検出できる。
    """
    ref_year = reference_date.year if reference_date else None
    return parse_japanese_date(dl_text, reference_year=ref_year)


# ── eiicon 専用 ───────────────────────────────────────────────────

def _parse_eiicon(soup: BeautifulSoup, url: str) -> ParsedPage:
    page = ParsedPage(url=url)
    page.title = _og_meta(soup, "og:title") or (soup.title.string if soup.title else "")
    page.organizer = _og_meta(soup, "og:site_name") or "eiicon"

    # 本文
    main = soup.find("div", class_=re.compile(r"detail|content|description", re.I))
    page.body_text = main.get_text(" ", strip=True) if main else _body_text(soup)

    # 掲載日・更新日
    time_tag = soup.find("time")
    if time_tag:
        dt_attr = time_tag.get("datetime", "")
        page.published_date = parse_japanese_date(str(dt_attr)) or parse_japanese_date(
            time_tag.get_text()
        )

    # 締め切り（掲載日の年を参照年として渡す）
    dl_text = _find_deadline_text(page.body_text)
    page.raw_deadline_text = dl_text
    page.deadline_date = _parse_deadline(dl_text, page.published_date)

    return page


# ── peatix 専用 ───────────────────────────────────────────────────

def _parse_peatix(soup: BeautifulSoup, url: str) -> ParsedPage:
    page = ParsedPage(url=url)
    page.title = _og_meta(soup, "og:title") or (soup.title.string if soup.title else "")
    page.organizer = _og_meta(soup, "og:site_name") or "Peatix"

    # JSON-LDからイベント日時を取得（年込みなので参照年不要）
    ld = _extract_jsonld(soup)
    if ld.get("endDate"):
        page.deadline_date = parse_japanese_date(str(ld["endDate"]))
        page.raw_deadline_text = str(ld["endDate"])
    if ld.get("startDate"):
        page.published_date = parse_japanese_date(str(ld["startDate"]))

    # 本文
    desc = soup.find("div", id=re.compile(r"description|summary", re.I))
    page.body_text = desc.get_text(" ", strip=True) if desc else _body_text(soup)

    return page


# ── creww 専用 ────────────────────────────────────────────────────

def _parse_creww(soup: BeautifulSoup, url: str) -> ParsedPage:
    page = ParsedPage(url=url)
    page.title = _og_meta(soup, "og:title") or (soup.title.string if soup.title else "")
    page.organizer = _og_meta(soup, "og:site_name") or "creww"

    # 本文
    main = soup.find("div", class_=re.compile(r"challenge|detail|overview", re.I))
    page.body_text = main.get_text(" ", strip=True) if main else _body_text(soup)

    # 掲載日（締め切り解析より先に取得）
    time_tag = soup.find("time")
    if time_tag:
        page.published_date = parse_japanese_date(
            str(time_tag.get("datetime", "")) or time_tag.get_text()
        )

    # 締め切り（掲載日の年を参照年として渡す）
    dl_text = _find_deadline_text(page.body_text)
    page.raw_deadline_text = dl_text
    page.deadline_date = _parse_deadline(dl_text, page.published_date)

    return page


# ── 汎用パーサー ──────────────────────────────────────────────────

def _parse_generic(soup: BeautifulSoup, url: str) -> ParsedPage:
    page = ParsedPage(url=url)

    # タイトル: OGP → <title> の順
    page.title = (
        _og_meta(soup, "og:title")
        or (soup.title.string.strip() if soup.title and soup.title.string else "")
    )

    # 主催: JSON-LD → OGP
    ld = _extract_jsonld(soup)
    organizer = ld.get("organizer") or ld.get("publisher") or {}
    if isinstance(organizer, dict):
        page.organizer = organizer.get("name", "")
    elif isinstance(organizer, str):
        page.organizer = organizer
    page.organizer = page.organizer or _og_meta(soup, "og:site_name")

    # 本文
    page.body_text = _body_text(soup)

    # 掲載日・更新日（締め切り解析より先に取得）
    pub = ld.get("datePublished") or ld.get("dateCreated") or ""
    mod = ld.get("dateModified") or ""
    page.published_date = parse_japanese_date(str(pub))
    page.updated_date = parse_japanese_date(str(mod))

    # time タグにフォールバック
    if not page.published_date:
        for t in soup.find_all("time"):
            d = parse_japanese_date(str(t.get("datetime", "")) or t.get_text())
            if d:
                page.published_date = d
                break

    # 締め切り（掲載日の年を参照年として渡す）
    dl_text = _find_deadline_text(page.body_text)
    page.raw_deadline_text = dl_text
    page.deadline_date = _parse_deadline(dl_text, page.published_date)

    return page


# ── ルーター ──────────────────────────────────────────────────────

def parse_html(url: str, html: str) -> Optional[ParsedPage]:
    """
    URLとHTMLを受け取り、サイトに応じたパーサーで ParsedPage を返す。
    解析失敗時はNoneを返す。
    """
    try:
        soup = _soup(html)
        host = urlparse(url).hostname or ""

        if "eiicon.net" in host:
            return _parse_eiicon(soup, url)
        elif "peatix.com" in host:
            return _parse_peatix(soup, url)
        elif "creww.me" in host:
            return _parse_creww(soup, url)
        else:
            return _parse_generic(soup, url)
    except Exception as exc:
        logger.warning(f"Parse failed [{url}]: {exc}")
        return None
