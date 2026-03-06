"""
Prashant Shah RS & Breadth — Morning Dashboard v7
==================================================
Expanded: 13 sectors + cap rotation (Next50/Mid/Sml/Micro)
Output:   Infographic PNG → Telegram
Run:      python morning_dashboard.py
Secrets:  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  (env vars / GitHub Secrets)
"""

import os, sys

import yfinance as yf, pandas as pd, numpy as np
import urllib.request, io as _io, time, warnings
from datetime import datetime, timedelta
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
warnings.filterwarnings('ignore')

END, START = datetime.today(), datetime.today() - timedelta(days=450)

TICKERS = {
    # Core indices
    'nifty50'    : '^NSEI',
    'nifty500'   : '^CRSLDX',
    'niftynext50': '^NSMIDCP',
    # Cap segments — ETF proxies (Yahoo doesn't host these sub-indices reliably)
    'niftymid'   : 'MOM100.NS',       # Motilal Midcap 100 ETF ✅
    'niftysml'   : 'SETFNIF50.NS',    # SBI Smallcap ETF proxy ✅
    'niftymicro' : 'NM250IETF.NS',    # Nippon Microcap 250 ETF (primary)
    # 8 confirmed working sector indices
    'bank'       : '^NSEBANK',
    'it'         : '^CNXIT',
    'pharma'     : '^CNXPHARMA',
    'auto'       : '^CNXAUTO',
    'metal'      : '^CNXMETAL',
    'fmcg'       : '^CNXFMCG',
    'energy'     : '^CNXENERGY',
    'realty'     : '^CNXREALTY',
    # 5 additional sectors
    'infra'      : '^CNXINFRA',
    'media'      : '^CNXMEDIA',
    'psubank'    : 'PSUBNKBEES.NS',   # Nippon PSU Bank BeES ✅
    'finance'    : 'NETFFINLOG.NS',   # Nippon Financial Services ETF (primary)
    'healthcare' : 'PHARMABEES.NS',   # Nippon Pharma BeES ✅
    # RS Switch assets (these 3 are essential — do NOT remove)
    'gold'       : 'GOLDBEES.NS',     # ✅ confirmed
    'usdinr'     : 'USDINR=X',        # ✅ confirmed
}

TICKER_FALLBACKS = {
    'niftymid'  : ['MOM100.NS','MAFSETF.NS','MIDCAP100ETF.NS'],
    'niftysml'  : ['SETFNIF50.NS','SETFNN50.NS','^CNXSC'],
    'niftymicro': ['NM250IETF.NS','NMICRO.NS','MICROCAP.NS',
                   'NIFMICAP.NS','NIFTYMICRO250.NS','HDFCMICRO.NS'],
    'finance'   : ['NETFFINLOG.NS','NIFTYFINANCE.NS','FINSETNIF.NS',
                   'LICNFNHGP.NS','ICICIFIN.NS','MAFIN.NS',
                   'AXISFIN.NS','^CNXFINANCE','^CNXFIN'],
    'psubank'   : ['PSUBNKBEES.NS','PSUBANKBEES.NS','SETFPSUBN.NS'],
    'healthcare': ['PHARMABEES.NS','HEALTHIETF.NS','^CNXHEALTHCARE'],
}

BOND_TICKERS = [
    ('ICICIB22.NS',    'ICICI Bond ETF'),
    ('NIFTYGS10YR.NS', 'Nifty GS 10YR'),
    ('LICNETFGSC.NS',  'LIC G-Sec ETF'),
    ('GSEC10YBEES.NS', 'Nippon G-Sec ETF'),
]

SECTOR_NAMES = [
    'bank','it','pharma','auto','metal','fmcg','energy','realty',
    'infra','media','psubank','finance','healthcare'
]
SECTOR_DISPLAY = {
    'bank':'BANK','it':'IT','pharma':'PHARMA','auto':'AUTO',
    'metal':'METAL','fmcg':'FMCG','energy':'ENERGY','realty':'REALTY',
    'infra':'INFRA','media':'MEDIA','psubank':'PSU BANK',
    'finance':'FINANCE','healthcare':'HEALTHCARE',
}
SECTOR_URLS = {
    'bank'      :'https://nsearchives.nseindia.com/content/indices/ind_niftybanklist.csv',
    'it'        :'https://nsearchives.nseindia.com/content/indices/ind_niftyitlist.csv',
    'pharma'    :'https://nsearchives.nseindia.com/content/indices/ind_niftypharmalist.csv',
    'auto'      :'https://nsearchives.nseindia.com/content/indices/ind_niftyautolist.csv',
    'fmcg'      :'https://nsearchives.nseindia.com/content/indices/ind_niftyfmcglist.csv',
    'metal'     :'https://nsearchives.nseindia.com/content/indices/ind_niftymetallist.csv',
    'energy'    :'https://nsearchives.nseindia.com/content/indices/ind_niftyenergylist.csv',
    'realty'    :'https://nsearchives.nseindia.com/content/indices/ind_niftyrealty.csv',
    'infra'     :'https://nsearchives.nseindia.com/content/indices/ind_niftyinfrastructurelist.csv',
    'media'     :'https://nsearchives.nseindia.com/content/indices/ind_niftymedialist.csv',
    'psubank'   :'https://nsearchives.nseindia.com/content/indices/ind_niftypsubanklist.csv',
    'finance'   :'https://nsearchives.nseindia.com/content/indices/ind_niftyfinancelist.csv',
    'healthcare':'https://nsearchives.nseindia.com/content/indices/ind_niftyhealthcarelist.csv',
}

