import os, csv, re
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use("Agg") #anti-grain geometry for background saving
import matplotlib.pyplot as plt
from tqdm import tqdm

REPORT_DIR = "D:/Samtel-Portfolio/data/raw/Access" #stk exported access reports live here
CONFIGS = ["SSO", "C1", "C2", "C3", "C4"] #same 5 configs built in phase 0
CONFIG_LABEL = { #short legend names for the charts
    "SSO": "R (SSO 97.6)",
    "C1": "C1 (40, 18S)",
    "C2": "C2 (24s/6p)",
    "C3": "C3 (24s/4p)",
    "C4": "C4 (32s/4p)",
}
REP_OUT = "D:\Samtel-Portfolio\data\processed" #final numbers table lands here
SOVEREIGN_PREFIX = "GSI_" #indian GS carry this prefix, the sovereign filter key
INJECT_STEP_S = 60.0 #one synthetic packet per asset every minute
P_LO, P_HI = 50, 95 #typical & realistic worst case percentiles
UNIT_S = 60.0 #divide seconds by this to report everything in minutes
UNIT_LBL = "minutes"
OUT_DIR = "D:\Samtel-Portfolio\dashboards" #charts land here
FMT = "%d %b %Y %H:%M:%S.%f" #to match stk format
COLOURS = ["#4FC3F7", "#FFB74D", "#81C784", "#E57373", "#BA68C8" ] #one colour per config, same order as CONFIGS

def _col_map(header): #internal helper
    idx = {}
    for i, h in enumerate(header): #headers & its number in csv
        h1 = h.strip().lower() #removes hidden spaces & puts things in lower case for all headers
        if h1.startswith("start time"): idx["start"] = i 
        elif h1.startswith("stop time"): idx["stop"] = i
        elif h1.startswith("duration"): idx["dur"] = i
        elif h1 == "to object": idx["to"] = i 
        elif h1 == "from object": idx["from"] = i #just to understanding the mapping of each header 
    
    idx.setdefault("start", 0); idx.setdefault("stop", 1); idx.setdefault("dur", 2)
    idx.setdefault("to",19); idx.setdefault("from", 20) #safety line if csv exported without headers
    return idx #a dictionary of required headers and their numbering in the csv row

_PRE_TO = ("To Satellite ", "To Sensor ", "To ")
_PRE_FROM = ("From Target ", "From Facility ", "From Place ", "From ") #internal constant tuples
def _strip(s, prefixes):
    for p in prefixes:
        if s.startswith(p): return s[len(p):].strip() #removing first n characters & spaces like "To Satellite"
    return s.strip() #A clean object name

def load_access(path): 
    rows = []
    with open(path, newline="") as f: #safe opening & closing of file
        r = csv.reader(f) #removes commas from csv
        header = next(r) #saves first row and removes it from r:headers
        idx = _col_map(header) 
        for row in r:
            if len(row) <= max(idx.values()): #highest column for file check
                continue #back to for loop
            try:
                float(row[idx["dur"]]) #if dur column have float
            except ValueError: #for the last summary lines 
                continue
            try:
                s = datetime.strptime(row[idx["start"]].strip(),FMT) #Start time & using the defined format
                e = datetime.strptime(row[idx["stop"]].strip(),FMT)
            except ValueError: # skip the corrupted time rows
                continue
            sat = _strip(row[idx["to"]], _PRE_TO) 
            oth = _strip(row[idx["from"]], _PRE_FROM)
            rows.append((s,e,sat,oth)) #make tuple of time & objects
    return rows #returns back structured data

def merge(intervals):
    iv = sorted(intervals) # sorted start & end time lists
    out = []
    for s, e in iv:
        if out and s <= out[-1][1]:# looks for last recorderd block & its end time to check overlap
            out[-1][1] = max(out[-1][1], e) #stretch the time of last block to merge the time
        else:
            out.append([s,e]) # no overlap
    return out #returns a list of coverage windows

