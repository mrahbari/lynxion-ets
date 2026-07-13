"""Risk alerts and notification service following hexagonal architecture."""

import smtplib
from email.mime.text import MIMEText
import requests
import json
import time
from typing import Dict, Any, List
from abc import ABC, abstractmethod

from shared.logger import EnhancedLogger


class INotificationService(ABC):
    """Port for notification services following hexagonal architecture."""

    @abstractmethod
    def send_notification(self, message: str, subject: str = "Alert", notification_type: str = "info", parse_mode: str = None) -> bool:
        """Send a notification."""
        pass


class EmailNotificationService(INotificationService):
    """Email notification service implementation."""

    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587,
                 username: str = "", password: str = "",
                 from_email: str = "", to_email: str = ""):
        self.config = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "from_email": from_email,
            "to_email": to_email
        }
        self.logger = EnhancedLogger("EmailNotificationService")

    def send_notification(self, message: str, subject: str = "Alert", notification_type: str = "info", parse_mode: str = None) -> bool:
        """Send an email notification."""
        try:
            msg = MIMEText(message)
            msg["Subject"] = subject
            msg["From"] = self.config["from_email"]
            msg["To"] = self.config["to_email"]

            with smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"]) as server:
                server.starttls()
                server.login(self.config["username"], self.config["password"])
                server.send_message(msg)

            self.logger.info(f"Email sent: {subject}")
            return True
        except Exception as e:
            self.logger.error(f"Email error: {e}")
            return False


class TelegramNotificationService(INotificationService):
    """Telegram notification service implementation."""

    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.config = {
            "bot_token": bot_token,
            "chat_id": chat_id
        }
        self.logger = EnhancedLogger("TelegramNotificationService")

    def send_notification(self, message: str, subject: str = "Alert", notification_type: str = "info", parse_mode: str = None) -> bool:
        """Send a Telegram notification."""
        try:
            url = f"https://api.telegram.org/bot{self.config['bot_token']}/sendMessage"
            
            # Formulate text
            if parse_mode == "HTML":
                text = f"<b>{subject}</b>\n\n{message}"
            else:
                text = f"{subject}: {message}"
                
            data = {
                "chat_id": self.config["chat_id"],
                "text": text
            }
            if parse_mode:
                data["parse_mode"] = parse_mode
                
            response = requests.post(url, data=data)

            if response.status_code == 200:
                self.logger.info(f"Telegram sent: {subject}")
                return True
            else:
                self.logger.error(f"Telegram error: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Telegram error: {e}")
            return False


