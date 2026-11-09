"""Виртуальная кухня для --sim. Мир: мм, Z вверх, угол (0,0) на полу.
AB (y=0)  — стена под кухню: выпуклость 4 мм + завал 2 мм/м.
BC (x=W)  — ниша 800 x 1200, глубина 250, низ 850.
CD (y=D)  — полукруглый выступ R350 (центр 2100, D), на всю высоту.
DA (x=0)  — пилястра 400 x 300.
Пол и потолок с уклоном. Штатив наклонён, азимут произвольный, индекс V с ошибкой,
акселерометр со смещением нуля — всё это станция должна найти сама."""
import math
import numpy as np

W, D = 4200.0, 3400.0
FLOOR = (0.0015, 0.0008, 0.0)                 # z = a x + b y + c
CEIL = (0.0010, -0.0005, 2700.0)
NI = dict(y0=1200.0, y1=2000.0, z0=850.0, z1=2050.0, dep=250.0)
ARC = dict(cx=2100.0, cy=D, r=350.0)
PIL = dict(y0=1500.0, y1=1900.0, dep=300.0)
O = np.array([1800.0, 1300.0, 1350.0])        # центр станции
TX, TY, AZ = 0.6, -0.4, 20.0                  # наклон штатива, азимут нуля Hz (град)
V0_TRUE = 0.05                                # ошибка индекса V
IMU_BIAS = np.array([0.004, -0.006])          # смещение нуля акселерометра (~0,3°)
SIGMA_D = 1.0


def Rx(a): a = math.radians(a); return np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
def Ry(a): a = math.radians(a); return np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
def Rz(a): a = math.radians(a); return np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])


def bump(x, z):                               # неровность стены AB, + = в комнату
    return 4.0*math.sin(math.pi*x/W)*math.sin(math.pi*z/2700) + 0.002*(z - 1350)


class Room:
    def __init__(self, seed=1):
        self.rng = np.random.default_rng(seed); self.set_pose(O, TX, TY, AZ)
        Z0, Z1 = -300.0, 3100.0
        q = []                                                  # (p0, p1, p2, p3, tag)
        def vq(a, b, z0=Z0, z1=Z1, tag=0):
            q.append(([a[0], a[1], z0], [b[0], b[1], z0], [b[0], b[1], z1], [a[0], a[1], z1], tag))
        def hq(x0, x1, y0, y1, z): q.append(([x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z], 0))
        vq((0, 0), (W, 0), tag=1)
        vq((W, 0), (W, NI["y0"])); vq((W, NI["y1"]), (W, D))
        vq((W, NI["y0"]), (W, NI["y1"]), Z0, NI["z0"]); vq((W, NI["y0"]), (W, NI["y1"]), NI["z1"], Z1)
        xb = W + NI["dep"]
        vq((xb, NI["y0"]), (xb, NI["y1"]), NI["z0"], NI["z1"])
        vq((W, NI["y0"]), (xb, NI["y0"]), NI["z0"], NI["z1"]); vq((W, NI["y1"]), (xb, NI["y1"]), NI["z0"], NI["z1"])
        hq(W, xb, NI["y0"], NI["y1"], NI["z0"]); hq(W, xb, NI["y0"], NI["y1"], NI["z1"])
        cx, cy, r = ARC["cx"], ARC["cy"], ARC["r"]
        vq((W, D), (cx + r, D)); vq((cx - r, D), (0, D))
        th = np.linspace(0, -math.pi, 181)
        P = [(cx + r*math.cos(t), cy + r*math.sin(t)) for t in th]
        for a, b in zip(P[:-1], P[1:]): vq(a, b)
        vq((0, D), (0, PIL["y1"])); vq((0, PIL["y0"]), (0, 0))
        p = PIL["dep"]
        vq((0, PIL["y1"]), (p, PIL["y1"])); vq((p, PIL["y1"]), (p, PIL["y0"])); vq((p, PIL["y0"]), (0, PIL["y0"]))
        T = []; tags = []
        for a, b, c, d, tag in q:
            T += [(a, b, c), (a, c, d)]; tags += [tag, tag]
        T = np.array(T, float)
        self.V0, self.E1, self.E2, self.tag = T[:, 0], T[:, 1] - T[:, 0], T[:, 2] - T[:, 0], np.array(tags)

    def set_pose(self, o, tx, ty, az):
        """Перенос станции (новая стоянка): точка, наклон штатива, азимут нуля Hz."""
        self.O = np.array(o, float); self.Rt = Ry(ty) @ Rx(tx); self.Rw = Rz(az) @ self.Rt

    def aim_world(self, P):
        """Только для теста: Hz, V на точку мира (как если бы оператор навёл луч на марку)."""
        q = self.Rw.T @ (np.asarray(P, float) - self.O); q /= np.linalg.norm(q)
        return math.degrees(math.atan2(q[1], q[0])) % 360, math.degrees(math.asin(q[2]))

    def ray(self, o, d):
        P = np.cross(d, self.E2); det = np.einsum("ij,ij->i", self.E1, P)
        ok = np.abs(det) > 1e-9; inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
        Tv = o - self.V0; u = np.einsum("ij,ij->i", Tv, P)*inv
        Q = np.cross(Tv, self.E1); v = (Q @ d)*inv; t = np.einsum("ij,ij->i", self.E2, Q)*inv
        ok &= (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 1e-6)
        tw = np.where(ok, t, np.inf); k = int(np.argmin(tw)); t = tw[k]
        for a, b, c in (FLOOR, CEIL):
            den = d[2] - a*d[0] - b*d[1]
            if abs(den) > 1e-12:
                tp = (a*o[0] + b*o[1] + c - o[2]) / den
                if 1e-6 < tp < t: t, k = tp, -1
        if k >= 0 and self.tag[k] == 1 and abs(d[1]) > 1e-6:      # неровная стена AB
            for _ in range(3):
                p = o + t*d; t = (bump(p[0], p[2]) - o[1]) / d[1]
        return t

    def measure(self, hz, v):
        h, e = math.radians(hz), math.radians(v)
        di = np.array([math.cos(e)*math.cos(h), math.cos(e)*math.sin(h), math.sin(e)])
        return float(self.ray(self.O, self.Rw @ di) + self.rng.normal(0, SIGMA_D))

    def imu(self, hz, v=0.0):
        """MPU6050 в голове: X — по лучу, Y — вдоль оси V, Z — «вверх» головы. v — истинный угол V прибора."""
        u = self.Rt.T @ np.array([0, 0, 1.0]); h, e = math.radians(hz), math.radians(v)
        eb = np.array([math.cos(e)*math.cos(h), math.cos(e)*math.sin(h), math.sin(e)]); ea = np.array([-math.sin(h), math.cos(h), 0])
        sx = u @ eb + IMU_BIAS[0] + self.rng.normal(0, 2e-5); sy = u @ ea + IMU_BIAS[1] + self.rng.normal(0, 2e-5)
        return np.array([sx, sy, math.sqrt(max(0, 1 - sx*sx - sy*sy))])
