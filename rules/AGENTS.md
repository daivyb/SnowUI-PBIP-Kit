# Reglas Globales de Consultoría Power BI — SnowUI PBIP Kit

1. **Separación de configuración (`brand-config.json`)**: nunca edites colores hexadecimales o moneda manualmente en decenas de visuales o SVGs; actualiza `brand-config.json` y ejecuta `apply_brand.py`.
2. **Cierra Power BI Desktop antes de editar**: nunca modifiques `.tmdl`, `.json` PBIR o `CustomVisuals/` mientras Power BI Desktop esté abierto.
3. **Geometría anti-recorte**: todo `textbox` debe tener `height >= 34` (`38–42` recomendado) y todo `slicer` Dropdown `height >= 60` (`66` en topbar).
4. **Gestión segura de páginas**: usa `manage_pages.py` (`clone`, `delete`, `set-preset`, `sync`) para mantener consistentes `pages.json`, navegación lateral y `reset_filters.bookmark.json`.
5. **TMDL estricto**: indentación con tabulador (`\t`), `lineageTag`s UUID v4 únicos, sin colisiones columna/medida, y exclusividad entre `formatString:` y `formatStringDefinition =`.
6. **QA obligatorio**: ejecuta `verify_all.py` antes de entregar o abrir el `.pbip`.
