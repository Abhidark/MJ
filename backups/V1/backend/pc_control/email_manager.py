"""
MJ Email Manager
Read and send emails via IMAP/SMTP.
Supports Gmail (app password) and Outlook.
Config stored in email_config.json.
"""

import imaplib
import smtplib
import email
import json
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from pathlib import Path
from datetime import datetime
from typing import Optional

CONFIG_FILE = Path(__file__).parent.parent / "email_config.json"

DEFAULT_CONFIG = {
    "email": "",
    "password": "",  # App password (not regular password)
    "provider": "gmail",  # gmail or outlook
    "imap_server": "imap.gmail.com",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "configured": False,
}

PROVIDER_SETTINGS = {
    "gmail": {
        "imap_server": "imap.gmail.com",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
    },
    "outlook": {
        "imap_server": "outlook.office365.com",
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
    },
    "yahoo": {
        "imap_server": "imap.mail.yahoo.com",
        "smtp_server": "smtp.mail.yahoo.com",
        "smtp_port": 587,
    },
}


def load_email_config() -> dict:
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def save_email_config(config: dict):
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def setup_email(email_addr: str, password: str, provider: str = "gmail") -> dict:
    """Configure email settings."""
    provider = provider.lower()
    settings = PROVIDER_SETTINGS.get(provider, PROVIDER_SETTINGS["gmail"])

    config = {
        "email": email_addr,
        "password": password,
        "provider": provider,
        "imap_server": settings["imap_server"],
        "smtp_server": settings["smtp_server"],
        "smtp_port": settings["smtp_port"],
        "configured": True,
    }

    # Test connection
    try:
        mail = imaplib.IMAP4_SSL(config["imap_server"])
        mail.login(email_addr, password)
        mail.logout()
        save_email_config(config)
        return {"success": True, "message": f"Email configured! {email_addr} ({provider}) connected."}
    except Exception as e:
        return {"success": False, "message": f"Email connect failed: {str(e)}. App password sahi hai?"}


def read_emails(count: int = 5, folder: str = "INBOX") -> dict:
    """Read recent emails."""
    config = load_email_config()
    if not config.get("configured"):
        return {"success": False, "message": "Email setup nahi hai. Pehle setup karo: /email-setup"}

    try:
        mail = imaplib.IMAP4_SSL(config["imap_server"])
        mail.login(config["email"], config["password"])
        mail.select(folder)

        _, msg_nums = mail.search(None, "ALL")
        msg_list = msg_nums[0].split()

        if not msg_list:
            mail.logout()
            return {"success": True, "message": "Inbox empty hai!", "emails": []}

        # Get last N emails
        recent = msg_list[-count:]
        recent.reverse()

        emails = []
        for num in recent:
            _, msg_data = mail.fetch(num, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            # Decode subject
            subject = ""
            raw_subject = msg.get("Subject", "")
            if raw_subject:
                decoded = decode_header(raw_subject)
                for part, charset in decoded:
                    if isinstance(part, bytes):
                        subject += part.decode(charset or "utf-8", errors="ignore")
                    else:
                        subject += str(part)

            # Decode from
            from_addr = msg.get("From", "Unknown")
            date_str = msg.get("Date", "")

            # Get body preview
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        except Exception:
                            pass
                        break
            else:
                try:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                except Exception:
                    pass

            emails.append({
                "subject": subject[:100],
                "from": from_addr[:60],
                "date": date_str[:30],
                "preview": body[:150].replace("\n", " ").strip(),
            })

        mail.logout()

        # Format response
        lines = [f"Last {len(emails)} emails:"]
        for i, e in enumerate(emails, 1):
            lines.append(f"\n{i}. From: {e['from']}")
            lines.append(f"   Subject: {e['subject']}")
            lines.append(f"   Preview: {e['preview'][:80]}...")

        return {"success": True, "message": "\n".join(lines), "emails": emails}

    except Exception as e:
        return {"success": False, "message": f"Email read failed: {str(e)}"}


def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email."""
    config = load_email_config()
    if not config.get("configured"):
        return {"success": False, "message": "Email setup nahi hai."}

    try:
        msg = MIMEMultipart()
        msg["From"] = config["email"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
        server.starttls()
        server.login(config["email"], config["password"])
        server.send_message(msg)
        server.quit()

        return {"success": True, "message": f"Email bhej diya {to} ko! Subject: {subject}"}

    except Exception as e:
        return {"success": False, "message": f"Email send failed: {str(e)}"}


def check_unread() -> dict:
    """Check unread email count."""
    config = load_email_config()
    if not config.get("configured"):
        return {"success": False, "message": "Email setup nahi hai.", "count": 0}

    try:
        mail = imaplib.IMAP4_SSL(config["imap_server"])
        mail.login(config["email"], config["password"])
        mail.select("INBOX")
        _, msgs = mail.search(None, "UNSEEN")
        count = len(msgs[0].split()) if msgs[0] else 0
        mail.logout()
        return {"success": True, "message": f"{count} unread email(s) hai.", "count": count}
    except Exception as e:
        return {"success": False, "message": f"Check failed: {str(e)}", "count": 0}


def parse_email_command(text: str) -> Optional[dict]:
    """Parse email commands from user text."""
    lower = text.lower().strip()

    # Setup email
    m = re.search(r"(?:email setup|setup email|email config)\s+(\S+@\S+)\s+(\S+)\s*(\w+)?", lower)
    if m:
        return {
            "action": "setup",
            "email": m.group(1),
            "password": m.group(2),
            "provider": m.group(3) or "gmail",
        }

    # Check/read emails
    if any(w in lower for w in ["check email", "email check", "read email", "email padho",
                                 "mera email", "inbox", "email dikhao", "mail check", "mail padho"]):
        return {"action": "read"}

    # Unread count
    if any(w in lower for w in ["unread email", "kitne email", "new email", "naye email"]):
        return {"action": "unread"}

    # Send email
    m = re.search(
        r"(?:send|bhejo|email karo|mail karo|email bhejo)\s+(?:email\s+)?(?:to\s+)?(\S+@\S+)\s+(?:subject\s+)?(.+?)(?:\s+body\s+(.+))?$",
        lower
    )
    if m:
        return {
            "action": "send",
            "to": m.group(1),
            "subject": m.group(2).strip(),
            "body": m.group(3).strip() if m.group(3) else m.group(2).strip(),
        }

    # Simple send pattern
    m = re.search(r"(?:email|mail)\s+(?:bhejo|karo|send)\s+(.+?)\s+ko\s+(.+)", lower)
    if m:
        to_part = m.group(1).strip()
        msg_part = m.group(2).strip()
        # Check if to_part is email
        if "@" in to_part:
            return {"action": "send", "to": to_part, "subject": msg_part, "body": msg_part}

    return None


def handle_email_command(cmd: dict) -> dict:
    """Handle email commands."""
    action = cmd["action"]

    if action == "setup":
        return setup_email(cmd["email"], cmd["password"], cmd.get("provider", "gmail"))
    elif action == "read":
        return read_emails()
    elif action == "unread":
        return check_unread()
    elif action == "send":
        return send_email(cmd["to"], cmd["subject"], cmd.get("body", cmd["subject"]))

    return {"success": False, "message": "Unknown email command."}