def revisit_gaps(spans):
    return np.array([spans[i + 1][0] - spans[i][1] for i in  range(len(spans) - 1)]) #numpy array of all the gaps

def collection_sweep(inj,starts, stops, n): #simulation time, pass start time, pass end time, assets
    coll = np.full(len(inj), np.nan) #creates blank array of n length
    carr = np.full(len(inj), -1, dtype=np.int64) #IDs for the passes
    lo = 0 #low index for Two-pointer optimization: pass counter
    for i in range(len(inj)):
        t = inj[i]#current packet time
        while lo<n and stops[lo]< t:#if pass less than STK simulation time and pass ends before packet generates(packet misses the pass)
            lo += 1#wait for next pass
        if lo>= n:#packet time excceeds STK simulation time
            break
        if starts[lo]<=t: #pass starts time earlier than current packet time
            coll[i] = t; carr[i] = lo#catches the current packet & its ID
        else:#if current packet is earlier than pass
            coll[i] = starts[lo]; carr[i] = lo#catches pass start time as packet collection time and its Packet ID
    return coll, carr #returns packet collection time & its ID

def build_gs_map(gs_rows, allowed): 
    by = {}

    for s, e, sat, gs in gs_rows:
        if allowed(gs):#checks for Indian GS
            by.setdefault(sat, []).append((s, e))#adds/creates sat, add its start & end time of passes to the dict
    
    out = {}
    for sat, lst in by.items():
        lst.sort()#sort specific sat passes
        st = np.array([x[0] for x in lst])#sort start time
        sp = np.array([x[1] for x in lst])#sort end time
        out[sat] = (st, np.maximum.accumulate(sp))#deals with overlapping gs
    return out

def delivery_batch(taus, st, pmax): #packet collection times, gs pass start times, running max of pass end times
    out = np.full(len(taus), np.nan) #blank delivery array, the downlink leg
    k = np.searchsorted(st, taus, side = "right")-1 #binary search: last gs pass that started on or before each packet
    in_contact = (k >= 0) & (pmax[np.clip(k,0,len(pmax) - 1)] >= taus) #that pass or an earlier overlapping one still open = sat sitting over a gs right now
    out[in_contact] = taus[in_contact] #already in contact so packet lands the same instant it is collected
    j = np.searchsorted(st, taus, side = "right") #first gs pass strictly after the packet
    nxt = ~in_contact & (j<len(st)) #not in contact but a future pass exists to catch it
    out[nxt] = st[np.clip(j, 0, len(st) - 1)][nxt] #packet waits onboard & lands the moment next pass opens
    return out #delivery times, nan = collected but never downlinked inside the window

def pstats(a):
    a = a[~np.isnan(a)] #throw the undelivered packets out before stats
    if a.size == 0:
        return dict(p50 = np.nan, p95 = np.nan, mx = np.nan, n = 0) #nothing survived to measure
    return dict(p50 = np.percentile(a, P_LO), p95 = np.percentile(a, P_HI),
                mx=a.max(), n =a.size) #typical, realistic worst, absolute worst & sample count

def gap_stats(spans):
    if len(spans) == 0:
        return dict(p50 = np.nan, p95=np.nan, mx = np.nan, n=0) #no coverage windows at all
    g = revisit_gaps(spans)
    if g.size == 0:
        return dict(p50=0.0, p95=0.0, mx = 0.0, n=0) #single continuous window means zero gap
    return pstats(g/UNIT_S) #gap seconds converted to minutes

def to_sec(dts, epoch):
    return np.array([(d - epoch).total_seconds() for d in dts], dtype = float) #datetime to plain seconds from epoch, numpy friendly

