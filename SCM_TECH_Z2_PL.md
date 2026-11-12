# SCM Tech Z2 — maszyna, narzędzia, zasady programów Xilog (.xxl)

Kontekst dla asystenta AI. Źródło: edytor XXL (`xxl.html` w tym repozytorium), tabela narzędzi DEF.TLG (Xilog Plus\Job, 07.10.2026), standardy warsztatu (07.10–09.10.2026), katalog Blum 2027/28.
Czego nie ma w danych — oznaczone **BRAK DANYCH**, nie wymyślać.

---

## 1. Maszyna

| Parametr | Wartość |
|---|---|
| Model | SCM Tech Z2 (centrum CNC: wiercenie + frezowanie + piła) |
| Oprogramowanie | Xilog Plus (programy `.xxl`, tekst; kodowanie UTF-8 lub Windows-1250, końce linii CRLF) |
| Pole robocze X × Y | **3050 × 1248 mm** |
| Baza stołu | **prawy górny róg** stołu; element kładziemy **obrzeżem (przodem) do bazy** |
| Grubość domyślna | DZ = 18 mm |
| Obroty / posuwy wrzeciona | BRAK DANYCH (z DEF.TLG wzięte tylko średnice) |
| Głowica wiertarska (liczba wrzecion, rozstaw) | BRAK DANYCH |
| Przyssawki / strefy stołu | BRAK DANYCH |

### Układ współrzędnych i ściany
- X=0, Y=0 — zero programu (w Xilog — lewy dolny róg; na stole — baza w prawym górnym rogu, widok lustrzany).
- F1 — górna płaszczyzna; F2 — prawe czoło (X=DX); F3 — lewe czoło (X=0); F4 — przód (Y=0); F5 — tył (Y=DY) (instrukcja Xilog Editor, str. 81).
- **Bok szafki:** X=0 = GÓRA szafki, X=DX = DÓŁ; Y=0 = przednia krawędź (obrzeże) → do bazy.
- **Front:** X=0 = dół frontu; Y=0 = krawędź od strony zawiasów.
- Wysokość „od dołu szafki” h → współrzędna maszyny X = DX − h.

---

## 2. Narzędzia (DEF.TLG, 07.10.2026)

| T | Ø, mm | Nazwa |
|---|---|---|
| 82 | 3.4 | PILA 3,4 (piła; rowki HDF) |
| 83 | 3.4 | PILA 3,4 |
| 91 | 16.0 | — |
| 93 | 10.0 | — |
| 101 | 12.0 | FREZ MALY WSTAWKI |
| 102 | 11.35 | FREZ FI12 |
| 103 | 17.0 | FREZ FI 19.55 |
| 104 | 16.0 | FREZ ZENITA (główny frez: wycięcia, okręgi) |
| 105 | 80.0 | 80x14 Frezowanie |
| 106 | 16.0 | FREZ 16 |
| 107 | 34.0 | frez maly raczka kopia |
| 108 | 42.0 | — |
| 109 | 23.6 | GRUBASY h=70mm |
| 110 | 52.0 | frez skosny 45* |
| 111 | 9.27 | FI=10 |
| 112 | 12.0 | HPL Dimar |
| 113 | 36.0 | FREZ DO FRONTU 1 |
| 114 | 8.0 | P2B-R4.0 |
| 115 | 6.0 | SPIRAL |
| 116 | 30.0 | FREZ DO FRONTU 4 |
| 117 | 12.0 | FREZ Z WYMIENNYMI NOZAMI |
| 118 | 6.0 | 6X21mm |
| 119 | 4.0 | 4x10 |
| 120 | 6.0 | 6X21mm |
| 121 | 12.0 | FREZ Z WYMIENNYMI NOZAMI |
| 122 | 60.0 | 60 |
| 123 | 52.0 | frez skosny 45* |
| 124 | 66.0 | 91 stopni |
| 125 | 180.0 | PIŁKA 180 |
| 126 | 51.7 | stara barsa |
| 127 | 6.0 | SPIRAL |
| 128 | 50.8 | KULA DUZA |
| 129 | 15.4 | FREZ DO FUTRYN |
| 130 | 52.0 | frez skosny 45* |
| 131 | 22.0 | Dimar krztaltowy |
| 132 | 8.0 | P2B-R4.0 |
| 133 | 54.0 | Dimar 130 |
| 134 | 28.3 | frez profil |
| 135 | 80.0 | 80x14 Frezowanie |
| 136 | 78.2 | 80 frezowanie |
| 137 | 17.4 | FREZ FI=17.4 |
| 138 | 28.3 | profil 28.3 |
| 139 | 6.0 | CMT 6x12.7 |
| 140 | 80.0 | SZTOTKA 75mm |
| 182 | 3.3 | — |

