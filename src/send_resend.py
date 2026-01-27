from __future__ import annotations

from typing import List
import requests


def send_email_resend(api_key: str, email_from: str, email_to: List[str], subject: str, html: str) -> None:
    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"from": email_from, "to": email_to, "subject": subject, "html": html},
        timeout=30,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Resend error {r.status_code}: {r.text}")
