# Proyecto Power BI SnowUI (`PBIP / PBIR / TMDL / PBIVIZ`)

Proyecto estructurado bajo el estándar **SnowUI PBIP Kit**: **TMDL** (`<Proyecto>.SemanticModel/`), **PBIR** (`<Proyecto>.Report/`), **4 visuales personalizados SnowUI (PBIVIZ)** (`pbiviz/`) y configuración centralizada de marca, moneda y diales de estilo en [brand-config.json](./brand-config.json).

## Reglas Operativas Críticas

1. **Cerrar Power BI Desktop antes de editar**: nunca modifiques `.tmdl`, `.json` PBIR o `CustomVisuals/` mientras Power BI Desktop tenga abierto el `.pbip`.
2. **Única fuente de verdad visual (`brand-config.json`)**: tras cambiar colores, logo, moneda o diales en `brand-config.json`, ejecuta `apply_brand.py`.
3. **Gestión segura de páginas**: usa `manage_pages.py` (`clone`, `delete`, `set-preset`, `sync`) para componer páginas libres y alternar entre `web-scroll` (`1440×1708`) y `screen-16x9` (`1440×810`).
4. **Cero colisiones en TMDL ni doble formato**: ninguna `measure` puede llamarse igual que una `column` en la misma tabla, y nunca mezcles `formatString:` con `formatStringDefinition =`.
5. **Verificación previa al cierre**: ejecuta `verify_all.py` después de cualquier cambio antes de abrir Power BI Desktop.