def run():
    os.makedirs(OUT_DIR, exist_ok= True)
    asset_raw, gs_raw = {}, {} #two csv families per config
    all_starts = []
    for c in CONFIGS: #load both access csv per config
        ap = os.path.join(REPORT_DIR, f"Asset_{c}_Access_Data.csv")
        gp = os.path.join(REPORT_DIR, f"GS_{c}_Access_Data.csv")
        asset_raw[c] = load_access(ap) #sat to asset passes
        gs_raw[c] = load_access(gp) #sat to gs passes
        all_starts += [r[0] for r in asset_raw[c]] + [r[0] for r in gs_raw[c]] #collecting every start time for the epoch hunt
    epoch = min(all_starts) #earliest access anywhere becomes t = 0
    win_end = max(max(r[1] for r in asset_raw[c]) for c in CONFIGS) #latest asset access end
    win_end = max(win_end, max(max(r[1] for r in gs_raw[c]) for c in CONFIGS)) #stretched further if any gs access ends later
    T_end = (win_end - epoch).total_seconds() #full analysis window in seconds
    inj = np.arange(0.0, T_end, INJECT_STEP_S) #synthetic packet born at each asset every 60s
    assets = sorted({r[3] for r in asset_raw[CONFIGS[0]]}) #asset names read from the csv itself, every config shares the same 5

    print(f"epoch={epoch} window ={T_end/86400:.3f} d "
          f"packets/asset = {len(inj)} assets = {assets}")
    
    REV = {} #revisit stats per config & asset
    LAT_S = {}; LAT_G = {} #latency over sovereign & global network
    GAP_S = {}; GAP_G = {} #gs contact gaps of sovereign & global network
    DROP = {} #dropped packet accounting

    work = [(c,a) for c in CONFIGS for a in assets] #every config asset pair under one tqdm bar
    for c, a in tqdm(work, desc = "revisit+latency"):
        arows = [r for r in asset_raw[c] if r[3] == a] #keep passes of this asset only
        s = to_sec([r[0] for r in arows], epoch)
        e = to_sec([r[1] for r in arows], epoch)
        order = np.argsort(s) #sort passes by start time

        s,e = s[order], e[order]
        sats = [arows[i][2] for i in order] #which sat owns which pass, kept in the same sorted order

        spans = merge(list(zip(s.tolist(), e.tolist()))) #overlapping passes fused into clean coverage windows
        REV[(c,a)] = gap_stats(spans) #gaps between windows = revisit intervals

        coll, carr = collection_sweep(inj, s, e, len(s)) #uplink leg: asset packet to sat
        valid = carr >= 0 #packets some sat actually picked
        no_cover = int((~valid).sum()) #packets born after the final pass, nothing left to catch them

        if(c, "sov") not in run._cache: #gs maps built once per config & reused for all its assets
            run._cache[(c, "sov")] = build_gs_map(
                [(to_sec([r[0]], epoch)[0], to_sec([r[1]], epoch)[0], r[2], r[3])
                  for r in gs_raw[c]],
                lambda g: g.startswith(SOVEREIGN_PREFIX)) #indian GS only
            run._cache[(c, "glob")] = build_gs_map(
                [(to_sec([r[0]], epoch)[0], to_sec([r[1]], epoch)[0], r[2], r[3])
                  for r in gs_raw[c]],
                lambda g: True) #every GS allowed
        gmap_s = run._cache[(c, "sov")]
        gmap_g = run._cache[(c, "glob")]

        div_s = np.full(len(inj), np.nan) #delivery times over the indian network
        div_g = np.full(len(inj), np.nan) #delivery times over the full network
        carrier_names = np.array(sats)[np.clip(carr,0,len(sats) - 1)] #carrier index to sat name, clip so the -1 of uncollected packets doesnt misbehave
        for sat in set(np.array(sats)[carr[valid]]): #loop only the sats that actually carried something
            m = valid & (carrier_names == sat) #packets riding this particular sat
            taus = coll[m] #their onboard collection times
            if sat in gmap_s:
                st, pm = gmap_s[sat]; div_s[m] = delivery_batch(taus, st, pm) #downlink through indian GS
            if sat in gmap_g:
                st, pm = gmap_g[sat]; div_g[m] = delivery_batch(taus, st, pm) #downlink through the full network

        lat_s = (div_s - inj) #birth to delivery, both legs counted
        lat_g = (div_g - inj)
        LAT_S[(c, a)] = pstats(lat_s/UNIT_S) #stats reported in minutes
        LAT_G[(c, a)] = pstats(lat_g/UNIT_S)
        DROP[(c,a)] = (no_cover,
                       int(np.isnan(lat_s[valid]).sum()), #collected but indian GS never saw the sat again
                       int(np.isnan(lat_g[valid]).sum())) #collected but no GS anywhere saw the sat again
        
    for c in CONFIGS: #network level blackout check, independent of assets
        gs_sec = [(to_sec([r[0]], epoch)[0], to_sec([r[1]], epoch)[0], r[3])
                  for r in gs_raw[c]] #every gs pass of the config in seconds
        sov = merge([(s, e) for s, e, g in gs_sec if g.startswith(SOVEREIGN_PREFIX)]) #fused indian GS contact windows
        glb = merge([(s, e) for s, e, g in gs_sec]) #fused full network contact windows
        GAP_S[c] = gap_stats(sov)
        GAP_G[c] = gap_stats(glb)
    
    write_csv(assets, REV, LAT_S, LAT_G, GAP_S, GAP_G, DROP)
    make_charts(assets, REV, LAT_S, LAT_G)
    print(f"\n Done. Outputs in: {OUT_DIR}")

