import sys, os, time, json, math, numpy as np
sys.path.insert(0, sys.argv[1]); os.chdir(sys.argv[1])
import web, sim_room
A = web.App(sys.argv[2], True); A.project = A.projects()[0]
st = A.station(); room = st.ard.room
REFS = {"1": (1000, sim_room.bump(1000, 1600), 1600), "2": (4200, 2600, 1500), "3": (1000, 3400, 2000)}
def aim(P):
    h, v = room.aim_world(P); st.ard.move(*st.deg2steps(h - st.ard.h_off, v - st.ard.v_off))
for k, P in REFS.items(): aim(P); A.job_ref(k)
t = time.time(); A.job_level(900, 0, 360, 0.5); print("level s", round(time.time() - t, 1))
A.job_surface("A-B", "wall", 100, 2400, 600, 100); A.job_surface("A-B", "floor", 0, 0, 600, 100)
A.job_newsetup("S2"); room.set_pose((2800, 2200, 1250), -0.3, 0.7, 137)
A.job_calib()
for k, P in REFS.items(): aim(P); A.job_ref(k)
A.job_scan()
print("\n".join(l for l in A.log if "S1" in l or "S2" in l or "уровень" in l.lower() or "наклон" in l or "индекс" in l or "ОШИБ" in l)[-3000:])
m = A.model()
for s in m["setups"]: print(s["name"], s.get("reg"))
for lv in m["levels"]: print("уровень", lv["h"], "dz", round(lv["dz_max"], 2), [(p["type"], round(p["len"]), round(p.get("r", 0))) for p in lv["parts"]], lv["features"])
for sf in m["surfaces"]: print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in sf.items()})
c1 = m["rooms"][0]["corners"]; c2 = m["rooms"][1]["corners"]
e = [min(math.hypot(a["x"] - b["x"], a["y"] - b["y"]) for b in c2) for a in c1]
print("стоянка 2 против 1, углы (мм):", " ".join(f"{x:.1f}" for x in e))
print("H углов S2-S1:", " ".join(f"{min(c2, key=lambda b: math.hypot(a['x']-b['x'], a['y']-b['y']))['ceil'] - a['ceil']:+.1f}" for a in c1))