errors = []
print(f'✅ Config ready  {START.date()} → {END.date()}')
print(f'   Sectors: {len(SECTOR_NAMES)} | RS Switch assets: gold, bonds, usdinr')

# ── STEP 1: Fetch closes ─────────────────────────────────────────────────
# Small initial delay helps avoid Yahoo Finance rate-limit on fresh CI runners
print('STEP 1: Fetching closes...\n')
# curl_cffi impersonates a real Chrome browser at TLS level —
# the only reliable way to bypass Yahoo Finance IP blocks on CI runners.
# yfinance automatically uses it when installed (no code changes needed).
try:
    from curl_cffi import requests as _cffi_sess
    _cffi_sess.Session(impersonate="chrome")
    print("  ✅ curl_cffi available — Yahoo Finance TLS bypass active")
except ImportError:
    print("  ⚠️  curl_cffi not found — Yahoo may block CI runner IPs")
time.sleep(8)  # let runner network settle

def try_tickers(key, tickers_list, retries=3, backoff=15):
    """Try each ticker in order; retry up to `retries` times with backoff.
    Handles GitHub Actions / CI IP rate-limiting by Yahoo Finance."""
    for t in tickers_list:
        for attempt in range(retries):
            try:
                df = yf.download(t, start=START, end=END, progress=False, auto_adjust=True)
                if not df.empty and len(df) > 50:
                    return df['Close'].squeeze(), t
            except Exception as e:
                pass
            if attempt < retries - 1:
                wait = backoff * (attempt + 1)
                print(f'    ↻ {t}: attempt {attempt+1} failed, retrying in {wait}s...')
                time.sleep(wait)
    return None, None

closes_raw = {}
for key, primary in TICKERS.items():
    fallbacks = TICKER_FALLBACKS.get(key, [])
    all_try   = [primary] + [f for f in fallbacks if f != primary]
    series, used = try_tickers(key, all_try)
    if series is not None:
        closes_raw[key] = series
        note = f' (via {used})' if used != primary else ''
        print(f'  ✅ {key:15s}{note}')
    else:
        print(f'  ❌ {key:15s} — all failed')
        errors.append(f'{key}: no data')

# Bond fallback
bond_loaded = False; bond_ticker_used = None
for bt, bl in BOND_TICKERS:
    try:
        df_b = yf.download(bt, start=START, end=END, progress=False, auto_adjust=True)
        if not df_b.empty and len(df_b) > 50:
            closes_raw['bonds'] = df_b['Close'].squeeze()
            bond_ticker_used = bt; bond_loaded = True
            print(f'  ✅ bonds         ({bt})')
            break
    except: pass
if not bond_loaded:
    print('  ❌ bonds — all failed'); errors.append('bonds: all failed')

closes   = pd.DataFrame(closes_raw).ffill()
last_date = closes.index[-1]
days_old  = (datetime.today() - pd.Timestamp(last_date)).days
if 'nifty50' not in closes.columns:
    print('CRITICAL: Nifty 50 unavailable — cannot continue.', file=sys.stderr)
    sys.exit(1)
if days_old > 5:
    print(f'WARNING: Data is {days_old} days old (weekend/holiday is fine).')
print(f'\n✅ STEP 1 DONE — Last close: {last_date.date()} ({days_old}d old), {closes.shape[1]} series')

# ── STEP 2: RS Switch (3 assets) ────────────────────────────────────────
print('STEP 2: RS Switch...')

# These 3 keys must exist in closes for full RS Switch
asset_labels = {
    'gold'  : 'Gold (GOLDBEES)',
    'bonds' : 'Bonds (GS/ETF)',
    'usdinr': 'USDINR',
}
rs_switch = {}
for ak, lbl in asset_labels.items():
    if ak not in closes.columns:
        rs_switch[ak] = 'N/A'
        print(f'  ⚠️  Nifty vs {lbl:22s}: N/A (data missing)')
        continue
    ratio  = closes['nifty50'] / closes[ak]
    status = 'ON' if ratio.iloc[-1] > ratio.rolling(50).mean().iloc[-1] else 'OFF'
    rs_switch[ak] = status
    icon = '✅' if status == 'ON' else '❌'
    print(f'  {icon} Nifty vs {lbl:22s}: {status}')

valid = {k: v for k, v in rs_switch.items() if v in ('ON','OFF')}
on_n  = sum(1 for v in valid.values() if v == 'ON')
tot   = len(valid)
switch_overall = 'ON' if on_n == tot and tot > 0 else ('OFF' if on_n == 0 else 'PARTIAL')
print(f'\n  OVERALL: {switch_overall} ({on_n}/{tot} ON)')
print('✅ STEP 2 DONE')

# ── STEP 3: Cap Rotation ─────────────────────────────────────────────────
print('STEP 3: Cap rotation...')
def cap_sig(a, b):
    if a not in closes.columns or b not in closes.columns: return None
    r = closes[a] / closes[b]
    above  = bool(r.iloc[-1] > r.rolling(50).mean().iloc[-1])
    rs_pct = round((closes[a].pct_change(50).iloc[-1] - closes[b].pct_change(50).iloc[-1])*100, 2)
    return {'above_ma': above, 'rs_pct': rs_pct}

