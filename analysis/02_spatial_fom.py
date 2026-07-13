import os, csv, math
import numpy as np
import matplotlib
matplotlib.use("Agg") #anti-grain geometry for background saving
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

FOM_DIR = "D:\Samtel-Portfolio\data/raw\Revisit" #stk figure-of-merit grids, one csv per config, a value at every grid point
OUT_DIR = "D:\Samtel-Portfolio\dashboards"
REP_OUT = "D:\Samtel-Portfolio\data\processed"
FOM_MAP = {1: "C1", 2: "C2", 3: "C3", 4: "C4", 5: "SSO"} #stk numbers the FOMs in creation order, mapping them back to my names
CONFIG_LABEL = {"C1": "C1 · 18 sats / 3 pl · 40°",
                "C2": "C2 · 24 sats / 6 pl · 40°",
                "C3": "C3 · 24 sats / 4 pl · 40°",
                "C4": "C4 · 32 sats / 8×4 pl · 40°",
                "SSO": "R_sso · 18 sats / 3 pl · 97.6°"} #panel titles
LINE_COLOR = {"SSO": "#4FC3F7", "C1": "#FFB74D", "C2": "#81C784",
              "C3": "#E57373", "C4": "#BA68C8"} #same palette as phase 1 so the whole chart set reads as one deck

BINS = [0, 15, 30, 60, 95, 190] #legend cut at 1 orbit & 2 orbits, not at round decimal numbers
BIN_COLORS = ["#BA68C8", "#4FC3F7", "#4DB6AC", "#81C784", "#FFD54F", "#E57373"] #purple best -> red worst
ORBIT_MIN = 95.0 #one orbital period at 525 km, the honest yardstick for a revisit gap

ASSETS = { #name -> (lat, lon), same 5 strategic points placed in phase 0
    "EEZ_EAST": (15.00, 87.00), "EEZ_WEST": (15.00, 68.00),
    "Ladakh":   (34.00, 77.50), "Siachen":  (35.42, 77.10),
    "Tawang":   (27.59, 91.87),
}
GSI = {"Bengaluru": (12.97, 77.59), "Lucknow": (26.85, 80.95),
       "PortBlair": (11.62, 92.72), "Shadnagar": (17.10, 78.20)} #indian GS, drawn as markers only, they dont enter the maths here

P1_MAX = { #per-asset MAX revisit out of phase 1, same 10 deg mask, these are the numbers the grid has to bound
    "C1":  {"EEZ_EAST": 212.50, "EEZ_WEST": 212.58, "Ladakh": 9.49,
            "Siachen": 9.80,  "Tawang": 12.75},
    "C2":  {"EEZ_EAST": 18.17,  "EEZ_WEST": 18.17,  "Ladakh": 10.06,
            "Siachen": 9.83,  "Tawang": 12.21},
    "C3":  {"EEZ_EAST": 13.43,  "EEZ_WEST": 13.56,  "Ladakh": 9.49,
            "Siachen": 9.08,  "Tawang": 12.75},
    "C4":  {"EEZ_EAST": 12.44,  "EEZ_WEST": 12.43,  "Ladakh": 5.29,
            "Siachen": 4.89,  "Tawang": 8.54},
    "SSO": {"EEZ_EAST": 152.95, "EEZ_WEST": 152.95, "Ladakh": 158.85,
            "Siachen": 158.04, "Tawang": 161.68},
}
OLD_GRID_MIN = {"C1": 4.331, "C2": 1.174, "C3": 0.0, "C4": 0.0, "SSO": 74.629} #grid minima from the earlier 0 deg run, kept so the 10 deg mask can be proved to have bitten
GATE_TOL = 2.0 #min, slack between a grid cell & a point target, the two conventions never land on the same number
NBHD_DEG = 1.0 #half width of the box searched around an asset to pull its grid value
BELT = (8.0, 37.0) #india strategic belt, the only latitudes this mission actually has to serve

def load_fom(path): #stk writes a preamble above the real table, so DictReader is useless here
    lats, lons, vals = [], [], []
    unit = None
    with open(path, newline="") as f: #safe opening & closing of file
        in_data = False
        for line in f:
            line = line.strip()
            if not in_data:
                if line.startswith('"Latitude'): #the header line is the marker where the real data starts
                    unit = "sec" if "(sec)" in line else "min" #stk exports seconds by default, catching the unit off the header itself
                    in_data = True
                continue #still inside the preamble, back to for loop
            parts = line.split(",")
            if len(parts) != 3: #lat, lon, value; anything else is a footer or summary line
                continue
            try:
                la, lo, v = float(parts[0]), float(parts[1]), float(parts[2])
            except ValueError: #skip the corrupted rows
                continue
            lats.append(la); lons.append(lo); vals.append(v)
    lats, lons, vals = map(np.array, (lats, lons, vals)) #3 flat numpy arrays, one entry per grid point
    if unit == "sec":
        vals = vals / 60.0 #everything in this script lives in minutes
    return lats, lons, vals, unit #grid + the unit it arrived in, so the readout can prove the conversion happened

