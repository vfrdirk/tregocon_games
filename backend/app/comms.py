"""Notifications (M9): email (AWS SES) + SMS (Twilio).

Provider abstraction so the rest of the app just calls comms.send_email /
comms.send_sms. If credentials/env are absent (sandbox), the provider is
DISABLED and calls are logged instead of erroring — so the app runs here
without AWS/Twilio accounts, and is ready for Phase 1 by setting env vars.

Credentials are ALWAYS read from environment — never hardcoded, never in code.
"""
import logging
import os

logger = logging.getLogger("tregocon.comms")


class EmailProvider:
    def __init__(self):
        self.name = "ses"
        self.enabled = bool(os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"))
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client(
                "ses",
                region_name=os.environ.get("AWS_REGION", os.environ.get("SES_REGION", "us-east-1")),
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            )
        return self._client

    def send(self, to: str, subject: str, body: str) -> bool:
        if not self.enabled:
            logger.info("[email:disabled] to=%s subj=%s body=%s", to, subject, body[:80])
            return False
        from_email = os.environ.get("SES_FROM_EMAIL")
        if not from_email:
            logger.error("[email] SES_FROM_EMAIL not set; cannot send")
            return False
        self._get_client().send_email(
            Source=from_email,
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
            },
        )
        return True


class SmsProvider:
    def __init__(self):
        self.name = "twilio"
        self.enabled = bool(os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN"))
        self._client = None

    def _get_client(self):
        if self._client is None:
            from twilio.rest import Client
            self._client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
        return self._client

    def send(self, to: str, body: str) -> bool:
        if not self.enabled:
            logger.info("[sms:disabled] to=%s body=%s", to, body[:80])
            return False
        from_number = os.environ.get("TWILIO_FROM_NUMBER")
        if not from_number:
            logger.error("[sms] TWILIO_FROM_NUMBER not set; cannot send")
            return False
        self._get_client().messages.create(to=to, from_=from_number, body=body)
        return True


class Comms:
    def __init__(self):
        self.email = EmailProvider()
        self.sms = SmsProvider()

    def send_email(self, to, subject, body):
        return self.email.send(to, subject, body)

    def send_sms(self, to, body):
        return self.sms.send(to, body)


# Singleton shared across the app.
comms = Comms()


# ---------- templates (plain-text; upgrade to HTML later) ----------
def tpl_welcome_pending(display_name: str) -> tuple:
    subj = "TregoCon — registration received"
    body = (
        f"Hi {display_name},\n\n"
        "Thanks for registering for TregoCon! Your account is pending admin approval. "
        "You'll get another email as soon as you're approved and registration opens.\n\n"
        "See you at the resort!\n— The TregoCon Crew"
    )
    return subj, body


def tpl_approved(display_name: str, event_name: str) -> tuple:
    subj = f"{event_name} — you're approved!"
    body = (
        f"Hi {display_name},\n\n"
        f"Your TregoCon registration is approved. When registration opens, log in and "
        f"reserve your lodging, pick your meals, and post games to the On-Deck board.\n\n"
        "See you there!\n— The TregoCon Crew"
    )
    return subj, body


def tpl_event_open(event_name: str, url: str) -> tuple:
    subj = f"{event_name} — registration is OPEN!"
    body = (
        f"Hi,\n\n"
        f"{event_name} registration is now open. Reserve your room, choose your meals, "
        f"and start the game board:\n{url}\n\n"
        "— The TregoCon Crew"
    )
    return subj, body
