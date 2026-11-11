"""Самокалибровка круга Hz: печатный шкив с эксцентриситетом 0,08 мм, эллипсом и биением шкива мотора.
python3 t6.py <station/pi> <папка>"""
import sys, os, shutil, math, numpy as np
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.chdir(sys.argv[1])
import web, sim_room, simmap
d = sys.argv[2]; shutil.rmtree(d, ignore_errors=True)
ECC = {"1": [0.075, 30.0], "2": [0.02, 70.0], "3": [0.006, 200.0], "12": [0.025, 10.0]}   # град: e=0,08 мм на R61; эллипс; биение 16T 0,027 мм


def corners_err(A):
    r0 = A.model()["rooms"][0]; to_w, _ = simmap.maps(r0)
    return np.array([np.min(np.linalg.norm(simmap.TW - to_w([c["x"], c["y"], 0])[:2], axis=1)) for c in r0["corners"]])


A = web.App(d, True); A.cfg["sim_hz_ecc"] = ECC
A.new_project("before"); A.job_scan(); e0 = corners_err(A)
print(f"без поправки: углы комнаты max {e0.max():.1f} мм, среднее {e0.mean():.1f} мм")
st = A.st; room = st.ard.room; O, AZ = room.O.copy(), sim_room.AZ
for k, (dA, dx, dy) in enumerate([(0, 0, 0), (83, 30, 20), (171, -25, 35), (262, 10, -30)]):
    room.set_pose(O + [dx, dy, 0], sim_room.TX, sim_room.TY, AZ + dA); A.job_hzcal_pose()
A.job_hzcal_solve()
print("\n".join(l for l in A.log if "круг Hz:" in l and ("СКО" in l)))
# сравнение найденной ошибки с истинной (кадр счётчика: 0 = метка)
lin = np.arange(0, 360, 1.0); tru = np.array([st.ard._err(x + st.ard.h_off) for x in lin]); fit = np.array([st.hz_corr(x) for x in lin])
print(f"ошибка круга: была ±{np.abs(tru - tru.mean()).max():.4f}°, осталась ±{np.abs((tru - tru.mean()) - (fit - fit.mean())).max():.4f}°")
room.set_pose(O, sim_room.TX, sim_room.TY, AZ)
A.new_project("after"); A.job_scan(); e1 = corners_err(A)
print(f"с поправкой: углы комнаты max {e1.max():.1f} мм, среднее {e1.mean():.1f} мм")
