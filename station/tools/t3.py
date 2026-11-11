import sys, os, shutil, math, numpy as np
sys.path.insert(0, sys.argv[1]); os.chdir(sys.argv[1])
import web, sim_room
d = sys.argv[2]; shutil.rmtree(d, ignore_errors=True)
A = web.App(d, True); A.new_project("floor"); st = A.station(); room = st.ard.room
fz = lambda x, y: sim_room.FLOOR[0]*x + sim_room.FLOOR[1]*y
room.set_pose((1700, 1400, fz(1700, 1400) + 152), 1.8, -1.6, 75)          # на полу, ножки на неровном полу
A.job_mount("floor"); A.job_scan()
print("\n".join(l for l in A.log if "наклон" in l or "индекс" in l or "станция" in l or "S1:" in l or "ОШИБ" in l or "трасса" in l))
m = A.model(); r = m["rooms"][0]
T = [(0,0),(4200,0),(4200,1200),(4450,1200),(4450,2000),(4200,2000),(4200,3400),(2450,3400),(1750,3400),(0,3400),(0,1900),(300,1900),(300,1500),(0,1500)]
off = [c for c in r["corners"] if abs(c["x"]) < 50 and c["y"] > 3000][0]["y"] - 3400
print("углы (с учётом выпуклости AB %.1f):" % off, " ".join(f'{min(math.hypot(q[0]-c["x"], q[1]-(c["y"]-(off if c["y"]>100 else 0))) for q in T):.1f}' for c in r["corners"]))
print("H:", " ".join(f'{c["h"]:.0f}' for c in r["corners"]), "| истина ≈", " ".join(f'{2700 - 0.0005*c["y"] + 0.001*c["x"] - (0.0015*c["x"] + 0.0008*c["y"]):.0f}' for c in r["corners"]))
# быстрый замер: 2 точки
P1, P2 = (1000, sim_room.bump(1000, 1600), 1600), (4200, 2600, 1500)
for P in (P1, P2):
    h, v = room.aim_world(P); st.ard.move(*st.deg2steps((h - st.ard.h_off) % 360, v - st.ard.v_off)); A.job_qpoint("p")
q = A.state()["quick"]; L = math.dist(q[0], q[1]); print(f"P2P: станция {L:.1f}  истина {math.dist(P1, P2):.1f}  ΔH {q[1][2]-q[0][2]:+.1f} (истина {P2[2]-P1[2]:+.1f})")
