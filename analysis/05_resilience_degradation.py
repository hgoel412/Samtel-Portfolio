import os, csv, math, itertools
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use("Agg") #anti-grain geometry for background saving
import matplotlib.pyplot as plt
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, **k): return x #no tqdm on the machine, the loop still has to run

REPORT_DIR = "D:\Samtel-Portfolio\data/raw\Access" #same stk access exports phase 1 chewed on
OUT_DIR = "D:\Samtel-Portfolio\dashboards"
REP_OUT = "D:\Samtel-Portfolio\data\processed"
CONFIGS = ["C3", "C4"] #only the 4 plane family, phase 3 already killed the 6 plane option on launch count
CONFIG_LABEL = {"C3": "C3 (24 sats · 4 planes)",
                "C4": "C4 (32 sats · 4 planes)"}
CONFIG_COLOR = {"C3": "#E57373", "C4": "#BA68C8"} #same palette as phase 1
EXPECTED_SATS = {"C3": 24, "C4": 32} #a safety check, the csv must contain every sat i built
KMAX = 8 #kill up to 8 sats, a third of C3, past that the constellation is not a constellation
SAMPLE_TRIALS = 200 #random draws per k once exhaustive enumeration blows up
ENUM_CAP = 500 #sits just above C(32,2)=496, so k<=2 stays exact for BOTH configs & k>=3 falls to sampling
SEED = 42
SOVEREIGN_PREFIX = "GSI_" #indian GS carry this prefix, the sovereign filter key
INJECT_STEP_S = 60.0 #one synthetic packet per asset every minute, same grid as phase 1
P_HI = 95 #realistic worst case percentile
UNIT_S = 60.0 #divide seconds by this to report everything in minutes
FMT = "%d %b %Y %H:%M:%S.%f" #to match stk format

def _col_map(header): #internal helper, same parser as phase 1
    idx = {}
    for i, h in enumerate(header): #headers & its number in csv
        hl = h.strip().lower() #removes hidden spaces & puts things in lower case for all headers
        if   hl.startswith("start time"): idx["start"] = i
        elif hl.startswith("stop time"):  idx["stop"]  = i
        elif hl.startswith("duration"):   idx["dur"]   = i
        elif hl == "to object":           idx["to"]    = i
        elif hl == "from object":         idx["from"]  = i
    idx.setdefault("start", 0); idx.setdefault("stop", 1); idx.setdefault("dur", 2)
    idx.setdefault("to", 19);   idx.setdefault("from", 20) #safety line if csv exported without headers
    return idx #a dictionary of required headers and their numbering in the csv row

_PRE_TO   = ("To Satellite ", "To Sensor ", "To ")
_PRE_FROM = ("From Target ", "From Facility ", "From Place ", "From ") #internal constant tuples
def _strip(s, prefixes):
    for p in prefixes:
        if s.startswith(p): return s[len(p):].strip() #removing first n characters & spaces like "To Satellite"
    return s.strip() #A clean object name

def load_access(path):
    rows = []
    with open(path, newline="") as f: #safe opening & closing of file
        r = csv.reader(f) #removes commas from csv
        idx = _col_map(next(r)) #first row is the headers, next() eats it
        for row in r:
            if len(row) <= max(idx.values()): #highest column for file check
                continue
            try:
                float(row[idx["dur"]]) #if dur column have float
            except ValueError: #for the last summary lines
                continue
            try:
                s = datetime.strptime(row[idx["start"]].strip(), FMT)
                e = datetime.strptime(row[idx["stop"]].strip(),  FMT)
            except ValueError: #skip the corrupted time rows
                continue
            rows.append((s, e, _strip(row[idx["to"]], _PRE_TO),
                         _strip(row[idx["from"]], _PRE_FROM))) #make tuple of time & objects
    return rows #returns back structured data

