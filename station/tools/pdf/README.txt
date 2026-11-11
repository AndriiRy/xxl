PDF сборки: docs/station_v6_sborka.pdf
1b) python3 steps.py ../../cad img  -> img/step1..7.png (иллюстрации сборки по шагам, позиции из module assembly())
1) python3 rp.py ../../cad base spacer deck housing alidade pod_lid_l pod_lid_r head head_lid v_cart v_hub v_drum v_knob collar foot fit_rings target_cyl target_mini
   -> img/*.png (миниатюры) + parts.json (объём, габарит)
2) db/items/*.json — выгрузка чек-листа (ArtifactData list items, out_dir=db)
3) python3 build.py  (reportlab, шрифты DejaVu)