cap_results = {
    'next50': cap_sig('niftynext50', 'nifty50'),
    'mid'   : cap_sig('niftymid',    'nifty50'),
    'sml'   : cap_sig('niftysml',    'nifty50'),
    'micro' : cap_sig('niftymicro',  'nifty50'),
    'broad' : cap_sig('nifty500',    'nifty50'),
}
cap_display = {'next50':'Next 50','mid':'Midcap','sml':'Smallcap','micro':'Microcap','broad':'Nifty500'}
for k, v in cap_results.items():
    if v: print(f'  {"▲" if v["above_ma"] else "▼"} {cap_display[k]:10s}: RS={v["rs_pct"]:+.2f}%')
    else: print(f'  ◌ {cap_display[k]:10s}: N/A')
broad = cap_results.get('broad')
universe       = 'Nifty 500 (Broad)' if (broad and broad['above_ma']) else 'Nifty 100 (Large Cap)'
cap_signal_str = 'MID/SMALL LEADING' if (broad and broad['above_ma']) else 'LARGE CAP ONLY'
print(f'  Universe: {universe}\n✅ STEP 3 DONE')

# ── STEP 4: Sector RS Ranking ────────────────────────────────────────────
print('STEP 4: Sector RS...')
sector_results = []
for s in SECTOR_NAMES:
    if s not in closes.columns:
        sector_results.append({'sector':s,'rs_alpha':None,'above_ma':None,'pattern':'N/A','rank':0})
        continue
    rs_a   = (closes[s].pct_change(50).iloc[-1] - closes['nifty50'].pct_change(50).iloc[-1]) * 100
    ratio  = closes[s] / closes['nifty50']
    above  = bool(ratio.iloc[-1] > ratio.rolling(50).mean().iloc[-1])
    pat    = ('FLYING' if rs_a>0 and above else 'LION' if rs_a>0
              else 'BEARISH STAR' if above else 'DROWNING')
    sector_results.append({'sector':s,'rs_alpha':round(rs_a,2),'above_ma':above,'pattern':pat})
    icon = '★' if pat=='FLYING' else ('▼' if pat=='DROWNING' else ' ')
    print(f' {icon} {SECTOR_DISPLAY.get(s,s):12s}: RS={rs_a:+.2f}% → {pat}')
sector_results.sort(key=lambda x: x['rs_alpha'] if x['rs_alpha'] is not None else -999, reverse=True)
for i, r in enumerate(sector_results): r['rank'] = i+1
flying = [r['sector'] for r in sector_results if r['pattern']=='FLYING']
drown  = [r['sector'] for r in sector_results if r['pattern']=='DROWNING']
print(f'\n  ★ FLYING: {[SECTOR_DISPLAY.get(s,s) for s in flying]}')
print(f'  ▼ DROWN:  {[SECTOR_DISPLAY.get(s,s) for s in drown]}')
print('✅ STEP 4 DONE')

# ── STEP 5: Breadth ⏳ ~8 min ────────────────────────────────────────────
print('STEP 5: Breadth... ~8 min\n')
def fetch_nse_stocks(url):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        df = pd.read_csv(_io.StringIO(r.read().decode()))
    return [s.strip()+'.NS' for s in df['Symbol'].dropna()]

breadth_available = True; symbols = []
try:
    symbols = fetch_nse_stocks('https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv')
    print(f'  ✅ {len(symbols)} Nifty 500 constituents')
except Exception as e:
    print(f'  ⚠️  {e}'); breadth_available = False