def union_gaps(starts, stops): #vectorised merge(): gaps between the fused coverage windows, sec
    if starts.size == 0:
        return None #every sat serving this asset is dead, no coverage at all
    cm = np.maximum.accumulate(stops) #running max of the end times, handles passes nested inside other passes
    new = np.empty(starts.size, bool); new[0] = True
    new[1:] = starts[1:] > cm[:-1] #a pass starting after everything before it ended opens a NEW window
    sidx = np.flatnonzero(new) #index where each merged window starts
    eidx = np.append(sidx[1:] - 1, starts.size - 1) #last pass belonging to each window
    span_s, span_e = starts[sidx], cm[eidx] #window start & its true end, the running max
    return span_s[1:] - span_e[:-1] #gap = next window's start minus this window's end, empty array if coverage is continuous

def collect(inj, starts, stops, sat_idx): #vectorised phase 1 two-pointer sweep, uplink leg
    if starts.size == 0:
        return None, None, len(inj) #asset is blind, every packet dropped
    M = np.maximum.accumulate(stops)
    i = np.searchsorted(M, inj, side="left") #first pass whose running-max end clears the packet time
    valid = i < starts.size #beyond the last pass nothing can ever catch the packet
    ic = np.clip(i, 0, starts.size - 1)
    coll = np.where(starts[ic] <= inj, inj, starts[ic]) #pass already open -> collect now, else wait for it to open
    coll[~valid] = np.nan
    carr = np.where(valid, sat_idx[ic], -1) #which sat is carrying it, -1 = nobody
    return coll, carr, int((~valid).sum()) #same carrier the phase 1 loop picks: if the running max first clears t at i, then every earlier pass ended before t, so stops[i] >= t is the FIRST pass that can hold the packet

def delivery(coll, carr, gs_tables, n_inj): #downlink leg, each packet rides its own carrier down to an indian GS
    dlv = np.full(n_inj, np.nan) #blank delivery array
    for s in np.unique(carr[carr >= 0]): #loop only the sats that actually carried something
        tbl = gs_tables.get(s)
        m = carr == s #packets riding this particular sat
        if tbl is None:
            continue #this carrier never sees an indian GS in the whole window, its packets stay nan
        st, pm = tbl
        taus = coll[m] #their onboard collection times
        out = np.full(taus.size, np.nan)
        k = np.searchsorted(st, taus, side="right") - 1 #last GS pass that opened on or before the packet
        kc = np.clip(k, 0, pm.size - 1)
        inc = (k >= 0) & (pm[kc] >= taus) #that pass still open = sat sitting over a GS right now
        out[inc] = taus[inc] #already in contact so it lands the instant it is collected
        j = np.searchsorted(st, taus, side="right") #first GS pass strictly after the packet
        nx = ~inc & (j < st.size) #not in contact but a future pass exists
        out[nx] = st[np.clip(j, 0, st.size - 1)][nx] #packet waits onboard & lands when that pass opens
        dlv[m] = out
    return dlv

def p95(x):
    return float(np.percentile(x, P_HI)) if x.size else 0.0 #empty = continuous coverage = zero gap, not a failure

def precompute(cfg): #everything that does NOT change when sats die, built once & reused across every trial
    arows = load_access(os.path.join(REPORT_DIR, f"Asset_{cfg}_Access_Data.csv"))
    grows = load_access(os.path.join(REPORT_DIR, f"GS_{cfg}_Access_Data.csv"))
    epoch = min(min(r[0] for r in arows), min(r[0] for r in grows)) #earliest access anywhere becomes t = 0
    tend  = max(max(r[1] for r in arows), max(r[1] for r in grows)) #latest access anywhere closes the window
    T = (tend - epoch).total_seconds()
    sats = sorted({r[2] for r in arows} | {r[2] for r in grows}) #union, a sat can appear in one file & not the other
    sid  = {s: i for i, s in enumerate(sats)} #sat name -> integer, np.isin on strings is painfully slow
    assets = sorted({r[3] for r in arows})

    per_asset = {}
    for a in assets:
        rs = [r for r in arows if r[3] == a] #keep passes of this asset only
        s = np.array([(r[0] - epoch).total_seconds() for r in rs])
        e = np.array([(r[1] - epoch).total_seconds() for r in rs])
        k = np.array([sid[r[2]] for r in rs], dtype=np.int64) #the owning sat of each pass, as an integer
        o = np.argsort(s, kind="stable") #stable, so equal start times keep their file order & the run stays reproducible
        per_asset[a] = (s[o], e[o], k[o])

    gs_tables = {}
    by = {}
    for r in grows:
        if r[3].startswith(SOVEREIGN_PREFIX): #indian GS only, this whole study is about the sovereign case
            by.setdefault(sid[r[2]], []).append(
                ((r[0] - epoch).total_seconds(), (r[1] - epoch).total_seconds()))
    for s, lst in by.items():
        lst.sort() #sort this sat's GS passes
        st = np.array([x[0] for x in lst])
        pm = np.maximum.accumulate(np.array([x[1] for x in lst])) #deals with overlapping GS
        gs_tables[s] = (st, pm)

    inj = np.arange(0.0, T, INJECT_STEP_S) #the packet grid, identical for every asset & every trial
    return dict(sats=sats, assets=assets, per_asset=per_asset,
                gs=gs_tables, inj=inj, T=T) #all of it in RAM, this dict is read thousands of times