Wiertła (XBO) maszyna dobiera po D — numeru T się nie podaje.

---

## 3. Składnia .xxl (używana)

```
H DX=720 DY=510 DZ=18 -L C=0 T=0 R=1 *MM /"def"   ; nagłówek: wymiary elementu
; komentarz
PAR A=100 "opis"              ; parametr
L B=DX/2                      ; zmienna lokalna
XBO X=.. Y=.. Z=.. R=1 D=5 N="P" F=1               ; wiercenie
XBO X=.. Y=.. Z=12 R=3# x=32 D=5 N="P" F=1         ; rząd: R otworów co x (lub y)
XGIN Q=0 G=1                  ; wejście frezowania
XG0 X=.. Y=.. Z=.. T=104 E=1 C=2 F=1               ; start frezu
XL2P X=.. Y=..                ; linia
XAR2 X=.. Y=.. r=.. G=2|3     ; łuk po promieniu (G2 zgodnie z zegarem, G3 przeciwnie; r<0 — długi łuk)
XA2P X=.. Y=.. I=.. J=.. G=2  ; łuk po środku
XGOUT Q=0 G=1                 ; wyjście frezowania
XN X=1400                     ; odjazd, ostatnia linia
```
- `N="P"` — nieprzelotowy; `N="L"` — przelotowy.
- `F=1` góra, `F=2..5` czoła (dla czoła: X=DZ/2 — środek grubości).
- `C=1` korekcja z prawej, `C=2` z lewej, `C=0` po osi.
- Wyrażenia: `DX/2`, `DY-32`, `DZ+8`, `(DX-36)/2`, SQRT, SIN, COS (stopnie).
- Błędy wykrywane przez edytor: XBO bez `R=1` (Xilog powtórzy poprzednie R!), XG0 bez `F=1`, brak `XN`, otwór poza elementem, głębokość ≥ DZ przy N="P", frez głębiej niż DZ, element większy niż pole 3050×1248, brak T w tabeli.

---

## 4. Standardy wierceń warsztatu

| Węzeł | Wiercenie |
|---|---|
| Kołek (płaszczyzna) | Ø8 × 12 |
| Kołek (czoło) | Ø8 × 28, F2/F3, X=DZ/2 |
| Konfirmat (płaszczyzna) | Ø7 na wylot, Z=DZ+8, N="L" |
| Konfirmat (czoło) | Ø4.8 × 41 |
| Rozmieszczenie wiązania | kołki 32 od końców (+ środkowy przy L>400); konfirmaty 64 od końców + środek + co ≤450 |
| Krótki element L≤150 | kołek 32 + konfirmat L−32; L<90 — jeden konfirmat na środku |
| Bok widoczny | tylko kołki (bez konfirmatów) |
| Półka ruchoma (p32) | Ø5 × 12, 3 otw. co 32 (lub p64 — co 64), Y=50 i DY−50 |
| Zawias — płytka na boku | Ø5 × 12, Y=37, ±16 od osi (2 otw. co 32) |
| Zawias — puszka na froncie | Ø35 × 13, Y=22.5; INSERTA Ø8 × 11.5, Y=32, ±22.5 |
| Prowadnica (ogólna) | Ø5 × 12, Y=37 i 261 |
| Tył z płyty | Y=DY−9: kołek DZ+32, konfirmat Ø7 DZ+68 / DX−DZ−32, kołek DX−DZ−68; dłuższe — dodatkowe co ≤600 |
| Tył widoczny | kołki + mimośród Ø25 × 12, Y=DY−17 |
| Szorta (trawers) | kołek 32, konfirmat 68 od krawędzi, szerokość domyślna 100 |
| Zawieszki szafki górnej | X=51, Y=DY−66 / DY−34, Ø7 × 2 (znacznik) |
| Rowek HDF | piła T82, domyślnie Y=DY−16, głębokość 10 |
| Wycięcie / kieszeń | T104, C=2 |
| Otwór okrągły >Ø35 | frezowanie T104 po okręgu |

### Prowadnice Blum / GTV (Ø5 × 12, Y od przodu)

