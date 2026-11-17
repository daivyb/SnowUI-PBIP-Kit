---
name: pbir-report-layout
description: >-
  Diseña, edita, duplica/elimina y audita las páginas PBIR por arquetipos,
  presets de lienzo (web-scroll / screen-16x9), coordenadas anti-recorte, slicers,
  botones de navegación, marcadores y tema visual SnowUI dentro de `<Proyecto>.Report/`.
  Úsala al ajustar tarjetas, agregar o quitar páginas, reubicar filtros o corregir recortes.
---

# Edición Modular y Auditoría PBIR

Procedimiento para componer páginas libres por arquetipos o editar visuales manteniendo integridad de esquema Microsoft, navegación sincronizada y cero recortes en Power BI Desktop.

> [!NOTE]
> Consulta la geometría de los arquetipos A/B/C, presets (`web-scroll` y `screen-16x9`) y sintaxis PBIR en [snowui-design-system.md](./references/snowui-design-system.md).

## Gestión Segura de Páginas (`manage_pages.py`)

Nunca dupliques o borres carpetas de página a mano sin actualizar `pages.json`, la barra lateral de todas las páginas y `reset_filters.bookmark.json`. Usa:

```powershell
# Duplicar una página arquetipo para un nuevo dominio de negocio
python .agents/skills/pbir-report-layout/scripts/manage_pages.py clone --source overview --target ventas --title "Ventas"

# Eliminar una página
python .agents/skills/pbir-report-layout/scripts/manage_pages.py delete --target ubicacion

# Cambiar preset de lienzo (web-scroll 1440x1708 <-> screen-16x9 1440x810)
python .agents/skills/pbir-report-layout/scripts/manage_pages.py set-preset --target all --preset screen-16x9

# Resincronizar sidebar y reset_filters tras ediciones manuales
python .agents/skills/pbir-report-layout/scripts/manage_pages.py sync
```

## Validación Obligatoria

1. **Cierra Power BI Desktop** antes de modificar archivos PBIR.
2. **Respeta alturas mínimas**: `textbox` ≥ `34px` (`38–42px` recomendado), `slicer` Dropdown ≥ `60px` (`66px` en topbar).
3. **Audita integridad y bindings contra TMDL**:
   ```powershell
   python .agents/skills/pbir-report-layout/scripts/audit_pbir_layout.py
   ```