def eval_trial(P, dead): #one kill set: worst-asset P95 revisit & sovereign latency, in minutes
    inj = P["inj"]; T = P["T"]
    dead = np.asarray(sorted(dead), dtype=np.int64)
    wr, wl, drop_max = 0.0, 0.0, 0.0
    for a in P["assets"]:
        s, e, k = P["per_asset"][a]
        alive = ~np.isin(k, dead) #drop every pass owned by a dead sat, the rest of the geometry is untouched
        sf, ef, kf = s[alive], e[alive], k[alive]
        g = union_gaps(sf, ef)
        rev = T if g is None else (p95(g) if g.size else 0.0) #no coverage at all -> charge the whole window, an honest penalty
        coll, carr, n_unc = collect(inj, sf, ef, kf)
        if coll is None:
            lat, dfrac = T, 1.0 #asset blind, everything dropped
        else:
            dlv = delivery(coll, carr, P["gs"], inj.size)
            lt = dlv - inj #birth to delivery, both legs counted
            ok = ~np.isnan(lt)
            dfrac = 1.0 - ok.sum() / inj.size #fraction of packets that never made it down
            lat = p95(lt[ok]) if ok.any() else T
        wr = max(wr, rev); wl = max(wl, lat); drop_max = max(drop_max, dfrac) #WORST asset carries the trial, a constellation is only as good as the site it serves worst
    return wr / UNIT_S, wl / UNIT_S, drop_max

def run_config(cfg):
    P = precompute(cfg)
    n = len(P["sats"])
    if n != EXPECTED_SATS[cfg]: #a sat missing from the csv would quietly bias every curve downward
        print(f"[WARN] {cfg}: found {n} satellites, expected {EXPECTED_SATS[cfg]}")
    else:
        print(f"{cfg}: {n} satellites, {len(P['assets'])} assets, "
              f"window {P['T'] / 86400:.3f} d, grid {P['inj'].size}")
    res = {}
    for k in range(KMAX + 1): #k = how many sats are dead
        rng = np.random.default_rng(SEED + 1000 * CONFIGS.index(cfg) + k) #its own stream per config & per k, so a rerun reproduces exactly
        if k == 0:
            trials = [()] #nothing dead, one trial, this IS the phase 1 baseline
        elif math.comb(n, k) <= ENUM_CAP:
            trials = list(itertools.combinations(range(n), k)) #few enough combinations, so enumerate them ALL, no sampling error
        else:
            trials = [tuple(rng.choice(n, size=k, replace=False))
                      for _ in range(SAMPLE_TRIALS)] #combinatorics blew up, fall back to random draws
        R, L, D = [], [], []
        for dead in tqdm(trials, desc=f"{cfg} k={k}", leave=False):
            wr, wl, dm = eval_trial(P, dead)
            R.append(wr); L.append(wl); D.append(dm)
        R, L, D = map(np.array, (R, L, D))
        res[k] = dict(n=len(trials),
                      rev=(np.median(R), np.percentile(R, 10), np.percentile(R, 90)),
                      lat=(np.median(L), np.percentile(L, 10), np.percentile(L, 90)),
                      drop=(float(D.mean()), float(D.max()))) #median & the 10-90 spread, WHICH sats die matters as much as how many
        if k == 0:
            print(f"  {cfg} baseline (k=0, = P1): worst-asset revisit P95 "
                  f"{R[0]:.1f} min · sovereign latency P95 {L[0]:.1f} min") #cross check against phase 1, these two must agree or one of the scripts is wrong
    return res

