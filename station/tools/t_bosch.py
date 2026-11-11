"""Проверка драйвера дальномера с пресетом bosch на имитации однопроводного порта (эхо + ответ 00 04 LE*0,05 мм + CRC),
сна прибора (молчит до нажатия кнопки) и ошибки замера. python3 t_bosch.py <station/pi>"""
import sys, types
sys.path.insert(0, sys.argv[1]); import station as S


class FakeGLM:
    """Отладочный порт Bosch: TX и RX на одном проводе — Pi слышит свою команду, затем ответ прибора."""
    def __init__(self, port, baud, timeout): assert baud == 9600; self.buf, self.d_mm, self.awake, self.err = b"", 1824.0, False, False
    def reset_input_buffer(self): self.buf = b""
    @property
    def in_waiting(self): return len(self.buf)
    def write(self, b):
        self.buf += b                                                    # эхо
        if not self.awake: return
        if b == bytes.fromhex("c0 40 00 ee"):
            if self.err: self.buf += bytes([0x01, 0x00, 0xFA]); return
            self.buf += bytes([0x00, 0x04]) + int(round(self.d_mm/0.05)).to_bytes(4, "little") + b"\x16"
    def read(self, n): out, self.buf = self.buf[:n], self.buf[n:]; return out


class Btn:
    def __init__(self, dev): self.dev = dev
    def on(self): self.dev.awake = True
    def off(self): pass


fake = {}
sys.modules["serial"] = types.SimpleNamespace(Serial=lambda *a, **k: fake.setdefault("s", FakeGLM(*a, **k)))
cfg = dict(S.CFG_DEFAULT["laser"], preset="bosch")
L = S.Laser(dict(cfg, trigger_gpio=None, cmd_hex=""))                   # кнопки нет: пресет даёт команду
dev = fake["s"]; dev.awake = True
print(f"замер {L.measure():.2f} мм (задано {dev.d_mm})"); assert abs(L.measure() - 1824.0) < 0.05
for hx, shown in (("00 04 13 0e 00 00 32", 180.0), ("00 04 4a 86 00 00 16", 1824.0)):   # примеры с форума (экран прибора)
    raw = int.from_bytes(bytes.fromhex(hx)[2:6], "little")*0.05
    print(f"  форум: {hx} -> {raw:.1f} мм, на экране {shown:.0f} мм, разница {shown - raw:+.1f} мм")
print("  разница = отсчёт от передней кромки / задней кромки прибора (корпус ~105 мм); у нас уходит в калибровку d0")
dev.d_mm = 4321.35; print(f"замер {L.measure():.2f} мм (задано 4321.35)")
dev.err = True
try: L.measure(); print("ОШИБКА: статус ошибки не пойман")
except RuntimeError as e: print("ошибка замера поймана:", e)
dev.err = False; dev.awake = False; L.btn = Btn(dev); L.c["press_ms"] = 1
S.time.sleep = lambda t: None
print(f"прибор спал — разбужен кнопкой, замер {L.measure():.2f} мм")
