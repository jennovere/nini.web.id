r"""
NINI MC TEST - GITHUB-SAFE VERSION
Kloningan mc_test.py yang sudah di-SANITIZE untuk dipublish ke GitHub Pages.
Tujuannya: tetap menampilkan transparansi performa, tapi MINIMalkan risiko
strategi dilacak / di-clone.

DATA YANG DI-MASKING:
  - Entry/Exit time: hanya TANGGAL (jam dibuang) -> cegah reverse signal time
  - Equity & drawdown curve: downsample ke HARIAN (bukan per-trade)
  - Tabel PNL PER JAM ENTRY: DIBUANG (membocorkan jam profitable)
  - Tabel PER PAIR: DIBUANG (membocorkan pair andalan + equity min)
  - KPI BEST/WORST trade: DIBUANG (bisa di-reverse ke tanggal tertentu)
  - meta: notional, leverage, margin, MAX_FLOATING, MAX_SAME_TIME,
    skip_wave, skip_float, fee per route -> semua DIBUANG (blueprint risk)
  - sum: min_eq & min_t DIBUANG (titik terburuk MC = alpha leak)

DATA YANG DIPERTAHANKAN (untuk transparansi):
  - Total trades, WR, PnL, PF, MaxDD (USDT saja), Expectancy
  - Daily PnL + Cum (sudah tanggal only)
  - Monthly PnL + Ret%
  - DAFTAR TRADE: tgl entry/exit, pair, side, gross, fee, net, cum, route
  - OPEN POSITIONS: TANGGAL entry + ENTRY PRICE + side + status
  - TOP DD PERIOD (tanggal only)

RESPONSIVE: viewport meta + CSS mobile portrait (<=700px) agar enak
dibuka di HP (nini.web.id/portofolio_2nd_account.html) tanpa zoom.

Output: result/portofolio_2nd_account.html (self-contained)
Auto-reload 1 jam; REPORT_NO_OPEN=1 untuk auto_pipeline.
"""
import os
import csv
import math
import json
import base64
import tempfile
import webbrowser
import heapq
from datetime import datetime
from collections import defaultdict

# ================== CONFIG (identik mc_test.py) ==================
START_DATE      = "2023-01-01"
CAPITAL         = 3000.0
MARGIN_PER_TRADE= 100.0
LEVERAGE        = 10.0
MAX_FLOATING    = 2
MAX_SAME_TIME   = 1

FEE_ENTRY = 0.0002
FEE_TP1   = 0.0002
FEE_TP2   = 0.0002
FEE_BEP   = 0.0005
FEE_SL    = 0.0005

TRADELAB_DIR = r"D:\TRADELAB"
BACKTEST_DIR = os.path.join(TRADELAB_DIR, "tradinglab", "backtest")
SCAN_ROOTS = [BACKTEST_DIR]
OPEN_BROWSER = True
OUT_NAME = "portofolio_2nd_account.html"

# Logo Nini (embed base64)
LOGO_CANDIDATES = [
    os.path.join(TRADELAB_DIR, "tradinglab", "assets", "nini_logo.png"),
    os.path.join(TRADELAB_DIR, "tradinglab", "result", "nini_logo.png"),
    os.path.join(TRADELAB_DIR, "nini_logo.png"),
]

# URUTAN simbol di bawah = PRIORITAS WAVE bila beberapa pair signal
# pada entry_time yang sama (index kecil = prioritas lebih tinggi).
FILTER_SYMBOLS = (
    "ZECUSDT", "WIFUSDT", "ZENUSDT", "TIAUSDT", "SUPERUSDT", "ZILUSDT", "PORTALUSDT", "POLUSDT", "XRPUSDT", "PENDLEUSDT",
    "ONTUSDT", "NOTUSDT", "NEOUSDT", "NEIROUSDT", "MEWUSDT", "LTCUSDT", "LDOUSDT", "KSMUSDT", "JUPUSDT", "IOUSDT",
    "IDUSDT", "HMSTRUSDT", "GALAUSDT", "FLOWUSDT", "FILUSDT", "ETHUSDT", "DOGEUSDT", "DASHUSDT", "COMPUSDT", "BTCUSDT",
    "BNBUSDT", "AXSUSDT", "AVAXUSDT", "ARBUSDT", "ALTUSDT", "ALICEUSDT", "AEVOUSDT", "AAVEUSDT", "RENDERUSDT",
    "SEIUSDT", "ZROUSDT", "PEOPLEUSDT", "OGNUSDT", "MOODENGUSDT", "MEMEUSDT", "MASKUSDT", "MANAUSDT", "IOTAUSDT", "INJUSDT",
    "IMXUSDT", "FETUSDT", "ENAUSDT", "CRVUSDT", "CATIUSDT", "BRETTUSDT", "BLURUSDT", "BBUSDT", "ANKRUSDT", "QTUMUSDT",
    "ROSEUSDT", "SANDUSDT", "SNXUSDT", "SUSHIUSDT", "TURBOUSDT", "VETUSDT", "XTZUSDT", "RVNUSDT", "ONDOUSDT", "LINKUSDT",
    "DYDXUSDT", "BATUSDT", "ALGOUSDT", "1000BONKUSDT", "1000CATUSDT", "1000FLOKIUSDT", "EIGENUSDT", "ACEUSDT", "ARUSDT", "BELUSDT",
    "BOMEUSDT", "CELOUSDT", "WLDUSDT", "ETCUSDT", "GOATUSDT", "SKLUSDT", "SUIUSDT", "UNIUSDT", "THETAUSDT", "SOLUSDT",
    "ATOMUSDT", "BIGTIMEUSDT", "CHZUSDT", "DOTUSDT", "ENSUSDT", "IOSTUSDT", "KAVAUSDT", "XLMUSDT", "LISTAUSDT", "MANTAUSDT",
    "NEARUSDT", "OPUSDT", "PIXELUSDT", "SCRUSDT", "STRKUSDT", "STXUSDT", "UMAUSDT", "ZKUSDT",
)
_FILTER_SET = set(FILTER_SYMBOLS)
SYM_ORDER = {s: i for i, s in enumerate(FILTER_SYMBOLS)}

TIME_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M",
                "%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]
OPEN_TOTAL = 0
OPEN_POSITIONS = []


