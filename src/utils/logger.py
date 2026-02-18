"""
ロガー設定
logs/YYYY-MM-DD.log ファイル + stdout の二重出力
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.config import LOG_DIR


def get_logger(name: str = "reverse_accel") -> logging.Logger:
    """モジュール共通ロガーを返す（初回呼び出し時にハンドラをセットアップ）"""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # 既にセットアップ済みなら再設定しない

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── ファイルハンドラ（YYYY-MM-DD.log） ───────────────────────
    today = datetime.now().strftime("%Y-%m-%d")
    log_file: Path = LOG_DIR / f"{today}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # ── コンソールハンドラ (stdout) ───────────────────────────────
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