run._cache = {} #dict hung on the function itself, plain python trick so the cache survives across the loop

def write_csv(assets, REV, LAT_S, LAT_G, GAP_S, GAP_G, DROP):
    path = os.path.join(REP_OUT, "revisit_latency_results.csv")
    with open(path, "w", newline="") as f: #safe opening & closing of file
        w = csv.writer(f)
        w.writerow([f"all values in {UNIT_LBL}"]) #units banner on top of the csv
        w.writerow(["config", "asset", "metric", "network",
                    "P50", "P95", "max", "n_samples"])
        for c in CONFIGS:
            for a in assets: #three rows per config asset pair
                r = REV[(c,a)]
                w.writerow([c,a,"revisit", "-",
                            f"{r['p50']:.2f}", f"{r['p95']:.2f}", f"{r['mx']:.2f}", r["n"]])
                ls, lg = LAT_S[(c, a)], LAT_G[(c, a)]
                w.writerow([c, a, "latency", "sovereign",
                            f"{ls['p50']:.2f}", f"{ls['p95']:.2f}", f"{ls['mx']:.2f}", ls["n"]])
                w.writerow([c, a, "latency", "global",
                            f"{lg['p50']:.2f}", f"{lg['p95']:.2f}", f"{lg['mx']:.2f}", lg["n"]])
                
        w.writerow([]) #blank row to separate the tables
        w.writerow(["config", "GS-contact-gap network", "P50", "P95", "max"])
        for c in CONFIGS:
            for tag, G in (("sovereign", GAP_S), ("global", GAP_G)): #second table: network blackout gaps
                g = G[c]
                w.writerow([c, tag, f"{g['p50']:.2f}", f"{g['p95']:.2f}", f"{g['mx']:.2f}"])
        w.writerow([])
        w.writerow(["config", "asset", "dropped_no_coverage",
                    "dropped_no_sovereign_dlv", 'dropped_no_global_dlv']) #third table: dropped packet accounting
        for c in CONFIGS:
            for a in assets:
                w.writerow([c, a, *DROP[(c,a)]]) #unpacks the drop tuple straight into the row
    print(f" wrote {path}")

