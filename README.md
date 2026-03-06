# 🌅 Morning Dashboard v3 — Setup Guide

## What this does
Runs every weekday at **8:30 AM IST** automatically via GitHub Actions.
Generates a beautiful infographic PNG and sends it to your Telegram.

---

## Files
| File | Purpose |
|------|---------|
| `morning_dashboard.py` | Main script — all logic + infographic + Telegram |
| `.github/workflows/morning_dashboard.yml` | GitHub Actions automation |

---

## One-time Setup

### Step 1 — Create a GitHub repo
1. Go to https://github.com/new
2. Create a **private** repo, e.g. `morning-dashboard`
3. Upload both files:
   - `morning_dashboard.py` → root of repo
   - `morning_dashboard.yml` → inside `.github/workflows/` folder

### Step 2 — Add Telegram Bot secrets
1. Create a Telegram bot via [@BotFather](https://t.me/BotFather) → get `BOT_TOKEN`
2. Get your `CHAT_ID`:
   - Message your bot once
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Find `"chat":{"id":XXXXXXXXX}` — that's your chat ID
3. In GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**:
   - `TELEGRAM_BOT_TOKEN` = your bot token
   - `TELEGRAM_CHAT_ID` = your chat ID (include `-` for group chats)

### Step 3 — Enable Actions
1. Go to your repo → **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**

### Step 4 — Test immediately
1. Actions → **Morning Dashboard — Daily Run** → **Run workflow** → Run
2. Watch it run (~10 min) and check Telegram

---

## What's included (v3 — expanded)

### Sectors (16 total — 8 original + 8 new)
| Original | New |
|----------|-----|
| Bank | Financial Services |
| IT | PSU Banks |
| Pharma | Healthcare |
| Auto | Capital Goods |
| Metal | Consumer Durables |
| FMCG | Oil & Gas |
| Energy | Infrastructure |
| Realty | Media |

### Cap Rotation (5 segments)
- Nifty 500 / Nifty 50 (broad universe signal)
- Next 50 / Nifty 50
- **Midcap 150 / Nifty 50** ← new
- Smallcap 250 / Nifty 50
- **Microcap 250 / Nifty 50** ← new

### All original blocks preserved
- Block 1: RS Switch (Nifty vs Gold, Bonds, USDINR)
- Block 2: Cap Rotation
- Block 3: Sector RS Ranking with FLYING / LION / BEARISH STAR / DROWNING
- Block 4: Breadth (% above 200MA, 50MA, RSI>60, 52W High)
- Block 5: Top 5 stocks in each Flying sector
- Block 6: Action A/B/C/D with full rationale

---

## Schedule
- **Automatic**: Every Mon–Fri at 8:30 AM IST (3:00 AM UTC)
- **Manual**: GitHub Actions → Run workflow anytime
- GitHub Actions provides **2,000 free minutes/month** on private repos
  (this script uses ~10 min/run × 22 trading days = ~220 min/month ✅)

---

## Troubleshooting
- **No Telegram message**: Check secrets spelling exactly — `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
- **Stale data warning**: Runs on holidays will show warning — normal, no action needed
- **Low breadth stock count (<300)**: NSE rate limiting; data is still usable
- **Sector N/A**: Yahoo Finance ticker may have changed; check `TICKERS` dict in the script
