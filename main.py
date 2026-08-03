"""
Daily crypto price email.

Fetches current USD + NGN price and 24h % change for BTC, ETH, BNB,
USDT, PI, and TON from the CoinGecko public API and emails a summary
via SMTP.

Environment variables (set as GitHub Actions secrets):
    SMTP_HOST       e.g. smtp.gmail.com
    SMTP_PORT       e.g. 587
    SMTP_USER       the Gmail address sending the email
    SMTP_PASSWORD   a Gmail App Password (NOT your normal password)
    EMAIL_TO        address(es) to send the report to (comma-separated ok)
"""

import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

COINS = {
    "bitcoin": "Bitcoin (BTC)",
    "ethereum": "Ethereum (ETH)",
    "binancecoin": "BNB",
    "tether": "Tether (USDT)",
    "pi-network": "Pi Network (PI)",
    "the-open-network": "Toncoin (TON)",
}

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"


def fetch_prices() -> dict:
    """Fetch current USD + NGN price and 24h change for all coins in one request."""
    params = {
        "ids": ",".join(COINS.keys()),
        "vs_currencies": "usd,ngn",
        "include_24hr_change": "true",
    }
    resp = requests.get(COINGECKO_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def format_price(value: float, symbol: str = "$") -> str:
    if value >= 1:
        return f"{symbol}{value:,.2f}"
    return f"{symbol}{value:,.6f}"


def build_email_body(data: dict) -> tuple[str, str]:
    """Returns (plain_text_body, html_body)."""
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")

    text_lines = [f"Crypto Price Report — {today}\n"]
    html_rows = []

    for coin_id, label in COINS.items():
        coin_data = data.get(coin_id)
        if not coin_data:
            text_lines.append(f"{label}: data unavailable")
            html_rows.append(
                f"<tr><td>{label}</td><td colspan='3'>data unavailable</td></tr>"
            )
            continue

        price_usd = coin_data.get("usd")
        price_ngn = coin_data.get("ngn")
        change = coin_data.get("usd_24h_change")

        price_usd_str = format_price(price_usd, "$") if price_usd is not None else "N/A"
        price_ngn_str = format_price(price_ngn, "₦") if price_ngn is not None else "N/A"

        if change is None:
            change_str = "N/A"
            color = "#666666"
        else:
            arrow = "▲" if change >= 0 else "▼"
            color = "#1a9c4c" if change >= 0 else "#d13c3c"
            change_str = f"{arrow} {abs(change):.2f}%"

        text_lines.append(
            f"{label}: {price_usd_str}  |  {price_ngn_str}  ({change_str} 24h)"
        )
        html_rows.append(
            f"<tr>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;'>{label}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;text-align:right;'>{price_usd_str}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;text-align:right;'>{price_ngn_str}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;text-align:right;color:{color};font-weight:bold;'>{change_str}</td>"
            f"</tr>"
        )

    text_body = "\n".join(text_lines)

    html_body = f"""\
<html>
  <body style="font-family:Arial,sans-serif;background:#f7f7f7;padding:20px;">
    <div style="max-width:480px;margin:auto;background:#fff;border-radius:8px;padding:24px;">
      <h2 style="margin-top:0;">📊 Crypto Price Report</h2>
      <p style="color:#666;margin-top:-10px;">{today}</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
          <tr style="background:#fafafa;">
            <th style="text-align:left;padding:8px 12px;">Coin</th>
            <th style="text-align:right;padding:8px 12px;">Price (USD)</th>
            <th style="text-align:right;padding:8px 12px;">Price (NGN)</th>
            <th style="text-align:right;padding:8px 12px;">24h Change</th>
          </tr>
        </thead>
        <tbody>
          {''.join(html_rows)}
        </tbody>
      </table>
      <p style="color:#999;font-size:12px;margin-top:20px;">Data via CoinGecko API</p>
    </div>
  </body>
</html>
"""
    return text_body, html_body


def send_email(text_body: str, html_body: str) -> None:
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    email_to = os.environ["EMAIL_TO"]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Crypto Price Report — {today}"
    msg["From"] = smtp_user
    msg["To"] = email_to

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, email_to.split(","), msg.as_string())


def main():
    try:
        data = fetch_prices()
    except requests.RequestException as e:
        print(f"Failed to fetch prices: {e}", file=sys.stderr)
        sys.exit(1)

    text_body, html_body = build_email_body(data)

    try:
        send_email(text_body, html_body)
    except Exception as e:
        print(f"Failed to send email: {e}", file=sys.stderr)
        sys.exit(1)

    print("Email sent successfully.")
    print(text_body)


if __name__ == "__main__":
    main()