# ================== HELPERS ==================
def _atomic_write_text(path, text):
    path = str(path)
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp): os.unlink(tmp)
        except OSError: pass
        raise


def _load_logo_b64():
    for p in LOGO_CANDIDATES:
        try:
            with open(p, "rb") as f:
                b = f.read()
            if b:
                return "data:image/png;base64," + base64.b64encode(b).decode("ascii")
        except Exception:
            continue
    return ""


def to_float(v):
    s = str(v or "").strip().replace(",", "").replace("%", "")
    if s in ("", "-", "nan", "none", "null"): return None
    try:
        f = float(s)
        return f if math.isfinite(f) else None
    except Exception: return None


def parse_time(v):
    s = str(v or "").strip()
    if not s: return None
    for fmt in TIME_FORMATS:
        try: return datetime.strptime(s, fmt)
        except Exception: pass
    return None


def clean_symbol(fn):
    base = os.path.splitext(fn)[0].upper()
    for suf in ("_30M_AUDIT_V2", "_30M_AUDIT"):
        if base.endswith(suf): base = base[:-len(suf)]
    return base


def load_trades():
    global OPEN_TOTAL, OPEN_POSITIONS
    OPEN_TOTAL = 0; OPEN_POSITIONS = []
    out = []; seen = set()
    for root in SCAN_ROOTS:
        if not os.path.isdir(root): continue
        for dp, _, files in os.walk(root):
            for fn in files:
                if not fn.lower().endswith("_v2.csv"): continue
                path = os.path.abspath(os.path.join(dp, fn))
                if path in seen: continue
                seen.add(path)
                sym = clean_symbol(fn)
                if FILTER_SYMBOLS and sym not in _FILTER_SET: continue
                try: f = open(path, "r", encoding="utf-8", errors="replace")
                except Exception: continue
                with f:
                    for row in csv.reader(f):
                        if len(row) < 15: continue
                        rt = str(row[11]).strip().upper()
                        if rt == "MISS": continue
                        if rt == "OPEN":
                            OPEN_TOTAL += 1
                            et = parse_time(row[1])
                            side = str(row[2]).strip().upper()
                            if side == "BUY": side = "LONG"
                            elif side == "SELL": side = "SHORT"
                            OPEN_POSITIONS.append({
                                "sym": sym, "side": side, "et": et,
                                "ep": to_float(row[4]),
                            })
                            continue
                        et = parse_time(row[1]); xt = parse_time(row[6])
                        pct = to_float(row[13])
                        if et is None or pct is None: continue
                        _sd = str(row[2]).strip().upper()
                        _sd = "LONG" if _sd == "BUY" else ("SHORT" if _sd == "SELL" else _sd)
                        out.append({
                            "sym": sym, "side": _sd,
                            "et": et, "xt": xt or et,
                            "pct": pct, "ep": to_float(row[4]),
                            "route": str(row[12]).strip().upper(),
                        })
    OPEN_POSITIONS.sort(key=lambda p: p["et"] or datetime.min, reverse=True)
    return out


def trade_fee(route, notional):
    entry = notional * FEE_ENTRY
    if "CL" in route or "SL" in route: return entry + notional * FEE_SL
    if "TP1+BEP" in route: return entry + (notional/2)*FEE_TP1 + (notional/2)*FEE_BEP
    if "TP1+TP2" in route: return entry + (notional/2)*FEE_TP1 + (notional/2)*FEE_TP2
    if "TP1+OPEN" in route: return entry + (notional/2)*FEE_TP1
    return entry + notional * FEE_SL


def downsample(pts, n=800):
    if len(pts) <= n: return pts
    st = len(pts) / n
    return [pts[int(i * st)] for i in range(n)] + [pts[-1]]


