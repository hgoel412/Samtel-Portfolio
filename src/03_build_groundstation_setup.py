import sys
import time
from pathlib import Path
from tqdm import tqdm

src_dir = Path(__file__).parent.resolve()
sys.path.append(str(src_dir))

from common.stk_connect import get_stk_root
from ansys.stk.core.stkobjects import STKObjectType 

MIN_ELV_DEG = 10.0

_CONNECT_TYPE = {
    STKObjectType.FACILITY: "Facility", #A dict lookup for python & Connect Parser connnector
    STKObjectType.TARGET: "Target"
}

GENERAL_GS = [                      #immutable tupples 
    ("GSG_Hawaii", 19.00, -155.50, 0.010),
    ("GSG_Santiago", -33.50, -70.70, 0.520),
    ("GSG_Kourou", 5.20, -52.70, 0.010),
    ("GSG_Madrid", 40.40, -4.20, 0.770),
    ("GSG_Hartebeesthoek", -25.90, 27.70, 1.540),
    ("GSG_Singapore", 1.35, 103.80, 0.015),
    ("GSG_Sydney", -33.80, 151.00, 0.040),
]

SOVEREIGN_GS = [
    ("GSI_Shadnagar", 17.00, 78.20, 0.600),
    ("GSI_Lucknow", 26.90, 80.95, 0.120),
    ("GSI_Bengaluru", 13.00, 77.50, 0.900),
    ("GSI_PortBlair", 11.65, 92.70, 0.015),
]

ASSETS = [
    ("AST_Ladakh", 33.70, 78.70, 4.300),
    ("AST_Siachen", 35.40, 77.10, 5.400),
    ("AST_Tawang", 27.60, 91.90, 3.000),
    ("AST_EEZ_WEST", 15.00, 62.00, 0.000),
    ("AST_EEZ_EAST", 15.00, 87.00, 0.000),
]

def set_min_elevation(root, obj_type, name, deg = MIN_ELV_DEG):
    try:
        root.execute_command(
            f"SetConstraint */{_CONNECT_TYPE[obj_type]}/{name} ElevationAngle Min {deg}" #set constraint inside current scenario in the facility
        ) 
        return True
    except Exception as e:
        print(f"Elevation not set on {name}: {e}")
        return False
    
def make_place(scenario, root, obj_type, name, lat, lon, alt_km):
    if scenario.children.contains(obj_type,name): #replace any existing facility with current one
        scenario.children.unload(obj_type, name)
    obj = scenario.children.new(obj_type, name) #place empty object in tree
    obj.position.assign_geodetic(lat,lon,alt_km) #assign the parameters
    set_min_elevation(root, obj_type, name) #set min elevation of 10 deg
    return obj

def get_or_load_scenario(root, sc_path):
    try:
        if root.current_scenario is not None:
            print("using the current open scenario for building")
            return root.current_scenario #checks for active scenario
    except Exception:
        pass

    print(f"Loading Scenario {sc_path}")
    root.load_scenario(str(sc_path))
    return root.current_scenario

def build_ground_segment():
    print("\n*3 Ground Segment + Assets Building..")
    tic = time.perf_counter()

    engine, root = get_stk_root()

    project_root = src_dir.parent
    sc_path = project_root / "scenario" / "Sovereign_IoT" / "Sovereign_IoT.sc"
    scenario = get_or_load_scenario(root,sc_path)

    root.units_preferences.item("Distance").set_current_unit("km") #set the units in settings

    root.begin_update()

    print("\n Building General GS:")
    for name, lat, lon, alt in tqdm(GENERAL_GS, desc = "General GS", unit = "site"): #loops for building
        make_place(scenario, root, STKObjectType.FACILITY, name, lat, lon, alt)
    
    print("\n Building Sovereign GS:")
    for name, lat, lon, alt in tqdm(SOVEREIGN_GS, desc = "Indian GS", unit = "site"):
        make_place(scenario, root, STKObjectType.FACILITY, name, lat, lon, alt)

    print("\n Building Assets:")
    for name, lat, lon, alt in tqdm(ASSETS, desc = "Assets", unit = "asset"):
        make_place(scenario, root, STKObjectType.TARGET, name, lat, lon, alt)
    
    root.end_update()

    print(f"\n Saving Scenario: {sc_path}")
    root.save()

    print("\n Validation:")
    groups = [ #a list of lists for validation
        ("General GS (Facility)", STKObjectType.FACILITY, GENERAL_GS),
        ("Sovereign GS (Facility)", STKObjectType.FACILITY, SOVEREIGN_GS),
        ("Assets (Target)", STKObjectType.TARGET, ASSETS)
    ]

    all_ok = True
    for label, obj_type, table in groups: #unpacks the list of lists for validation
        present = sum(scenario.children.contains(obj_type, row[0]) for row in table)
        ok = (present == len(table))
        all_ok = all_ok and ok
        print(f" {label:26s}: {present}/{len(table)} in scenario {'OK' if ok else 'MISSING'}")
        for name, lat, lon, alt in table:
            mark = "OK" if scenario.children.contains(obj_type, name) else "MISSING"
            print(f" {name:18s} lat{lat:7.2f} lon{lon:8.2f} alt {alt:5.3f} km [{mark}]")
        assert ok, f"{label}: only {present}/{len(table)} created"
    
    print(f"\n Validation {'PASSED' if all_ok else 'FAILED'}. Min-Elevation: {MIN_ELV_DEG}")

    toc = time.perf_counter()
    print(f"Built everything in {toc - tic:.2f} sec.")
    return engine

if __name__ == "__main__":
    engine = build_ground_segment()
    try:
        engine.shutdown()
    except Exception as e:
        print(f"Shutdown raise(continuing): {e}")
    print("STK Shutdown complete")