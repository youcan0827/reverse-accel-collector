"""
Gmail SMTP SSL によるメール通知
件名: [ReverseAccel] YYYY-MM-DD 実行結果
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


def build_body(
    registered: list[dict],
    excluded_count: int,
    duplicate_count: int,
    errors: list[str],
) -> str:
    """
    メール本文を組み立てる。

    Args:
        registered:      登録済みレコードのリスト（{"タイトル": ..., "参照URL": ...}）
        excluded_count:  期限フィルタで除外された件数
        duplicate_count: 重複排除された件数
        errors:          エラーメッセージのリスト
    """
    today = today_jst().isoformat()
    candidate = [r for r in registered if r.get("ステータス") == "候補"]
    uncertain = [r for r in registered if r.get("ステータス") == "要確認"]

    lines = [
        f"=== リバース型アクセラ収集レポート ({today}) ===",
        "",
        f"【登録件数】{len(registered)}件",
        f"  - 候補:   {len(candidate)}件",
        f"  - 要確認: {len(uncertain)}件",
        f"【除外件数】{excluded_count}件（期限切れ／90日超）",
        f"【重複排除】{duplicate_count}件",
        "",
    ]

    if registered:
        lines.append("【登録案件一覧】")
        for r in registered:
            status = r.get("ステータス", "")
            title = r.get("タイトル", "（タイトル不明）")
            url = r.get("参照URL", "")
            lines.append(f"  [{status}] {title}")
            if url:
                lines.append(f"    {url}")
        lines.append("")

    if errors:
        lines.append("【エラー】")
        for e in errors:
            lines.append(f"  - {e}")
        lines.append("")
    else:
        lines.append("【エラー】なし")
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
    """
    実行結果レポートメールを送信する。
    SMTP接続失敗時はログに記録して終了（例外を握り潰す）。
    """
    today = today_jst().isoformat()
    subject = f"[ReverseAccel] {today} 実行結果"
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
