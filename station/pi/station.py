#!/usr/bin/env python3
"""Управление станцией с Raspberry Pi 3/4.
Arduino (моторы) — USB; лазерный модуль — UART Pi (GPIO14 TX -> RX модуля, GPIO15 RX <- TX модуля, 3,3 В).

  python3 station.py sniff [бод ...]       # перехват UART внутри ручного дальномера
  python3 station.py probe                 # сырой ответ дальномера (подбор протокола по даташиту)
  python3 station.py measure -n 20         # серия замеров: среднее, СКО
  python3 station.py jog H 1000            # ручной ход (H|V, микрошаги)
  python3 station.py calrev                # калибровка шагов на оборот Hz по метке на стене
  python3 station.py scan -o scan.json     # профиль стен + пол/потолок -> scan.json
  python3 station.py scan --dxf room.dxf   # то же + сразу DXF (scan2dxf.py рядом)
  python3 station.py photos --dxf room.dxf # фото всех стен по room_geom.json -> развёртки в масштабе -> в DXF
  python3 station.py camcal                # калибровка камеры: луч наведён в центр чёрного кружка на стене
  добавить --sim к любой команде — работа без железа (виртуальная комната 4000x3200)
"""
import argparse, json, math, os, re, statistics, subprocess, sys, time
import numpy as np

CFG_DEFAULT = {
    "arduino": {"port": "/dev/ttyUSB0", "baud": 115200},
    "laser": {
        "port": "/dev/serial0", "baud": 19200, "timeout": 3.0,
        "cmd_hex": "",                # команда одиночного замера из даташита, напр. "aa 00 00 20 00 01 00 00 21"
        "mode": "ascii",              # ascii: число из ответа по regex | binary: байты offset/length
        "regex": r"(\d+\.\d+|\d+)", "scale": 1000.0,      # ascii: метры -> мм (scale=1 если ответ в мм)
        "offset": 6, "length": 4, "endian": "big",         # binary: поле расстояния, scale: ед. -> мм
        "trigger_gpio": None,         # ручной дальномер: GPIO, замыкающий кнопку через PC817 (напр. 17)
        "presses": 1, "press_ms": 150, "gap_ms": 400,      # сколько нажатий нужно для замера
    },
    "steps_per_rev_hz": 59323,        # 3200 мкш * (120,5/6,5); уточнить командой calrev
    "steps_per_rev_v": 34708,         # 3200 * (70,5/6,5)
    "v_min_deg": -45.0,               # ниже луч упирается в барабан/корпус; исключение — отвес (-90° через полую ось)
    "settle_s": 0.3,
    "avg": 2,                          # замеров на точку
    "profile_step_deg": 0.5,
    "profile_levels_deg": [0.0],       # доп. уровни профиля, напр. [-15, 0, 15]
    "plane_v_deg": [35, 50, 70, -25, -32, -40, -45], "plane_hz_step_deg": 20,   # ниже -45° луч упирается в корпус
    "mount": "tripod",                 # tripod | floor | table — установка станции
    "mounts": {
        "tripod": {"plane_v_deg": [35, 50, 70, -25, -32, -40, -45], "max_tilt_deg": 3.0},
        "floor":  {"plane_v_deg": [25, 35, 50, 70, -6, -9, -13, -20], "max_tilt_deg": 5.0, "profile_z": 1000, "step": 1.0},
        "table":  {"plane_v_deg": [25, 35, 50, 70, -20, -28, -36, -44], "max_tilt_deg": 5.0, "profile_z": 1000, "step": 1.0}},
    "base_drop_mm": 152,               # луч над опорой (ножки) — из station.scad, BEAM_H
    "battery": {"ina219": None, "cells": 3},   # INA219 (адрес 64) в правой башне — напряжение 3S (9,0–12,6 В)
    "cal": {"d0": 0, "hz0": 0, "v0": 0, "tilt_x": 0, "tilt_y": 0, "e": 0},
    "camera": {},                      # поля поверх photos.CAM_DEFAULT
    "imu": {"bus": 1, "addr": 104, "sign": [1, 1, 1], "settle_s": 1.0},   # MPU6050; sign — знаки осей
    "edge_iter": 8,                    # бисекций на кромку (0,5° / 2^8 = 0,002°)
    "probe_step_deg": 4.0,             # грубый шаг поиска верха/низа ниши
    "max_tilt_deg": 3.0,
}
CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_cfg():
    cfg = json.loads(json.dumps(CFG_DEFAULT))
    if os.path.exists(CFG_PATH):
        user = json.load(open(CFG_PATH))
        for k, v in user.items():
            if isinstance(v, dict): cfg[k].update(v)
            else: cfg[k] = v
    return cfg


