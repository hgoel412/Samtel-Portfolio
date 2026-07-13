import os, csv
import numpy as np
import matplotlib
matplotlib.use("Agg") #anti-grain geometry for background saving
import matplotlib.pyplot as plt

CSV_PATH = "D:\Samtel-Portfolio\data/raw\Lifetime\Lifetime.csv" #the record grid filled from the STK Lifetime GUI runs
OUT_DIR = "D:\Samtel-Portfolio\dashboards"
RULE_YR = 5.0 #post mission disposal rule, the only hard number the regulator cares about
DESIGN_BAND = (525, 550) #design window carried over from phase 1, shaded on the chart
ASSUMPTIONS = ("3U CubeSAT · m 4 kg · Cd 2.2 · A 0.03 sqm (B=61 kg/sqm) · Jacchia-Roberts ·"
               "CSSI predicted flux (sig = 0) · epoch 1 Jul 2026 · "
               "decay alt 65 km · J4 mean elements · rotating atmosphere ON ·"
               "lifetimes from launch epoch") #printed under the chart, an uncited lifetime number is worthless

def load(path):
    rows = []
    with open(path, newline="") as f: #safe opening & closing of file
        for d in csv.DictReader(f): #this csv i wrote myself so the headers are clean, DictReader is safe here
            rows.append(dict(
                alt = float(d["Altitude_km"]),
                long_ = float(d["Life_Minus2Sigma_yr"]), #low flux -> thin atmosphere -> sat hangs around the LONGEST
                nom = float(d["Life_Nominal_yr"]),
                short = float(d["Life_Plus2Sigma_yr"]), #high flux -> puffed up atmosphere -> dies SOONEST
                call = d["Disposal_Call"].strip(),
                a02 = float(d["Area_0.02_yr"]), #bare tumbling body, least drag, longest life
                a045 = float(d["Area_0.045_yr"]), #high drag case, the passive lever
                a03 = float(d["Area_0.03_yr"]), #the design area, same case as nominal
            ))
    rows.sort(key=lambda r: r["alt"]) #altitude ascending so the chart doesnt zigzag
    return rows

def sanity(rows): #every ordering physics demands, checked before a single pixel is plotted
    ok = True
    for r in rows:
        if not (r["short"] <= r["nom"] <= r["long_"]): #high flux life under nominal under low flux life, no exceptions
            print(f"[WARN] sigma ordering broken at {r['alt']:.0f} km"); ok = False
        if not (r["a045"] <= r["a03"] <= r["a02"]): #more area = more drag = shorter life
            print(f"[WARN] area ordering broken at {r['alt']:.0f} km"); ok = False
        if abs(r["a03"] - r["nom"]) > 1e-9: #A=0.03 IS the nominal case, the two columns must be the same number
            print(f"[WARN] A=0.03 column != nominal at {r['alt']:.0f} km"); ok = False
        rule_call = "Naturally Compliant" if r["long_"] <= RULE_YR else "Requires EOL Burn" #judged on the LONGEST life, never the nominal, that is the pessimistic edge
        if rule_call != r["call"]: #catches a mis-typed call in the GUI record grid
            print(f"[WARN] call mismatch at {r['alt']:.0f} km: "
                  f"CSV says '{r['call']}', -2sigma says '{rule_call}'"); ok = False
    alts  = [r["alt"] for r in rows]
    noms  = [r["nom"] for r in rows]
    if any(b <= a for a, b in zip(noms, noms[1:])): #life must strictly climb with altitude
        print("[WARN] nominal life not monotonic in altitude"); ok = False
    if ok:
        print("sanity: all orderings, monotonicity, and disposal calls consistent")
    return ok #ultimate safety check