stock_data = {}; tb = max((len(symbols)+49)//50, 1)
for i in range(0, len(symbols), 50):
    batch = symbols[i:i+50]; bn = i//50+1
    try:
        df = yf.download(batch, start=START, end=END, progress=False, auto_adjust=True)
        c  = df['Close'] if isinstance(df.columns, pd.MultiIndex) else df[['Close']].rename(columns={'Close':batch[0]})
        stock_data.update(c.to_dict('series'))
    except: pass
    if bn%5==0 or bn==tb: print(f'  Batch {bn}/{tb} — {len(stock_data)} stocks')
    time.sleep(0.8)

sc = pd.DataFrame(stock_data).ffill().dropna(axis=1, thresh=200)
n  = sc.shape[1]
print(f'  ✅ Valid: {n} stocks')

def rsi14(s):
    d=s.diff(); g=d.clip(lower=0).rolling(14).mean(); lo=(-d.clip(upper=0)).rolling(14).mean()
    return 100-(100/(1+g/lo))

if n > 0:
    b200  = round((sc.iloc[-1] > sc.rolling(200).mean().iloc[-1]).sum()/n*100, 1)
    b50   = round((sc.iloc[-1] > sc.rolling(50).mean().iloc[-1]).sum()/n*100,  1)
    b52wh = round((sc.iloc[-1] >= sc.rolling(252).max().iloc[-1]*0.99).sum()/n*100, 1)
    brsi  = round((sc.apply(rsi14).iloc[-1] > 60).sum()/n*100, 1)
    bzone = 'OVERBOUGHT' if b50>75 else ('OVERSOLD' if b50<25 else 'NEUTRAL')
    print(f'\n  Above 200MA: {b200}%  |  Above 50MA: {b50}% [{bzone}]  |  RSI>60: {brsi}%  |  52W Hi: {b52wh}%')
else:
    b200=b50=b52wh=brsi=None; bzone='UNKNOWN'; breadth_available=False
print('✅ STEP 5 DONE')

# ── STEP 6: Top Stocks in Flying Sectors ─────────────────────────────────
print('STEP 6: Top stocks in Flying sectors...')
top_stocks = {}
if not flying:
    print('  ℹ️  No Flying sectors today.')
else:
    for sec in flying:
        if sec not in SECTOR_URLS: continue
        print(f'  Scanning {SECTOR_DISPLAY.get(sec, sec)}...')
        try: sec_syms = fetch_nse_stocks(SECTOR_URLS[sec])
        except Exception as e: errors.append(f'{sec}: {e}'); continue
        sec_data = {}
        for i in range(0, len(sec_syms), 30):
            try:
                df = yf.download(sec_syms[i:i+30], start=START, end=END, progress=False, auto_adjust=True)
                c  = df['Close'] if isinstance(df.columns, pd.MultiIndex) else df[['Close']].rename(columns={'Close':sec_syms[i]})
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
                ranked.append({'stock':stock.replace('.NS',''),'rs_alpha':round(rs_a,2),'above_50ma':above})
            except: pass
        top5 = sorted(ranked, key=lambda x: x['rs_alpha'], reverse=True)[:5]
        top_stocks[sec] = top5
        for i,s in enumerate(top5):
            print(f'    {i+1}. {s["stock"]:22s} RS={s["rs_alpha"]:+.2f}%  50MA:{"✅" if s["above_50ma"] else "❌"}')
print('✅ STEP 6 DONE')

# ── STEP 7: Action A/B/C/D ───────────────────────────────────────────────
bzone_val = bzone if breadth_available else 'UNKNOWN'
if switch_overall=='OFF' or bzone_val=='OVERSOLD':
    action_code='D'; action_text='DEFENSIVE / SHORT — Do NOT buy. Protect longs.'
elif bzone_val=='OVERBOUGHT':
    action_code='C'; action_text='HOLD ONLY — No new positions. Tighten trailing stops.'
elif switch_overall=='PARTIAL':
    action_code='B'; action_text='SELECTIVE LONG — Top Flying sector only. Half size.'
elif switch_overall=='ON':
    action_code='A'; action_text='AGGRESSIVE LONG — Rank 1-2 stocks in Flying sectors. Look for breakouts.'
else:
    action_code='D'; action_text='DEFENSIVE — Conditions unclear. No new positions.'
print(f'  ► ACTION [{action_code}]: {action_text}\n✅ STEP 7 DONE')


# ── CELL 10: Infographic ─────────────────────────────────────────────────────
today_str = datetime.today().strftime('%d-%b-%Y')
last_str  = last_date.strftime('%d-%b-%Y')
run_time  = datetime.now().strftime('%H:%M')

C_BG    = '#FFFFFF'; C_CARD  = '#F6F8FA'; C_CARD2 = '#EFF2F5'
C_BDR   = '#D0D7DE'; C_GREEN = '#1A7F37'; C_RED   = '#CF222E'
C_AMBER = '#9A6700'; C_BLUE  = '#0550AE'; C_TEAL  = '#1B7C3D'
C_BLACK = '#1F2328'; C_GREY  = '#656D76'; C_LGREY = '#EAEEF2'
PAT_COL = {'FLYING':C_GREEN,'LION':C_TEAL,'BEARISH STAR':C_AMBER,'DROWNING':C_RED,'N/A':C_GREY}
PAT_BG  = {'FLYING':'#DAFBE1','LION':'#D1F5DB','BEARISH STAR':'#FFF8C5','DROWNING':'#FFEBE9','N/A':'#F8F9FA'}
ACT_COL = {'A':C_GREEN,'B':C_BLUE,'C':C_AMBER,'D':C_RED}
ACT_BG  = {'A':'#DAFBE1','B':'#DDF4FF','C':'#FFF8C5','D':'#FFEBE9'}
ac      = ACT_COL.get(action_code, C_GREY)
ab      = ACT_BG.get(action_code,  C_LGREY)

def hline(ax, y, x0=0.02, x1=0.98, c=None):
    ax.plot([x0,x1],[y,y], color=c or C_BDR, lw=0.8, transform=ax.transAxes, zorder=2)

def style(ax, bg=C_CARD, bdr=C_BDR, lw=0.8):
    ax.set_facecolor(bg)
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_color(bdr); sp.set_linewidth(lw)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

# ─── Build figure ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(18, 26), facecolor=C_BG, dpi=300)
fig.patch.set_facecolor(C_BG)
gs = gridspec.GridSpec(6, 1, figure=fig,
                       top=0.97, bottom=0.015, left=0.025, right=0.975,
                       hspace=0.03, height_ratios=[0.65, 1.0, 3.2, 1.45, 2.9, 1.75])

# ── Row 0: Header ─────────────────────────────────────────────────────────────
ax0 = fig.add_subplot(gs[0]); style(ax0, C_BLACK, C_BLACK, 0)
ax0.set_xlim(0,1); ax0.set_ylim(0,1); ax0.axis('off')
ax0.text(0.015, 0.66, '🌅  MORNING DASHBOARD',
         transform=ax0.transAxes, fontsize=22, fontweight='bold', color='white', va='center')
ax0.text(0.015, 0.22,
         f'Data: {last_str}  •  Run: {run_time} IST  •  Prashant Shah RS & Breadth  •  v5',
         transform=ax0.transAxes, fontsize=10, color='#8B949E', va='center')
ax0.add_patch(FancyBboxPatch((0.72,0.08),0.265,0.84, boxstyle='round,pad=0.01',
              transform=ax0.transAxes, facecolor=ab, edgecolor=ac, linewidth=2, clip_on=False))
ax0.text(0.853, 0.68, f'ACTION  [ {action_code} ]',
         transform=ax0.transAxes, fontsize=15, fontweight='bold', color=ac, va='center', ha='center')
ax0.text(0.853, 0.24, action_text.split("—")[0].strip(),
         transform=ax0.transAxes, fontsize=9.5, color=ac, va='center', ha='center')

# ── Row 1: RS Switch + Cap Rotation ──────────────────────────────────────────
gs1  = gridspec.GridSpecFromSubplotSpec(1,2, subplot_spec=gs[1], wspace=0.012)
ax_sw  = fig.add_subplot(gs1[0]); style(ax_sw, C_CARD)
ax_cap = fig.add_subplot(gs1[1]); style(ax_cap, C_CARD)
for ax in [ax_sw, ax_cap]:
    ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')

# RS Switch — all 3 assets
ax_sw.text(0.03, 0.93, 'BLOCK 1  —  RS SWITCH  (Equity vs Asset Classes)',
           transform=ax_sw.transAxes, fontsize=9.5, color=C_GREY, fontweight='bold', va='top')
sw_items = [
    ('vs Gold (GOLDBEES)', rs_switch.get('gold','N/A')),
    ('vs Bonds (GS/ETF)', rs_switch.get('bonds','N/A')),
    ('vs USDINR',          rs_switch.get('usdinr','N/A')),
]
for idx,(lbl,val) in enumerate(sw_items):
    y   = 0.725 - idx*0.162
    col = C_GREEN if val=='ON' else (C_RED if val=='OFF' else C_AMBER)
    dot = '●' if val=='ON' else ('○' if val=='OFF' else '◌')
    ax_sw.text(0.04, y, f'{dot}  Nifty {lbl}',
               transform=ax_sw.transAxes, fontsize=11.5, color=col, va='center')
    ax_sw.text(0.84, y, val, transform=ax_sw.transAxes,
               fontsize=12, fontweight='bold', color=col, va='center', ha='center')
hline(ax_sw, 0.225)
oc  = C_GREEN if switch_overall=='ON' else (C_RED if switch_overall=='OFF' else C_AMBER)
ob  = '#DAFBE1' if switch_overall=='ON' else ('#FFEBE9' if switch_overall=='OFF' else '#FFF8C5')
ax_sw.add_patch(FancyBboxPatch((0.03,0.04),0.50,0.155, boxstyle='round,pad=0.01',
                transform=ax_sw.transAxes, facecolor=ob, edgecolor=oc, lw=1.5, clip_on=False))
ax_sw.text(0.28, 0.117, f'OVERALL:  {switch_overall}',
           transform=ax_sw.transAxes, fontsize=13, fontweight='bold', color=oc, va='center', ha='center')

# Cap Rotation — 4 cap segments
ax_cap.text(0.03, 0.93, 'BLOCK 2  —  CAP ROTATION  (50-bar RS-Alpha vs Nifty 50)',
            transform=ax_cap.transAxes, fontsize=9.5, color=C_GREY, fontweight='bold', va='top')
cap_rows = [('Next 50 ','next50'),('Midcap  ','mid'),('Smallcap','sml'),('Microcap','micro')]
for idx,(lbl,key) in enumerate(cap_rows):
    y   = 0.74 - idx*0.148
    res = cap_results.get(key)
    if not res:
        ax_cap.text(0.04,y,f'◌  {lbl}  N/A', transform=ax_cap.transAxes,
                    fontsize=10.5, color=C_GREY, va='center'); continue
    col   = C_GREEN if res['above_ma'] else C_RED
    arrow = '▲' if res['above_ma'] else '▼'
    ma_lbl = 'ABOVE 50MA' if res['above_ma'] else 'BELOW 50MA'
    ax_cap.text(0.04, y, f'{arrow}  {lbl}   {res["rs_pct"]:+.1f}%',
                transform=ax_cap.transAxes, fontsize=11.5, color=col, va='center')
    ax_cap.text(0.72, y, ma_lbl, transform=ax_cap.transAxes,
                fontsize=10, color=col, va='center', ha='left', fontweight='bold')
hline(ax_cap, 0.225)
uc = C_GREEN if 'Broad' in universe else C_AMBER
ub = '#DAFBE1' if 'Broad' in universe else '#FFF8C5'
ax_cap.add_patch(FancyBboxPatch((0.03,0.04),0.56,0.155, boxstyle='round,pad=0.01',
                 transform=ax_cap.transAxes, facecolor=ub, edgecolor=uc, lw=1.5, clip_on=False))
ax_cap.text(0.31, 0.117, f'UNIVERSE:  {cap_signal_str}',
            transform=ax_cap.transAxes, fontsize=12, fontweight='bold', color=uc, va='center', ha='center')

# ── Row 2: Sector Bar Chart ───────────────────────────────────────────────────
ax2 = fig.add_subplot(gs[2]); style(ax2, C_CARD)
ax2.set_facecolor(C_CARD)
for sp in ax2.spines.values(): sp.set_visible(True); sp.set_color(C_BDR); sp.set_linewidth(0.8)
valid_s  = [r for r in sector_results if r['rs_alpha'] is not None]
labels_s = [SECTOR_DISPLAY.get(r['sector'],r['sector']) for r in valid_s]
values_s = [r['rs_alpha'] for r in valid_s]
pats_s   = [r['pattern'] for r in valid_s]
max_v    = max(abs(v) for v in values_s)*1.6 if values_s else 10
ax2.set_xlim(-max_v, max_v); ax2.set_ylim(-0.6, len(labels_s)-0.4)
# Row bg bands
for i,pat in enumerate(pats_s):
    ax2.add_patch(plt.Rectangle((-max_v, i-0.42), max_v*2, 0.84,
                                facecolor=PAT_BG.get(pat,'#F8F9FA'),
                                alpha=0.4, zorder=0, edgecolor='none'))
ax2.barh(range(len(labels_s)), values_s,
         color=[PAT_COL.get(p,C_GREY) for p in pats_s],
         height=0.54, alpha=0.85, edgecolor='none', zorder=2)
ax2.axvline(0, color=C_BDR, lw=1.5, zorder=3)
ax2.set_yticks([])
ax2.tick_params(axis='x', colors=C_GREY, labelsize=7.5)
ax2.set_facecolor(C_CARD)
for sp in ax2.spines.values(): sp.set_color(C_BDR); sp.set_linewidth(0.8)
for i,(val,pat,lbl) in enumerate(zip(values_s,pats_s,labels_s)):
    col = PAT_COL.get(pat, C_GREY)
    ax2.text(-max_v*1.03, i, f'{i+1:2d}', va='center', ha='right', fontsize=10, color=C_GREY, fontweight='bold')
    ax2.text(-max_v*0.97, i, lbl,         va='center', ha='left',  fontsize=11, color=C_BLACK, fontweight='bold')
    x_off = max_v*0.03 if val>=0 else -max_v*0.03
    ax2.text(val+x_off, i, f'{val:+.1f}%', va='center',
             ha='left' if val>=0 else 'right', fontsize=10.5, color=col, fontweight='bold')
    if pat in ('FLYING','DROWNING'):
        badge = '★ FLYING' if pat=='FLYING' else '▼ DROWNING'
        ax2.text(max_v*0.62, i, badge, va='center', ha='left', fontsize=10, color=col,
                 fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.2', facecolor=PAT_BG.get(pat,'white'),
                           edgecolor=col, linewidth=0.8))
