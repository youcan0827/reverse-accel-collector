"""
Gmail SMTP SSL によるメール通知
件名: [ReverseAccel] YYYY-MM-DD N件
0件でも必ず送信する
"""
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

from src.config import (
    EMAIL_APP_PASSWORD,
    EMAIL_FROM,
    EMAIL_TO,
    SMTP_HOST,
    SMTP_PORT,
)
from src.utils.dates import today_jst
from src.utils.logger import get_logger

logger = get_logger()

_STARS = {1: "★☆☆☆☆", 2: "★★☆☆☆", 3: "★★★☆☆", 4: "★★★★☆", 5: "★★★★★"}


def build_body(
    registered: list[dict],
    excluded_count: int,
    duplicate_count: int,
    errors: list[str],
) -> str:
    today = today_jst().isoformat()

    lines = [f"=== リバース型アクセラ収集レポート ({today}) ===", ""]

    if registered:
        lines.append(f"【案件リスト】{len(registered)}件")
        lines.append("")
        for i, r in enumerate(registered, 1):
            url = r.get("参照URL", "")
            score = r.get("参加お勧め度", 0)
            stars = _STARS.get(int(score), "?????") if score else "未評価"
            lines.append(f"{i}. {url}")
            lines.append(f"   参加お勧め度: {stars} ({score}/5)")
            lines.append("")
    else:
        lines.append("【案件リスト】該当なし")
        lines.append("")

    lines.append(f"除外: 期限切れ {excluded_count}件 / 重複 {duplicate_count}件")

    if errors:
        lines.append("")
        lines.append("【エラー】")
        for e in errors:
            lines.append(f"  - {e}")

    lines.append("")
    lines.append("---")
    lines.append("本メールは自動送信されました。")
    return "\n".join(lines)


def send_report(
    registered: list[dict],
    excluded_count: int,
    duplicate_count: int,
    errors: list[str],
) -> None:
    today = today_jst().isoformat()
    count = len(registered)
    subject = f"[ReverseAccel] {today} {count}件"
    body = build_body(registered, excluded_count, duplicate_count, errors)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Date"] = formatdate()

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
            smtp.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
        logger.info(f"メール送信完了: {subject}")
    except Exception as exc:
        logger.error(f"メール送信失敗: {exc}")