def chart(rows):
    os.makedirs(OUT_DIR, exist_ok=True)
    alt   = np.array([r["alt"]   for r in rows]) #unpacking the dicts into flat arrays for plotting
    nom   = np.array([r["nom"]   for r in rows])
    long_ = np.array([r["long_"] for r in rows])
    short = np.array([r["short"] for r in rows])
    a02   = np.array([r["a02"]   for r in rows])
    a045  = np.array([r["a045"]  for r in rows])

    plt.style.use("dark_background")
    plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#0d1117",
                         "savefig.facecolor": "#0d1117", "font.size": 10}) #github dark shade on every chart
    fig, ax = plt.subplots(figsize=(11, 6))

    ax.axvspan(*DESIGN_BAND, color="#ffffff", alpha=0.06) #faint band over 525-550, where the architecture actually lives
    ax.text(np.mean(DESIGN_BAND), ax.get_ylim()[1], "", ha="center")

    ax.fill_between(alt, short, long_, color="#4FC3F7", alpha=0.22,
                    label="±2sigma predicted solar flux") #the band is solar flux uncertainty, not model error
    ax.plot(alt, nom, "-o", color="#4FC3F7", lw=2, ms=5,
            label="nominal  (A=0.03 m², B≈61)")

    ax.plot(alt, a02,  "--s", color="#81C784", lw=1.4, ms=4,
            label="A=0.02 m²  (B≈91, bare tumbling)") #drag area bracket, dashed so it never reads as a prediction
    ax.plot(alt, a045, "--^", color="#FFB74D", lw=1.4, ms=4,
            label="A=0.045 m²  (B≈40, high drag)")

    ax.axhline(RULE_YR, color="#E57373", lw=1.6, ls=":") #the 5 yr line, everything above it needs a burn
    ax.text(alt[-1] - 4, RULE_YR + 0.45, "5-yr disposal rule", color="#E57373",
            fontsize=8.5, ha="right", va="bottom")

    for r in rows:
        if r["long_"] <= RULE_YR: #compliance judged on the upper band edge, the worst case for disposal
            ax.annotate("naturally compliant\n(−2sigma≤ 5 yr)",
                        xy=(r["alt"], r["long_"]), xytext=(r["alt"] + 8, r["long_"] + 2.5),
                        color="#81C784", fontsize=8,
                        arrowprops=dict(arrowstyle="-", color="#81C784", lw=0.8))
    ax.text(np.mean(DESIGN_BAND), max(long_.max(), a02.max()) * 0.97,
            "design\nwindow", ha="center", va="top", color="#cfd8dc", fontsize=8.5) #label pinned to the tallest curve so it never collides

    ax.set_xlabel("Circular orbit altitude  (km)   ·   i = 40°")
    ax.set_ylabel("Orbital lifetime  (years)")
    ax.set_title("Orbital lifetime vs altitude — decay & disposal compliance",
                 fontsize=12, fontweight="bold")
    fig.text(0.5, 0.935,
             "upper band edge (-2sigma, low flux) judges disposal · "
             "lower edge (+2sigma) judges service worst-case",
             ha="center", fontsize=8.5, color="#90a4ae") #the reading rule spelt out, the band is easy to read backwards
    ax.legend(fontsize=8, framealpha=0.15, loc="upper left")
    ax.grid(alpha=0.25)
    fig.text(0.5, 0.012, ASSUMPTIONS, ha="center", fontsize=7.2, color="#78909c")
    fig.tight_layout(rect=[0, 0.035, 1, 0.925]) #headroom for the reading rule, footroom for the assumptions strip
    out = os.path.join(OUT_DIR, "05_lifetime_vs_altitude.png")
    fig.savefig(out, dpi=160)
    plt.close(fig) #free the memory before the next figure
    print(f"wrote {out}")

def readout(rows):
    print("\nalt   -2sigma   nom    +2sigma   disposal (judged on -2σ)")
    for r in rows:
        print(f"{r['alt']:>4.0f}  {r['long_']:>5.1f}  {r['nom']:>5.1f}  "
              f"{r['short']:>5.1f}   {r['call']}")
    lever = [r for r in rows if r["a045"] <= RULE_YR and r["long_"] > RULE_YR] #altitudes that fail at the design area but pass on drag alone
    for r in lever:
        print(f"\nlever: {r['alt']:.0f} km non-compliant at A=0.03 "
              f"but A=0.045 gives {r['a045']:.1f} yr (nominal sigma) — "
              f"passive drag augmentation reaches compliance without propulsion") #the whole point of the bracket: a sail is cheaper than a thruster

if __name__ == "__main__":
    rows = load(CSV_PATH)
    sanity(rows) #gates first, no point charting a table that contradicts itself
    chart(rows)
    readout(rows)