# ---------------- железо ----------------
class Arduino:
    def __init__(self, port, baud):
        import serial
        self.s = serial.Serial(port, baud, timeout=120)
        time.sleep(2.0)                                     # автосброс Uno/Nano
        while self.s.in_waiting: self.s.readline()
        self.pos = self.cmd("P")

    def cmd(self, line):
        self.s.write((line + "\n").encode())
        r = self.s.readline().decode(errors="replace").strip()
        if r.startswith(("OK", "POS")) and len(r.split()) == 3:
            return tuple(int(x) for x in r.split()[1:])
        if r.startswith("HOME"): return int(r.split()[1])
        if r == "OK": return None
        raise RuntimeError(f"Arduino: {line!r} -> {r!r}")

    def move(self, h, v): self.pos = self.cmd(f"M {int(round(h))} {int(round(v))}"); return self.pos
    def jog(self, ax, n): self.pos = self.cmd(f"J {ax} {int(n)}"); return self.pos
    def zero(self): self.pos = self.cmd("Z")
    def setpos(self, h, v): self.pos = self.cmd(f"S {int(round(h))} {int(round(v))}"); return self.pos
    def home(self): return self.cmd("H")


class Laser:
    def __init__(self, c):
        import serial
        self.c = c
        self.s = serial.Serial(c["port"], c["baud"], timeout=c["timeout"])
        self.cmd = bytes.fromhex(c["cmd_hex"]) if c["cmd_hex"] else b""
        self.btn = None
        if c["trigger_gpio"] is not None:
            from gpiozero import OutputDevice
            self.btn = OutputDevice(c["trigger_gpio"], active_high=True, initial_value=False)
        if not self.cmd and self.btn is None:
            sys.exit("config.json: задайте laser.cmd_hex (модуль) или laser.trigger_gpio (ручной дальномер)")

    def trigger(self):
        if self.cmd: self.s.write(self.cmd); return
        for k in range(self.c["presses"]):
            self.btn.on(); time.sleep(self.c["press_ms"] / 1000); self.btn.off()
            if k < self.c["presses"] - 1: time.sleep(self.c["gap_ms"] / 1000)

    def raw(self):
        self.s.reset_input_buffer(); self.trigger()
        time.sleep(0.05); buf = b""; t0 = time.time()
        while time.time() - t0 < self.c["timeout"]:
            chunk = self.s.read(self.s.in_waiting or 1)
            buf += chunk
            if not chunk and buf: break
        return buf

    def measure(self):
        b = self.raw(); c = self.c
        if c["mode"] == "binary":
            f = b[c["offset"]:c["offset"] + c["length"]]
            if len(f) < c["length"]: raise RuntimeError(f"короткий ответ: {b.hex(' ')}")
            return int.from_bytes(f, c["endian"]) * c["scale"]
        m = re.search(c["regex"], b.decode(errors="replace"))
        if not m: raise RuntimeError(f"нет числа в ответе: {b!r}")
        return float(m.group(1)) * c["scale"]