ax2.text(0.5, 1.011, 'BLOCK 3  —  SECTOR RS RANKING  (50-bar RS-Alpha vs Nifty 50)',
         transform=ax2.transAxes, fontsize=10, color=C_GREY, fontweight='bold', ha='center', va='bottom')
ax2.legend(handles=[mpatches.Patch(color=c,label=l) for c,l in
           [(C_GREEN,'FLYING ★'),(C_TEAL,'LION'),(C_AMBER,'BEARISH STAR'),(C_RED,'DROWNING ▼')]],
           loc='lower right', fontsize=10, facecolor='white', edgecolor=C_BDR, ncol=4, framealpha=1.0)

# ── Row 3: Breadth Gauges ─────────────────────────────────────────────────────
gs3 = gridspec.GridSpecFromSubplotSpec(1,4, subplot_spec=gs[3], wspace=0.012)
bcfg = [
    ('% Above 200-day MA',               b200,  80, 20, ''),
    ('% Above 50-day MA  ◀ PRIMARY',     b50,   75, 25, bzone_val),
    ('% Stocks  RSI > 60',               brsi,  70, 20, ''),
    ('% Near 52-Week High',              b52wh, 25,  5, ''),
]
for bi,(blbl,bval,hi,lo,verdict) in enumerate(bcfg):
    axb = fig.add_subplot(gs3[bi])
    style(axb, C_CARD2 if bi==1 else C_CARD, C_BLUE if bi==1 else C_BDR, 1.5 if bi==1 else 0.8)
    axb.set_xlim(0,1); axb.set_ylim(0,1); axb.axis('off')
    axb.text(0.5, 0.93, blbl, transform=axb.transAxes,
             fontsize=9 if bi!=1 else 9.5,
             color=C_BLACK if bi==1 else C_GREY,
             fontweight='bold' if bi==1 else 'normal',
             ha='center', va='top')
    if bval is not None:
        col = C_RED if bval>hi else (C_GREEN if bval<lo else C_AMBER)
        bg_c = '#FFEBE9' if bval>hi else ('#DAFBE1' if bval<lo else '#FFF8C5')
        axb.text(0.5, 0.58, f'{bval:.1f}%', transform=axb.transAxes,
                 fontsize=30 if bi==1 else 26, fontweight='bold',
                 color=col, ha='center', va='center')
        axb.add_patch(FancyBboxPatch((0.08,0.20),0.84,0.10, boxstyle='round,pad=0.01',
                      facecolor=C_LGREY, edgecolor=C_BDR, lw=0.5, transform=axb.transAxes))
        fw = 0.84*min(bval/100, 1)
        if fw > 0.005:
            axb.add_patch(FancyBboxPatch((0.08,0.20),fw,0.10, boxstyle='round,pad=0.01',
                          facecolor=col, alpha=0.75, edgecolor='none', transform=axb.transAxes))
        if verdict:
            axb.add_patch(FancyBboxPatch((0.08,0.04),0.84,0.13, boxstyle='round,pad=0.01',
                          facecolor=bg_c, edgecolor=col, lw=1.0, transform=axb.transAxes))
            axb.text(0.5, 0.105, verdict, transform=axb.transAxes,
                     fontsize=11, color=col, ha='center', va='center', fontweight='bold')
    else:
        axb.text(0.5, 0.5, 'N/A', transform=axb.transAxes,
                 fontsize=18, color=C_GREY, ha='center', va='center')
