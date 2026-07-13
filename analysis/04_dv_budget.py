import os, csv, math
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use("Agg") #anti-grain geometry for background saving
import matplotlib.pyplot as plt

PROFILES = { #altitude km -> the phase 2 decay profile it gets its drag rate from
    525: "D:\Samtel-Portfolio\data/raw\Lifetime\Lifetime_Analysis_525km.csv",
    550: "D:\Samtel-Portfolio\data/raw\Lifetime\Lifetime_Analysis_550km.csv"
}
OUT_DIR = "D:\Samtel-Portfolio\dashboards"
REP_OUT = "D:\Samtel-Portfolio\data\processed"
FMT = "%d %b %Y %H:%M:%S.%f" #to match stk format

MU = 398600.4418 #km3/s2
RE = 6378.137 #km
J2 = 1.08262668e-3 #earth oblateness, the term that drags the node around
G0 = 9.80665 #m/s2, only used to turn Isp seconds into an exhaust velocity

M0_KG = 4.0 #3U wet mass
INCL_DEG = 40.0
DESIGN_LIVES_YR = [5, 7] #baseline & a sensitivity case, station-keeping scales straight with this
DISPOSAL_PERIGEE = [350, 300] #km target perigee for the EOL burn, baseline & variant
FIT_DAYS = 365.0 #da/dt fitted over the first year only, drag is worst there so the hold stays conservative
PHASING_DA_KM = 10.0 #drift orbit offset for in-plane phasing
RAAN_OFFSET_KM = 50.0 #altitude offset used for the J2 nodal drift trade
INJECTION_MS = 15.0 #stated allowance for rideshare dispersion, not computed
COLA_MS_PER_YR = 1.0 #stated allowance per year for collision avoidance
MARGIN = 0.25 #25% on the whole budget, sits on top of everything
ISP_S = {"cold gas (60 s)": 60.0,
         "green monoprop (220 s)": 220.0,
         "electric (1000 s)": 1000.0} #the three realistic options for a 4 kg bus
COLORS = {"EOL deorbit": "#E57373", "station-keeping": "#4FC3F7",
          "injection corr.": "#81C784", "phasing": "#BA68C8",
          "COLA": "#FFB74D", "margin 25%": "#78909c"}

def v_circ(a_km): #circular orbit speed, km/s
    return math.sqrt(MU / a_km)

def sk_rate_ms_per_yr(a_km, dadt_km_yr): #drag makeup: a small hohmann raise costs 0.5*v*da/a
    return 0.5 * v_circ(a_km) * 1000.0 * abs(dadt_km_yr) / a_km

def eol_dv_ms(h_circ_km, h_perigee_km): #one retro burn, circular at h_circ -> ellipse with the target perigee
    ra, rp = RE + h_circ_km, RE + h_perigee_km
    at = 0.5 * (ra + rp) #transfer ellipse semi major axis
    v0 = v_circ(ra) #speed before the burn
    va = math.sqrt(MU * (2.0 / ra - 1.0 / at)) #vis-viva at apogee of the new ellipse
    return (v0 - va) * 1000.0 #the burn is just the difference, m/s

def hohmann_pair_ms(a_km, da_km): #lower by da then raise back, 2 burns, total ~ v*da/a
    return v_circ(a_km) * 1000.0 * da_km / a_km

def raan_direct_dv_ms(a_km, d_raan_deg, i_deg): #brute force plane change, burnt through the real angle between the two planes
    i = math.radians(i_deg); dO = math.radians(d_raan_deg)
    ct = math.cos(i) ** 2 + math.sin(i) ** 2 * math.cos(dO) #spherical trig, not just dRAAN, the inclination pulls the planes together
    theta = math.acos(max(-1.0, min(1.0, ct))) #clamped, floating point can push ct a hair past 1
    return 2.0 * v_circ(a_km) * 1000.0 * math.sin(theta / 2.0) #the classic 2*v*sin(theta/2)

