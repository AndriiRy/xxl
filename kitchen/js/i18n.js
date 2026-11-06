// Перевод интерфейса RU → PL (фразы; применяется к любому тексту на странице через MutationObserver)
(function (K) {
'use strict';
const PL = {
  'Конфигуратор кухни': 'Konfigurator kuchni', 'Новый': 'Nowy', 'Открыть': 'Otwórz', 'Сохранить проект': 'Zapisz projekt', 'Стены из Fusion…': 'Ściany z Fusion / LiDAR…',
  'CSV раскрой': 'CSV rozkrój', 'Настройки': 'Ustawienia', 'Библиотека': 'Biblioteka', 'Стены': 'Ściany', 'План': 'Rzut', 'Спецификация': 'Specyfikacja', 'Редактор модуля': 'Edytor korpusu',
  'Шкафов': 'Szafek', 'пересечений': 'kolizji', 'замечаний': 'uwag', 'ошибок': 'błędów',
  'Столешницы автоматически': 'Blaty automatycznie', 'Новый модуль': 'Nowy moduł', 'Экспорт': 'Eksport', 'Импорт': 'Import', 'Сброс': 'Reset',
  'Нижние': 'Dolne', 'Верхние': 'Górne', 'Пеналы': 'Słupki', 'Столешницы': 'Blaty', 'Доборы': 'Blendy', 'Прочее': 'Inne',
  'Нижний с дверцами': 'Dolna z drzwiami', 'Нижний под угол (косые боки)': 'Dolna pod kątem (skośne boki)', 'Нижний с ящиками': 'Dolna z szufladami', 'Верхний с дверцами': 'Górna z drzwiami',
  'Пенал под скос (скос по ширине)': 'Słupek pod skos (skos po szerokości)', 'Пенал с вырезом под балку': 'Słupek z wycięciem pod belkę', 'Пенал': 'Słupek', 'Столешница': 'Blat', 'Фальшпанель / бленда': 'Blenda / panel maskujący', 'Фальшпанель': 'Blenda',
  'Бок левый (торцы под углом)': 'Bok lewy (krawędzie pod kątem)', 'Бок правый (торцы под углом)': 'Bok prawy (krawędzie pod kątem)', 'Бок левый (с вырезом)': 'Bok lewy (z wycięciem)', 'Бок правый (с вырезом)': 'Bok prawy (z wycięciem)',
  'Бок левый': 'Bok lewy', 'Бок правый': 'Bok prawy', 'Дно (трапеция)': 'Wieniec dolny (trapez)', 'Дно (бока на дне)': 'Wieniec dolny (boki na wieńcu)', 'Дно (между боков)': 'Wieniec dolny (między bokami)', 'Дно': 'Wieniec dolny',
  'Царга передняя (трапеция)': 'Trawers przedni (trapez)', 'Царга задняя (трапеция)': 'Trawers tylny (trapez)', 'Царга передняя': 'Trawers przedni', 'Царга задняя': 'Trawers tylny',
  'Крышка наклонная (торцы под углом)': 'Wieniec górny skośny', 'Крышка (на боках)': 'Wieniec górny (na bokach)', 'Крышка (между боков)': 'Wieniec górny (między bokami)', 'Крышка': 'Wieniec górny',
  'Задняя стенка (скос)': 'Plecy (skos)', 'Задняя стенка (накладная)': 'Plecy (nakładane)', 'Задняя стенка (в паз 10 мм)': 'Plecy (we wpust 10 mm)', 'Задняя стенка (внутри)': 'Plecy (wewnątrz)', 'Задняя стенка': 'Plecy HDF',
  'Полка (трапеция)': 'Półka (trapez)', 'Полка выреза': 'Półka wycięcia', 'Стенка выреза': 'Ścianka wycięcia', 'Полка': 'Półka', 'Фасад со скосом': 'Front ze skosem', 'Фасад (дверь)': 'Front (drzwi)', 'Фасад (ящик)': 'Front (szuflada)',
  'Ящик: боковина': 'Szuflada: bok', 'Ящик: перед/зад': 'Szuflada: przód/tył', 'Ящик: дно ХДФ': 'Szuflada: dno HDF', 'Цоколь': 'Cokół',
  'Ширина по фронту': 'Szerokość frontu', 'Ширина': 'Szerokość', 'Высота слева': 'Wysokość z lewej', 'Высота справа': 'Wysokość z prawej', 'Высота': 'Wysokość', 'Глубина корпуса': 'Głębokość korpusu', 'Глубина от стены': 'Głębokość od ściany', 'Глубина': 'Głębokość',
  'Полок': 'Półek', 'Дверей (0 = авто)': 'Drzwi (0 = auto)', 'Ящиков': 'Szuflad', 'Толщина': 'Grubość', 'Длина по стене (по заднему краю)': 'Długość po ścianie (tylna krawędź)', 'Длина': 'Długość',
  'Угол левого бока, ° (+ сзади уже)': 'Kąt lewego boku, ° (+ węższy z tyłu)', 'Угол правого бока, °': 'Kąt prawego boku, °',
  'Подрезка левого торца, ° (+ наружный угол, − внутренний)': 'Docięcie lewego końca, ° (+ narożnik zewn., − wewn.)', 'Подрезка правого торца, °': 'Docięcie prawego końca, °',
  'Вырез: высота': 'Wycięcie: wysokość', 'Вырез: глубина от задней стороны': 'Wycięcie: głębokość od tyłu',
  'Метка': 'Etykieta', 'Положение': 'Położenie', 'Поворот °': 'Obrót °', 'Доп. высота, мм': 'Dod. wysokość, mm', 'Отступ от стены до ХДФ, мм': 'Odsunięcie od ściany do HDF, mm',
  'держать фронт корпуса на': 'trzymaj front korpusu', 'мм от стены (меняется глубина)': 'mm od ściany (zmienia się głębokość)',
  'К стене': 'Do ściany', 'Подогнать к стыкам': 'Dopasuj do łączeń', 'Копия': 'Kopia', 'Удалить': 'Usuń', 'Детали': 'Elementy', 'Редактировать модуль': 'Edytuj moduł',
  'Выберите шкаф на плане или добавьте модуль из библиотеки (перетащите на план — он сам встанет к ближайшей стене).': 'Wybierz szafkę na rzucie lub dodaj moduł z biblioteki (przeciągnij na rzut — sam stanie przy najbliższej ścianie).',
  'Комната-заготовка': 'Pomieszczenie-szablon', 'Длина X': 'Długość X', 'Глубина Y': 'Głębokość Y', 'Толщина стен': 'Grubość ścian', 'Эркер ½ восьмиугольника (север)': 'Wykusz ½ ośmiokąta (północ)',
  'Ширина проёма': 'Szerokość otworu', 'Глубина (стороны 45°)': 'Głębokość (boki 45°)', 'Высота парапета': 'Wysokość parapetu', 'Верх окна': 'Góra okna', 'дверь, вода, розетка': 'drzwi, woda, gniazdko', 'Создать': 'Utwórz',
  'Импорт стен из Fusion (JSON)': 'Import ścian (Fusion JSON / LiDAR RoomPlan JSON / OBJ)', 'Тела': 'Bryły', 'Имя': 'Nazwa', 'Тип': 'Typ', 'Контур x,y; x,y…': 'Kontur x,y; x,y…', '+ Тело': '+ Bryła',
  'Стены по длинам и углам': 'Ściany wg długości i kątów', 'Старт X, Y': 'Start X, Y', 'комната слева': 'pomieszczenie po lewej', 'Добавить стены': 'Dodaj ściany',
  'Балка / скос потолка': 'Belka / skos sufitu', 'Линия X1,Y1 – X2,Y2': 'Linia X1,Y1 – X2,Y2', 'Балка: ширина': 'Belka: szerokość', 'Балка: низ от пола': 'Belka: spód od podłogi', '+ Балка (по оси линии)': '+ Belka (po osi linii)',
  'Скос: высота у линии': 'Skos: wysokość przy linii', 'Скос: высота на расстоянии': 'Skos: wysokość w odległości', 'Расстояние в комнату (± сторона)': 'Odległość w głąb (± strona)', '+ Скос': '+ Skos',
  'Стена': 'Ściana', 'Парапет': 'Parapet', 'Балка': 'Belka', 'Скос потолка': 'Skos sufitu', 'Потолок/выступ': 'Sufit/występ', 'Окно': 'Okno', 'Дверь': 'Drzwi', 'Вода': 'Woda', 'Канализация': 'Kanalizacja', 'Газ': 'Gaz', 'Розетка': 'Gniazdko', 'Вытяжка': 'Okap', 'Колонна': 'Kolumna',
  'Материалы': 'Materiały', 'Роль': 'Rola', 'Название': 'Nazwa', 'Кромка': 'Obrzeże', 'Корпус': 'Korpus', 'Фасады': 'Fronty', 'Размеры кухни, мм': 'Wymiary kuchni, mm', 'Лист': 'Płyta', 'Длина × ширина': 'Długość × szerokość', 'Запас на отход': 'Zapas na odpad', 'Применить': 'Zastosuj', 'Отмена': 'Anuluj',
  'Зазор между фасадами': 'Szczelina między frontami', 'Высота цоколя': 'Wysokość cokołu', 'Высота корпуса нижних': 'Wysokość korpusu dolnych', 'Низ верхних шкафов от пола': 'Spód górnych od podłogi', 'Высота верхних': 'Wysokość górnych', 'Высота пеналов': 'Wysokość słupków',
  'Отступ нижних от стены до ХДФ (30–52)': 'Odsunięcie dolnych od ściany do HDF (30–52)', 'Отступ верхних от стены': 'Odsunięcie górnych od ściany', 'Фронт корпуса от стены': 'Front korpusu od ściany', 'Глубина столешницы (напуск = глубина − фронт)': 'Głębokość blatu (nawis = głębokość − front)',
  'Сохранить в библиотеку': 'Zapisz w bibliotece', 'Закрыть': 'Zamknij', 'Низ от пола:': 'Spód od podłogi:', 'Габарит (контур, пусто = W×D):': 'Obrys (pusty = W×D):', 'к стене': 'do ściany', 'в наружный угол': 'w narożnik zewn.',
  'Параметры': 'Parametry', 'Переменные (считаются по порядку)': 'Zmienne (liczone po kolei)', 'Фурнитура': 'Okucia', 'Шаги сборки (по строке на шаг)': 'Kroki montażu (wiersz = krok)', '+ строка': '+ wiersz', '+ Добавить': '+ Dodaj',
  'Мастер корпуса:': 'Kreator korpusu:', 'между боков': 'między bokami', 'бока на дне': 'boki na wieńcu', 'царги': 'trawersy', 'крышка между боков': 'wieniec między bokami', 'крышка на боках': 'wieniec na bokach', 'без верха': 'bez góry',
  'внутри (накладная в проём)': 'wewnątrz (w światło)', 'в паз 10 мм': 'we wpust 10 mm', 'накладная сзади': 'nakładane z tyłu', 'Заменить каркас': 'Zamień korpus',
  'Деталь': 'Element', 'Матер.': 'Mater.', 'Кол-во': 'Ilość', 'размер x': 'wymiar x', 'размер y': 'wymiar y', 'размер z / толщина': 'wymiar z / grubość', 'поворот z°': 'obrót z°', 'Ось Д': 'Oś dł.', 'Присадка': 'Wiercenie', 'Присадка в': 'Wiercenie w', 'Петли': 'Zawiasy', 'Если': 'Jeśli', 'Плоскость контура': 'Płaszczyzna', 'Контур=сечение': 'Kontur=przekrój',
  'По умолч.': 'Domyśl.', 'или формула': 'lub wzór', 'шаг': 'krok', 'Формула': 'Wzór', 'Кол-во (формула)': 'Ilość (wzór)',
  'Предпросмотр: тяните — вращение, колесо — масштаб, Shift+тяните — сдвиг.': 'Podgląd: przeciągnij — obrót, kółko — zoom, Shift+przeciągnij — przesuw.',
  'Печать / PDF': 'Drukuj / PDF', 'CSV для раскроя': 'CSV do rozkroju', 'Спецификация проекта': 'Specyfikacja projektu',
  '1. Технический анализ изделия': '1. Analiza techniczna', '2. Материалы и фурнитура': '2. Materiały i okucia', '3. Деталировка (карта раскроя)': '3. Formatki (rozkrój)', '4. Пошаговый процесс изготовления': '4. Proces produkcji', '5. Инструкция по сборке': '5. Instrukcja montażu',
  'Развёртки стен (мм)': 'Rozwinięcia ścian (mm)', 'Чертежи корпусов (мм)': 'Rysunki korpusów (mm)', 'вид спереди': 'widok z przodu', 'вид сбоку (фронт слева)': 'widok z boku (front z lewej)', 'до стены': 'do ściany', 'длина стены': 'długość ściany',
  'Модуль': 'Moduł', 'Ш×В×Г, мм': 'S×W×G, mm', 'Низ от пола, мм': 'Spód od podłogi, mm', 'Позиция (x; y), поворот': 'Pozycja (x; y), obrót', 'Замечания:': 'Uwagi:',
  'Элемент': 'Element', 'Материал': 'Materiał', 'Толщина, мм': 'Grubość, mm', 'Деталей, шт': 'Elementów, szt', 'Площадь, м²': 'Powierzchnia, m²', 'Кромка, м.п.': 'Obrzeże, mb', 'Фурнитура / крепёж': 'Okucia / łączniki',
  'Шкафы': 'Szafki', 'Шт': 'Szt', 'Д×Ш, мм': 'Dł×Szer, mm', 'фигурная': 'kształtka', 'Фигурные детали — раскрой по шаблону': 'Kształtki — rozkrój wg szablonu', 'Вершины': 'Wierzchołki', 'заготовка': 'formatka',
  'Раскрой:': 'Rozkrój:', 'Кромление:': 'Oklejanie:', 'Присадка:': 'Wiercenie:', 'Общий порядок на объекте': 'Kolejność montażu na obiekcie',
  'ЛДСП корпус': 'Płyta wiórowa korpus', 'МДФ/ЛДСП фасад': 'Front MDF/płyta', 'ХДФ': 'HDF', 'Столешница (спек)': 'Blat (spiek)',
  'Ножка регулируемая': 'Nóżka regulowana', 'Ручка': 'Uchwyt', 'Конфирмат': 'Konfirmat', 'Полкодержатель': 'Podpórka półki', 'Петля накладная с планкой (чашка Ø35)': 'Zawias nakładany z prowadnikiem (puszka Ø35)', 'Евровинт 6,3×13 для планки петли': 'Wkręt euro 6,3×13 do prowadnika',
  'Направляющие шариковые полного выдвижения': 'Prowadnice kulkowe pełnego wysuwu', 'Саморез': 'Wkręt', 'крепление фасада ящика': 'mocowanie frontu szuflady', 'Навес шкафа регулируемый': 'Zawieszka regulowana', 'Уголок мебельный': 'Kątownik meblowy',
  'Петли': 'Zawiasy', 'Ящики': 'Szuflady', 'Подъёмники': 'Podnośniki', 'Аксессуары': 'Akcesoria', 'Ручки': 'Uchwyty', 'Техника': 'AGD',
  'пласть': 'płaszczyzna', 'торец': 'krawędź', 'сквозное': 'przelotowe', 'в торец': 'w krawędź', 'чашка петли, 22,5 от кромки': 'puszka zawiasu, 22,5 od krawędzi', 'планка петли': 'prowadnik zawiasu', 'под полку': 'pod półkę',
  'рёбра': 'krawędzie', 'Нет шкафов': 'Brak szafek', 'Сохранено': 'Zapisano', 'заходит на': 'nachodzi na', 'изделие': 'element', 'окно': 'okno', 'мм от пола': 'mm od podłogi', 'ошибка модуля': 'błąd modułu',
  'Столешниц создано': 'Utworzono blatów', 'Торцы у изломов стен подрезаны под угол стыка.': 'Końce przy załamaniach ścian docięte pod kąt łączenia.', 'Нет рядов нижних шкафов спиной к стене.': 'Brak rzędów dolnych szafek przy ścianie.',
  'План: колесо — масштаб, перетаскивание пустого места — сдвиг, двойной клик — вписать. Alt при перетаскивании — без прилипания. R — повернуть 90°, Shift+R — 45°, Del — удалить. Угловой модуль эркера бросайте у наружного угла эркера.': 'Rzut: kółko — zoom, przeciąganie tła — przesuw, dwuklik — dopasuj. Alt przy przeciąganiu — bez przyciągania. R — obrót 90°, Shift+R — 45°, Del — usuń. Szafka pod kątem przy załamaniu ściany sama dopasuje się do łączenia blatu.',
  'Листов': 'Płyt', '(копия)': '(kopia)', 'с запасом': 'z zapasem', 'ошибка формулы кол-ва': 'błąd wzoru ilości', 'Неизвестная переменная': 'Nieznana zmienna', 'в формуле': 'we wzorze',
  'Нижний с ящиками (Antaro)': 'Dolna z szufladami (Antaro)', 'Под духовку + ящик (Antaro)': 'Pod piekarnik + szuflada (Antaro)', 'Под мойку (ящик Antaro / двери)': 'Pod zlew (szuflada Antaro / drzwi)',
  'Карго (cargo)': 'Cargo', 'Посудомойка встраиваемая (фасад)': 'Zmywarka do zabudowy (front)', 'Колонна под холодильник': 'Słupek na lodówkę', 'Верхний над вытяжкой (подшкафная)': 'Górna nad okapem (podszafkowy)',
  'Конструктор фасадов': 'Konstruktor frontów', 'Сгенерировать фасады и наполнение': 'Generuj fronty i wyposażenie', 'Секция': 'Sekcja', 'ящик': 'szuflada', 'дверь': 'drzwi', 'ниша': 'wnęka', 'открытая': 'otwarta',
  'Высота фасада, мм (0 = авто)': 'Wysokość frontu, mm (0 = auto)', 'Перенос телефон ⇄ компьютер': 'Przeniesienie telefon ⇄ komputer', 'Скачать всё (проект, стены, библиотека, настройки)': 'Pobierz wszystko (projekt, ściany, biblioteka, ustawienia)', 'Загрузить всё': 'Wczytaj wszystko',
  'Фасад ПММ': 'Front zmywarki', 'Фасад холодильника': 'Front lodówki', 'Фасад морозилки (нижний)': 'Front zamrażarki (dolny)', 'Фасад карго': 'Front cargo', 'Полка над холодильником': 'Półka nad lodówką', 'Полка под духовку': 'Półka pod piekarnik', 'Перегородка': 'Przegroda',
  'Ниша холодильника (высота)': 'Wnęka lodówki (wysokość)', 'Высота ниши духовки': 'Wysokość wnęki piekarnika', 'Высота вытяжки (ниша снизу)': 'Wysokość okapu (wnęka od dołu)', 'Глубина корпуса (бок)': 'Głębokość korpusu (bok)',
  'Каркас': 'Korpus', 'Фасады:': 'Fronty:', 'Ножки, цоколь.': 'Nóżki, cokół.', 'зазоры 2 мм': 'szczeliny 2 mm'
};
K.lang = 'ru';
const keys = Object.keys(PL).sort((a, b) => b.length - a.length);
K.tr = function (s) {
  if (K.lang !== 'pl' || !s || !/[А-Яа-яЁё]/.test(s)) return s;
  for (const k of keys) if (s.includes(k)) s = s.split(k).join(PL[k]);
  return s;
};
function walk(n) {
  if (n.nodeType === 3) { const t = K.tr(n.nodeValue); if (t !== n.nodeValue) n.nodeValue = t; return; }
  if (n.nodeType !== 1 || n.tagName === 'SCRIPT' || n.tagName === 'STYLE') return;
  for (const a of ['title', 'placeholder']) if (n.hasAttribute && n.hasAttribute(a)) n.setAttribute(a, K.tr(n.getAttribute(a)));
  for (const c of n.childNodes) walk(c);
}
K.setLang = function (l) {
  K.lang = l === 'pl' ? 'pl' : 'ru';
  document.documentElement.lang = K.lang;
  if (K.lang !== 'pl') return;
  walk(document.body);
  new MutationObserver((ms) => { for (const m of ms) for (const n of m.addedNodes) walk(n); }).observe(document.body, { childList: true, subtree: true });
  const A = window.alert.bind(window), C = window.confirm.bind(window);
  window.alert = (m) => A(K.tr(String(m))); window.confirm = (m) => C(K.tr(String(m)));
};
})(window.K = window.K || {});
