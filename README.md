# Crypto Price Email

Sends a daily email at 6:00 AM (WAT) with the current price (in both USD
and NGN), plus how much it's moved since yesterday's email — in $, ₦,
and % — for Bitcoin, Ethereum, BNB, Tether (USDT), Pi Network, and
Toncoin. Powered by the free
[CoinGecko API](https://www.coingecko.com/en/api) and run entirely on
GitHub Actions (no server needed).

## Setup

1. **Create a Gmail App Password**
   - Go to your Google Account → Security → 2-Step Verification (must be on)
   - Then Security → App passwords → generate one for "Mail"
   - Copy the 16-character password

2. **Push this repo to GitHub**

3. **Add repository secrets**
   Go to your repo → Settings → Secrets and variables → Actions → New repository secret, and add:

   | Secret name     | Value                                  |
   |-----------------|-----------------------------------------|
   | `SMTP_USER`     | your Gmail address                     |
   | `SMTP_PASSWORD` | the App Password from step 1           |
   | `EMAIL_TO`      | the email address(es) to send reports to (comma-separated for multiple) |

4. **Test it manually**
   Go to the "Actions" tab → "Daily Crypto Price Email" → "Run workflow"
   to trigger it immediately without waiting for the schedule.

## Schedule

Runs daily at **5:00 AM UTC (6:00 AM WAT)** via the cron in
`.github/workflows/daily-crypto-email.yml`. Edit the `cron` line there
to change the time — GitHub Actions cron is always in UTC.

## Local testing

```bash
pip install -r requirements.txt
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=you@gmail.com
export SMTP_PASSWORD=your_app_password
export EMAIL_TO=you@gmail.com
python main.py
```

## Notes

- GitHub Actions' free-tier cron jobs can run a few minutes late,
  especially during high load — this is normal.
- CoinGecko's free tier has generous rate limits for a single daily call,
  no API key required.
- The script keeps a `last_prices.json` file in the repo to remember
  yesterday's prices for the day-over-day comparison. The workflow
  auto-commits it after each run — you don't need to touch it manually.
  The first email you receive after setup will show "no comparison yet"
  since there's no prior snapshot to compare against.