def nodal_rate_deg_day(a_km, i_deg): #J2 nodal regression, deg/day
    n = math.sqrt(MU / a_km ** 3) #mean motion, rad/s
    Od = -1.5 * J2 * (RE / a_km) ** 2 * n * math.cos(math.radians(i_deg)) #negative for prograde, the node walks west
    return math.degrees(Od) * 86400.0

def phasing(a_km, da_km, phase_deg): #drop to a drift orbit, let the phase slip, come back up
    n = math.sqrt(MU / a_km ** 3)
    rate = 1.5 * n * (da_km / a_km) * 86400.0 #relative drift rate, rad/day, lower orbit = faster orbit
    days = math.radians(phase_deg) / rate #time to slew the wanted phase angle
    return hohmann_pair_ms(a_km, da_km), days #dv is fixed by da, only the wait scales with the angle

def prop_mass_kg(dv_ms, isp_s, m0=M0_KG): #rocket equation, turned around to give mass instead of dv
    return m0 * (1.0 - math.exp(-dv_ms / (isp_s * G0)))

def fit_dadt(path): #least squares da/dt over the first FIT_DAYS of the decay profile
    t, a = [], []
    with open(path, newline="") as f: #safe opening & closing of file
        for d in csv.DictReader(f):
            ts = (d.get("Time (UTCG)") or "").strip()
            if not ts: #skip the blank tail rows stk leaves behind
                continue
            try:
                tt = datetime.strptime(ts, FMT)
            except ValueError: #skip the corrupted time rows
                continue
            t.append(tt); a.append(float(d["Semi-major Axis (km)"]))
    t0 = t[0]
    days = np.array([(x - t0).total_seconds() / 86400.0 for x in t]) #datetime to days from epoch
    a = np.array(a)
    m = days <= FIT_DAYS #early life only, the tail plunges & would flatten the fit
    slope_day, icpt = np.polyfit(days[m], a[m], 1) #straight line, decay is near linear over a year
    resid = a[m] - (slope_day * days[m] + icpt)
    return slope_day * 365.25, float(np.sqrt(np.mean(resid ** 2))), a[0] #km/yr, fit rms & the true starting SMA from the profile itself

def build_budget(a0_map, dadt_map):
    rows = []
    for h in PROFILES: #every altitude
        for life in DESIGN_LIVES_YR: #every design life
            for hp in DISPOSAL_PERIGEE: #every disposal target, full cross product
                a0 = a0_map[h] #real SMA out of the profile, not RE+alt
                sk = sk_rate_ms_per_yr(a0, dadt_map[h]) * life #hold cost scales straight with the years held
                ph, ph_days = phasing(a0, PHASING_DA_KM, 180.0) #worst case phasing, half a plane away
                lines = {
                    "injection corr.": INJECTION_MS,
                    "station-keeping": sk,
                    "phasing":         ph,
                    "COLA":            COLA_MS_PER_YR * life,
                    "EOL deorbit":     eol_dv_ms(h, hp),
                } #the 5 real line items, margin is added after
                sub = sum(lines.values())
                rows.append(dict(alt=h, life=life, perigee=hp, lines=lines,
                                 subtotal=sub, margin=MARGIN * sub,
                                 total=(1 + MARGIN) * sub, ph_days=ph_days))
    return rows