| Kod | System | NL | Y otworów | Min. oś nad wieńcem dolnym |
|---|---|---|---|---|
| ba | Blum TANDEMBOX antaro | ≤270 / ≤350 / ≤400 / ≤600 | 37,133 / 37,165 / 37,229 / 37,261 | 33 |
| lg | Blum LEGRABOX | ≤270 / ≤350 / ≤500 / ≤600 | 37,69,197 / 37,69,261 / +293 / +293,357 | 38 |
| mv | Blum MOVENTO | ≤270 / ≤350 / ≤600 | 37,69,197 / 37,69,261 / 37,69,261,293 | 38 |
| bt | Blum TANDEM 560H | ≤270/≤380/≤420/≤550/≤600 | 37,69,133 / 37,69,261 / 37,69,229 / 37,69,261 / 37,69,261,325 | 37 |
| mb | Blum MERIVOBOX | ≤350 / ≤600 | 37,69,197,229 / 37,69,261,293 | 54 |
| ax | GTV AXIS PRO | ≤270/≤350/≤400/≤550 | 37,133 / 37,165 / 37,229 / 37,261 | 22.8 nad spodem szuflady ⚠ |

NL = głębokość boku − 10 (bok 510 → NL500).

### Podnośniki AVENTOS (Ø5; X od górnej krawędzi boku X=0)

| Kod | System | X | Y | Z | Min. LH |
|---|---|---|---|---|---|
| hks | HK-S | 74 | 37, 101 | 5 | 150 |
| hk | HK top | 36 | 37, 69, 133, 165 | 11.5 | 173 |
| hkxs | HK-XS | 137+DZ, 169+DZ | 37 | 11.5 | 200 |
| hl | HL top | 63, 127 | 101, 229 | 11.5 | 255–399 |
| hs | HS top | 63, 127 | 101, 229 | 11.5 | 307 |
| hf | HF top | 116, 180 (KH<520: 93.5, 157.5) | 101, 229 | 11.5 | 443 |

### Typowe elementy (szablony edytora)

| Element | DX × DY |
|---|---|
| Bok szafki dolnej | 720 × 510 |
| Bok szafki górnej | 720 × 330 |
| Bok słupka | 2100 × 560 |
| Wieniec / półka stała | 564 × 510 |
| Półka ruchoma | 562 × 490 |
| Front | 716 × 596 |

Wzorcowe programy na PC maszyny: `Andrii\BOKI DOLNE`, `Andrii\BOKI GORNE FREZ NA2`, `TYLNE WIERCENIA`.

---

## 5. Edytor XXL (podgląd i edycja .xxl)

- Plik: `xxl.html` (to repozytorium, PWA, działa offline). Online: `https://andriiry.github.io/xxl/xxl.html` (GitHub Pages, jeśli włączone).
- Funkcje: otwieranie .xxl (📂 / przeciągnięcie), widok 2D elementu z czołami F2–F5, odtwarzanie krok po kroku, pomiar, dodawanie otworów, zakładki „Kod / Wymiary / Sprawdzenie / Tekst”, zapis z oryginalnym kodowaniem i CRLF.
- Widok: `↗0` — jak na stole (baza w prawym górnym rogu), `↙0` — jak w Xilog.
- ⚙: tabela narzędzi (Ø, nazwa), pole maszyny, liczenie wysokości (od bazy X=0 / od dołu szafki), język RU/PL.
- Polecenia tekstowe (pole ✍), generują XBO/XG0:

```
W 600                 wiązanie na 600: kołki + konfirmaty
W 600 widoczny        tylko kołki
W / W lewa / W prawa  wiązanie w czole F3+F2 / jedna strona
p32 300 · p64 300 650 półki ruchome
z 100 620             płytki zawiasów
zawias front 100 616  puszki Ø35 + INSERTA
ba 55.5 nl 450        prowadnica Blum (bt lg mv mb ax)
hks hk hkxs hl hs hf  AVENTOS
sz 9 · tyl · tw · zw  szorta / tył / tył widoczny / zawieszki
rowek hdf 510         rowek T82
otwór fi 8 gł 12 100 200 · konfirmat 100 200
wycięcie 200x100 na 300 150 gł 10 · okrąg fi 60 300 200
W 300; p32 600; W 900 kilka poleceń przez «;»
```
Po rosyjsku też: «под щит 600», «полки 300», «петли 100 600».

---

## 6. Braki — uzupełnić przy maszynie
- Parametry skrawania (S obr/min, F m/min) dla każdego T.
- Długości/wysięgi narzędzi, pozycje w magazynie.
- Konfiguracja głowicy wiertarskiej.
- Układ przyssawek/stref, podciśnienie.
- Korekcje, punkty zerowe Xilog, wersja Xilog Plus.
