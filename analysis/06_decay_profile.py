import os, csv
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use("Agg") #anti-grain geometry for background saving
import matplotlib.pyplot as plt

PROFILES = [ #(csv path, label, expected life yr, colour), only the two design window edges
    ("D:\Samtel-Portfolio\data/raw\Lifetime\Lifetime_Analysis_525km.csv", "525 km", 8.6,  "#4FC3F7"),
    ("D:\Samtel-Portfolio\data/raw\Lifetime\Lifetime_Analysis_550km.csv", "550 km", 10.3, "#FFB74D"),
]
OUT_DIR = "D:\Samtel-Portfolio\dashboards"
FMT = "%d %b %Y %H:%M:%S.%f" #to match stk format
ASSUMPTIONS = ("3U CubeSat · m 4 kg · Cd 2.2 · A 0.03 m² (B≈61 kg/m²) · Jacchia-Roberts · "
               "CSSI predicted flux (sigma=0) · epoch 1 Jul 2026 · i 40° circular · "
               "unattended decay from launch epoch — no station-keeping") #printed under the chart, a decay curve with no stated atmosphere is worthless

def load(path): #stk lifetime time history, exported at a 10 orbit cadence
    t, apo, peri = [], [], []
    with open(path, newline="") as f: #safe opening & closing of file
        for d in csv.DictReader(f):
            ts = (d.get("Time (UTCG)") or "").strip()
            if not ts: #skip the blank tail rows stk leaves behind
                continue
            try:
                tt = datetime.strptime(ts, FMT)
            except ValueError: #skip the corrupted time rows
                continue
            t.append(tt)
            apo.append(float(d["Height of Apogee (km)"])) #tracking both apsides, that is what shows the orbit dies circular
            peri.append(float(d["Height of Perigee (km)"]))
    t0 = t[0]
    yrs = np.array([(x - t0).total_seconds() / (365.25 * 86400.0) for x in t]) #julian years since epoch, the x axis
    return t0, t[-1], yrs, np.array(apo), np.array(peri) #first & last date kept so the gate can be printed as real calendar dates

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    plt.style.use("dark_background")
    plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
                         "savefig.facecolor": "#0d1117", "font.size": 10}) #github dark shade on every chart
    fig, ax = plt.subplots(figsize=(11, 6))

    for path, label, expect, color in PROFILES:
        t0, t1, yrs, apo, peri = load(path)
        life = yrs[-1] #the profile just runs until the sat is gone, so its own length IS the lifetime
        gate = "OK" if abs(life - expect) <= 0.1 else "MISMATCH" #safety check, this curve must reproduce the phase 2 table number
        print(f"{label}: {t0:%d %b %Y} -> {t1:%d %b %Y}  life {life:.2f} yr "
              f"(table {expect}) [{gate}]  final perigee {peri[-1]:.0f} km  "
              f"samples {len(yrs)}")
        ax.plot(yrs, apo,  color=color, lw=1.6, label=f"{label} — apogee / perigee") #solid = apogee
        ax.plot(yrs, peri, color=color, lw=1.0, ls=":") #dotted = perigee, same colour, they ride together the whole way down
        ax.annotate(f"{life:.1f} yr\n({t1:%b %Y})",
                    xy=(yrs[-1], peri[-1]), xytext=(yrs[-1] - 1.15, peri[-1] + 150),
                    color=color, fontsize=9, ha="center",
                    arrowprops=dict(arrowstyle="-", color=color, lw=0.9)) #label pulled left & up, the two plunges nearly overlap

    ax.set_xlabel("Years since epoch (1 Jul 2026)")
    ax.set_ylabel("Altitude  (km)")
    ax.set_title("Unattended decay profiles — design-window altitudes",
                 fontsize=12, fontweight="bold")
    fig.text(0.5, 0.935,
             "slow drag fade, then terminal plunge · eccentricity stays ≤0.003 — "
             "the orbit dies circular · disposal is an altitude decision",
             ha="center", fontsize=8.5, color="#90a4ae") #the takeaway: nothing can be done at end of life except pick the altitude at the start
    ax.set_ylim(0, 600) #floor at 0, the curve has to be seen hitting the ground
    ax.set_xlim(left=0)
    ax.legend(fontsize=8.5, framealpha=0.15, loc="lower left") #lower left is the only empty corner, both curves plunge on the right
    ax.grid(alpha=0.25)
    fig.text(0.5, 0.012, ASSUMPTIONS, ha="center", fontsize=7.2, color="#78909c")
    fig.tight_layout(rect=[0, 0.035, 1, 0.925]) #headroom for the takeaway line, footroom for the assumptions strip
    out = os.path.join(OUT_DIR, "06_decay_profile_design_window.png")
    fig.savefig(out, dpi=160)
    plt.close(fig) #free the memory before the next figure
    print(f"wrote {out}")

if __name__ == "__main__":
    main()