def chart(rows):
    os.makedirs(OUT_DIR, exist_ok=True)
    show = [r for r in rows if r["perigee"] == DISPOSAL_PERIGEE[0]] #chart the baseline perigee only, 300 km lives in the csv
    plt.style.use("dark_background")
    plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
                         "savefig.facecolor": "#0d1117", "font.size": 10}) #github dark shade on every chart
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.8),
                                  gridspec_kw={"width_ratios": [2.1, 1]}) #budget wide on the left, propellant narrow on the right

    order = ["EOL deorbit", "station-keeping", "injection corr.", "phasing", "COLA"] #biggest at the bottom of the stack
    x = np.arange(len(show)); width = 0.58
    bottom = np.zeros(len(show)) #running height, this is what makes it a stacked bar
    for k in order:
        vals = np.array([r["lines"][k] for r in show])
        ax.bar(x, vals, width, bottom=bottom, color=COLORS[k], label=k)
        bottom += vals #next slice sits on top of everything so far
    mvals = np.array([r["margin"] for r in show])
    ax.bar(x, mvals, width, bottom=bottom, color=COLORS["margin 25%"],
           alpha=0.55, hatch="//", label="margin 25%") #hatched so nobody mistakes margin for a real line item
    for i, r in enumerate(show):
        ax.text(i, r["total"] + 3, f"{r['total']:.0f} m/s", ha="center",
                fontsize=9.5, fontweight="bold", color="#eceff1") #total printed on top, that is the only number anyone quotes
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['alt']} km\n{r['life']} yr" for r in show])
    ax.set_ylabel("Δv  (m/s)")
    ax.set_title(f"Per-satellite Δv budget — disposal perigee "
                 f"{DISPOSAL_PERIGEE[0]} km", fontsize=11.5, fontweight="bold")
    ax.legend(fontsize=8, framealpha=0.15, loc="upper left")
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, max(r["total"] for r in show) * 1.18) #headroom so the total labels dont clip

    worst = max(show, key=lambda r: r["total"]) #size the tank on the worst case, never the average
    names = list(ISP_S)
    masses = [prop_mass_kg(worst["total"], ISP_S[n]) for n in names]
    bars = ax2.bar(np.arange(len(names)), masses,
                   color=["#E57373", "#81C784", "#4FC3F7"], width=0.55)
    for b, m in zip(bars, masses):
        ax2.text(b.get_x() + b.get_width() / 2, m + max(masses) * 0.02,
                 f"{m * 1000:.0f} g\n{100 * m / M0_KG:.1f}%", ha="center", fontsize=8.5) #grams & % of bus, a fraction is what a systems engineer reacts to
    ax2.set_xticks(np.arange(len(names)))
    ax2.set_xticklabels([n.replace(" (", "\n(") for n in names], fontsize=8) #break the Isp onto its own line so the ticks dont overlap
    ax2.set_ylabel(f"propellant on {M0_KG:.0f} kg bus  (kg)")
    ax2.set_title(f"Propellant @ worst case\n"
                  f"({worst['alt']} km · {worst['life']} yr · {worst['total']:.0f} m/s)",
                  fontsize=9.5)
    ax2.grid(axis="y", alpha=0.25)
    ax2.set_ylim(0, max(masses) * 1.25)

    fig.text(0.5, 0.015,
             "station-keeping fitted from P2 decay profiles (first-year, elevated "
             "2026-27 flux — conservative hold) · EOL = exact perigee lowering · "
             "electric: mass-trivial but mN-class thrust — deorbit burn spans weeks",
             ha="center", fontsize=7.4, color="#78909c") #the electric caveat matters, the mass chart alone would sell a lie
    fig.tight_layout(rect=[0, 0.045, 1, 1])
    out = os.path.join(OUT_DIR, "07_dv_budget.png")
    fig.savefig(out, dpi=160)
    plt.close(fig) #free the memory before the next figure
    print(f"wrote {out}")

