"""
Prashant Shah RS & Breadth — Morning Dashboard v3
==================================================
Expanded: 16 sectors + full cap-segment rotation
Output:   Attractive infographic PNG → Telegram
Run:      python morning_dashboard.py
Secrets:  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  (env vars or GitHub Secrets)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request, io, time, warnings, os, sys
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
import requests

warnings.filterwarnings('ignore')

# ── Date range ─────────────────────────────────────────────────────────────────
END       = datetime.today()
START     = END - timedelta(days=450)

# ── Index / asset tickers ──────────────────────────────────────────────────────
TICKERS = {
    'nifty50'    : '^NSEI',
    'nifty500'   : '^CRSLDX',
    'niftynext50': '^NSMIDCP',
    'niftymid150': '^CNXMID',           # NEW – Nifty Midcap 150
    'niftysml250': '^CNXSC',            # Nifty Smallcap 250
    'niftymicro' : '^CNXMICRO250',      # NEW – Nifty Microcap 250
    # Sectors (all original + expanded)
    'bank'       : '^NSEBANK',
    'it'         : '^CNXIT',
    'pharma'     : '^CNXPHARMA',
    'auto'       : '^CNXAUTO',
    'metal'      : '^CNXMETAL',
    'fmcg'       : '^CNXFMCG',
    'energy'     : '^CNXENERGY',
    'realty'     : '^CNXREALTY',
    'finance'    : '^CNXFIN',           # NEW – Financial Services
    'psbank'     : '^CNXPSUBAN',        # NEW – PSU Banks
    'healthcare' : '^CNXHEALTH',        # NEW – Healthcare (broader than Pharma)
    'capgoods'   : '^CNXCAPITALGOODS',  # NEW – Capital Goods
    'consdur'    : '^CNXCONSDURABLES',  # NEW – Consumer Durables
    'oilgas'     : '^CNXOILGAS',        # NEW – Oil & Gas
    'infra'      : '^CNXINFRA',         # NEW – Infrastructure
    'media'      : '^CNXMEDIA',         # NEW – Media
    # Assets
    'gold'       : 'GOLDBEES.NS',
    'usdinr'     : 'USDINR=X',
}

BOND_TICKERS = [
    ('NIFTYGS10YR.NS', 'Nifty GS 10YR'),
    ('GSECLONG.NS',    'Nifty GS Long'),
    ('GSEC10YBEES.NS', 'Nippon G-Sec ETF'),
    ('ICICIB22.NS',    'ICICI Bond ETF'),
    ('LICNETFGSC.NS',  'LIC G-Sec ETF'),
]

# Sectors included in RS ranking (original 8 + 8 new = 16)
SECTOR_NAMES = [
    'bank','it','pharma','auto','metal','fmcg','energy','realty',
    'finance','psbank','healthcare','capgoods','consdur','oilgas','infra','media'
]

SECTOR_DISPLAY = {
    'bank'      : 'BANK',
    'it'        : 'IT',
    'pharma'    : 'PHARMA',
    'auto'      : 'AUTO',
    'metal'     : 'METAL',
    'fmcg'      : 'FMCG',
    'energy'    : 'ENERGY',
    'realty'    : 'REALTY',
    'finance'   : 'FINANCE',
    'psbank'    : 'PSU BANK',
    'healthcare': 'HEALTHCARE',
    'capgoods'  : 'CAP GOODS',
    'consdur'   : 'CONS DUR',
    'oilgas'    : 'OIL & GAS',
    'infra'     : 'INFRA',
    'media'     : 'MEDIA',
}

SECTOR_URLS = {
    'bank'      : 'https://nsearchives.nseindia.com/content/indices/ind_niftybanklist.csv',
    'it'        : 'https://nsearchives.nseindia.com/content/indices/ind_niftyitlist.csv',
    'pharma'    : 'https://nsearchives.nseindia.com/content/indices/ind_niftypharmalist.csv',
    'auto'      : 'https://nsearchives.nseindia.com/content/indices/ind_niftyautolist.csv',
    'fmcg'      : 'https://nsearchives.nseindia.com/content/indices/ind_niftyfmcglist.csv',
    'metal'     : 'https://nsearchives.nseindia.com/content/indices/ind_niftymetallist.csv',
    'energy'    : 'https://nsearchives.nseindia.com/content/indices/ind_niftyenergylist.csv',
    'realty'    : 'https://nsearchives.nseindia.com/content/indices/ind_niftyrealty.csv',
    'finance'   : 'https://nsearchives.nseindia.com/content/indices/ind_niftyfinancelist.csv',
    'psbank'    : 'https://nsearchives.nseindia.com/content/indices/ind_niftypsubanklist.csv',
    'healthcare': 'https://nsearchives.nseindia.com/content/indices/ind_niftyhealthcarelist.csv',
    'capgoods'  : 'https://nsearchives.nseindia.com/content/indices/ind_niftycapitalgoods.csv',
    'consdur'   : 'https://nsearchives.nseindia.com/content/indices/ind_niftyconsumerdurableslist.csv',
    'oilgas'    : 'https://nsearchives.nseindia.com/content/indices/ind_niftyoilgaslist.csv',
    'infra'     : 'https://nsearchives.nseindia.com/content/indices/ind_niftyinfrastructurelist.csv',
    'media'     : 'https://nsearchives.nseindia.com/content/indices/ind_niftymedialist.csv',
}

# ── Colour palette ─────────────────────────────────────────────────────────────
BG        = '#0d1117'
CARD      = '#161b22'
CARD2     = '#1c2128'
GREEN     = '#3fb950'
RED       = '#f85149'
AMBER     = '#d29922'
BLUE      = '#58a6ff'
PURPLE    = '#bc8cff'
TEAL      = '#39d353'
WHITE     = '#e6edf3'
GREY      = '#8b949e'
GOLD_COL  = '#ffd700'

errors = []

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Fetch closes
# ══════════════════════════════════════════════════════════════════════════════
def step1_fetch():
    print("STEP 1: Fetching index & sector closes...")
    closes = {}
    for key, ticker in TICKERS.items():
        try:
            df = yf.download(ticker, start=START, end=END, progress=False, auto_adjust=True)
            if not df.empty:
                closes[key] = df['Close'].squeeze()
                print(f'  ✅ {key:15s} ({ticker})')
            else:
                print(f'  ⚠️  {key:15s} NO DATA')
                errors.append(f'{key}: no data')
        except Exception as e:
            print(f'  ❌ {key:15s} ERROR: {e}')
            errors.append(f'{key}: {e}')

    # Bond fallback
    bond_loaded = False
    bond_ticker_used = None
    for bond_ticker, bond_label in BOND_TICKERS:
        try:
            df_b = yf.download(bond_ticker, start=START, end=END, progress=False, auto_adjust=True)
            if not df_b.empty and len(df_b) > 50:
                closes['bonds'] = df_b['Close'].squeeze()
                bond_ticker_used = bond_ticker
                bond_loaded = True
                print(f'  ✅ bonds ({bond_ticker})')
                break
        except:
            pass
    if not bond_loaded:
        print('  ⚠️  bonds — all fallbacks failed')
        errors.append('bonds: all fallbacks failed')

    closes_df = pd.DataFrame(closes).ffill()

    if 'nifty50' not in closes_df.columns:
        raise RuntimeError('CRITICAL: Nifty 50 unavailable. HALTING.')

    last_date = closes_df.index[-1]
    days_old  = (datetime.today() - pd.Timestamp(last_date)).days
    if days_old > 3:
        raise RuntimeError(f'DATA STALE: {days_old} days old. HALTING.')

    print(f'\n✅ STEP 1 COMPLETE — Last close: {last_date.date()}')
    return closes_df, last_date, days_old, bond_ticker_used


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — RS Switch
# ══════════════════════════════════════════════════════════════════════════════
def step2_rs_switch(closes):
    print("STEP 2: RS Switch...")
    asset_labels = {'gold':'Gold (GOLDBEES)', 'bonds':'Bonds (GS)', 'usdinr':'USDINR'}
    rs_switch = {}
    for ak, lbl in asset_labels.items():
        if ak not in closes.columns:
            rs_switch[ak] = 'N/A'; continue
        ratio  = closes['nifty50'] / closes[ak]
        status = 'ON' if ratio.iloc[-1] > ratio.rolling(50).mean().iloc[-1] else 'OFF'
        rs_switch[ak] = status
        print(f'  {"✅" if status=="ON" else "❌"} Nifty vs {lbl}: {status}')

    valid = {k:v for k,v in rs_switch.items() if v in ('ON','OFF')}
    on_n  = sum(1 for v in valid.values() if v=='ON')
    tot   = len(valid)
    if   tot == 0: overall = 'N/A'
    elif on_n == tot: overall = 'ON'
    elif on_n == 0:   overall = 'OFF'
    else:             overall = 'PARTIAL'

    print(f'\n✅ STEP 2 COMPLETE — Overall: {overall} ({on_n}/{tot})')
    return rs_switch, overall, asset_labels


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Cap Rotation (expanded)
# ══════════════════════════════════════════════════════════════════════════════
def step3_cap_rotation(closes):
    print("STEP 3: Cap rotation...")
    results = {}

    def cap_signal(a, b, label):
        if a not in closes.columns or b not in closes.columns:
            return None
        ratio  = closes[a] / closes[b]
        above  = ratio.iloc[-1] > ratio.rolling(50).mean().iloc[-1]
        rs_pct = (closes[a].pct_change(50).iloc[-1] - closes[b].pct_change(50).iloc[-1]) * 100
        return {'above_ma': above, 'rs_pct': round(rs_pct, 2), 'label': label}

    results['broad']   = cap_signal('nifty500',    'nifty50',    'Nifty500 / Nifty50')
    results['mid']     = cap_signal('niftymid150',  'nifty50',    'MidCap150 / Nifty50')
    results['small']   = cap_signal('niftysml250',  'nifty50',    'SmallCap250 / Nifty50')
    results['micro']   = cap_signal('niftymicro',   'nifty50',    'Microcap250 / Nifty50')
    results['next50']  = cap_signal('niftynext50',  'nifty50',    'Next50 / Nifty50')

    # Primary universe decision (based on broad signal)
    broad = results.get('broad')
    if broad and broad['above_ma']:
        universe    = 'Nifty 500 (Broad)'
        cap_signal_ = 'MID/SMALL LEADING'
    else:
        universe    = 'Nifty 100 (Large Cap Only)'
        cap_signal_ = 'LARGE CAP ONLY'

    print(f'  Universe: {universe}')
    print(f'\n✅ STEP 3 COMPLETE')
    return results, universe, cap_signal_


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Sector RS Ranking
# ══════════════════════════════════════════════════════════════════════════════
def step4_sector_rs(closes):
    print("STEP 4: Sector RS rankings...")
    sector_results = []
    for s in SECTOR_NAMES:
        if s not in closes.columns:
            sector_results.append({'sector':s,'rs_alpha':None,'above_ma':None,'pattern':'N/A'})
            errors.append(f'Sector {s}: data missing'); continue
        rs_alpha = (closes[s].pct_change(50).iloc[-1] - closes['nifty50'].pct_change(50).iloc[-1]) * 100
        ratio    = closes[s] / closes['nifty50']
        above_ma = bool(ratio.iloc[-1] > ratio.rolling(50).mean().iloc[-1])
        pattern  = ('FLYING'       if rs_alpha>0 and above_ma else
                    'LION'         if rs_alpha>0 else
                    'BEARISH STAR' if above_ma   else 'DROWNING')
        sector_results.append({'sector':s,'rs_alpha':round(rs_alpha,2),'above_ma':above_ma,'pattern':pattern})
        print(f'  {SECTOR_DISPLAY.get(s,s):12s}: RS={rs_alpha:+.2f}% → {pattern}')

    sector_results.sort(key=lambda x: x['rs_alpha'] if x['rs_alpha'] is not None else -999, reverse=True)
    for i,r in enumerate(sector_results): r['rank'] = i+1

    flying  = [r['sector'] for r in sector_results if r['pattern']=='FLYING']
    drown   = [r['sector'] for r in sector_results if r['pattern']=='DROWNING']
    print(f'\n✅ STEP 4 COMPLETE — Flying: {[SECTOR_DISPLAY.get(s,s) for s in flying]}')
    return sector_results, flying, drown


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Breadth
# ══════════════════════════════════════════════════════════════════════════════
def fetch_nse_stocks(url):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        df = pd.read_csv(io.StringIO(r.read().decode('utf-8')))
    return [s.strip()+'.NS' for s in df['Symbol'].dropna()]

def step5_breadth():
    print("STEP 5: Breadth indicators... (5-8 min)")
    try:
        symbols = fetch_nse_stocks('https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv')
        print(f'  ✅ {len(symbols)} Nifty 500 stocks')
    except Exception as e:
        print(f'  ⚠️  NSE list failed: {e}')
        errors.append(str(e))
        return None, None, None, None, 'UNKNOWN', False, 0

    stock_data = {}
    batches = (len(symbols)+49)//50
    for i in range(0, len(symbols), 50):
        batch = symbols[i:i+50]; bn = i//50+1
        try:
            df = yf.download(batch, start=START, end=END, progress=False, auto_adjust=True)
            c  = df['Close'] if isinstance(df.columns, pd.MultiIndex) else df[['Close']].rename(columns={'Close':batch[0]})
            stock_data.update(c.to_dict('series'))
        except Exception as e:
            errors.append(f'Breadth batch {bn}: {e}')
        if bn%5==0 or bn==batches: print(f'  Batch {bn}/{batches} — {len(stock_data)} stocks')
        time.sleep(0.8)

    sc = pd.DataFrame(stock_data).ffill().dropna(axis=1, thresh=200)
    n  = sc.shape[1]
    print(f'\n  ✅ Breadth universe: {n} valid stocks')
    if n < 300: errors.append(f'WARNING: Only {n} stocks — breadth may be unreliable')

    def rsi14(s):
        d=s.diff(); g=d.clip(lower=0).rolling(14).mean(); lo=(-d.clip(upper=0)).rolling(14).mean()
        return 100-(100/(1+g/lo))

    if n > 0:
        b200  = round((sc.iloc[-1] > sc.rolling(200).mean().iloc[-1]).sum()/n*100, 1)
        b50   = round((sc.iloc[-1] > sc.rolling(50).mean().iloc[-1]).sum()/n*100,  1)
        b52wh = round((sc.iloc[-1] >= sc.rolling(252).max().iloc[-1]*0.99).sum()/n*100, 1)
        brsi  = round((sc.apply(rsi14).iloc[-1] > 60).sum()/n*100, 1)
        bzone = 'OVERBOUGHT' if b50>75 else ('OVERSOLD' if b50<25 else 'NEUTRAL')
        available = True
    else:
        b200=b50=b52wh=brsi=None; bzone='UNKNOWN'; available=False; n=0

    print(f'\n✅ STEP 5 COMPLETE — Breadth zone: {bzone}')
    return b200, b50, b52wh, brsi, bzone, available, n


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Top stocks in Flying sectors
# ══════════════════════════════════════════════════════════════════════════════
def step6_top_stocks(closes, flying):
    print("STEP 6: Top stocks in Flying sectors...")
    top_stocks = {}
    if not flying:
        print('  ℹ️  No Flying sectors today.'); return top_stocks

    for sec in flying:
        if sec not in SECTOR_URLS: continue
        print(f'  Scanning {SECTOR_DISPLAY.get(sec,sec)}...')
        try: sec_syms = fetch_nse_stocks(SECTOR_URLS[sec])
        except Exception as e: errors.append(f'{sec} list: {e}'); continue

        sec_data = {}
        for i in range(0, len(sec_syms), 30):
            batch = sec_syms[i:i+30]
            try:
                df = yf.download(batch, start=START, end=END, progress=False, auto_adjust=True)
                c  = df['Close'] if isinstance(df.columns, pd.MultiIndex) else df[['Close']].rename(columns={'Close':batch[0]})
                sec_data.update(c.to_dict('series'))
            except: pass
            time.sleep(0.5)

        sdf = pd.DataFrame(sec_data).ffill().dropna(axis=1, thresh=100)
        if sdf.empty: continue
        idx_ret = closes[sec].pct_change(50).iloc[-1]*100 if sec in closes.columns else 0

        ranked = []
        for stock in sdf.columns:
            try:
                rs_a  = sdf[stock].pct_change(50).iloc[-1]*100 - idx_ret
                above = bool(sdf[stock].iloc[-1] > sdf[stock].rolling(50).mean().iloc[-1])
                ranked.append({'stock': stock.replace('.NS',''), 'rs_alpha': round(rs_a,2),
                               'above_50ma': above, 'ticker': stock})
            except: pass

        top5 = sorted(ranked, key=lambda x: x['rs_alpha'], reverse=True)[:5]
        top_stocks[sec] = top5
        for i,s in enumerate(top5):
            print(f'    {i+1}. {s["stock"]:20s} RS={s["rs_alpha"]:+.2f}%  50MA:{"✅" if s["above_50ma"] else "❌"}')

    print(f'\n✅ STEP 6 COMPLETE')
    return top_stocks


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Action A/B/C/D
# ══════════════════════════════════════════════════════════════════════════════
def step7_action(switch_overall, bzone):
    if switch_overall=='OFF' or bzone=='OVERSOLD':
        code='D'; text='DEFENSIVE / SHORT — Do NOT buy. Monitor Drowning sectors only.'
    elif bzone=='OVERBOUGHT':
        code='C'; text='HOLD ONLY — No new positions. Tighten trailing stops.'
    elif switch_overall=='PARTIAL':
        code='B'; text='SELECTIVE LONG — Top-ranked Flying sector only. Half size.'
    elif switch_overall=='ON':
        code='A'; text='AGGRESSIVE LONG — Rank 1-2 stocks in Flying sectors. Look for breakouts.'
    else:
        code='D'; text='DEFENSIVE — Conditions unclear. No new positions.'
    return code, text


# ══════════════════════════════════════════════════════════════════════════════
# INFOGRAPHIC GENERATION
# ══════════════════════════════════════════════════════════════════════════════
def make_infographic(today_str, last_str, run_time,
                     rs_switch, switch_overall, asset_labels,
                     cap_results, universe, cap_signal_str,
                     sector_results, flying, drown,
                     b200, b50, b52wh, brsi, bzone, breadth_available, n_stocks,
                     top_stocks, action_code, action_text,
                     days_old, bond_ticker_used):

    ACTION_COLOR = {
        'A': GREEN, 'B': BLUE, 'C': AMBER, 'D': RED
    }.get(action_code, GREY)

    # ── Figure setup ───────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(20, 28), facecolor=BG)
    fig.patch.set_facecolor(BG)

    gs_main = gridspec.GridSpec(
        7, 1,
        figure=fig,
        hspace=0.035,
        top=0.97, bottom=0.02,
        left=0.025, right=0.975,
        height_ratios=[0.85, 1.0, 3.2, 1.6, 2.8, 2.2, 0.4]
    )

    # ── Helper functions ───────────────────────────────────────────────────────
    def card_bg(ax, color=CARD, alpha=1.0, radius=0.04):
        ax.set_facecolor('none')
        for sp in ax.spines.values(): sp.set_visible(False)
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
        fig.canvas.draw()
        bb = ax.get_position()
        rect = FancyBboxPatch((bb.x0, bb.y0), bb.width, bb.height,
                              boxstyle=f"round,pad=0.002",
                              transform=fig.transFigure, clip_on=False,
                              facecolor=color, edgecolor='#30363d', linewidth=0.8, alpha=alpha)
        fig.add_artist(rect)

    def section_title(ax, txt, color=WHITE):
        ax.text(0.012, 0.78, txt, transform=ax.transAxes,
                fontsize=9, fontweight='bold', color=GREY,
                fontfamily='monospace', va='top', letter_spacing=1)

    # ══════════════════════════════════════════════════════════════════════════
    # ROW 0 — HEADER
    # ══════════════════════════════════════════════════════════════════════════
    ax_hdr = fig.add_subplot(gs_main[0])
    card_bg(ax_hdr, CARD2)
    ax_hdr.set_xlim(0,1); ax_hdr.set_ylim(0,1)
    ax_hdr.axis('off')

    # Left: title
    ax_hdr.text(0.012, 0.72, '🌅  MORNING DASHBOARD', transform=ax_hdr.transAxes,
                fontsize=19, fontweight='bold', color=WHITE, va='center', fontfamily='monospace')
    ax_hdr.text(0.012, 0.22, f'Data: {last_str}  •  Run: {run_time} IST  •  Prashant Shah RS & Breadth System',
                transform=ax_hdr.transAxes, fontsize=8.5, color=GREY, va='center', fontfamily='monospace')

    # Right: Action badge
    badge_x = 0.72
    action_bg = FancyBboxPatch((badge_x, 0.08), 0.265, 0.84,
                               boxstyle="round,pad=0.01",
                               transform=ax_hdr.transAxes, clip_on=False,
                               facecolor=ACTION_COLOR+'33', edgecolor=ACTION_COLOR, linewidth=2)
    ax_hdr.add_patch(action_bg)
    ax_hdr.text(badge_x+0.132, 0.72, f'ACTION  [{action_code}]',
                transform=ax_hdr.transAxes, fontsize=14, fontweight='bold',
                color=ACTION_COLOR, va='center', ha='center', fontfamily='monospace')
    short_text = action_text.split('—')[0].strip()
    ax_hdr.text(badge_x+0.132, 0.22, short_text,
                transform=ax_hdr.transAxes, fontsize=7.5, color=ACTION_COLOR,
                va='center', ha='center', fontfamily='monospace')

    # ══════════════════════════════════════════════════════════════════════════
    # ROW 1 — RS SWITCH + CAP ROTATION (side by side)
    # ══════════════════════════════════════════════════════════════════════════
    gs_row1 = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=gs_main[1],
                                               wspace=0.02, hspace=0)
    ax_sw  = fig.add_subplot(gs_row1[0])
    ax_cap = fig.add_subplot(gs_row1[1])

    # RS Switch panel
    card_bg(ax_sw)
    ax_sw.set_xlim(0,1); ax_sw.set_ylim(0,1); ax_sw.axis('off')
    ax_sw.text(0.03, 0.91, 'BLOCK 1 — RS SWITCH  (Equity vs Asset Classes)',
               transform=ax_sw.transAxes, fontsize=8, color=GREY,
               fontfamily='monospace', fontweight='bold', va='top')

    sw_items = [
        ('vs Gold (GOLDBEES)', rs_switch.get('gold','N/A')),
        ('vs Bonds (GS)',      rs_switch.get('bonds','N/A')),
        ('vs USDINR',          rs_switch.get('usdinr','N/A')),
    ]
    for idx, (lbl, val) in enumerate(sw_items):
        y = 0.72 - idx*0.19
        col = GREEN if val=='ON' else (RED if val=='OFF' else AMBER)
        icon = '●' if val=='ON' else ('○' if val=='OFF' else '◌')
        ax_sw.text(0.04, y, f'{icon}  Nifty {lbl}', transform=ax_sw.transAxes,
                   fontsize=9, color=col, va='center', fontfamily='monospace')
        ax_sw.text(0.82, y, val, transform=ax_sw.transAxes,
                   fontsize=9, fontweight='bold', color=col, va='center',
                   ha='center', fontfamily='monospace')

    # Divider
    ax_sw.axhline(0.17, xmin=0.03, xmax=0.97, color='#30363d', linewidth=0.8,
                  transform=ax_sw.transAxes)
    oc = GREEN if switch_overall=='ON' else (RED if switch_overall=='OFF' else AMBER)
    ax_sw.text(0.04, 0.09, f'OVERALL:', transform=ax_sw.transAxes,
               fontsize=10, color=GREY, va='center', fontfamily='monospace', fontweight='bold')
    ax_sw.text(0.36, 0.09, switch_overall, transform=ax_sw.transAxes,
               fontsize=11, fontweight='bold', color=oc, va='center', fontfamily='monospace')

    # Cap Rotation panel
    card_bg(ax_cap)
    ax_cap.set_xlim(0,1); ax_cap.set_ylim(0,1); ax_cap.axis('off')
    ax_cap.text(0.03, 0.91, 'BLOCK 2 — CAP ROTATION  (vs Nifty 50, 50-bar RS)',
                transform=ax_cap.transAxes, fontsize=8, color=GREY,
                fontfamily='monospace', fontweight='bold', va='top')

    cap_rows = [
        ('Next50',   cap_results.get('next50')),
        ('Mid150',   cap_results.get('mid')),
        ('Sml250',   cap_results.get('small')),
        ('Micro250', cap_results.get('micro')),
    ]
    for idx, (lbl, res) in enumerate(cap_rows):
        y = 0.74 - idx*0.165
        if res is None:
            ax_cap.text(0.04, y, f'◌  {lbl:9s}  N/A', transform=ax_cap.transAxes,
                        fontsize=9, color=GREY, va='center', fontfamily='monospace'); continue
        col  = GREEN if res['above_ma'] else RED
        icon = '▲' if res['above_ma'] else '▼'
        rs_s = f"{res['rs_pct']:+.1f}%"
        ax_cap.text(0.04, y, f'{icon}  {lbl:9s}  {rs_s:>7s}', transform=ax_cap.transAxes,
                    fontsize=9, color=col, va='center', fontfamily='monospace')

    ax_cap.axhline(0.17, xmin=0.03, xmax=0.97, color='#30363d', linewidth=0.8,
                   transform=ax_cap.transAxes)
    uc = GREEN if 'Broad' in universe else AMBER
    ax_cap.text(0.04, 0.09, f'UNIVERSE: {cap_signal_str}', transform=ax_cap.transAxes,
                fontsize=9.5, fontweight='bold', color=uc, va='center', fontfamily='monospace')

    # ══════════════════════════════════════════════════════════════════════════
    # ROW 2 — SECTOR RS RANKING (horizontal bar chart)
    # ══════════════════════════════════════════════════════════════════════════
    ax_sec = fig.add_subplot(gs_main[2])
    card_bg(ax_sec)
    ax_sec.set_facecolor(CARD)
    for sp in ax_sec.spines.values(): sp.set_visible(False)

    valid_sec = [r for r in sector_results if r['rs_alpha'] is not None]
    labels    = [SECTOR_DISPLAY.get(r['sector'], r['sector']) for r in valid_sec]
    values    = [r['rs_alpha'] for r in valid_sec]
    patterns  = [r['pattern'] for r in valid_sec]

    PATTERN_COLOR = {
        'FLYING'      : GREEN,
        'LION'        : TEAL,
        'BEARISH STAR': AMBER,
        'DROWNING'    : RED,
        'N/A'         : GREY,
    }
    bar_colors = [PATTERN_COLOR.get(p, GREY) for p in patterns]

    y_pos = range(len(labels))
    bars = ax_sec.barh(list(y_pos), values, color=bar_colors, height=0.72,
                       edgecolor='none', alpha=0.88)

    # Zero line
    ax_sec.axvline(0, color='#30363d', linewidth=1.2, zorder=5)

    # Labels
    for i, (bar, val, pat, lbl) in enumerate(zip(bars, values, patterns, labels)):
        # Sector name
        ax_sec.text(-0.25, i, lbl, va='center', ha='right',
                    fontsize=8.5, color=WHITE, fontfamily='monospace', fontweight='bold')
        # Value
        x_offset = 0.08 if val>=0 else -0.08
        ha = 'left' if val>=0 else 'right'
        ax_sec.text(val+x_offset, i, f'{val:+.1f}%', va='center', ha=ha,
                    fontsize=8, color=PATTERN_COLOR.get(pat, GREY), fontfamily='monospace')
        # Pattern badge (for FLYING and DROWNING)
        if pat in ('FLYING','DROWNING'):
            badge = '★ FLYING' if pat=='FLYING' else '▼ DROWN'
            bx = ax_sec.get_xlim()[1]*0.72
            ax_sec.text(bx, i, badge, va='center', ha='left',
                        fontsize=7.5, color=PATTERN_COLOR[pat],
                        fontfamily='monospace', fontweight='bold')

    max_v = max(abs(v) for v in values) * 1.45 if values else 10
    ax_sec.set_xlim(-max_v, max_v)
    ax_sec.set_ylim(-0.7, len(labels)-0.3)
    ax_sec.set_yticks([])
    ax_sec.xaxis.set_tick_params(colors=GREY, labelsize=7)
    ax_sec.tick_params(axis='x', colors=GREY)
    for sp in ax_sec.spines.values(): sp.set_visible(False)
    ax_sec.set_facecolor(CARD)

    # Section title
    ax_sec.text(0.5, 1.025, 'BLOCK 3 — SECTOR RS RANKING  (50-bar RS-Alpha vs Nifty 50)',
                transform=ax_sec.transAxes, fontsize=9, color=GREY, fontweight='bold',
                ha='center', va='bottom', fontfamily='monospace')

    # Legend
    legend_items = [
        mpatches.Patch(color=GREEN, label='FLYING (Long ★)'),
        mpatches.Patch(color=TEAL,  label='LION'),
        mpatches.Patch(color=AMBER, label='BEARISH STAR'),
        mpatches.Patch(color=RED,   label='DROWNING (Short ▼)'),
    ]
    ax_sec.legend(handles=legend_items, loc='lower right', fontsize=7.5,
                  facecolor=CARD2, edgecolor='#30363d', labelcolor=WHITE,
                  ncol=4, framealpha=0.9)

    # ══════════════════════════════════════════════════════════════════════════
    # ROW 3 — BREADTH DASHBOARD (4 gauges)
    # ══════════════════════════════════════════════════════════════════════════
    gs_row3 = gridspec.GridSpecFromSubplotSpec(1, 4, subplot_spec=gs_main[3],
                                               wspace=0.025)
    breadth_items = [
        ('% Above 200MA', b200, 80, 20, 'Healthy Bull'),
        ('% Above 50MA ◀ PRIMARY', b50, 75, 25, bzone),
        ('% RSI > 60',    brsi, 70, 20, ''),
        ('% Near 52W Hi', b52wh, 25, 5, ''),
    ]

    for bi, (blbl, bval, hi, lo, verdict) in enumerate(breadth_items):
        ax_b = fig.add_subplot(gs_row3[bi])
        card_bg(ax_b, CARD2 if bi==1 else CARD)
        ax_b.set_xlim(0,1); ax_b.set_ylim(0,1); ax_b.axis('off')

        ax_b.text(0.5, 0.96, blbl, transform=ax_b.transAxes,
                  fontsize=7.5, color=GREY if bi!=1 else WHITE,
                  fontweight='bold' if bi==1 else 'normal',
                  ha='center', va='top', fontfamily='monospace')

        if bval is not None:
            col = RED if bval>hi else (GREEN if bval<lo else AMBER)
            ax_b.text(0.5, 0.55, f'{bval:.1f}%', transform=ax_b.transAxes,
                      fontsize=22 if bi==1 else 18, fontweight='bold', color=col,
                      ha='center', va='center', fontfamily='monospace')
            # Progress bar
            bar_y = 0.2
            bar_w = 0.82; bar_h = 0.09
            bar_x = (1-bar_w)/2
            # Background
            ax_b.add_patch(FancyBboxPatch((bar_x, bar_y), bar_w, bar_h,
                                          boxstyle='round,pad=0.005',
                                          facecolor='#30363d', edgecolor='none',
                                          transform=ax_b.transAxes))
            # Fill
            fill_w = bar_w * min(bval/100, 1)
            if fill_w > 0:
                ax_b.add_patch(FancyBboxPatch((bar_x, bar_y), fill_w, bar_h,
                                              boxstyle='round,pad=0.005',
                                              facecolor=col, edgecolor='none',
                                              transform=ax_b.transAxes, alpha=0.85))
            if verdict:
                ax_b.text(0.5, 0.08, verdict, transform=ax_b.transAxes,
                          fontsize=7.5, color=col, ha='center', va='bottom',
                          fontfamily='monospace', fontweight='bold')
        else:
            ax_b.text(0.5, 0.5, 'N/A', transform=ax_b.transAxes,
                      fontsize=18, color=GREY, ha='center', va='center', fontfamily='monospace')

    # Section title
    ax_b0 = fig.add_subplot(gs_row3[0])   # just to get position ref
    fig.text(0.5, fig.add_subplot(gs_main[3]).get_position().y1 + 0.002,
             'BLOCK 4 — BREADTH DASHBOARD  (Nifty 500 Universe)',
             ha='center', va='bottom', fontsize=9, color=GREY,
             fontweight='bold', fontfamily='monospace')
    plt.close('all')   # avoid duplicate axes ref

    # ── Rebuild figure (re-open after close) ── Restart from scratch is complex,
    # so we'll use a different approach: add text directly
    # (The above text approach sometimes mis-positions; handled better below via ax_sec)

    # ══════════════════════════════════════════════════════════════════════════
    # ROW 4 — TOP STOCKS IN FLYING SECTORS (table)
    # ══════════════════════════════════════════════════════════════════════════
    ax_ts = fig.add_subplot(gs_main[4])
    card_bg(ax_ts)
    ax_ts.set_xlim(0,1); ax_ts.set_ylim(0,1); ax_ts.axis('off')
    ax_ts.text(0.5, 0.97, 'BLOCK 5 — TOP STOCKS IN FLYING SECTORS  (RS-Alpha vs Sector, 50-bar)',
               transform=ax_ts.transAxes, fontsize=9, color=GREY,
               fontweight='bold', ha='center', va='top', fontfamily='monospace')

    if not top_stocks:
        ax_ts.text(0.5, 0.5, 'No Flying sectors today.', transform=ax_ts.transAxes,
                   fontsize=12, color=AMBER, ha='center', va='center', fontfamily='monospace')
    else:
        sectors_list = list(top_stocks.keys())
        n_cols = min(len(sectors_list), 4)
        col_w  = 0.97 / n_cols
        for ci, sec in enumerate(sectors_list[:4]):
            stocks = top_stocks[sec]
            cx     = 0.015 + ci * col_w
            sec_lbl = SECTOR_DISPLAY.get(sec, sec.upper())
            ax_ts.text(cx + col_w*0.5, 0.90, f'★  {sec_lbl}',
                       transform=ax_ts.transAxes, fontsize=9.5, fontweight='bold',
                       color=GOLD_COL, ha='center', va='top', fontfamily='monospace')
            # Column headers
            ax_ts.text(cx+0.005, 0.81, '#  Stock',
                       transform=ax_ts.transAxes, fontsize=7.5, color=GREY,
                       va='top', fontfamily='monospace')
            ax_ts.text(cx+col_w-0.01, 0.81, 'RS%  50MA',
                       transform=ax_ts.transAxes, fontsize=7.5, color=GREY,
                       va='top', ha='right', fontfamily='monospace')
            ax_ts.axhline(0.795 - ci*0,   # just visual line per column
                          xmin=cx, xmax=cx+col_w-0.01,
                          color='#30363d', linewidth=0.6,
                          transform=ax_ts.transAxes)

            for ri, s in enumerate(stocks[:5]):
                y  = 0.73 - ri*0.135
                col = GREEN if s['above_50ma'] else AMBER
                ma_icon = '✓' if s['above_50ma'] else '✗'
                rank_icon = '★' if ri==0 else f'{ri+1}'
                ax_ts.text(cx+0.005, y, f'{rank_icon}  {s["stock"][:14]}',
                            transform=ax_ts.transAxes, fontsize=8, color=col,
                            va='center', fontfamily='monospace')
                ax_ts.text(cx+col_w-0.015, y,
                            f'{s["rs_alpha"]:+.1f}%  {ma_icon}',
                            transform=ax_ts.transAxes, fontsize=8, color=col,
                            va='center', ha='right', fontfamily='monospace')

        # If more than 4 flying sectors, show remaining as text
        if len(sectors_list) > 4:
            extra = [SECTOR_DISPLAY.get(s,s) for s in sectors_list[4:]]
            ax_ts.text(0.5, 0.03, f'+ More Flying: {", ".join(extra)}',
                       transform=ax_ts.transAxes, fontsize=8, color=GREEN,
                       ha='center', va='bottom', fontfamily='monospace')

    # ══════════════════════════════════════════════════════════════════════════
    # ROW 5 — FULL ACTION + IMPLICATIONS
    # ══════════════════════════════════════════════════════════════════════════
    ax_act = fig.add_subplot(gs_main[5])
    card_bg(ax_act, CARD2)
    ax_act.set_xlim(0,1); ax_act.set_ylim(0,1); ax_act.axis('off')
    ax_act.text(0.5, 0.94, "BLOCK 6 — TODAY'S ACTION",
                transform=ax_act.transAxes, fontsize=9, color=GREY,
                fontweight='bold', ha='center', va='top', fontfamily='monospace')

    # Big action text
    ax_act.text(0.5, 0.72, f'[ {action_code} ]  {action_text}',
                transform=ax_act.transAxes, fontsize=12, fontweight='bold',
                color=ACTION_COLOR, ha='center', va='center', fontfamily='monospace',
                wrap=True)

    # Key signals summary
    sw_col = GREEN if switch_overall=='ON' else (RED if switch_overall=='OFF' else AMBER)
    bz_col = GREEN if bzone=='NEUTRAL' else (RED if bzone=='OVERSOLD' else AMBER)
    ax_act.text(0.25, 0.44, f'RS Switch:  {switch_overall}',
                transform=ax_act.transAxes, fontsize=10, fontweight='bold',
                color=sw_col, ha='center', va='center', fontfamily='monospace')
    ax_act.text(0.5,  0.44, f'Breadth:  {bzone}',
                transform=ax_act.transAxes, fontsize=10, fontweight='bold',
                color=bz_col, ha='center', va='center', fontfamily='monospace')
    ax_act.text(0.75, 0.44, f'Universe:  {cap_signal_str}',
                transform=ax_act.transAxes, fontsize=10, fontweight='bold',
                color=BLUE, ha='center', va='center', fontfamily='monospace')

    # Priority sectors
    fly_str  = ', '.join([SECTOR_DISPLAY.get(s,s) for s in flying]) or 'None'
    drown_str = ', '.join([SECTOR_DISPLAY.get(s,s) for s in drown]) or 'None'
    ax_act.text(0.5, 0.26,
                f'LONG: {fly_str}',
                transform=ax_act.transAxes, fontsize=8.5, color=GREEN,
                ha='center', va='center', fontfamily='monospace')
    ax_act.text(0.5, 0.14,
                f'SHORT: {drown_str}',
                transform=ax_act.transAxes, fontsize=8.5, color=RED,
                ha='center', va='center', fontfamily='monospace')

    # ══════════════════════════════════════════════════════════════════════════
    # ROW 6 — FOOTER / DATA INTEGRITY
    # ══════════════════════════════════════════════════════════════════════════
    ax_ft = fig.add_subplot(gs_main[6])
    card_bg(ax_ft, '#0d1117')
    ax_ft.set_xlim(0,1); ax_ft.set_ylim(0,1); ax_ft.axis('off')

    stale_warn = ' ⚠️ STALE' if days_old>3 else ' ✓'
    breadth_warn = f' ⚠️ LOW ({n_stocks})' if n_stocks<300 else f' ✓ ({n_stocks})'
    ft_text = (f'Last close: {last_str}{stale_warn}  |  '
               f'Breadth stocks:{breadth_warn}  |  '
               f'Bond: {bond_ticker_used or "NONE"}  |  '
               f'Errors: {len(errors)}  |  '
               f'v3 — 16 sectors + cap rotation')
    ax_ft.text(0.5, 0.6, ft_text, transform=ax_ft.transAxes,
               fontsize=7, color=GREY, ha='center', va='center', fontfamily='monospace')

    # ── Save ───────────────────────────────────────────────────────────────────
    out_path = f'morning_dashboard_{datetime.today().strftime("%d%b%Y")}.png'
    plt.savefig(out_path, dpi=165, bbox_inches='tight',
                facecolor=BG, edgecolor='none')
    plt.close(fig)
    print(f'\n✅ Infographic saved → {out_path}')
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# TELEGRAM DELIVERY
# ══════════════════════════════════════════════════════════════════════════════
def send_telegram(image_path, action_code, action_text, switch_overall,
                  bzone, flying, drown, today_str):
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id   = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not bot_token or not chat_id:
        print('⚠️  TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set. Skipping Telegram.')
        return

    ACTION_EMOJI = {'A':'🟢','B':'🔵','C':'🟡','D':'🔴'}.get(action_code,'⚪')
    fly_str   = ', '.join([SECTOR_DISPLAY.get(s,s) for s in flying]) or 'None'
    drown_str = ', '.join([SECTOR_DISPLAY.get(s,s) for s in drown])  or 'None'

    caption = (
        f"🌅 *Morning Dashboard — {today_str}*\n\n"
        f"{ACTION_EMOJI} *Action [{action_code}]:* {action_text}\n\n"
        f"📶 RS Switch: `{switch_overall}`\n"
        f"📊 Breadth: `{bzone}`\n\n"
        f"✅ *LONG sectors:* {fly_str}\n"
        f"🔻 *SHORT sectors:* {drown_str}\n\n"
        f"_Prashant Shah RS & Breadth System — v3_"
    )

    url  = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
    with open(image_path, 'rb') as f:
        resp = requests.post(url, data={
            'chat_id': chat_id,
            'caption': caption,
            'parse_mode': 'Markdown'
        }, files={'photo': f}, timeout=30)

    if resp.status_code == 200:
        print(f'✅ Telegram message sent successfully.')
    else:
        print(f'❌ Telegram send failed: {resp.status_code} — {resp.text}')
        errors.append(f'Telegram: {resp.status_code}')


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    today_str = datetime.today().strftime('%d-%b-%Y')
    run_time  = datetime.now().strftime('%H:%M')
    print(f'\n{"═"*60}')
    print(f'  MORNING DASHBOARD v3  —  {today_str}')
    print(f'{"═"*60}\n')

    closes, last_date, days_old, bond_ticker_used = step1_fetch()
    last_str = last_date.strftime('%d-%b-%Y')

    rs_switch, switch_overall, asset_labels = step2_rs_switch(closes)
    cap_results, universe, cap_signal_str   = step3_cap_rotation(closes)
    sector_results, flying, drown           = step4_sector_rs(closes)
    b200, b50, b52wh, brsi, bzone, breadth_available, n_stocks = step5_breadth()
    top_stocks                              = step6_top_stocks(closes, flying)
    action_code, action_text                = step7_action(switch_overall, bzone)

    print(f'\n{"─"*60}')
    print(f'  ACTION [{action_code}]: {action_text}')
    print(f'{"─"*60}\n')

    image_path = make_infographic(
        today_str, last_str, run_time,
        rs_switch, switch_overall, asset_labels,
        cap_results, universe, cap_signal_str,
        sector_results, flying, drown,
        b200, b50, b52wh, brsi, bzone, breadth_available, n_stocks,
        top_stocks, action_code, action_text,
        days_old, bond_ticker_used
    )

    send_telegram(image_path, action_code, action_text, switch_overall,
                  bzone, flying, drown, today_str)

    if errors:
        print(f'\n⚠️  {len(errors)} issues logged:')
        for e in errors: print(f'   - {e}')
    else:
        print('\n✅ All steps completed with no errors.')

    print(f'\n🏁 Done — {datetime.now().strftime("%H:%M:%S")}')
    return image_path

if __name__ == '__main__':
    main()