def main():
    start_dt = parse_time(START_DATE + " 00:00") or datetime(2023, 1, 1)
    notional = MARGIN_PER_TRADE * LEVERAGE
    trades = [t for t in load_trades() if t["et"] >= start_dt]
    for t in trades:
        t["gross"] = notional * t["pct"] / 100.0
        t["fee"] = trade_fee(t["route"], notional)
        t["net"] = t["gross"] - t["fee"]

    # ---- WAVE FILTER (prioritas urutan FILTER_SYMBOLS, berlaku bersama) ----
    open_candidates = list(OPEN_POSITIONS)
    skipped_wave = 0
    if MAX_SAME_TIME > 0:
        by_et = defaultdict(list)
        for t in trades: by_et[t["et"]].append(("T", t))
        for p in open_candidates: by_et[p["et"]].append(("O", p))
        kept_trades, kept_opens = [], []
        for et, lst in by_et.items():
            lst.sort(key=lambda x: SYM_ORDER.get(x[1]["sym"], len(FILTER_SYMBOLS)))
            for kind, obj in lst[:MAX_SAME_TIME]:
                if kind == "T": kept_trades.append(obj)
                else: kept_opens.append(obj)
            skipped_wave += max(0, len(lst) - MAX_SAME_TIME)
        trades, open_candidates = kept_trades, kept_opens

    # ---- MAX FLOATING (TP1+OPEN: slot bebas saat TP1) ----
    skipped_float = 0
    if MAX_FLOATING > 0:
        trades.sort(key=lambda t: t["et"])
        heap, accepted = [], []
        for t in trades:
            while heap and heap[0] <= t["et"]: heapq.heappop(heap)
            if len(heap) >= MAX_FLOATING:
                skipped_float += 1; continue
            heapq.heappush(heap, t["xt"]); accepted.append(t)
        trades = accepted
    trades.sort(key=lambda t: t["xt"])

    # ---- OPEN POSITIONS (lolos wave+float) ----
    if MAX_FLOATING > 0:
        heap2 = [t["xt"] for t in trades]; heapq.heapify(heap2)
        open_kept, open_skip = [], 0
        for p in sorted(open_candidates, key=lambda x: x["et"] or datetime.min):
            et = p["et"] or datetime.min
            while heap2 and heap2[0] <= et: heapq.heappop(heap2)
            if len(heap2) >= MAX_FLOATING: open_skip += 1; continue
            heapq.heappush(heap2, datetime.max); open_kept.append(p)
    else:
        open_kept, open_skip = list(open_candidates), 0

    open_rows = [{"sym": p["sym"], "side": p["side"], "et": p["et"],
                  "ep": p["ep"], "status": "OPEN"} for p in open_kept]
    for t in trades:
        if t["route"] == "TP1+OPEN":
            sd = t["side"]
            sd = "LONG" if sd == "BUY" else ("SHORT" if sd == "SELL" else sd)
            open_rows.append({"sym": t["sym"], "side": sd, "et": t["et"],
                              "ep": t.get("ep"), "status": "TP1+OPEN"})
    open_rows.sort(key=lambda x: x["et"] or datetime.min, reverse=True)

    # Cum per trade (urutan realisasi/exit)
    _cum = 0.0
    for _t in trades:
        _cum += _t["net"]; _t["cum"] = round(_cum, 2)

    # KPI dasar
    eq = 0.0; peak = 0.0; maxdd = 0.0
    series, dd_series = [], []
    for t in trades:
        eq += t["net"]; series.append([t["xt"], eq])
        peak = max(peak, eq); maxdd = max(maxdd, peak - eq)
        dd_series.append([t["xt"], -(peak - eq)])
    net = eq
    min_eq = 0.0
    run = 0.0
    for t in trades:
        run += t["net"]
        if run < min_eq: min_eq = run
    shared_mc = (CAPITAL + min_eq) <= 0
    wins = [t for t in trades if t["net"] > 0]
    losses = [t for t in trades if t["net"] < 0]
    gw = sum(t["net"] for t in wins); gl = abs(sum(t["net"] for t in losses))
    total = len(trades)

    max_cl_streak, _cur = 0, 0
    for t in trades:
        if t["net"] < 0:
            _cur += 1
            if _cur > max_cl_streak: max_cl_streak = _cur
        else: _cur = 0

    # DD periods (tanggal only, aman)
    dd_periods = []
    pv = series[0][1]; pts_ = series[0][0]; cm = 0.0; indd = False
    for ts, v in series:
        if v >= pv:
            if indd and cm > 0:
                dd_periods.append({"s": pts_, "e": ts, "d": (ts - pts_).days,
                                   "depth": round(cm, 2)})
            pv = v; pts_ = ts; cm = 0.0; indd = False
        else:
            indd = True; cm = max(cm, pv - v)
    if indd and cm > 0:
        dd_periods.append({"s": pts_, "e": series[-1][0],
                           "d": (series[-1][0] - pts_).days, "depth": round(cm, 2)})
    dd_periods.sort(key=lambda x: -x["depth"])
    for p in dd_periods:
        p["pct"] = round(p["depth"] / CAPITAL * 100, 2) if CAPITAL else 0.0
        p["s"] = p["s"].strftime("%Y-%m-%d")
        p["e"] = p["e"].strftime("%Y-%m-%d")
    top_dd = dd_periods[:1]
    top_dd_pct = top_dd[0]["pct"] if top_dd else 0.0

    # Daily (sudah tanggal only -> aman)
    daily = defaultdict(lambda: {"trades": 0, "win": 0, "loss": 0, "pnl": 0.0})
    monthly = defaultdict(lambda: {"pnl": 0.0, "gross": 0.0, "fee": 0.0, "trades": 0, "win": 0})
    for t in trades:
        v = t["net"]; dx = t["xt"]
        dk = dx.strftime("%Y-%m-%d"); mk = dx.strftime("%Y-%m")
        daily[dk]["trades"] += 1; daily[dk]["pnl"] += v
        if v > 0: daily[dk]["win"] += 1
        elif v < 0: daily[dk]["loss"] += 1
        monthly[mk]["pnl"] += v; monthly[mk]["gross"] += t["gross"]; monthly[mk]["fee"] += t["fee"]; monthly[mk]["trades"] += 1
        if v > 0: monthly[mk]["win"] += 1
    run = CAPITAL; monthly_list = []
    for k in sorted(monthly):
        x = monthly[k]; ret = x["pnl"] / run * 100 if run else 0
        monthly_list.append({"m": k, "pnl": round(x["pnl"], 2), "gross": round(x["gross"], 2), "fee": round(x["fee"], 2),
                             "trades": x["trades"], "ret": round(ret, 2)})
        run += x["pnl"]
    daily_list, cum = [], 0.0
    for k, v in sorted(daily.items()):
        cum += v["pnl"]
        daily_list.append({
            "date": k, "trades": v["trades"], "win": v["win"], "loss": v["loss"],
            "wr": round(v["win"] / v["trades"] * 100, 1) if v["trades"] else 0,
            "pnl": round(v["pnl"], 2), "cum": round(cum, 2)})

    # ============================================================
    # SANITASI: buang/transform field sensitif sebelum JSON-embed
    # ============================================================
    trade_list = [
        {"ed": t["et"].strftime("%Y-%m-%d"),
         "xd": t["xt"].strftime("%Y-%m-%d"),
         "sym": t["sym"], "side": t["side"],
         "gross": round(t["gross"], 2), "fee": round(t["fee"], 2),
         "net": round(t["net"], 2), "cum": t.get("cum", 0.0),
         "route": t["route"]}
        for t in sorted(trades, key=lambda x: x["et"])
    ]
    open_list = [
        {"sym": o["sym"], "side": o["side"],
         "ed": o["et"].strftime("%Y-%m-%d") if o["et"] else "-",
         "ep": round(o["ep"], 4) if o["ep"] is not None else None,
         "status": o["status"]}
        for o in open_rows
    ]
    daily_equity = {}
    daily_dd = {}
    run = 0.0; peak_r = 0.0
    for t in sorted(trades, key=lambda x: x["xt"]):
        run += t["net"]; peak_r = max(peak_r, run)
        dkey = t["xt"].strftime("%Y-%m-%d")
        daily_equity[dkey] = round(run, 2)
        daily_dd[dkey] = round(-(peak_r - run), 2)
    equity_daily = [[k, v] for k, v in sorted(daily_equity.items())]
    dd_daily = [[k, v] for k, v in sorted(daily_dd.items())]

    R = {
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "capital": CAPITAL,
        "pairs": len({t["sym"] for t in trades}),
        "total_trades": total,
        "win_rate": round(len(wins) / total * 100, 2) if total else 0,
        "net": round(net, 2),
        "fees": round(sum(t["fee"] for t in trades), 2),
        "pf": round(gw / gl, 2) if gl else 0,
        "maxdd": round(maxdd, 2),
        "exp": round(net / total, 2) if total else 0,
        "mc": shared_mc,
        "opens": len(open_list),
        "max_cl_streak": max_cl_streak,
        "top_dd_pct": top_dd_pct,
        "dd_periods": top_dd,
        "monthly": monthly_list,
        "daily": daily_list,
        "trades": trade_list,
        "opens_list": open_list,
        "equity": equity_daily,
        "drawdown": dd_daily,
        "period_start": trades[0]["et"].strftime("%Y-%m-%d") if trades else "-",
        "period_end": trades[-1]["xt"].strftime("%Y-%m-%d") if trades else "-",
    }

    def _jdefault(o):
        if isinstance(o, datetime): return o.strftime("%Y-%m-%d %H:%M")
        raise TypeError(f"Object of type {o.__class__.__name__} not JSON serializable")

    logo_src = _load_logo_b64()
    html = HTML_TEMPLATE.replace("__R__", json.dumps(R, default=_jdefault))
    html = html.replace("__LOGO_SRC__", logo_src)
    outdir = os.path.join(TRADELAB_DIR, "tradinglab", "result")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, OUT_NAME)
    _atomic_write_text(path, html)

    # Sinkron 4 kartu statistik landing page (index.html) dari dict R yang sama
    # -> ikut ter-commit di cycle auto_pipeline; ringan, lokal saja.
    try:
        import sync_landing_stats
        sync_landing_stats.apply(R)
    except Exception as _e:
        print("SYNC LANDING STATS SKIP: %r" % (_e,))

    # Regenerasi sitemap.xml (lastmod = mtime artefak) sebelum git_deploy cycle
    try:
        import subprocess as _sp
        import sys as _sys
        _sm = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "tradinglab", "tools", "generate_sitemap.py")
        if os.path.isfile(_sm):
            _sp.run([_sys.executable, _sm], capture_output=True, timeout=60)
    except Exception as _e:
        print("GENERATE SITEMAP SKIP: %r" % (_e,))

    print("=" * 60)
    print("MC TEST GITHUB-SAFE | start=%s | capital=%s" % (START_DATE, CAPITAL))
    print("Trades=%d | WR=%.2f%% | Net=%+.2f | MaxDD=%.2f"
          % (total, R["win_rate"], net, maxdd))
    print("Logo: %s" % ("OK" if logo_src else "NOT FOUND"))
    print("Report (GitHub-safe): %s" % path)
    print("=" * 60)
    if OPEN_BROWSER and not os.environ.get("REPORT_NO_OPEN"):
        webbrowser.open("file:///" + path.replace("\\", "/"))


