---
name: brand-theming
description: >-
  Aplica y actualiza la identidad visual del cliente (colores, diales de estilo,
  logo, moneda y cultura) desde `brand-config.json` hacia SVGs, tema JSON PBIR,
  overrides visuales, tokens PBIVIZ y parámetros TMDL. Úsala cuando cambies de
  cliente, ajustes paleta/moneda o modifiques `brand-config.json`.
---

# Inyección Automática de Marca (`brand-config.json`)

Flujo automatizado para transformar la estética, logo y moneda del reporte PBIP sin editar manualmente decenas de archivos JSON, SVG o LESS/TS.

> [!NOTE]
> Consulta la referencia completa de campos y diales de estilo en [brand-config-schema.md](./references/brand-config-schema.md).

## Pasos Recomendados

1. **Cierra Power BI Desktop** antes de ejecutar cambios sobre el proyecto.
2. **Edita `brand-config.json`** en la raíz del proyecto:
   - `client`: nombre visible, subtítulo, breadcrumb, pie de página, `themeName` y `locale`.
   - `assets`: ruta al logo del cliente (`logoPath`) y nombre registrado (`registeredLogoName`).
   - `currency`: `code` (`USD`, `PEN`, `EUR`), `symbol`, `numberLocale` y `mode` (`auto` | `brand` | `custom`).
   - `style`: diales de variación controlada (`canvasPreset`, `cornerRadius`, `kpiSurfaceMode`, `sidebarMode`, `fontFamily`).
   - `colors`: paleta de marca (`brand`, `semantic`, `surfaces`, `text`, `dataColors`).
3. **Valida primero con simulación**:
   ```powershell
   python .agents/skills/brand-theming/scripts/apply_brand.py --dry-run
   ```
4. **Aplica la marca y valida QA**:
   ```powershell
   python .agents/skills/brand-theming/scripts/apply_brand.py
   ```
   - Usa `--skip-build` si solo cambiaste textos/colores PBIR o si no necesitas recompilar los `.pbiviz`.
   - Usa `--config <ruta>` para probar configuraciones alternas (ej. `templates/brand-config.example.json`).
5. **Verifica salida `0` errores** en `verify_all.py` antes de abrir el `.pbip`.
