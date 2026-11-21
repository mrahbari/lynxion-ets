"""Telegram self-test: validates TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID from .env and sends one test message.

Usage:  python3 scripts/telegram_selftest.py
Never prints the token. Uses the same TelegramNotificationService the trading runtime uses.
"""
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)
except ImportError:
    pass

token = os.getenv("TELEGRAM_BOT_TOKEN", "")
chat = os.getenv("TELEGRAM_CHAT_ID", "")
if not token or not chat:
    sys.exit("FAIL: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing in .env")

r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15).json()
if not r.get("ok"):
    sys.exit(f"FAIL getMe: {r.get('error_code')} {r.get('description')} -> create a new token with @BotFather")
print(f"getMe OK: @{r['result']['username']}")

from infrastructure.services.risk_alerts import TelegramNotificationService  # noqa: E402

ok = TelegramNotificationService(token, chat).send_notification(
    "Lynxion Telegram self-test. If you see this, trade notifications will be delivered.",
    "Lynxion self-test", "info", parse_mode="HTML")
if not ok:
    sys.exit("FAIL sendMessage: check TELEGRAM_CHAT_ID and that you pressed /start in the bot chat")
print("sendMessage OK")