# Breadth title using a dedicated thin axes strip
# Title via fig.text — avoids creating a duplicate axis over the breadth gauges
p3 = gs[3].get_position(fig)
fig.text(0.5, p3.y1 + 0.003,
         'BLOCK 4  —  BREADTH DASHBOARD  (Nifty 500 Universe)',
         fontsize=10, color=C_GREY, fontweight='bold',
         ha='center', va='bottom')

# ── Row 4: Top Stocks ─────────────────────────────────────────────────────────
ax_ts = fig.add_subplot(gs[4]); style(ax_ts, C_CARD)
ax_ts.set_xlim(0,1); ax_ts.set_ylim(0,1); ax_ts.axis('off')
ax_ts.text(0.5, 0.975,
           'BLOCK 5  —  TOP STOCKS IN FLYING SECTORS  (RS-Alpha vs Sector, 50-bar)',
           transform=ax_ts.transAxes, fontsize=10, color=C_GREY,
           fontweight='bold', ha='center', va='top')
if not top_stocks:
    ax_ts.text(0.5, 0.5, 'No Flying sectors today — no stock scan run.',
               transform=ax_ts.transAxes, fontsize=14, color=C_AMBER,
               ha='center', va='center', style='italic')
else:
    secs_list = list(top_stocks.keys())
    n_cols    = min(len(secs_list), 4)
    col_w     = 0.96 / n_cols
    for ci, sec in enumerate(secs_list[:4]):
        stocks = top_stocks[sec]; cx = 0.02 + ci*col_w
        ax_ts.add_patch(FancyBboxPatch((cx,0.860),col_w-0.015,0.088,
                        boxstyle='round,pad=0.01', facecolor='#DAFBE1',
                        edgecolor=C_GREEN, lw=1.0, transform=ax_ts.transAxes))
        ax_ts.text(cx+(col_w-0.015)*0.5, 0.904,
                   f'★  {SECTOR_DISPLAY.get(sec,sec.upper())}',
                   transform=ax_ts.transAxes, fontsize=12, fontweight='bold',
                   color=C_GREEN, ha='center', va='center')
        ax_ts.text(cx+0.008, 0.830, 'Rank  Stock',
                   transform=ax_ts.transAxes, fontsize=9.5, color=C_GREY, va='top')
        ax_ts.text(cx+col_w-0.022, 0.830, 'RS%   50MA',
                   transform=ax_ts.transAxes, fontsize=9.5, color=C_GREY, va='top', ha='right')
        ax_ts.plot([cx+0.005, cx+col_w-0.018],[0.808,0.808],
                   color=C_BDR, lw=0.8, transform=ax_ts.transAxes)
        for ri,s in enumerate(stocks[:5]):
            y   = 0.753 - ri*0.138
            col = C_GREEN if s['above_50ma'] else C_AMBER
            rank = '★' if ri==0 else str(ri+1)
            ax_ts.text(cx+0.008, y, f'{rank}  {s["stock"][:15]}',
                       transform=ax_ts.transAxes, fontsize=11, color=col, va='center')
            ax_ts.text(cx+col_w-0.022, y,
                       f'{s["rs_alpha"]:+.1f}%   {"✓" if s["above_50ma"] else "✗"}',
                       transform=ax_ts.transAxes, fontsize=11, color=col,
                       va='center', ha='right', fontweight='bold')
    if len(secs_list) > 4:
        extra = [SECTOR_DISPLAY.get(s,s) for s in secs_list[4:]]
        ax_ts.text(0.5, 0.04, f'+ More Flying: {", ".join(extra)}',
                   transform=ax_ts.transAxes, fontsize=10.5, color=C_GREEN, ha='center', va='bottom')