HTML_TEMPLATE = r"""
<!DOCTYPE html><html lang="id"><head><meta charset="utf-8"><title>Audit Portofolio Live NINI — Performa Copy Trading Binance Futures</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Audit portofolio live NINI: performa copy trading Binance Futures tervalidasi kode — kurva equity, drawdown, dan daftar trade yang diperbarui otomatis tiap jam.">
<meta name="keywords" content="copy trading crypto indonesia, bot trading binance, portofolio trading transparan, audit portofolio live">
<link rel="canonical" href="https://nini.web.id/portofolio_2nd_account.html">
<meta property="og:title" content="Audit Portofolio Live NINI">
<meta property="og:description" content="Data historis trade transparan dan bisa diaudit siapa saja. Diperbarui otomatis tiap jam.">
<meta property="og:image" content="https://nini.web.id/assets/nini_logo.png">
<meta property="og:url" content="https://nini.web.id/portofolio_2nd_account.html">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
<meta name="robots" content="index,follow">
<script>setTimeout(function(){location.reload()},3600000)</script>
<style>
:root{--bg:#0b1220;--panel:#111a2c;--panel2:#0e1626;--border:#1e2a44;--text:#dfe7f5;--muted:#7d8aa5;--green:#22c55e;--red:#ef4444;--yellow:#f59e0b;--blue:#3b82f6}
*{margin:0;padding:0;box-sizing:border-box;font-family:Consolas,Monaco,monospace}
body{background:var(--bg);color:var(--text);font-size:13px;padding:16px}
.card{background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:14px}
h1{font-size:18px}h3{font-size:12px;letter-spacing:1px;color:var(--muted);margin-bottom:10px}
.g{color:var(--green)}.r{color:var(--red)}.y{color:var(--yellow)}.m{color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-bottom:14px}
.kpi{background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:10px}
.kpi small{display:block;color:var(--muted);font-size:10px;margin-bottom:4px}.kpi b{font-size:15px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:1000px){.grid2{grid-template-columns:1fr}}
table{width:100%;border-collapse:separate;border-spacing:0;font-size:12px}
th{color:var(--muted);text-align:left;padding:5px 6px;font-weight:normal}
td{padding:5px 6px;border-top:1px solid var(--border)}
.scroll thead th,.scrollbig thead th{position:sticky;top:0;background:var(--panel);z-index:2}
.mscroll thead th{position:sticky;top:0;background:var(--panel2);z-index:2}
.scroll{max-height:380px;overflow-y:auto}
.scrollbig{max-height:75vh;overflow-y:auto}
.chart-grid{display:grid;grid-template-columns:225px minmax(0,1fr) 265px;gap:12px}
@media(max-width:1150px){.chart-grid{grid-template-columns:1fr}}
.side{display:flex;flex-direction:column;gap:12px}
.spanel{background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:10px}
.spanel h3{margin-bottom:8px}
.kvrow{display:flex;justify-content:space-between;gap:8px;padding:3px 0;font-size:12px}
.kvrow span{color:var(--muted)}
.mscroll{max-height:420px;overflow-y:auto}
#eqC{width:100%;height:340px;display:block;cursor:crosshair}
#ddC{width:100%;height:110px;display:block;cursor:crosshair}
.chead{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:4px}
.ranges{margin-left:auto;display:flex;gap:4px}
.ranges button{background:var(--panel2);border:1px solid var(--border);color:var(--muted);padding:2px 9px;font-size:11px;border-radius:4px}
.ranges button.on{color:#fff;border-color:var(--blue)}
.annot{color:var(--muted);font-size:11px;text-align:center;margin-bottom:2px}
.tag{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:bold}
.tag-ok{background:#0d2b1c;color:var(--green);border:1px solid var(--green)}
.tag-warn{background:#3a2a10;color:var(--yellow);border:1px solid var(--yellow)}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:0 0 12px}
.backlink{display:inline-block;padding:6px 12px;border:1px solid var(--border);border-radius:6px;color:var(--muted);text-decoration:none;font-size:12px}
.cta-follow{display:inline-block;padding:7px 16px;border-radius:6px;background:var(--yellow);color:#0b1220;font-weight:bold;font-size:12px;text-decoration:none;box-shadow:0 0 12px rgba(245,158,11,.35)}
.cta-follow:hover{filter:brightness(1.1)}
#openCard{border:1px solid var(--yellow);box-shadow:0 0 14px rgba(245,158,11,.28)}
#openCard h3{color:var(--text)}
.run-blink{color:var(--yellow);font-weight:bold;animation:blinkAnim 1s ease-in-out infinite}
@keyframes blinkAnim{0%,100%{opacity:1}50%{opacity:.15}}
@media(prefers-reduced-motion:reduce){.run-blink{animation:none}}
/* ========== MOBILE PORTRAIT (<=700px) ========== */
@media(max-width:700px){
  body{padding:8px;font-size:12px}
  h1{font-size:15px}
  h1 img{width:30px;height:30px;vertical-align:-7px;margin-right:8px}
  .card{padding:10px;margin-bottom:10px}
  .kpi{padding:8px}
  .kpi b{font-size:13px}
  .kpi small{font-size:9px}
  .cards{grid-template-columns:repeat(auto-fill,minmax(105px,1fr));gap:6px}
  .chart-grid{grid-template-columns:1fr;gap:10px}
  .grid2{grid-template-columns:1fr;gap:10px}
  #eqC{height:260px}
  #ddC{height:80px}
  .scroll{max-height:320px}
  .scrollbig{max-height:60vh}
  .scroll,.scrollbig,.mscroll{overflow:auto;-webkit-overflow-scrolling:touch}
  th,td{padding:4px 5px;font-size:11px;white-space:nowrap}
  .kvrow{font-size:11px}
  .spanel{padding:8px}
  .ranges button{padding:4px 10px;font-size:12px}
  .annot{font-size:10px}
}
/* ========== SMALL PHONES (<=480px): tabel muat penuh tanpa scroll ========== */
@media(max-width:480px){
  body{padding:4px}
  .card{padding:8px}
  th,td{padding:2px 3px;font-size:9px}
  #tradeCard table{font-size:8.5px}
  #tradeCard th,#tradeCard td{padding:2px 2px}
  #tradeCard td:nth-child(9),#tradeCard th:nth-child(9){display:none}
  #tradeCard td:nth-child(2),#tradeCard th:nth-child(2){display:none}
}
</style></head><body>
<div class="topbar"><a href="https://nini.web.id/" class="backlink">← nini.web.id</a><a href="download/" class="cta-follow">Follow Nini Master Trade</a></div>
<div class="card"><h1><img id="logoImg" src="__LOGO_SRC__" alt="" style="width:38px;height:38px;border-radius:10px;vertical-align:-9px;margin-right:10px;display:none">Nini Portofolio Report Public — <span id="ttl"></span></h1><span class="m" id="meta"></span></div>
<div class="cards" id="kpis"></div>
<div class="card"><div class="chart-grid" id="chartGrid">
  <aside class="side">
    <div class="spanel"><h3>RETURN SUMMARY</h3><div id="sumL"></div></div>
    <div class="spanel"><h3>DRAWDOWN SUMMARY</h3><div id="ddL"></div></div>
  </aside>
  <div>
    <div class="chead"><h3>EQUITY CURVE (USDT)</h3><div class="ranges" id="ranges"></div></div>
    <div class="annot" id="annot"></div>
    <canvas id="eqC"></canvas><canvas id="ddC"></canvas>
  </div>
  <aside class="side" id="monthAside"><div class="spanel"><h3>MONTHLY PERFORMANCE (USDT)</h3><div id="monthR" class="mscroll"></div></div></aside>
</div></div>
<div class="grid2" id="midGrid">
  <div class="card" id="dailyCard"><h3>PNL PER TANGGAL (REALISASI/EXIT)</h3><div class="scroll"><table><thead><tr><th>Tanggal</th><th>Trades</th><th>W/L</th><th>WR</th><th>PnL</th><th>Total</th></tr></thead><tbody id="daily"></tbody></table></div></div>
  <div class="card" id="openCard"><h3>OPEN POSITIONS (<span class="run-blink">RUNNING</span>) — <span id="ocount"></span> PAIR</h3>
    <div class="scroll"><table><thead><tr><th>Pair</th><th>Side</th><th>Entry Date</th><th>Entry Price</th><th>Status</th></tr></thead><tbody id="opens"></tbody></table></div>
  </div>
</div>
<div class="card" id="tradeCard"><h3>DAFTAR TRADE — <span id="tcount"></span> ENTRY</h3>
  <div class="scrollbig"><table><thead><tr><th>Entry Date</th><th>Exit Date</th><th>Pair</th><th>Side</th><th>Gross</th><th>Fee</th><th>Net PnL</th><th>Total</th><th>Route</th></tr></thead><tbody id="trades"></tbody></table></div>
</div>
<div class="card" id="yearCard"><h3>YEARLY PERFORMANCE (USDT)</h3><div id="yearR"></div></div>
<div class="card"><span class="m">Versi publik: jam entry/exit tidak dipublikasikan; hanya tanggal, pair, side, route, dan PnL. Kurva equity downsample harian.</span></div>
<script>
const R=__R__;
const lg=document.getElementById('logoImg');
if(lg && lg.getAttribute('src')){lg.style.display='inline-block';}
function money(v){v=v||0;return v.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}
function p(v){return v>=0?'<span class="g">+'+money(v)+'</span>':'<span class="r">'+money(v)+'</span>'}
function kv(r){return r.map(x=>'<div class="kvrow"><span>'+x[0]+'</span><b>'+x[1]+'</b></div>').join('')}
document.getElementById('ttl').textContent='Start '+R.period_start+' → '+R.period_end;
document.getElementById('meta').textContent='Built '+R.built_at+' | Modal '+money(R.capital);
document.getElementById('kpis').innerHTML=[
['TOTAL TRADES',R.total_trades],['WIN RATE',R.win_rate+'%'],
['OPEN (RUNNING)','<span class="y">'+R.opens+'</span>'],
['TOTAL PNL',p(R.net)],['TOTAL EXCHANGE FEE','<span class="r">-'+money(R.fees)+'</span>'],
['PROFIT FACTOR',R.pf],['MAX DRAWDOWN','<span class="r">'+money(R.maxdd)+'</span>'],
['EXPECTANCY',p(R.exp)]
].map(k=>'<div class="kpi"><small>'+k[0]+'</small><b>'+k[1]+'</b></div>').join('');
document.getElementById('sumL').innerHTML=kv([
['Modal',money(R.capital)+' USDT'],
['Total Exchange Fee','<span class="r">-'+money(R.fees)+' USDT</span>'],
['Net Profit',p(R.net)+' USDT'],
['Final Equity',money(R.capital+R.net)+' USDT'],
['Total Return',((R.net/R.capital)*100>=0?'+':'')+((R.net/R.capital)*100).toFixed(2)+'%'],
['Avg Monthly Return',(function(){var M=R.monthly||[];var a=M.length?M.reduce(function(s,m){return s+(m.ret||0);},0)/M.length:0;return (a>=0?'+':'')+a.toFixed(2)+'%';})()]]);
document.getElementById('ddL').innerHTML=kv([
['Max Drawdown','<span class="r">-'+money(R.maxdd)+' USDT</span>'],
['Top DD % Modal','<span class="r">-'+R.top_dd_pct+'%</span>'],
['CL Beruntun Max','<span class="r">'+R.max_cl_streak+'x</span>'],
['Recovery Factor',(R.maxdd>0?(R.net/R.maxdd).toFixed(2):'0')]])
+'<div class="kvrow" style="margin-top:6px"><span>TOP DD PERIOD (terdalam)</span><b></b></div>'
+(R.dd_periods||[]).map(pp=>'<div class="kvrow"><span>'+pp.s+' → '+pp.e+'</span><b class="r">'+pp.d+'d / -'+money(pp.depth)+' ('+pp.pct+'%)</b></div>').join('')
||'<div class="kvrow"><span>-</span><b>-</b></div>';
document.getElementById('monthR').innerHTML='<table><thead><tr><th>Month</th><th>PnL</th><th>Ret%</th></tr></thead><tbody>'+
R.monthly.slice().reverse().map(m=>'<tr><td>'+m.m+'</td><td>'+p(m.pnl)+'</td><td class="'+(m.ret>=0?'g':'r')+'">'+(m.ret>=0?'+':'')+m.ret+'%</td></tr>').join('')+'</tbody></table>';
(function(){var M=R.monthly||[];var yEl=document.getElementById('yearR');if(!yEl)return;if(!M.length){yEl.innerHTML='<span class="m">-</span>';return;}
var byY={},run=R.capital||3000;M.slice().sort(function(a,b){return a.m<b.m?-1:1;}).forEach(function(m){var y=m.m.slice(0,4);if(!(y in byY)){byY[y]={y:y,pnl:0,gross:0,fee:0,trades:0,start:run};}byY[y].pnl+=m.pnl;byY[y].gross+=(m.gross||0);byY[y].fee+=(m.fee||0);byY[y].trades+=m.trades;run+=m.pnl;byY[y].end=run;});
var rows=Object.keys(byY).sort().map(function(y){var o=byY[y];var ret=o.start?o.pnl/o.start*100:0;return '<tr><td>'+y+'</td><td>'+o.trades+'</td><td>'+p(o.gross)+'</td><td class="r">-'+money(o.fee)+'</td><td>'+p(o.pnl)+'</td><td class="'+(ret>=0?'g':'r')+'">'+(ret>=0?'+':'')+ret.toFixed(2)+'%</td></tr>';}).join('');
yEl.innerHTML='<table><thead><tr><th>Year</th><th>Trades</th><th>Gross</th><th>Fee</th><th>Net PnL</th><th>Ret%</th></tr></thead><tbody>'+rows+'</tbody></table>';})();
document.getElementById('daily').innerHTML=R.daily.slice().reverse().map(d=>'<tr><td>'+d.date+'</td><td>'+d.trades+'</td><td>'+d.win+'/'+d.loss+'</td><td>'+d.wr+'%</td><td>'+p(d.pnl)+'</td><td>'+p(d.cum)+'</td></tr>').join('');
document.getElementById('ocount').textContent=(R.opens_list||[]).length;
document.getElementById('opens').innerHTML=(R.opens_list||[]).map(o=>{
const epStr = o.ep!=null ? o.ep.toLocaleString('en-US',{maximumFractionDigits:4}) : '-';
const tagClass = o.status==='TP1+OPEN' ? 'tag-ok' : 'tag-warn';
return '<tr><td>'+o.sym+'</td><td class="'+(o.side==='LONG'?'g':'r')+'">'+o.side+'</td><td class="m">'+o.ed+'</td><td>'+epStr+'</td><td><span class="tag '+tagClass+'">'+o.status+'</span></td></tr>';
}).join('') || '<tr><td colspan="5" class="m" style="text-align:center">Tidak ada posisi floating</td></tr>';
document.getElementById('tcount').textContent=(R.trades||[]).length;
document.getElementById('trades').innerHTML=(R.trades||[]).slice().reverse().map(t=>'<tr><td class="m">'+t.ed+'</td><td class="m">'+t.xd+'</td><td>'+t.sym+'</td><td class="'+(t.side==='LONG'?'g':'r')+'">'+t.side+'</td><td>'+p(t.gross)+'</td><td class="r">-'+money(t.fee)+'</td><td>'+p(t.net)+'</td><td>'+p(t.cum||0)+'</td><td class="m">'+t.route+'</td></tr>').join('');
let EQ=(R.equity||[]).map(e=>[new Date(e[0].replace(' ','T')+'T00:00:00').getTime(),e[1]]);
let DD=(R.drawdown||[]).map(e=>[new Date(e[0].replace(' ','T')+'T00:00:00').getTime(),e[1]]);
let view=[],ddv=[],rangeKey='ALL',HOV=-1,VM=null;
function buildRanges(){const el=document.getElementById('ranges');
el.innerHTML=['1M','3M','6M','1Y','YTD','ALL'].map(k=>'<button data-k="'+k+'">'+k+'</button>').join('');
el.querySelectorAll('button').forEach(b=>b.onclick=()=>{rangeKey=b.dataset.k;
el.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));applyRange();});
el.querySelector('[data-k="ALL"]').classList.add('on');}
function applyRange(){if(!EQ.length)return;const t1=EQ[EQ.length-1][0];const now=new Date(t1);let t0=EQ[0][0];
if(rangeKey==='1M')t0=+new Date(now.getFullYear(),now.getMonth()-1,now.getDate());
if(rangeKey==='3M')t0=+new Date(now.getFullYear(),now.getMonth()-3,now.getDate());
if(rangeKey==='6M')t0=+new Date(now.getFullYear(),now.getMonth()-6,now.getDate());
if(rangeKey==='1Y')t0=+new Date(now.getFullYear()-1,now.getMonth(),now.getDate());
if(rangeKey==='YTD')t0=+new Date(now.getFullYear(),0,1);
view=EQ.filter(e=>e[0]>=t0);ddv=DD.filter(e=>e[0]>=t0);
if(view.length<2){view=EQ.slice();ddv=DD.slice();}HOV=-1;drawAll();}
function drawAll(){if(!view.length)return;const t0=view[0][0],t1=view[view.length-1][0];
const vs=view.map(e=>e[1]);const mn=Math.min(0,...vs),mx=Math.max(0,...vs);
let pk=vs[0],mdd=0;for(const x of vs){pk=Math.max(pk,x);mdd=Math.max(mdd,pk-x);}
document.getElementById('annot').textContent='Peak: '+money(mx)+' | Final: '+money(vs[vs.length-1])+' | Max DD: -'+money(mdd);
VM={t0,t1,mn,mx,vals:vs};drawEq();drawDd();}
function hov(px,W,t0,t1){const L=6,Rm=6;const t=t0+(px-L)/((W-L-Rm)||1)*(t1-t0);
let lo=0,hi=view.length-1;while(hi-lo>1){const m=(hi+lo)>>1;(view[m][0]<t)?lo=m:hi=m;}
return (t-view[lo][0]<view[hi][0]-t)?lo:hi;}
function drawXAxis(x,X,L,W,Rm,H,B,T,t0,t1){try{
var spanD=(t1-t0)/86400000;var y0=new Date(t0).getFullYear(),y1=new Date(t1).getFullYear();
x.save();x.font='10px Consolas';x.textAlign='center';x.setLineDash([]);
function clin(lbl,xx){var tw=x.measureText(lbl).width;var tx=Math.min(Math.max(xx,tw/2+2),W-tw/2-2);x.fillText(lbl,tx,H-8);}
if(spanD>400){for(var y=y0;y<=y1;y++){var tt=+new Date(y,0,1);var inside=(tt>=t0&&tt<=t1);
var ttx=Math.min(Math.max(tt,t0),t1);var xx=X(ttx);
if(inside){x.strokeStyle='#1e2a44';x.beginPath();x.moveTo(xx,T);x.lineTo(xx,H-B+4);x.stroke();}
x.fillStyle='#aeb9d0';clin(String(y),xx);}}
else if(spanD>150){var d0=new Date(t0),d1=new Date(t1);var yy=d0.getFullYear(),mm=d0.getMonth(),guard=0;
while((yy<d1.getFullYear()||(yy===d1.getFullYear()&&mm<=d1.getMonth()))&&guard<60){guard++;var ttm=+new Date(yy,mm,1);
if(ttm>=t0&&ttm<=t1){var xx2=X(ttm);x.strokeStyle='#1e2a44';x.beginPath();x.moveTo(xx2,T);x.lineTo(xx2,H-B+4);x.stroke();
x.fillStyle='#7d8aa5';clin(yy+'-'+String(mm+1).padStart(2,'0'),xx2);}mm++;if(mm>11){mm=0;yy++;}}}
else{for(var i=0;i<=5;i++){var tti=t0+(t1-t0)*i/5;var dd=new Date(tti);
var lbl=dd.getFullYear()+'-'+String(dd.getMonth()+1).padStart(2,'0')+'-'+String(dd.getDate()).padStart(2,'0');
x.fillStyle='#7d8aa5';clin(lbl,X(tti));}}
x.restore();}catch(_e){}}
function drawEq(){const cv=document.getElementById('eqC');const dpr=devicePixelRatio||1;
const W=cv.clientWidth,H=cv.clientHeight;cv.width=W*dpr;cv.height=H*dpr;
const x=cv.getContext('2d');x.setTransform(dpr,0,0,dpr,0,0);x.clearRect(0,0,W,H);
const {t0,t1,mn,mx,vals}=VM;const L=6,Rm=6,T=8,B=30;
const capBase=R.capital||1;
const X=t=>L+(t-t0)/((t1-t0)||1)*(W-L-Rm),Y=v=>T+(mx-v)/((mx-mn)||1)*(H-T-B);
x.font='10px Consolas';const st=5;const yticks=[];
for(let i=0;i<=st;i++){const v=mn+(mx-mn)*i/st,y=Y(v);
x.strokeStyle='#182338';x.beginPath();x.moveTo(L,y);x.lineTo(W-Rm,y);x.stroke();yticks.push([v,y]);}
const zy=Y(0);x.strokeStyle='#33415e';x.setLineDash([4,4]);x.beginPath();x.moveTo(L,zy);x.lineTo(W-Rm,zy);x.stroke();x.setLineDash([]);
const g=x.createLinearGradient(0,T,0,H-B);g.addColorStop(0,'rgba(34,197,94,.18)');g.addColorStop(1,'rgba(34,197,94,0)');
x.beginPath();view.forEach((e,i)=>{i?x.lineTo(X(e[0]),Y(vals[i])):x.moveTo(X(e[0]),Y(vals[i]))});
x.strokeStyle='#22c55e';x.lineWidth=1.6;x.stroke();
x.lineTo(X(t1),zy);x.lineTo(X(t0),zy);x.closePath();x.fillStyle=g;x.fill();
drawXAxis(x,X,L,W,Rm,H,B,T,t0,t1);
for(const [vv,yy] of yticks){const lt=(vv/1000).toFixed(1)+'k',rt=(vv/capBase*100).toFixed(0)+'%';
const ry=Math.min(Math.max(yy-12,T),H-B-14);
x.textAlign='left';const lw=x.measureText(lt).width;
x.fillStyle='rgba(11,18,32,.7)';x.fillRect(L+1,ry,lw+7,14);
x.fillStyle='#7d8aa5';x.fillText(lt,L+4,ry+11);
const rw=x.measureText(rt).width;x.textAlign='right';
x.fillStyle='rgba(11,18,32,.7)';x.fillRect(W-Rm-1-rw-7,ry,rw+7,14);
x.fillStyle='#7d8aa5';x.fillText(rt,W-Rm-4,ry+11);}
if(HOV>=0&&HOV<view.length){const e=view[HOV],xx=X(e[0]),yy=Y(vals[HOV]);
x.strokeStyle='#3b82f6';x.setLineDash([3,3]);x.beginPath();x.moveTo(xx,T);x.lineTo(xx,H-B);x.stroke();x.setLineDash([]);
x.fillStyle='#22c55e';x.beginPath();x.arc(xx,yy,3,0,7);x.fill();
const d=new Date(e[0]);const txt=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')+'  '+money(vals[HOV])+' USDT';
const tw=x.measureText(txt).width+12;let bx=xx+8;if(bx+tw>W-Rm)bx=xx-8-tw;
x.fillStyle='#0e1626';x.fillRect(bx,T+4,tw,16);x.strokeStyle='#1e2a44';x.strokeRect(bx,T+4,tw,16);
x.fillStyle='#dfe7f5';x.textAlign='left';x.fillText(txt,bx+6,T+15);}}
function drawDd(){const cv=document.getElementById('ddC');const dpr=devicePixelRatio||1;
const W=cv.clientWidth,H=cv.clientHeight;cv.width=W*dpr;cv.height=H*dpr;
const x=cv.getContext('2d');x.setTransform(dpr,0,0,dpr,0,0);x.clearRect(0,0,W,H);
const {t0,t1,vals}=VM;const L=6,Rm=6,T=4,B=24;
const X=t=>L+(t-t0)/((t1-t0)||1)*(W-L-Rm);
let pk=vals[0];const dd=vals.map(v=>{pk=Math.max(pk,v);return -(pk-v);});
const mn=Math.min(0,...dd)||-1;const Y=v=>T+(v/mn)*(H-T-B);
x.beginPath();dd.forEach((v,i)=>{const xx=X(view[i][0]),yy=Y(v);i?x.lineTo(xx,yy):x.moveTo(xx,yy)});
x.lineTo(X(t1),Y(0));x.lineTo(X(t0),Y(0));x.closePath();
x.fillStyle='rgba(239,68,68,.35)';x.fill();x.strokeStyle='#ef4444';x.lineWidth=1;x.stroke();
drawXAxis(x,X,L,W,Rm,H,B,T,t0,t1);
x.font='9px Consolas';x.textAlign='left';
for(const [dtxt,dyy] of [['0',T+7],[mn.toFixed(0),H-B]]){const dw=x.measureText(dtxt).width;
const dry=Math.min(Math.max(dyy-11,T),H-B-13);
x.fillStyle='rgba(11,18,32,.7)';x.fillRect(L+1,dry,dw+7,13);
x.fillStyle='#7d8aa5';x.fillText(dtxt,L+4,dry+10);}
if(HOV>=0&&HOV<view.length){const e=view[HOV],xx=X(e[0]),yy=Y(dd[HOV]);
x.strokeStyle='#3b82f6';x.setLineDash([3,3]);x.beginPath();x.moveTo(xx,T);x.lineTo(xx,H-B);x.stroke();x.setLineDash([]);
x.fillStyle='#ef4444';x.beginPath();x.arc(xx,yy,3,0,7);x.fill();
const d=new Date(e[0]);const txt=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')+'  DD: '+money(dd[HOV])+' USDT';
const tw=x.measureText(txt).width+12;let bx=xx+8;if(bx+tw>W-Rm)bx=xx-8-tw;
x.fillStyle='#0e1626';x.fillRect(bx,T+2,tw,14);x.strokeStyle='#1e2a44';x.strokeRect(bx,T+2,tw,14);
x.fillStyle='#dfe7f5';x.textAlign='left';x.fillText(txt,bx+4,T+12);}}
const eC=document.getElementById('eqC'),dC=document.getElementById('ddC');
eC.addEventListener('mousemove',e=>{if(!VM)return;HOV=hov(e.clientX-eC.getBoundingClientRect().left,eC.clientWidth,VM.t0,VM.t1);drawEq();drawDd();});
eC.addEventListener('mouseleave',()=>{HOV=-1;drawEq();drawDd();});
dC.addEventListener('mousemove',e=>{if(!VM)return;HOV=hov(e.clientX-dC.getBoundingClientRect().left,dC.clientWidth,VM.t0,VM.t1);drawEq();drawDd();});
dC.addEventListener('mouseleave',()=>{HOV=-1;drawEq();drawDd();});
window.addEventListener('resize',()=>{if(view.length)drawAll();});
(function(){var mg=document.getElementById('midGrid'),mA=document.getElementById('monthAside'),
dC=document.getElementById('dailyCard'),oC=document.getElementById('openCard'),tC=document.getElementById('tradeCard');
if(!mg||!mA||!dC||!oC||!tC)return;
var monthHome={p:mA.parentNode,n:mA.nextSibling},openHome={p:oC.parentNode,n:oC.nextSibling},mob=null;
function lay(){var isM=window.innerWidth<=700;if(isM===mob)return;mob=isM;
if(isM){mg.insertBefore(oC,dC);tC.after(mA);}
else{monthHome.p.insertBefore(mA,monthHome.n);openHome.p.insertBefore(oC,openHome.n);}}
var rt;window.addEventListener('resize',function(){clearTimeout(rt);rt=setTimeout(lay,150);});lay();})();
buildRanges();applyRange();
</script></body></html>
"""

if __name__ == "__main__":
    main()