def nbhd_max(lats, lons, vals, lat0, lon0, half=NBHD_DEG): #worst grid cell inside a +-1 deg box around the asset
    m = (np.abs(lats - lat0) <= half) & (np.abs(lons - lon0) <= half) #boolean mask of the cells sitting in the box
    return float(vals[m].max()) if m.any() else np.nan #max & not mean, because the gate is a worst-case test

def verify(data): #gate 1: the grid around an asset must be at least as bad as the asset itself
    print("\n== ACCEPTANCE GATES (grid must bound P1 asset max, 10°) ==")
    all_ok = True
    for cfg, (la, lo, v, unit) in data.items():
        gmin, gmax, gavg = v.min(), v.max(), v.mean() #whole grid, every latitude & longitude
        print(f"{cfg}: n={v.size}  min {gmin:.2f}  max {gmax:.2f}  "
              f"avg {gavg:.2f} min  [file unit: {unit}]")
        for a, (alat, alon) in ASSETS.items():
            gval = nbhd_max(la, lo, v, alat, alon)
            ref  = P1_MAX[cfg][a] #the phase 1 number for the same asset & same mask
            ok   = gval >= ref - GATE_TOL #grid should bound the point, the tolerance absorbs the convention gap
            all_ok &= ok #ultimate safety check
            flag = "OK " if ok else "FAIL"
            print(f"   {flag} {a:<9s} grid≥ {gval:7.2f}  vs P1 max {ref:7.2f}")
        rose = gmin > OLD_GRID_MIN[cfg] #gate 2: a falsifiable prediction, masking at 10 deg HAS to push the minima up
        all_ok &= rose
        print(f"   {'OK ' if rose else 'FAIL'} grid min rose "
              f"{OLD_GRID_MIN[cfg]:.3f} -> {gmin:.2f}"
              + ("   (0.000 pockets vanished)" if OLD_GRID_MIN[cfg] == 0 else "")) #the fake continuous-coverage cells the 0 deg run was producing
    print("== GATES:", "ALL PASS ==" if all_ok else "FAILURES PRESENT ==")
    return all_ok

def zonal(la, lo, v): #collapse the longitude axis, keep only what latitude does to revisit
    lats = np.unique(la) #one ring per latitude
    zmax = np.array([v[la == x].max() for x in lats]) #worst longitude on that ring
    zavg = np.array([v[la == x].mean() for x in lats]) #ring average, kept for the csv
    return lats, zmax, zavg

def band_above(lats, zmax, thr): #the contiguous |lat| <= 25 band where the zonal max breaks a threshold
    m = zmax > thr
    core = m & (np.abs(lats) <= 25.0) #only chasing the equatorial hole here, the poles are a different story
    if not core.any():
        return None #no hole at this threshold
    idx = np.flatnonzero(core)
    return lats[idx[0]], lats[idx[-1]], float(zmax[core].max()), \
        float(lats[core][int(np.argmax(zmax[core]))]) #band edges, peak value & the latitude it peaks at

def analyze(data):
    out = {}
    print("\n== SPATIAL STRUCTURE (minutes) ==")
    for cfg, (la, lo, v, _) in data.items():
        lats, zmax, zavg = zonal(la, lo, v)
        hole95  = band_above(lats, zmax, ORBIT_MIN) #where the gap grows past one full orbit
        hole150 = band_above(lats, zmax, 150.0) #a harder cut for the deep hole
        belt = (la >= BELT[0]) & (la <= BELT[1]) #india belt mask
        bstats = (v[belt].min(), v[belt].max(), v[belt].mean())
        frac = [(v[belt] <= t).mean() * 100 for t in (15, 30, 60)] #% of the belt served inside each latency class
        out[cfg] = dict(lats=lats, zmax=zmax, zavg=zavg,
                        hole95=hole95, hole150=hole150,
                        belt=bstats, beltfrac=frac)
        h = (f"{hole95[0]:+.1f}°..{hole95[1]:+.1f}°, peak {hole95[2]:.0f} min "
             f"@ {hole95[3]:+.1f}°" if hole95 else "none") #one line description of the hole, or none if the config closed it
        print(f"{cfg}: >1-orbit band: {h}")
        print(f"     India belt {BELT[0]:.0f}-{BELT[1]:.0f}°N: "
              f"min {bstats[0]:.1f} max {bstats[1]:.1f} avg {bstats[2]:.1f} | "
              f"≤15/30/60 min: {frac[0]:.0f}%/{frac[1]:.0f}%/{frac[2]:.0f}%")
    return out

