"""Проверка драйвера SCL3300 на имитации датчика (протокол «ответ в следующем кадре», CRC-8). python3 t_scl3300.py <station/pi>"""
import sys, math, numpy as np
sys.path.insert(0, sys.argv[1]); import station as S
D = S.SCL3300
for c in (*D.RD_ACC, D.RD_STATUS, D.RD_WHOAMI, D.WAKEUP, D.SW_RESET, D.MODE4, D.ANG_EN):     # CRC команд из даташита
    assert D.crc(c) == c & 0xFF, hex(c)
print("CRC всех команд из даташита совпадает")


class FakeSCL:
    """Имитация: отвечает на ПРЕДЫДУЩУЮ команду, данные — ускорение g*12000 с шумом."""
    def __init__(self, g): self.g, self.prev, self.rng = np.array(g, float), None, np.random.default_rng(1)
    def word(self, data, rs=1):
        v = (((self.prev or 0) >> 24) & 0xFC | rs) << 24 | (data & 0xFFFF) << 8; return v | D.crc(v)
    def xfer2(self, b):
        cmd = int.from_bytes(bytes(b), "big"); p = self.prev; self.prev = cmd
        if p in D.RD_ACC:
            i = D.RD_ACC.index(p); val = int(round((self.g[i] + self.rng.normal(0, 2e-5))*12000)) & 0xFFFF; out = self.word(val)
        elif p == D.RD_WHOAMI: out = self.word(0x00C1)
        else: out = self.word(0)
        self.prev = cmd; return list(out.to_bytes(4, "big"))


tilt = math.radians(0.5); g = [math.sin(tilt), 0.0, math.cos(tilt)]
d = D(spi=FakeSCL(g)); u = d.read_up(200, dt=0)
print(f"наклон по датчику {math.degrees(math.asin(u[0])):.4f}° (задан 0.5000°), вектор {np.round(u, 6)}")
bad = FakeSCL(g); d2 = D(spi=bad)
orig = bad.word; bad.word = lambda data, rs=1: orig(data, rs) ^ 0x01          # испорченный CRC
try: d2.acc(); print("ОШИБКА: битый CRC не пойман")
except IOError as e: print("битый CRC пойман:", e)
