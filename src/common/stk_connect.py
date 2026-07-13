from ansys.stk.core.stkdesktop import STKDesktop

def get_stk_root(visible = True):
    print("[Initializing..] STK 13 Booting Up. ")
    engine = STKDesktop.start_application(visible= visible) #launches stk
    root = engine.root #AgSTKObjectRoot

    root.units_preferences.item("DateFormat").set_current_unit("UTCG") #setting units
    print("STK Successfully Connected....")

    return engine, root

if __name__ == "__main__":
    eng, root_obj = get_stk_root(visible= True)
    print("Test Successful: Shutting down")

    try:
        eng.shutdown()
    except Exception as e:
        print(f"Shutdown raised (continuing): {e}")
    print("Shutdown Complete!")