# ── Row 5: Action ─────────────────────────────────────────────────────────────
ax_act = fig.add_subplot(gs[5]); style(ax_act, C_CARD2)
ax_act.set_xlim(0,1); ax_act.set_ylim(0,1); ax_act.axis('off')
ax_act.text(0.5, 0.96, "BLOCK 6  —  TODAY'S ACTION",
            transform=ax_act.transAxes, fontsize=10, color=C_GREY,
            fontweight='bold', ha='center', va='top')
ax_act.add_patch(FancyBboxPatch((0.02,0.63),0.96,0.27, boxstyle='round,pad=0.01',
                 transform=ax_act.transAxes, facecolor=ab, edgecolor=ac, lw=2, clip_on=False))
ax_act.text(0.5, 0.768, f'[ {action_code} ]  —  {action_text}',
            transform=ax_act.transAxes, fontsize=14, fontweight='bold',
            color=ac, ha='center', va='center')
sw_c = C_GREEN if switch_overall=='ON' else (C_RED if switch_overall=='OFF' else C_AMBER)
sw_b = '#DAFBE1' if switch_overall=='ON' else ('#FFEBE9' if switch_overall=='OFF' else '#FFF8C5')
bz_c = C_GREEN if bzone_val=='NEUTRAL' else (C_RED if bzone_val=='OVERSOLD' else C_AMBER)
bz_b = '#DAFBE1' if bzone_val=='NEUTRAL' else ('#FFEBE9' if bzone_val=='OVERSOLD' else '#FFF8C5')
for xi,(lbl,val,col,bg) in enumerate([
    ('RS Switch', switch_overall, sw_c, sw_b),
    ('Breadth',   bzone_val,      bz_c, bz_b),
    ('Universe',  cap_signal_str, C_BLUE, '#DDF4FF'),
]):
    x0 = 0.03 + xi*0.325
    ax_act.add_patch(FancyBboxPatch((x0,0.36),0.295,0.22, boxstyle='round,pad=0.01',
                     transform=ax_act.transAxes, facecolor=bg, edgecolor=col, lw=1.2, clip_on=False))
    ax_act.text(x0+0.1475, 0.47, f'{lbl}: {val}',
                transform=ax_act.transAxes, fontsize=12, fontweight='bold',
                color=col, ha='center', va='center')