def chart(results):
    os.makedirs(OUT_DIR, exist_ok=True)
    plt.style.use("dark_background")
    plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
                         "savefig.facecolor": "#0d1117", "font.size": 10}) #github dark shade on every chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.4)) #revisit left, latency right
    ks = np.arange(KMAX + 1)
    for cfg in CONFIGS:
        r = results[cfg]
        for ax, key in ((ax1, "rev"), (ax2, "lat")): #same plotting code drives both panels
            med = np.array([r[k][key][0] for k in ks])
            lo  = np.array([r[k][key][1] for k in ks])
            hi  = np.array([r[k][key][2] for k in ks])
            ax.plot(ks, med, "-o", color=CONFIG_COLOR[cfg], lw=2, ms=4.5,
                    label=CONFIG_LABEL[cfg]) #the median line is the story
            ax.fill_between(ks, lo, hi, color=CONFIG_COLOR[cfg], alpha=0.18) #the band is the risk, a wide band means the config cares WHICH sat you lose
    ax1.set_title("Worst-asset revisit P95 vs failures",
                  fontsize=11.5, fontweight="bold")
    ax2.set_title("Worst-asset sovereign latency P95 vs failures",
                  fontsize=11.5, fontweight="bold")
    for ax in (ax1, ax2):
        ax.set_xlabel("satellites failed (random, no replacement)")
        ax.set_ylabel("minutes"); ax.set_xticks(ks); ax.grid(alpha=0.25) #integer ticks, half a satellite cannot fail
    ax1.legend(fontsize=8.5, framealpha=0.15, loc="upper left") #one legend for the pair, both panels use the same colours
    fig.text(0.5, 0.015,
             "median line · band = 10th–90th percentile of failure outcomes · "
             "k≤2 exhaustively enumerated, k≥3 200 random draws (seed 42) · "
             "model = P1: first-contact store-and-forward, no ISL, sovereign "
             "delivery via GSI_ stations, 33-day window",
             ha="center", fontsize=7.4, color="#78909c") #the method printed on the chart, a resilience curve with no stated model is just a drawing
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    out = os.path.join(OUT_DIR, "08_degradation_resilience.png")
    fig.savefig(out, dpi=160)
    plt.close(fig) #free the memory before the next figure
    print(f"wrote {out}")

def write_csv(results):
    path = os.path.join(REP_OUT, "resilience_degradation.csv")
    with open(path, "w", newline="") as f: #safe opening & closing of file
        w = csv.writer(f)
        w.writerow(["worst-asset P95 metrics vs satellite failures (minutes)"]) #units banner on top of the csv
        w.writerow(["config", "k_failed", "n_trials",
                    "revisit_med", "revisit_p10", "revisit_p90",
                    "latency_med", "latency_p10", "latency_p90",
                    "dropfrac_mean", "dropfrac_max"])
        for cfg in CONFIGS:
            for k in range(KMAX + 1):
                r = results[cfg][k]
                w.writerow([cfg, k, r["n"], #n_trials printed so a reader can see where enumeration stopped & sampling began
                            *(f"{v:.2f}" for v in r["rev"]),
                            *(f"{v:.2f}" for v in r["lat"]),
                            f"{r['drop'][0]:.4f}", f"{r['drop'][1]:.4f}"])
    print(f"wrote {path}")

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    results = {cfg: run_config(cfg) for cfg in CONFIGS}
    for cfg in CONFIGS: #killing MORE sats can never make the constellation better, if the curve dips the sampling is too thin
        med = [results[cfg][k]["lat"][0] for k in range(KMAX + 1)]
        if any(b < a - 1.0 for a, b in zip(med, med[1:])): #1 min slack, small non-monotonic wobble is just draw noise
            print(f"[WARN] {cfg}: latency median not monotone (sampling noise?)")
    chart(results)
    write_csv(results)
