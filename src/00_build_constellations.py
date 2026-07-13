import sys
import time
import math
from pathlib import Path
from tqdm import tqdm

src_dir = Path(__file__).parent.resolve()
sys.path.append(str(src_dir)) # adding current folder to the system path

from common.stk_connect import get_stk_root 
from ansys.stk.core.stkobjects import STKObjectType, PropagatorType, CoordinateSystem

MU_Earth = 398600.4418 #km3/s2
RE_Earth = 6378.137 #km

def create_satellite(scenario, root, name, sma, ecc, inc, arg_p, raan, ma):
    if scenario.children.contains(STKObjectType.SATELLITE, name):
        scenario.children.unload(STKObjectType.SATELLITE, name)

    sat = scenario.children.new(STKObjectType.SATELLITE, name)
    sat.set_propagator_type(PropagatorType.J4_PERTURBATION) #J4 chosen for short term analysis as drag/SRP do not move access geometry enough to go for HPOP 
    prop = sat.propagator
    prop.initial_state.representation.assign_classical(
        CoordinateSystem.J2000, sma, ecc, inc, arg_p, raan, ma
    )
    prop.propagate()

def set_color(root,sat_name, color_name):
    try:
        root.execute_command(f"Graphics */Satellite/{sat_name} SetColor {color_name}") # to colour by plane for easier visualization
    except:
        pass

def build_constellation():
    print("\n [PHASE 0 STARTS..] \n Initiation Scenario")
    tic = time.perf_counter() #uses the execution time of script

    engine, root = get_stk_root()

    root.execute_command('New / Scenario Sovereign_IoT') #connect command and scenario name
    scenario = root.current_scenario #Object model command to hold the scenario in python

    start_t = "1 Jul 2026 00:00:00.000" # Scenario start & stop times
    stop_t = "3 Aug 2026 00:00:00.000"
    root.execute_command(f'SetAnalysisTimePeriod * "{start_t}" "{stop_t}"')

    configs = [
        {"name": "R_SSO", "N": 18, "P":3, "F": 1, "i": 97.6, "alt": 525},# SSO with 3 planes and 18 sats
        {"name": "C1", "N": 18, "P":3, "F": 1, "i": 40, "alt": 525}, # inclined with 3 planes
        {"name": "C2", "N": 24, "P":6, "F": 1, "i": 40, "alt": 525}, # 24 sats inclined with 6 planes
        {"name": "C3", "N": 24, "P":4, "F": 1, "i": 40, "alt": 525}, # 24 sats inclined with 4 planes
        {"name": "C4", "N": 32, "P":4, "F": 1, "i": 40, "alt": 525} # 32 sats inclined with 4 planes
    ]

    for cfg in configs:
        dropped = cfg["N"] - (cfg["N"] // cfg["P"]) * cfg["P"]
        assert dropped == 0, (
            f'{cfg["name"]}: N = {cfg["N"]} not divisible by P = {cfg["P"]} '
            f'-> {dropped} satellites would be slightly dropped.'  
        )

    print("\n Putting Walker Delta Configurations")
    root.begin_update() # freezes for all constellations and to recalculate the entire object tree at the end

    colors = ["Red", "Cyan", "Yellow", "Green", "Magenta", "Orange"]
    built = {}

    for config in tqdm(configs, desc = "Building Constellations", unit = "config"):
        cfg_name = config["name"] #current configuration iteration

        sma = RE_Earth + config["alt"]
        ecc = 0.0001 # near 0
        arg_p = 0
        inc = config['i'] 
        t = config["N"] #total sats
        p = config["P"] #planes
        f = config["F"] #phasing

        sats_per_plane = t // p 
        raan_spacing = 360.0/p
        in_plane_spacing = 360.0 / sats_per_plane #mean anamoly
        phase_offset = (f*360.0)/t 

        count = 0

        for p_idx in range(p): #iterating planes of the constellation
            raan = p_idx*raan_spacing 
            plane_color = colors[p_idx % len(colors)] #each plane to have specific colour

            for s_idx in range(sats_per_plane): #iterating the sats in each plane with phasing
                ma = (s_idx*in_plane_spacing) + (p_idx * phase_offset)
                ma = ma%360.0

                sat_name = f"{cfg_name}_P{p_idx+1}_S{s_idx+1}"

                create_satellite(scenario, root, sat_name, sma, ecc, inc, arg_p, raan, ma)
                set_color(root, sat_name, plane_color)
                count = count + 1
        built[cfg_name] = count
    root.end_update() #build the tree of simulation

    project_root = src_dir.parent
    scenario_name = "Sovereign_IoT"
    scenario_dir = project_root / "scenario" / scenario_name #estalbilsing my scenario
    scenario_dir.mkdir(parents=True, exist_ok = True)

    save_path = scenario_dir / f"{scenario_name}.sc" 
    print(f"\nSaving Scenario at : {save_path}")
    root.save_as(str(save_path.resolve())) #to avoid blank spaces in scenario name since STK doesnt accept spaces

    print("\n Validation Checks:")
    all_ok = True

    for config in configs:
        name, t, p = config["name"], config["N"], config["P"]
        sma = RE_Earth + config["alt"]
        sats_per_plane = t//p
        period_min = 2.0*math.pi*math.sqrt(sma**3 / MU_Earth) / 60.0 #kepler's 3rd law

        first_name = f"{name}_P1_S1"
        last_name = f"{name}_P{p}_S{sats_per_plane}"
        endpoints_ok = (
            scenario.children.contains(STKObjectType.SATELLITE, first_name) 
            and scenario.children.contains(STKObjectType.SATELLITE, last_name) #a safety check for 1st & last sat in each constellation
        )
        raan_set = sorted({round((j*360.0/p)%360.0, 1) for j in range(p)}) #just to read the sat & raan
        count_ok = (built[name] == t)
        period_ok = (92.0 <= period_min <= 98.0) #safety check for 525 km sat time period
        ok = count_ok and endpoints_ok and period_ok
        all_ok = all_ok and ok #ultimate safety check
 
        print(
            f"  {name:5s} | built {built[name]:>2}/{t:<2} {'OK' if count_ok else 'MISMATCH':8s}"
            f" | endpoints {'OK' if endpoints_ok else 'MISSING':7s}"
            f" | period {period_min:5.1f} min {'OK' if period_ok else 'CHECK':5s}"
            f" | i={config['i']}deg | RAAN {raan_set}"
        )
        assert count_ok, f"{name}: built {built[name]}, expected {t}"
        assert endpoints_ok, f"{name}: endpoint satellites missing from scenario"
        assert period_ok, f"{name}: period {period_min:.1f} min outside 92-98 min band"
    
    print(f"\nValidation {'PASSED' if all_ok else 'FAILED'}.")
 
    toc = time.perf_counter()
    print(f"PHASE 0 COMPLETE in {toc - tic:.2f} s.")

    return engine

if __name__ == "__main__":
    engine = build_constellation()
    engine.shutdown()
    print("Shut Down Of STK Complete")