fly_str   = '  ★  '.join([SECTOR_DISPLAY.get(s,s) for s in flying])  or 'None'
drown_str = '  ▼  '.join([SECTOR_DISPLAY.get(s,s) for s in drown])   or 'None'
ax_act.text(0.025, 0.255, 'LONG (Flying):',   transform=ax_act.transAxes, fontsize=11, color=C_GREY, va='center', fontweight='bold')
ax_act.text(0.210, 0.255, fly_str,            transform=ax_act.transAxes, fontsize=11,  color=C_GREEN, va='center', fontweight='bold')
ax_act.text(0.025, 0.145, 'SHORT (Drowning):', transform=ax_act.transAxes, fontsize=11, color=C_GREY, va='center', fontweight='bold')
ax_act.text(0.260, 0.145, drown_str,           transform=ax_act.transAxes, fontsize=11,  color=C_RED,   va='center', fontweight='bold')
stale = ' ⚠️ STALE' if days_old>3 else ' ✓'
ax_act.text(0.5, 0.04,
            f'Last close: {last_str}{stale}  |  Breadth: {n} stocks  |  Bond: {bond_ticker_used or "N/A"}  |  Issues: {len(errors)}',
            transform=ax_act.transAxes, fontsize=8.5, color=C_GREY, ha='center', va='center')

# ── Save ──────────────────────────────────────────────────────────────────────
fname = f'morning_dashboard_{datetime.today().strftime("%d%b%Y")}.png'
plt.savefig(fname, dpi=300, bbox_inches='tight', facecolor=C_BG, edgecolor='none', pad_inches=0.1)
plt.close(fig)
print(f'\n✅  Saved: {fname}')
print(f'  Image: {fname}  ({os.path.getsize(fname)//1024} KB)')

# ── TELEGRAM SEND ──────────────────────────────────────────────────────────────
print("\nSending to Telegram...")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "")

if not BOT_TOKEN or not CHAT_ID:
    print("⚠️  TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set. Skipping send.")
    print(f"   Infographic saved as: {fname}")
    sys.exit(0)

import requests as _rq

AE = {"A":"🟢","B":"🔵","C":"🟡","D":"🔴"}.get(action_code,"⚪")
fly_s  = ", ".join([SECTOR_DISPLAY.get(s,s) for s in flying])  or "None"
drn_s  = ", ".join([SECTOR_DISPLAY.get(s,s) for s in drown])   or "None"
caption = (
    f"🌅 *Morning Dashboard — {today_str}*\n\n"
    f"{AE} *Action [{action_code}]:* {action_text}\n\n"
    f"📶 RS Switch: `{switch_overall}`\n"
    f"📊 Breadth: `{bzone_val}`\n\n"
    f"✅ *LONG:* {fly_s}\n"
    f"🔻 *SHORT:* {drn_s}\n\n"
    f"_Prashant Shah RS & Breadth — v7_"
)

# Telegram rejects photos wider than ~2560px or larger than 10MB
from PIL import Image as _PIL
_img = _PIL.open(fname)
_w, _h = _img.size
if _w > 2560:
    _img = _img.resize((2560, int(_h * 2560 / _w)), _PIL.LANCZOS)
    _img.save(fname)
    print(f"  Resized to 2560px wide for Telegram")
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
with open(fname, "rb") as img:
    resp = _rq.post(
        url,
        data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"},
        files={"photo": img},
        timeout=60,
    )

if resp.status_code == 200:
    print("✅ Dashboard sent to Telegram successfully!")
else:
    print(f"❌ Telegram error: {resp.status_code} — {resp.text}")
    sys.exit(1)