# ---------------- симулятор ----------------
class Sim:
    """Виртуальная кухня sim_room.py: ниша, пилястра, полукруглый выступ, неровная стена, наклонённый штатив."""
    def __init__(self, cfg):
        import sim_room
        self.cfg, self.room, self.pos = cfg, sim_room.Room(), (0, 0)
        self.v_off = 7.3                                       # голова при включении наклонена на неизвестный угол
    def move(self, h, v): self.pos = (int(round(h)), int(round(v))); return self.pos
    def jog(self, ax, n): return self.move(self.pos[0] + (n if ax == "H" else 0), self.pos[1] + (n if ax == "V" else 0))
    def zero(self): self.v_off += self.deg()[1]; self.pos = (0, 0)
    def home(self): return 0
    def setpos(self, h, v):
        v_true = self.deg()[1] + self.v_off; self.pos = (int(round(h)), int(round(v))); self.v_off = v_true - self.deg()[1]; return self.pos
    def deg(self): return self.pos[0] / self.cfg["steps_per_rev_hz"] * 360, self.pos[1] / self.cfg["steps_per_rev_v"] * 360
    def raw(self): return f"D={self.measure()/1000:.4f}m\r\n".encode()
    def measure(self): h, v = self.deg(); return self.room.measure(h, v + self.v_off)
    def imu(self): h, v = self.deg(); return self.room.imu(h, v + self.v_off)


class IMU:
    """MPU6050 (GY-521) в голове: I2C-1 (pin 3 SDA, pin 5 SCL, pin 1 3,3V, pin 9 GND), адрес 0x68.
    Ось X — по лучу, Y — вдоль оси V (влево), Z — вверх. Возвращает единичный вектор «вверх» в осях датчика."""
    def __init__(self, bus=1, addr=0x68, sign=(1, 1, 1)):
        try: from smbus2 import SMBus
        except ImportError: from smbus import SMBus
        self.b, self.a, self.sign = SMBus(bus), addr, np.array(sign, float)
        self.b.write_byte_data(addr, 0x6B, 0); self.b.write_byte_data(addr, 0x1A, 6); self.b.write_byte_data(addr, 0x1C, 0)
        time.sleep(0.1)
    def read(self, n=300):
        acc = []
        for _ in range(n):
            d = self.b.read_i2c_block_data(self.a, 0x3B, 6)
            acc.append([((d[i] << 8) | d[i + 1]) - (65536 if d[i] > 127 else 0) for i in (0, 2, 4)]); time.sleep(0.004)
        a = np.mean(acc, 0) * self.sign; return a / np.linalg.norm(a)