class RiskAlertService:
    """Risk alert service following hexagonal architecture."""

    def __init__(self,
                 notification_services: List[INotificationService],
                 max_leverage: float = 10.0,
                 drawdown_threshold: float = -0.1):
        self.notification_services = notification_services
        self.max_leverage = max_leverage
        self.drawdown_threshold = drawdown_threshold
        self.logger = EnhancedLogger("RiskAlertService")

    def check_and_alert(self, trade_log: Dict[str, Any],
                       equity_curve: Dict[str, List[float]],
                       asset_performance: Dict[str, float]):
        """
        Check for risk conditions and send alerts.

        Args:
            trade_log: dict {asset: [trades]}
            equity_curve: dict {asset: [equity_over_time]}
            asset_performance: dict {asset: return%}
        """
        # 1) SL / TP Hit Alerts
        for asset, trades in trade_log.items():
            for trade in trades:
                if trade.get("sl_hit", False):
                    msg = f"⚠️ SL Hit | {asset} | {trade}"
                    self._send_alert(msg, "SL Hit Alert", "warning")
                if trade.get("tp_hit", False):
                    msg = f"✅ TP Hit | {asset} | {trade}"
                    self._send_alert(msg, "TP Hit Alert", "info")

        # 2) Margin Call / Leverage Breach
        for asset, curve in equity_curve.items():
            if curve and len(curve) > 1:
                initial_balance = curve[0]
                current_balance = curve[-1]
                if initial_balance != 0:
                    change_pct = abs(current_balance - initial_balance) / initial_balance
                    leverage_used = change_pct * self.max_leverage
                    if leverage_used > self.max_leverage:
                        msg = f"⚠️ Leverage Breach | {asset} | Used: {leverage_used:.2f}x"
                        self._send_alert(msg, "Leverage Alert", "critical")

        # 3) Asset Drop Alert
        for asset, ret in asset_performance.items():
            if ret < self.drawdown_threshold * 100:
                msg = f"⚠️ Asset Dropped Below Threshold | {asset} | Return: {ret:.2f}%"
                self._send_alert(msg, "Asset Drop Alert", "warning")

        self.logger.info("Risk check completed")

    def _send_alert(self, message: str, subject: str = "Alert", alert_type: str = "info"):
        """Send alert through all notification services."""
        for service in self.notification_services:
            try:
                service.send_notification(message, subject, alert_type)
            except Exception as e:
                self.logger.error(f"Error sending notification via {type(service).__name__}: {e}")

    def run_alert_monitor(self, check_interval: int = 60):
        """Run an alert monitoring loop."""
        self.logger.info(f"Starting alert monitor with {check_interval}s interval")
        while True:
            try:
                # In a real implementation, you'd fetch current data from repositories
                # This is just a placeholder for the real data
                self.logger.info("Checking for risk conditions...")

                # Placeholder data - in real implementation would fetch from repositories
                trade_log = {}
                equity_curve = {}
                asset_performance = {}

                # Perform risk check
                self.check_and_alert(trade_log, equity_curve, asset_performance)

                time.sleep(check_interval)
            except KeyboardInterrupt:
                self.logger.info("Alert monitor stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in alert monitor: {e}")
                time.sleep(check_interval)


# Backward compatibility functions
def send_email(subject, body):
    """Backward compatibility function for email sending."""
    email_service = EmailNotificationService()
    return email_service.send_notification(body, subject)

def send_telegram(message):
    """Backward compatibility function for Telegram sending."""
    telegram_service = TelegramNotificationService()
    return telegram_service.send_notification(message)

def check_and_alert(trade_log, equity_curve, asset_performance, max_leverage=10, dd_threshold=-0.1):
    """Backward compatibility function for alert checking."""
    # Create mock notification services for compatibility
    class MockNotificationService(INotificationService):
        def send_notification(self, message: str, subject: str = "Alert", notification_type: str = "info") -> bool:
            print(f"Notification: {subject} - {message}")
            return True

    alert_service = RiskAlertService(
        notification_services=[MockNotificationService()],
        max_leverage=max_leverage,
        drawdown_threshold=dd_threshold
    )

    alert_service.check_and_alert(trade_log, equity_curve, asset_performance)


if __name__ == "__main__":
    # Example usage
    print("Setting up risk alert service...")

    # Create notification services (with example/placeholder credentials)
    email_service = EmailNotificationService(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        username="example@gmail.com",
        password="password",
        from_email="example@gmail.com",
        to_email="recipient@gmail.com"
    )

    telegram_service = TelegramNotificationService(
        bot_token="YOUR_BOT_TOKEN",
        chat_id="YOUR_CHAT_ID"
    )

    # Create risk alert service
    risk_alert_service = RiskAlertService(
        notification_services=[email_service, telegram_service],
        max_leverage=10.0,
        drawdown_threshold=-0.1
    )

    # Example data
    trade_log = {
        "XAUUSD": [{"sl_hit": True, "side": "long", "size": 1, "entry": 2000}],
        "BTCUSD": [{"tp_hit": True, "side": "short", "size": 0.1, "entry": 30000}]
    }
    equity_curve = {
        "XAUUSD": [10000, 9800, 9700],
        "BTCUSD": [10000, 10100, 10250]
    }
    asset_performance = {
        "XAUUSD": -3.5,
        "BTCUSD": 2.5
    }

    # Run one-time check
    print("Running risk check...")
    risk_alert_service.check_and_alert(trade_log, equity_curve, asset_performance)

    print("Starting continuous monitoring (press Ctrl+C to stop)...")
    try:
        risk_alert_service.run_alert_monitor(check_interval=60)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")