def _grouped(ax, assets, p50, p95, ylabel, title): #internal helper, one engine for all three grouped charts
    nA, nC = len(assets), len(CONFIGS)
    width = 0.8/nC #5 config bars share 0.8 of the slot, 0.2 stays as gap between asset groups
    x = np.arange(nA) #one group per asset
    for ci, c in enumerate(CONFIGS):
        h = np.array([p50[(c, a)]["p50"] for a in assets]) #bar height = typical value
        hi = np.array([p95[(c, a)]["p95"] for a in assets]) #whisker top = realistic worst case
        yerr = np.vstack([np.zeros(nA), np.clip(hi - h, 0, None)]) #one sided whisker, P50 up to P95 only
        ax.bar(x + ci * width, h, width, yerr = yerr, capsize = 2.5,
               color=COLOURS[ci % len(COLOURS)], label = CONFIG_LABEL.get(c,c),
               error_kw=dict(ecolor = "#cfd8dc", lw=1)) #each config bar shifted inside its own group
    ax.set_xticks(x + width * (nC - 1) / 2) #tick sits at the centre of each 5 bar group
    ax.set_xticklabels([a.replace("AST_", "") for a in assets], rotation = 18, ha="right") #clean asset names on the x axis
    ax.set_ylabel(f"{ylabel} ({UNIT_LBL})")
    ax.set_title(title, fontsize=12, fontweight = "bold")
    ax.legend(fontsize=7.5, framealpha=0.15)
    ax.grid(axis="y", alpha=0.25)

def make_charts(assets, REV, LAT_S, LAT_G):
    plt.style.use("dark_background")
    plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
                         "savefig.facecolor": "#0d1117","font.size": 10}) #github dark shade on every chart
    sub = "bar = P50 (typical) · whisker = P95 (realistic worst-case)" #common subtitle for reading the bars

    for key, data, ttl, fn in [ #three charts out of the same helper
        ("rev", REV, "Revisit per asset - all 5 constellations",
         "01_revisit.png"),
        ("lats", LAT_S, "End-to-end latency - SOVEREIGN ground segment (Indian GS only)",
         "02_latency_sovereign.png"),
        ("latg", LAT_G, "End-to-End latency- GLOBAL integrated ground segment",
         "03_latency_global.png") 
    ]:
        fig, ax = plt.subplots(figsize = (11,5.5))
        ylbl = "Revisit interval" if key == "rev" else "Latency"
        _grouped(ax, assets, data, data, ylbl, ttl) #same dict passed twice, p50 & p95 keys both live inside it
        fig.text(0.5, 0.94, sub, ha = "center", fontsize = 8.5, color = "#90a4ae")
        fig.tight_layout(rect = [0,0,1,0.93]) #leaves headroom for the subtitle
        fig.savefig(os.path.join(OUT_DIR, fn), dpi = 160)
        plt.close(fig) #free the memory before next figure
        print(f"wrote {fn}")

    fig, ax = plt.subplots(figsize = (11,5.5)) #4th chart built by hand, max only so no whiskers
    nA, nC = len(assets), len(CONFIGS)
    width = 0.8/ nC
    x = np.arange(nA)
    for ci, c in enumerate(CONFIGS):
        h = np.array([LAT_S[(c,a)]["mx"] for a in assets]) #absolute worst packet of the whole window
        ax.bar(x + ci * width, h, width, color = COLOURS[ci % len(COLOURS)],
               label = CONFIG_LABEL.get(c,c))
        
    ax.set_xticks( x + width * (nC - 1) / 2)
    ax.set_xticklabels([a.replace("AST_", "") for a in assets], rotation=18, ha="right")
    ax.set_ylabel(f"Worst-case sovereign latency  ({UNIT_LBL})")
    ax.set_title("worst-case latency - SOVEREIGN ground segment",
                    fontsize = 12, fontweight = "bold")
    ax.legend(fontsize = 7.5, framealpha = 0.15); ax.grid(axis = "y", alpha = 0.25)
    fig.text(0.5,0.94, "absolute worst case · polar R wanders far from the Indian GS belt",
                ha = "center", fontsize = 8.5, color = "#90a5ae")
    fig.tight_layout(rect = [0,0,1,0.93])
    fig.savefig(os.path.join(OUT_DIR, "04_max_latency_sovereign.png"), dpi = 160)
    plt.close(fig)
    print("wrote 04_max_latency_sovereign.png ")
if __name__ == "__main__":
    run()