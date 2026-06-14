"""Send email notifications (optional).

If SMTP is not configured, drop notifications are logged instead of sent.
The test-email path always reports the real outcome so the UI can show it.
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


def _send(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    """Send one message. Returns (ok, message)."""
    if not config.SMTP_HOST:
        return False, "SMTP-palvelinta ei ole määritetty add-onin asetuksissa."
    if not to_email:
        return False, "Sähköpostiosoite puuttuu."

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
        log.info("Sähköposti lähetetty osoitteeseen %s", to_email)
        return True, "Lähetetty."
    except Exception as exc:  # noqa: BLE001
        log.error("Sähköpostin lähetys epäonnistui: %s", exc)
        return False, str(exc)


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
    ok, _ = _send(to_email, subject, body)
    return ok


def send_test_email(to_email: str) -> tuple[bool, str]:
    """Send a test message. Returns (ok, message) for display in the UI."""
    return _send(
        to_email,
        "Hintavahti: testiviesti",
        "Tämä on Hintavahdin testiviesti.\n\n"
        "Jos sait tämän, sähköposti-ilmoitukset on määritetty oikein.",
    )