def legend_check(data): #a sanity pass on the legend itself, an empty bin means a wasted colour
    print("\n== RECOMMENDED LEGEND BIN OCCUPANCY (% of grid points) ==")
    edges = BINS + [float("inf")] #open top bin to catch the 190+ tail
    print(f"{'':5s}" + "".join(f"{f'[{int(a)},{int(b) if b < 1e9 else 9999})':>12s}"
                               for a, b in zip(edges[:-1], edges[1:]))) #header row of bin ranges
    for cfg, (la, lo, v, _) in data.items():
        row = [((v >= a) & (v < b)).mean() * 100 for a, b in zip(edges[:-1], edges[1:])] #% of grid points landing in each bin
        print(f"{cfg:5s}" + "".join(f"{x:11.1f}%" for x in row))

def regrid(la, lo, v): #stk grids are ground-uniform so every latitude ring carries its own longitude spacing, pcolormesh needs a rectangle
    lats = np.unique(la)
    lon_t = np.arange(60.25, 95.0, 0.5) #one common longitude axis every ring gets resampled onto
    grid = np.full((lats.size, lon_t.size), np.nan) #blank rectangle, filled row by row
    for i, x in enumerate(lats):
        m = la == x
        ls, vs = lo[m], v[m] #this ring's own longitudes & values
        o = np.argsort(ls)
        ls, vs = ls[o], vs[o] #searchsorted needs them sorted
        j = np.clip(np.searchsorted(ls, lon_t), 0, ls.size - 1) #ring point at or just above each target longitude
        jm = np.clip(j - 1, 0, ls.size - 1) #and the one just below it
        pick = np.where(np.abs(ls[j] - lon_t) <= np.abs(ls[jm] - lon_t), j, jm) #nearest neighbour & not interpolation, i dont want invented values on a gate chart
        grid[i] = vs[pick]
    return lats, lon_t, grid

def chart09(data):
    plt.style.use("dark_background")
    plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
                         "savefig.facecolor": "#0d1117", "font.size": 9}) #github dark shade on every chart
    cmap = ListedColormap(BIN_COLORS) #discrete colours & not a continuous ramp, so the eye reads classes not gradients
    norm = BoundaryNorm(BINS + [10000], cmap.N) #drops each value into its bin
    fig, axes = plt.subplots(1, 5, figsize=(15, 6.2), sharey=True) #one panel per config, latitude axis shared
    for ax, (cfg, (la, lo, v, _)) in zip(axes, data.items()):
        lats, lon_t, g = regrid(la, lo, v)
        im = ax.pcolormesh(lon_t, lats, g, cmap=cmap, norm=norm, shading="nearest") #nearest, the grid is already the truth
        for name, (alat, alon) in ASSETS.items():
            ax.plot(alon, alat, "o", ms=4.5, mfc="none", mec="white", mew=1.1) #hollow circles = assets
        for name, (glat, glon) in GSI.items():
            ax.plot(glon, glat, "^", ms=4.5, mfc="none", mec="#eceff1", mew=1.0) #triangles = indian GS
        ax.set_title(CONFIG_LABEL[cfg], fontsize=8.6)
        ax.set_xlim(60, 95); ax.set_ylim(-40, 40) #cropped to the region that pays
        ax.set_xticks([60, 75, 90]); ax.grid(alpha=0.18)
    axes[0].set_ylabel("latitude (°)") #only the leftmost panel carries the y label, the axis is shared
    for ax in axes:
        ax.set_xlabel("longitude (°)")
    cb = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.015, ticks=BINS) #one bar for all 5 panels, they share a norm
    cb.ax.set_yticklabels(["0", "15", "30", "60", "95 (1 orbit)", "190+ (2 orbits)"]) #ticks named in orbits, that is the language the reader thinks in
    cb.set_label("max revisit over 33 d  (min)")
    fig.suptitle("Worst-case revisit fields — 10° elevation, 33-day window  ·  "
                 "○ assets  △ Indian GS", fontsize=11, fontweight="bold", y=0.99)
    fig.text(0.5, 0.012, "grid: 0.5° lat, ground-uniform lon spacing · "
             "bins anchored to the 95-min orbital period",
             ha="center", fontsize=7.4, color="#78909c")
    out = os.path.join(OUT_DIR, "09_fom_heatmaps.png")
    fig.savefig(out, dpi=160, bbox_inches="tight") #tight box, the shared colorbar hangs outside the axes
    plt.close(fig) #free the memory before the next figure
    print(f"wrote {out}")

