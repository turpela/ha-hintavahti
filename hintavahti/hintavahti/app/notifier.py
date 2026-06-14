"""Send price-drop notifications by email (optional).

If SMTP is not configured, messages are logged instead of sent.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from . import config

log = logging.getLogger("hintavahti.notifier")


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f} €".replace(".", ",")


def send_drop_email(
    to_email: str,
    product_name: str,
    product_url: str,
    new_price: float,
    old_price: float | None,
) -> bool:
    subject = f"Hinta laski: {product_name} — {_fmt(new_price)}"
    body = "\n".join([
        f"Seurattu tuote: {product_name}",
        "",
        f"Uusi hinta:   {_fmt(new_price)}",
        f"Edellinen:    {_fmt(old_price)}",
        "",
        f"Tuote: {product_url}",
    ])

    if not config.SMTP_HOST:
        log.info("SMTP ei käytössä — ilmoitus vain lokiin:\n%s", body)
        return False
    if not to_email:
        log.info("Tuotteelle ei sähköpostiosoitetta, ohitetaan ilmoitus.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            if config.SMTP_TLS:
                server.starttls(context=ssl.create_default_context())
            if config.SMTP_USER:
                server.login(config.SMTP_USER, config.SMTP_PASS)
            server.send_message(msg)
        log.info("Ilmoitus lähetetty osoitteeseen %s", to_email)
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("Sähköpostin lähetys epäonnistui: %s", exc)
        return False