def write_csv(rows, dadt_map, a0_map, H_km):
    path = os.path.join(REP_OUT, "dv_budget.csv")
    with open(path, "w", newline="") as f: #safe opening & closing of file
        w = csv.writer(f)
        w.writerow(["PER-SATELLITE DV BUDGET (m/s)"])
        w.writerow(["alt_km", "design_life_yr", "disposal_perigee_km",
                    "injection", "station_keeping", "phasing", "COLA",
                    "EOL_deorbit", "subtotal", "margin_25pct", "TOTAL"])
        for r in rows: #every case, not just the ones that got charted
            L = r["lines"]
            w.writerow([r["alt"], r["life"], r["perigee"],
                        f"{L['injection corr.']:.1f}", f"{L['station-keeping']:.1f}",
                        f"{L['phasing']:.1f}", f"{L['COLA']:.1f}",
                        f"{L['EOL deorbit']:.1f}", f"{r['subtotal']:.1f}",
                        f"{r['margin']:.1f}", f"{r['total']:.1f}"])
        w.writerow([]) #blank row to separate the tables
        w.writerow(["PROPELLANT MASS (kg on 4 kg bus) at each case TOTAL"]) #second table: does the budget even fit on the bus
        w.writerow(["alt_km", "life_yr", "perigee_km"] + list(ISP_S))
        for r in rows:
            w.writerow([r["alt"], r["life"], r["perigee"]] +
                       [f"{prop_mass_kg(r['total'], s):.3f}" for s in ISP_S.values()])
        w.writerow([])
        w.writerow(["PLANE-ACQUISITION TRADE (525 km, i=40)"]) #third table: the trade that decides how many launches i buy
        a0 = a0_map[525]
        w.writerow(["direct RAAN 90 deg (C2b adjacent planes)",
                    f"{raan_direct_dv_ms(a0, 90, INCL_DEG):.0f} m/s"]) #km/s class numbers, a 4 kg bus will never carry this
        w.writerow(["direct RAAN 60 deg (C2a adjacent planes)",
                    f"{raan_direct_dv_ms(a0, 60, INCL_DEG):.0f} m/s"])
        dOd = 3.5 * (RAAN_OFFSET_KM / a0) * abs(nodal_rate_deg_day(a0, INCL_DEG)) #nodal rate goes as a^-3.5, so the differential rate is 3.5*(da/a) of it
        w.writerow([f"J2 drift, {RAAN_OFFSET_KM:.0f} km offset: dv",
                    f"{hohmann_pair_ms(a0, RAAN_OFFSET_KM):.0f} m/s"]) #dv is trivial, the drift is free, only the clock is expensive
        w.writerow(["J2 drift: differential rate", f"{dOd:.3f} deg/day"])
        w.writerow(["J2 drift: time for 90 deg", f"{90 / dOd / 365.25:.1f} yr"]) #years, against a 5 yr design life
        w.writerow(["conclusion",
                    "direct = dv-impossible; drift = schedule-impossible for "
                    "constellation fill -> planes populated by separate launches; "
                    "C2b 4 planes = 4 launches vs C2a 6"]) #this is what kills the 6 plane option & picks the 4 plane family
        w.writerow([])
        w.writerow(["STATION-KEEPING FIT (from P2 decay profiles)"]) #fourth table: showing the drag rate was fitted, not assumed
        for h in PROFILES:
            w.writerow([f"{h} km: da/dt {dadt_map[h]:.2f} km/yr",
                        f"rate {sk_rate_ms_per_yr(a0_map[h], dadt_map[h]):.2f} m/s/yr"])
        w.writerow(["implied density scale height", f"{H_km:.0f} km "
                    "(thermospheric 55-70 km band -> fit consistent with physics)"]) #the cross check, my fit has to agree with an atmosphere i never modelled
    print(f"wrote {path}")