def chart10(res):
    plt.style.use("dark_background")
    plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
                         "savefig.facecolor": "#0d1117", "font.size": 10})
    fig, ax = plt.subplots(figsize=(11, 6))
    for cfg, r in res.items():
        ax.plot(r["lats"], r["zmax"], color=LINE_COLOR[cfg], lw=1.8,
                label=CONFIG_LABEL[cfg]) #worst case & not average, this is a gate chart
    ax.axhline(ORBIT_MIN, color="#cfd8dc", ls=":", lw=1.2) #anything above this line is a gap longer than one orbit
    ax.text(-39, ORBIT_MIN * 1.06, "1 orbital period", color="#cfd8dc", fontsize=8)
    ax.axhline(2 * ORBIT_MIN, color="#cfd8dc", ls=":", lw=1.0, alpha=0.7) #the SSO curve lives up here
    ax.text(-39, 2 * ORBIT_MIN * 1.06, "2 periods", color="#cfd8dc", fontsize=8)
    for a, (alat, _) in ASSETS.items():
        ax.axvline(alat, color="#546e7a", lw=0.7, alpha=0.5) #vertical guide at every asset latitude
    ax.text(15, ax.get_ylim()[0] * 1.05 + 4.6, "", fontsize=7)
    ax.set_yscale("log") #SSO sits 2 orders above the rest, a linear axis flattens everything else into the floor
    ax.set_xlabel("latitude (°)   ·   vertical guides = asset latitudes")
    ax.set_ylabel("worst max-revisit across longitudes  (min, log)")
    ax.set_title("Zonal worst-case revisit vs latitude — 10° mask, 33 days",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=8, framealpha=0.15, loc="upper right")
    ax.grid(alpha=0.25, which="both") #both = major & minor, the log axis needs the minor lines to be readable
    ax.set_xlim(-40, 40)
    out = os.path.join(OUT_DIR, "10_fom_latitude_profile.png")
    fig.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(f"wrote {out}")

def write_summary(data, res):
    path = os.path.join(REP_OUT, "spatial_fom_summary.csv")
    with open(path, "w", newline="") as f: #safe opening & closing of file
        w = csv.writer(f)
        w.writerow(["all values MINUTES; per-point files were (sec), normalized"]) #units banner on top of the csv
        w.writerow(["config", "grid_min", "grid_max", "grid_avg",
                    "belt_min", "belt_max", "belt_avg",
                    "belt_pct<=15", "belt_pct<=30", "belt_pct<=60",
                    "hole>1orbit_latlo", "hole_lathi", "hole_peak", "hole_peak_lat"])
        for cfg, (la, lo, v, _) in data.items():
            r = res[cfg]; h = r["hole95"]
            w.writerow([cfg, f"{v.min():.2f}", f"{v.max():.2f}", f"{v.mean():.2f}",
                        f"{r['belt'][0]:.2f}", f"{r['belt'][1]:.2f}",
                        f"{r['belt'][2]:.2f}",
                        *(f"{x:.1f}" for x in r["beltfrac"]),
                        *((f"{h[0]:.2f}", f"{h[1]:.2f}", f"{h[2]:.1f}",
                           f"{h[3]:.1f}") if h else ("", "", "", ""))]) #blanks when the config has no hole to report
        w.writerow([]) #blank row to separate the tables
        w.writerow(["value at asset (neighborhood max, min) vs P1 asset max"]) #second table: the gate evidence, side by side
        w.writerow(["config"] + [x for a in ASSETS for x in (f"{a}_grid", f"{a}_P1")])
        for cfg, (la, lo, v, _) in data.items():
            row = [cfg]
            for a, (alat, alon) in ASSETS.items():
                row += [f"{nbhd_max(la, lo, v, alat, alon):.2f}",
                        f"{P1_MAX[cfg][a]:.2f}"] #grid value & the phase 1 value it has to bound
            w.writerow(row)
    print(f"wrote {path}")

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    data = {}
    for n, cfg in FOM_MAP.items():
        p = os.path.join(FOM_DIR, f"FigureOfMerit{n}_Value_By_Grid_Point.csv")
        la, lo, v, unit = load_fom(p)
        data[cfg] = (la, lo, v, unit) #all 5 grids held in RAM, no interim files on disk
    verify(data) #gates first, no point charting a grid that failed
    res = analyze(data)
    legend_check(data)
    chart09(data)
    chart10(res)
    write_summary(data, res)