# ---------------- логика ----------------
class Station:
    def __init__(self, cfg, sim):
        self.cfg = cfg
        if sim: self.ard = self.las = Sim(cfg)
        else:
            self.ard = Arduino(cfg["arduino"]["port"], cfg["arduino"]["baud"])
            self.las = Laser(cfg["laser"])
        self.sim = sim
        try: self.v_home()                                     # V известен сразу после включения
        except Exception as e: print(f"  ноль V не найден (нет MPU6050?): {e}")

    def cam(self):
        import photos
        c = dict(photos.CAM_DEFAULT); c.update(self.cfg["camera"]); return c

    def move_deg(self, hz, v):
        h, s = self.ard.move(*self.deg2steps(hz, v))
        if not self.sim: time.sleep(self.cfg["settle_s"])
        return h / self.cfg["steps_per_rev_hz"] * 360, s / self.cfg["steps_per_rev_v"] * 360

    def pos_deg(self):
        h, s = self.ard.pos
        return h / self.cfg["steps_per_rev_hz"] * 360, s / self.cfg["steps_per_rev_v"] * 360

    def capture(self, path, cam):
        import photos
        if self.sim:
            if not hasattr(self, "_simcap"):
                self._simcap = photos.sim_capture_factory((0, 0, 0), (4000, 3200, 2700), (1500, 1200, 1400))
            self._simcap(path, cam, *self.pos_deg())
        else:
            photos.capture(path, cam)

    def deg2steps(self, hz, v):
        return hz / 360 * self.cfg["steps_per_rev_hz"], v / 360 * self.cfg["steps_per_rev_v"]

    def point(self, hz, v, plumb=False):
        vi = v - self.cfg["cal"].get("v0", 0)
        if vi < self.cfg["v_min_deg"] - 0.5 and not (plumb and abs(vi + 90) < 3):
            raise RuntimeError(f"V={vi:.1f}° — луч упрётся в корпус (минимум {self.cfg['v_min_deg']}°)")
        h, s = self.ard.move(*self.deg2steps(hz, v))
        if not self.sim: time.sleep(self.cfg["settle_s"])
        d = statistics.mean(self.las.measure() for _ in range(self.cfg["avg"]))
        return [h / self.cfg["steps_per_rev_hz"] * 360, s / self.cfg["steps_per_rev_v"] * 360, float(d)]

    # ---------- углы <-> направление (кадр станции по уровню) ----------
    def R_tilt(self):
        c = self.cfg["cal"]; tx, ty = math.radians(c.get("tilt_x", 0)), math.radians(c.get("tilt_y", 0))
        Rx = np.array([[1, 0, 0], [0, math.cos(tx), -math.sin(tx)], [0, math.sin(tx), math.cos(tx)]])
        Ry = np.array([[math.cos(ty), 0, math.sin(ty)], [0, 1, 0], [-math.sin(ty), 0, math.cos(ty)]])
        return Ry @ Rx

    def aim(self, p):
        """Точка в кадре станции (по уровню) -> команды Hz, V (град)."""
        c = self.cfg["cal"]; q = self.R_tilt().T @ np.asarray(p, float); q /= np.linalg.norm(q)
        return math.degrees(math.atan2(q[1], q[0])) % 360 + c.get("hz0", 0), math.degrees(math.asin(q[2])) + c.get("v0", 0)

    def xyz(self, pt):
        from scan2dxf import to_xyz
        return to_xyz(np.array([pt[:3]], float), self.cfg["cal"])[0]

    def battery(self):
        """Напряжение аккумулятора (INA219, шина 0x02: биты 15..3 x 4 мВ) -> (В, %)."""
        b = self.cfg["battery"]
        if self.sim: v = 11.6
        elif not b.get("ina219"): return None
        else:
            if not hasattr(self, "_ina"):
                try: from smbus2 import SMBus
                except ImportError: from smbus import SMBus
                self._ina = SMBus(1)
            w = self._ina.read_word_data(int(b["ina219"]), 0x02); w = ((w & 0xFF) << 8) | (w >> 8); v = (w >> 3) * 0.004
        tab = [(3.0, 0), (3.3, 3), (3.5, 12), (3.65, 30), (3.75, 50), (3.85, 65), (4.0, 85), (4.2, 100)]
        c = v / b.get("cells", 5); p = float(np.interp(c, [t[0] for t in tab], [t[1] for t in tab]))
        return round(v, 2), round(p)

    def imu_read(self):
        if self.sim: return self.ard.imu()
        if not hasattr(self, "_imu"):
            c = self.cfg["imu"]; self._imu = IMU(c["bus"], c["addr"], c["sign"])
        time.sleep(self.cfg["imu"]["settle_s"]); return self._imu.read()

    # ---------- авто-калибровка ----------
    def level(self):
        """Авто-нивелир: акселерометр на Hz-барабане в 4 положениях Hz. Смещение нуля датчика исключается,
        остаётся наклон штатива -> cal.tilt_x/tilt_y (компенсатор, как у тахеометра)."""
        A, b = [], []
        for hz in (0, 90, 180, 270):
            self.move_deg(hz, 0); s = self.imu_read(); c, sn = math.cos(math.radians(hz)), math.sin(math.radians(hz))
            A += [[c, sn, 1, 0], [-sn, c, 0, 1]]; b += [s[0], s[1]]
        x, res, *_ = np.linalg.lstsq(np.array(A), np.array(b), rcond=None)
        ux, uy = x[0], x[1]; uz = math.sqrt(max(0, 1 - ux*ux - uy*uy))
        tx, ty = math.degrees(math.atan2(uy, uz)), -math.degrees(math.asin(ux))
        r = np.array(A) @ x - np.array(b); sd = math.degrees(float(np.sqrt((r**2).mean())))
        self.cfg["cal"].update(tilt_x=tx, tilt_y=ty); self.move_deg(0, 0)
        print(f"  наклон штатива: X {tx:+.3f}°  Y {ty:+.3f}°  (смещение датчика {math.degrees(x[2]):+.2f}° {math.degrees(x[3]):+.2f}°, СКО {sd*3600:.0f}\")")
        mt = self.mode().get("max_tilt_deg", self.cfg["max_tilt_deg"])
        if math.hypot(tx, ty) > mt: raise RuntimeError(f"наклон {math.hypot(tx, ty):.1f}° > {mt}° — выставьте по пузырьку (штатив или ножки-конусы)")
        return tx, ty

    def v_index(self, v=60, n=8):
        """Индекс V без мишени: двойной замер (круг лево/право) по потолку (вниз -60° мешает корпус).
        Hz и Hz+180 через зенит смотрят в одну сторону; ошибка индекса даёт разную высоту одной плоскости."""
        est = []
        for vv in (v,):
            for k in range(n):
                hz = 360*k/n
                p1 = self.point(hz, vv); p2 = self.point(hz + 180, (180 if vv > 0 else -180) - vv)
                if not (p1[2] > 0 and p2[2] > 0): continue
                e = 0.0
                for _ in range(6):                                      # секущая по e: z1(e) = z2(e)
                    f = lambda ee: self._z_with_v0(p1, ee) - self._z_with_v0(p2, ee)
                    f0, f1 = f(e), f(e + 0.01); e -= f0*0.01/(f1 - f0) if f1 != f0 else 0
                est.append(e)
        est = np.array(est); med = float(np.median(est)); good = est[np.abs(est - med) < 0.03]
        v0 = float(good.mean()) if len(good) else med
        print(f"  индекс V: {v0:+.4f}°  (разброс {good.std()*3600 if len(good) > 1 else 0:.0f}\", {len(good)}/{len(est)})")
        self.cfg["cal"]["v0"] = v0; self.move_deg(0, 0); return v0

    def _z_with_v0(self, p, v0):
        from scan2dxf import to_xyz
        c = dict(self.cfg["cal"]); c["v0"] = v0; return to_xyz(np.array([p[:3]], float), c)[0][2]

    # ---------- скан ----------
    def v_home(self):
        """Ноль V по акселерометру в голове: угол луча к горизонту (с учётом наклона штатива) -> счётчик V.
        Смещение нуля датчика по этой оси = cal.v0 (находит «Индекс V», хранится в config.json)."""
        s = self.imu_read(); pitch = math.degrees(math.asin(max(-1, min(1, s[0]))))
        h, _ = self.pos_deg(); R = self.R_tilt(); V = pitch; hr = math.radians(h - self.cfg["cal"].get("hz0", 0))
        for _ in range(5):
            vr = math.radians(V); d = R @ np.array([math.cos(vr)*math.cos(hr), math.cos(vr)*math.sin(hr), math.sin(vr)])
            V += pitch - math.degrees(math.asin(d[2]))
        hs, _ = self.ard.pos; self.ard.setpos(hs, V / 360 * self.cfg["steps_per_rev_v"])
        print(f"  ноль V по акселерометру: луч {pitch:+.2f}° к горизонту")
        return V

    def plumb(self):
        """Лазерный отвес: луч строго вниз через полую ось -> высота оси станции над точкой под ней."""
        h, _ = self.pos_deg(); p = self.point(h, -90 + self.cfg["cal"].get("v0", 0), plumb=True)
        X = self.xyz(p); print(f"  отвес: ось станции на {-X[2]:.1f} мм над опорой (точка X{X[0]:+.1f} Y{X[1]:+.1f})")
        self.move_deg(h, 0); return p, X

    def mode(self):
        m = self.cfg["mounts"].get(self.cfg.get("mount", "tripod"), {}); return m

    def planes(self, vlist=None):
        c = self.cfg; pts = []
        for v in (vlist or self.mode().get("plane_v_deg", c["plane_v_deg"])):
            for hz in range(0, 360, int(c["plane_hz_step_deg"])):
                try: pts.append(self.point(hz, v + c["cal"].get("v0", 0)) + [1])
                except RuntimeError as e: print("  пропуск:", e)
        return pts

    def scan(self):
        """Штатив: профиль по горизонту + пол/потолок."""
        c = self.cfg; pts = []; t0 = time.time()
        n = int(round(360 / c["profile_step_deg"]))
        for lvl in c["profile_levels_deg"]:
            for k in range(n):
                pts.append(self.point(k * c["profile_step_deg"], lvl + c["cal"].get("v0", 0)) + [0])
                if k % 60 == 0: print(f"  профиль V={lvl:+.0f}°: {k}/{n}", flush=True)
        pts += self.planes()
        self.ard.move(0, 0)
        print(f"  точек: {len(pts)}, время {time.time()-t0:.0f} с")
        return {"cal": dict(c["cal"]), "points": pts}

    def refine_edge(self, rq, v=None):
        """Бисекция по Hz: точная кромка ближней грани (край ниши, пилястры, проёма)."""
        v = self.cfg["cal"].get("v0", 0) if v is None else v
        c, n = np.array(rq["c"]), np.array(rq["n"]); a, b = rq["hz_in"], rq["hz_out"]
        if abs(b - a) > 180: b += 360 if b < a else -360
        out = []
        for _ in range(self.cfg["edge_iter"]):
            m = (a + b)/2; p = self.point(m % 360, v); X = self.xyz(p); out.append(p + [2])
            if abs((X[:2] - c) @ n) < 8: a = m
            else: b = m
        return out

    def vprobe(self, face_xy, on_face, v_start=None):
        """Верх/низ грани ниши/выступа: шаг вверх/вниз до схода с грани, затем бисекция по V."""
        hz, v_mid = self.aim([face_xy[0], face_xy[1], 0]); out = []
        if v_start is not None: v_mid = v_start
        for sgn in (1, -1):
            a = v_mid; b = None; v = v_mid
            while abs(v - v_mid) < 85:
                v += sgn*self.cfg["probe_step_deg"]
                if v - self.cfg["cal"].get("v0", 0) < self.cfg["v_min_deg"]: break
                p = self.point(hz, v); out.append(p + [3])
                if on_face(self.xyz(p)): a = v
                else: b = v; break
            if b is None: continue
            for _ in range(self.cfg["edge_iter"]):
                m = (a + b)/2; p = self.point(hz, m); out.append(p + [3])
                if on_face(self.xyz(p)): a = m
                else: b = m
        return out

    def trace_level(self, z, hz0, hz1, step):
        """Трасса по уровню: луч держится на высоте z (кадр станции) — как «следовать по уровню» у DISTO 3D."""
        pts = []; span = (hz1 - hz0) % 360 or 360; N = max(2, int(span/step) + 1); v = 0.0; good = 0
        for k in range(N):
            hz = (hz0 + span*k/(N - 1)) % 360
            for it in range(5):
                p = self.point(hz, v + self.cfg["cal"].get("v0", 0)); X = self.xyz(p); rho = math.hypot(X[0], X[1])
                dv = math.degrees(math.atan2(z, rho) - math.atan2(X[2], rho)); v += dv
                if abs(X[2] - z) < 1.0: break
            if abs(X[2] - z) < 3: pts.append(p); good += 1
            if k % 40 == 0: print(f"  уровень {z:+.0f}: {k}/{N}", flush=True)
        print(f"  трасса: {good}/{N} точек на уровне")
        return pts

    def measure_grid(self, P):
        """Сетка точек (кадр станции) -> замеры. Змейкой, чтобы меньше ездить."""
        out = []
        for k, p in enumerate(P):
            out.append(self.point(*self.aim(p)))
            if k % 50 == 0: print(f"  сетка: {k}/{len(P)}", flush=True)
        return out