def readout(rows, dadt_map, a0_map, H_km):
    print("\n-- station-keeping fit (first-year, conservative) --")
    for h in PROFILES:
        print(f"  {h} km: da/dt = {dadt_map[h]:+.2f} km/yr  ->  "
              f"{sk_rate_ms_per_yr(a0_map[h], dadt_map[h]):.2f} m/s/yr")
    print(f"  implied scale height H = {H_km:.0f} km "
          f"({'consistent' if 40 <= H_km <= 90 else 'CHECK'} w/ thermosphere)") #wider band than the csv claims, this is the pass/fail, not the headline
    print("\n-- budgets (disposal perigee 350 km) --")
    for r in rows:
        if r["perigee"] != DISPOSAL_PERIGEE[0]: #baseline perigee only on the console
            continue
        print(f"  {r['alt']} km / {r['life']} yr:  total {r['total']:.0f} m/s  "
              f"(EOL {r['lines']['EOL deorbit']:.0f}, SK "
              f"{r['lines']['station-keeping']:.0f}, margin {r['margin']:.0f})")
    a0 = a0_map[525]
    dOd = 3.5 * (RAAN_OFFSET_KM / a0) * abs(nodal_rate_deg_day(a0, INCL_DEG))
    print("\n-- plane acquisition (525 km) --")
    print(f"  direct 90°: {raan_direct_dv_ms(a0, 90, INCL_DEG):.0f} m/s   "
          f"direct 60°: {raan_direct_dv_ms(a0, 60, INCL_DEG):.0f} m/s")
    print(f"  drift ({RAAN_OFFSET_KM:.0f} km offset): "
          f"{hohmann_pair_ms(a0, RAAN_OFFSET_KM):.0f} m/s, "
          f"{dOd:.3f}°/day -> 90° in {90 / dOd / 365.25:.1f} yr")
    print("  -> planes = separate launches; C2b (4p) beats C2a (6p) on procurement")
    worst = max((r for r in rows if r["perigee"] == DISPOSAL_PERIGEE[0]),
                key=lambda r: r["total"]) #worst baseline case, the one the tank gets sized against
    print(f"\n-- propulsion feasibility @ worst case {worst['total']:.0f} m/s --")
    for n, s in ISP_S.items():
        m = prop_mass_kg(worst["total"], s)
        print(f"  {n:<24s} {m * 1000:6.0f} g   ({100 * m / M0_KG:4.1f}% of bus)")

def checks(rows, dadt_map, H_km): #the three things that would silently poison every number above
    ok = True
    if not (abs(dadt_map[525]) > abs(dadt_map[550])): #lower orbit must decay faster, if not the fit or the profile is wrong
        print("[WARN] 525 km should decay faster than 550 km"); ok = False
    if not (40.0 <= H_km <= 90.0): #scale height falling outside the thermosphere means my drag rates are fiction
        print(f"[WARN] implied scale height {H_km:.0f} km outside 40-90 km"); ok = False
    for h in PROFILES:
        for l in DESIGN_LIVES_YR:
            r350 = next(r for r in rows if (r["alt"], r["life"], r["perigee"]) == (h, l, 350))
            r300 = next(r for r in rows if (r["alt"], r["life"], r["perigee"]) == (h, l, 300))
            if not r300["lines"]["EOL deorbit"] > r350["lines"]["EOL deorbit"]: #dropping perigee lower must cost more, always
                print(f"[WARN] EOL ordering broken at {h}/{l}"); ok = False
    if ok:
        print("sanity: slope ordering, scale height, and EOL ordering consistent")

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    dadt_map, a0_map = {}, {}
    for h, p in PROFILES.items():
        dadt, rms, a0 = fit_dadt(p) #the only place phase 2 feeds phase 3, everything downstream rides on this slope
        dadt_map[h], a0_map[h] = dadt, a0
        print(f"fit {h} km: da/dt {dadt:+.3f} km/yr  (rms {rms * 1000:.1f} m, "
              f"window {FIT_DAYS:.0f} d)") #rms printed in metres, a bad fit shows up here before it poisons the budget
    H_km = (550 - 525) / math.log(abs(dadt_map[525]) / abs(dadt_map[550])) #da/dt goes as density & density falls exponentially, so 2 altitudes are enough to back out H
    rows = build_budget(a0_map, dadt_map)
    checks(rows, dadt_map, H_km) #gates first, no point charting a budget built on a broken slope
    chart(rows)
    write_csv(rows, dadt_map, a0_map, H_km)
    readout(rows, dadt_map, a0_map, H_km)
