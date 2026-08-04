"""
Daily crypto price email.

Fetches current USD + NGN price for BTC, ETH, BNB, USDT, PI, and TON
from the CoinGecko public API, compares against the prices sent in
yesterday's email (stored in last_prices.json in this repo), and
emails a summary via SMTP showing the $ / ₦ difference and % change
since yesterday.

Environment variables (set as GitHub Actions secrets):
    SMTP_HOST       e.g. smtp.gmail.com
    SMTP_PORT       e.g. 587
    SMTP_USER       the Gmail address sending the email
    SMTP_PASSWORD   a Gmail App Password (NOT your normal password)
    EMAIL_TO        address(es) to send the report to (comma-separated ok)
"""

import json
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
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_prices.json")


def fetch_prices() -> dict:
    """Fetch current USD + NGN price for all coins in one request."""
    params = {
        "ids": ",".join(COINS.keys()),
        "vs_currencies": "usd,ngn",
    }
    resp = requests.get(COINGECKO_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def load_previous_prices() -> dict:
    """Load yesterday's snapshot, if it exists. Returns {} on first run."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_current_prices(data: dict) -> None:
    """Save today's snapshot so tomorrow's run can diff against it."""
    snapshot = {
        coin_id: {"usd": data[coin_id]["usd"], "ngn": data[coin_id]["ngn"]}
        for coin_id in COINS
        if coin_id in data
    }
    with open(STATE_FILE, "w") as f:
        json.dump(snapshot, f, indent=2)


def format_price(value: float, symbol: str = "$") -> str:
    if value >= 1:
        return f"{symbol}{value:,.2f}"
    return f"{symbol}{value:,.6f}"


def format_diff(value: float, symbol: str = "$") -> str:
    sign = "+" if value >= 0 else "-"
    abs_value = abs(value)
    if abs_value < 0.000001:
        abs_value = 0.0
    if abs_value >= 1 or abs_value == 0.0:
        return f"{sign}{symbol}{abs_value:,.2f}"
    return f"{sign}{symbol}{abs_value:,.6f}"


def build_email_body(data: dict, previous: dict) -> tuple[str, str]:
    """Returns (plain_text_body, html_body)."""
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    has_previous = bool(previous)

    text_lines = [f"Crypto Price Report — {today}\n"]
    if not has_previous:
        text_lines.append("(First run — no previous-day comparison yet.)\n")
    html_rows = []

    for coin_id, label in COINS.items():
        coin_data = data.get(coin_id)
        if not coin_data:
            text_lines.append(f"{label}: data unavailable")
            html_rows.append(
                f"<tr><td>{label}</td><td colspan='4'>data unavailable</td></tr>"
            )
            continue

        price_usd = coin_data.get("usd")
        price_ngn = coin_data.get("ngn")

        price_usd_str = format_price(price_usd, "$") if price_usd is not None else "N/A"
        price_ngn_str = format_price(price_ngn, "₦") if price_ngn is not None else "N/A"

        prev_coin = previous.get(coin_id)

        if prev_coin and price_usd is not None and price_ngn is not None:
            prev_usd = prev_coin.get("usd")
            prev_ngn = prev_coin.get("ngn")

            diff_usd = price_usd - prev_usd
            diff_ngn = price_ngn - prev_ngn
            pct_change = (diff_usd / prev_usd * 100) if prev_usd else 0.0

            arrow = "▲" if diff_usd >= 0 else "▼"
            color = "#1a9c4c" if diff_usd >= 0 else "#d13c3c"

            diff_usd_str = format_diff(diff_usd, "$")
            diff_ngn_str = format_diff(diff_ngn, "₦")
            change_str = f"{arrow} {diff_usd_str} | {diff_ngn_str} ({abs(pct_change):.2f}%)"
        else:
            change_str = "N/A (no data from yesterday)"
            color = "#666666"

        text_lines.append(
            f"{label}: {price_usd_str}  |  {price_ngn_str}   Change: {change_str}"
        )
        html_rows.append(
            f"<tr>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;'>{label}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;text-align:right;'>{price_usd_str}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;text-align:right;'>{price_ngn_str}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #eee;text-align:right;color:{color};font-weight:bold;font-size:12px;'>{change_str}</td>"
            f"</tr>"
        )

    text_body = "\n".join(text_lines)

    note = "" if has_previous else "<p style='color:#999;font-size:12px;'>First run — no previous-day comparison yet.</p>"

    html_body = f"""\
<html>
  <body style="font-family:Arial,sans-serif;background:#f7f7f7;padding:20px;">
    <div style="max-width:560px;margin:auto;background:#fff;border-radius:8px;padding:24px;">
      <h2 style="margin-top:0;">📊 Crypto Price Report</h2>
      <p style="color:#666;margin-top:-10px;">{today}</p>
      {note}
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
          <tr style="background:#fafafa;">
            <th style="text-align:left;padding:8px 12px;">Coin</th>
            <th style="text-align:right;padding:8px 12px;">Price (USD)</th>
            <th style="text-align:right;padding:8px 12px;">Price (NGN)</th>
            <th style="text-align:right;padding:8px 12px;">Change vs Yesterday</th>
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

    previous = load_previous_prices()
    text_body, html_body = build_email_body(data, previous)

    try:
        send_email(text_body, html_body)
    except Exception as e:
        print(f"Failed to send email: {e}", file=sys.stderr)
        sys.exit(1)

    save_current_prices(data)

    print("Email sent successfully.")
    print(text_body)


if __name__ == "__main__":
    main()
