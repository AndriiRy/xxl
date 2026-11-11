"""Переход между стоянками по цилиндрам-маркам (без наводки). python3 t7.py <station/pi> <папка>"""
import sys, os, shutil, math, time, numpy as np
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.chdir(sys.argv[1])
import web, sim_room
d = sys.argv[2]; shutil.rmtree(d, ignore_errors=True)
TG = [(600, 2800, 1150), (3700, 500, 1150), (400, 500, 1150)]   # на стойках: низ 1150, верх 1400 над полом
A = web.App(d, True); A.cfg["sim_targets"] = TG
A.new_project("cyl"); st = A.station(); room = st.ard.room
t0 = time.time(); A.job_scan(); A.job_targets(); t1 = time.time()
A.job_newsetup("S2"); room.set_pose((2800, 2200, 1250), -0.3, 0.7, 137)
A.job_calib(); A.job_scan(); t2 = time.time(); A.job_targets(); t3 = time.time()
m = A.model()
for s in m["setups"]: print(s["name"], {k: (round(v, 2) if isinstance(v, float) else v) for k, v in (s.get("reg") or {}).items()})
c1, c2 = m["rooms"][0]["corners"], m["rooms"][1]["corners"]
e = [min(math.hypot(a["x"] - b["x"], a["y"] - b["y"]) for b in c2) for a in c1]
dz = [min(c2, key=lambda b: math.hypot(a["x"] - b["x"], a["y"] - b["y"]))["ceil"] - a["ceil"] for a in c1]
print("стоянка 2 против 1, углы в плане (мм):", " ".join(f"{x:.1f}" for x in e), "| max", f"{max(e):.1f}")
print("высота потолка S2-S1 (мм):", " ".join(f"{x:+.1f}" for x in dz))
print(f"время: поиск цилиндров S1 {t1 - t0 - 0:.0f} с (вместе со сканом), S2 {t3 - t2:.0f} с (без скана)")