def sniff(port, bauds):
    """Поиск UART внутри ручного дальномера: провод с площадки TX платы -> GPIO15 (RX Pi), GND -> GND.
    На каждой скорости 8 с: в это время жать «замер» на дальномере. Ищем читаемый текст/повторяющиеся кадры."""
    import serial
    for b in [int(x) for x in bauds] or [9600, 19200, 38400, 57600, 115200]:
        s = serial.Serial(port, b, timeout=0.2); s.reset_input_buffer()
        print(f"--- {b} бод: жмите «замер» 2-3 раза ---", flush=True)
        buf = b""; t0 = time.time()
        while time.time() - t0 < 8: buf += s.read(256)
        s.close()
        if not buf: print("  тишина"); continue
        txt = sum(32 <= c < 127 or c in (10, 13) for c in buf) / len(buf)
        print(f"  {len(buf)} байт, печатных {txt:.0%}")
        print("  HEX:", buf[:96].hex(" ")); print("  ASCII:", buf[:96])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["sniff", "probe", "measure", "jog", "calrev", "scan",
                                    "photos", "camcal"])
    ap.add_argument("args", nargs="*"); ap.add_argument("-n", type=int, default=10)
    ap.add_argument("-o", default="scan.json"); ap.add_argument("--dxf"); ap.add_argument("--sim", action="store_true")
    a = ap.parse_args(); cfg = load_cfg()
    if a.cmd == "sniff": return sniff(cfg["laser"]["port"], a.args)
    st = Station(cfg, a.sim)

    if a.cmd == "probe":
        b = st.las.raw(); print("HEX:", b.hex(" ")); print("ASCII:", b)
    elif a.cmd == "measure":
        d = [st.las.measure() for _ in range(a.n)]
        print(f"n={a.n}  среднее={statistics.mean(d):.1f} мм  СКО={statistics.pstdev(d):.2f} мм  размах={max(d)-min(d):.1f}")
    elif a.cmd == "jog":
        print(st.ard.jog(a.args[0].upper(), int(a.args[1])))
    elif a.cmd == "calrev":
        print("Навести луч на метку на дальней стене (3-5 м), jog'ом. Enter — старт."); input()
        st.ard.zero(); spr = cfg["steps_per_rev_hz"]
        st.ard.move(spr, 0)
        print("Доведите точку до метки: +N / -N микрошагов, пустая строка — готово")
        while True:
            s = input("> ").strip()
            if not s: break
            st.ard.jog("H", int(s))
        real = st.ard.pos[0]
        print(f"steps_per_rev_hz = {real}  (было {spr}); впишите в config.json. Повторите 3 раза, возьмите среднее.")
    elif a.cmd == "scan":
        data = st.scan(); json.dump(data, open(a.o, "w")); print("записано", a.o)
        if a.dxf:
            here = os.path.dirname(os.path.abspath(__file__))
            s2d = next((p for p in (os.path.join(here, "scan2dxf.py"), os.path.join(here, "..", "scan2dxf.py")) if os.path.exists(p)), "scan2dxf.py")
            subprocess.run([sys.executable, s2d, a.o, a.dxf], check=True)

    elif a.cmd == "photos":
        import photos
        dxf = a.dxf or "room.dxf"; geom = json.load(open(os.path.splitext(dxf)[0] + "_geom.json"))
        outdir = os.path.splitext(dxf)[0] + "_photos"; cam = st.cam()
        photos.shoot(st, geom, outdir, cam, capture_fn=st.capture)
        st.ard.move(0, 0)
        sheets = photos.render_sheets(geom, outdir)
        photos.add_to_dxf(dxf, sheets, outdir); print("развёртки добавлены в", dxf)
    elif a.cmd == "camcal":
        # Лист А4 с чёрным кружком Ø40 на стене 2-4 м. Навести луч в центр кружка (jog), затем camcal.
        import photos
        cam = st.cam(); h0, v0 = st.pos_deg(); d = st.las.measure()
        hr, vr = math.radians(h0), math.radians(v0)
        P = d*np.array([math.cos(vr)*math.cos(hr), math.cos(vr)*math.sin(hr), math.sin(vr)])
        fh = math.degrees(math.atan(cam["width"]/2/cam["fx"])); fv = math.degrees(math.atan(cam["height"]/2/cam["fy"]))
        obs = []
        for dv in np.linspace(-0.75*fv, 0.75*fv, 5):
            for dh in np.linspace(-0.8*fh, 0.8*fh, 7):
                hz, v = st.move_deg(h0 + dh, v0 + dv); fn = f"camcal_{len(obs):02d}.jpg"
                st.capture(fn, cam)
                pred = photos.project(P[None], hz, v, cam)[0][0]
                m = photos.find_dark_mark(fn, near=pred, win=0.25*cam["width"])
                if m: obs.append((hz, v, *m))
        st.move_deg(h0, v0)
        res, rms = photos.camcal(P, obs, cam)
        print(f"кадров с меткой: {len(obs)}/35, СКО {rms:.2f} px")
        print('"camera": ' + json.dumps({k: round(v, 5) for k, v in res.items()}) + "   -> в config.json")

if __name__ == "__main__":
    main()
