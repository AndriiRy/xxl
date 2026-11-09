// Прошивка станции: 2 оси (Hz, V), протокол по USB-Serial 115200. Arduino Nano/Uno: STEP D2/D3, DIR D5/D6, EN D8, Холл D9.
// Библиотека: AccelStepper (Менеджер библиотек Arduino IDE).
// Команды (строка, \n):
//   M <hz> <v>   абсолютный ход в микрошагах, подход всегда с одной стороны (анти-люфт) -> "OK <hz> <v>"
//   J <axis> <n> относительный ход (axis: H|V)                                       -> "OK <hz> <v>"
//   P            позиция                                                             -> "POS <hz> <v>"
//   Z            текущая позиция = 0                                                 -> "OK 0 0"
//   S <hz> <v>   задать текущую позицию без движения (ноль V по акселерометру)         -> "OK <hz> <v>"
//   H            поиск нуля Hz по датчику Холла (вращение +)                         -> "HOME <шаги до метки>"
//   E <0|1>      питание моторов вкл/выкл                                            -> "OK"
#include <AccelStepper.h>

// ---- выбор моторов (Arduino Uno + CNC Shield v3) ----
// Hz: NEMA17 через драйвер в гнезде X (STEP D2, DIR D5), EN = D8.
// V : V_NEMA17 -> драйвер в гнезде Y (STEP D3, DIR D6)
//     иначе    -> 28BYJ-48 + ULN2003: IN1..IN4 = A0..A3 (на шилде: Abort, Hold, Resume, CoolEn)
#define V_NEMA17            // закомментировать -> 28BYJ-48 (только для пробы, точность хуже)

AccelStepper hz(AccelStepper::DRIVER, 2, 5);
const float HZ_VMAX = 3000, HZ_ACC = 4000;   // микрошаг/с, /с^2 (1/16)
const long  HZ_BL = 400;                      // перебег анти-люфт
#ifdef V_NEMA17
  AccelStepper vv(AccelStepper::DRIVER, 3, 6);
  const float V_VMAX = 3000, V_ACC = 4000;
  const long  V_BL = 400;
#else
  AccelStepper vv(AccelStepper::HALF4WIRE, A0, A2, A1, A3);   // порядок IN1, IN3, IN2, IN4
  const float V_VMAX = 700, V_ACC = 900;      // полушаг/с
  const long  V_BL = 300;                     // люфт редуктора 28BYJ ~1-3°: перебег обязателен
#endif
const int PIN_EN = 8;
const int PIN_HALL = 9;                       // KY-003 / A3144 -> X- endstop, активный LOW

void power(bool on) {
  digitalWrite(PIN_EN, on ? LOW : HIGH);
#ifndef V_NEMA17
  if (on) vv.enableOutputs(); else vv.disableOutputs();
#endif
}

void runBoth() { while (hz.distanceToGo() != 0 || vv.distanceToGo() != 0) { hz.run(); vv.run(); } }

void moveTo(long h, long v) {
  // подход с отрицательной стороны: сначала в (цель - BACKLASH), затем в цель
  if (hz.currentPosition() > h - HZ_BL || vv.currentPosition() > v - V_BL) {
    hz.moveTo(min(hz.currentPosition(), h - HZ_BL));
    vv.moveTo(min(vv.currentPosition(), v - V_BL));
    runBoth();
  }
  hz.moveTo(h); vv.moveTo(v); runBoth();
}

void reply(const char *tag) {
  Serial.print(tag); Serial.print(' ');
  Serial.print(hz.currentPosition()); Serial.print(' ');
  Serial.println(vv.currentPosition());
}

void home() {
  long start = hz.currentPosition();
  hz.setMaxSpeed(HZ_VMAX / 6);
  // если стоим на метке — сойти с неё
  while (digitalRead(PIN_HALL) == LOW) { hz.move(10); while (hz.distanceToGo()) hz.run(); }
  hz.moveTo(start + 2000000L);
  while (digitalRead(PIN_HALL) == HIGH && hz.distanceToGo()) hz.run();
  long found = hz.currentPosition() - start;
  hz.setCurrentPosition(0); hz.moveTo(0);   // остановка без торможения: скорость поиска мала
  hz.setMaxSpeed(HZ_VMAX);
  Serial.print("HOME "); Serial.println(found);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_HALL, INPUT_PULLUP);
  pinMode(PIN_EN, OUTPUT);
  hz.setMaxSpeed(HZ_VMAX); hz.setAcceleration(HZ_ACC);
  vv.setMaxSpeed(V_VMAX);  vv.setAcceleration(V_ACC);
  power(true);
  Serial.println("READY");
}

void loop() {
  if (!Serial.available()) return;
  String s = Serial.readStringUntil('\n'); s.trim();
  if (s.length() == 0) return;
  char c = s.charAt(0);
  String a = s.substring(1); a.trim();
  if (c == 'M') {
    int sp = a.indexOf(' ');
    moveTo(a.substring(0, sp).toInt(), a.substring(sp + 1).toInt()); reply("OK");
  } else if (c == 'J') {
    char ax = a.charAt(0); long n = a.substring(1).toInt();
    if (ax == 'H') moveTo(hz.currentPosition() + n, vv.currentPosition());
    else           moveTo(hz.currentPosition(), vv.currentPosition() + n);
    reply("OK");
  } else if (c == 'P') reply("POS");
  else if (c == 'Z') { hz.setCurrentPosition(0); vv.setCurrentPosition(0); reply("OK"); }
  else if (c == 'S') { int sp = a.indexOf(' '); hz.setCurrentPosition(a.substring(0, sp).toInt()); vv.setCurrentPosition(a.substring(sp + 1).toInt()); reply("OK"); }
  else if (c == 'H') home();
  else if (c == 'E') { power(a.toInt() != 0); Serial.println("OK"); }
  else Serial.println("ERR");
}
