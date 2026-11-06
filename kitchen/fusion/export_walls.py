# -*- coding: utf-8 -*-
"""Fusion 360: экспорт стен/окон/дверей/коммуникаций в JSON для конфигуратора кухни.

Установка: Fusion → Utilities → Add-Ins → Scripts and Add-Ins → «+» → выбрать эту папку/файл.
Именование тел (регистр не важен, достаточно начала имени):
  Стена*/Wall*, Окно*/Window*, Дверь*/Door*, Вода*/Water*, Канализ*/Sewer*, Газ*/Gas*,
  Розетк*/Socket*, Вытяж*/Vent*, Колонн*/Column*. Остальные тела → тип «other».
Экспортируются только ВИДИМЫЕ тела (лампочка включена). Берётся габаритный бокс (AABB):
наклонные стены аппроксимируются прямоугольником.
Единицы: мм. Вертикаль — Z (при Y-up спросит и пересчитает: x=X, y=-Z, z=Y).
"""
import adsk.core, adsk.fusion, traceback, json

KEYS = [
    ('wall', ['стена', 'wall']), ('window', ['окно', 'window']), ('door', ['дверь', 'door']),
    ('water', ['вода', 'water']), ('sewer', ['канализ', 'sewer', 'drain']), ('gas', ['газ', 'gas']),
    ('socket', ['розетк', 'socket', 'outlet']), ('vent', ['вытяж', 'vent', 'hood']),
    ('column', ['колонн', 'column', 'pillar']),
]


def kind(name):
    n = name.lower().strip()
    for k, prefixes in KEYS:
        for p in prefixes:
            if n.startswith(p):
                return k
    return 'other'


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('Откройте дизайн (Design).')
            return
        z_up = ui.messageBox('Вертикальная ось модели — Z?\n(Да = Z вверх, Нет = Y вверх)', 'Экспорт стен',
                             adsk.core.MessageBoxButtonTypes.YesNoButtonType) == adsk.core.DialogResults.DialogYes
        root = design.rootComponent
        bodies = list(root.bRepBodies)
        for occ in root.allOccurrences:
            bodies.extend(list(occ.bRepBodies))   # прокси-тела в контексте сборки
        out, zmax = [], 0.0
        for b in bodies:
            if not b.isVisible:
                continue
            bb = b.boundingBox
            mn, mx = bb.minPoint, bb.maxPoint
            k = 10.0  # см → мм
            if z_up:
                lo = [mn.x * k, mn.y * k, mn.z * k]
                hi = [mx.x * k, mx.y * k, mx.z * k]
            else:
                lo = [mn.x * k, -mx.z * k, mn.y * k]
                hi = [mx.x * k, -mn.z * k, mx.y * k]
            t = kind(b.name)
            if t == 'wall':
                zmax = max(zmax, hi[2])
            out.append({'name': b.name, 'type': t, 'min': [round(v, 1) for v in lo], 'max': [round(v, 1) for v in hi]})
        dlg = ui.createFileDialog()
        dlg.title = 'Сохранить стены'
        dlg.filter = 'JSON (*.json)'
        dlg.initialFilename = 'walls.json'
        if dlg.showSave() != adsk.core.DialogResults.DialogOK:
            return
        with open(dlg.filename, 'w', encoding='utf-8') as f:
            json.dump({'format': 'kitchen-walls/1', 'units': 'mm', 'height': round(zmax or 2700, 1), 'bodies': out}, f, ensure_ascii=False, indent=1)
        ui.messageBox('Экспортировано тел: %d\n%s' % (len(out), dlg.filename))
    except Exception:
        ui.messageBox('Ошибка:\n' + traceback.format_exc())
