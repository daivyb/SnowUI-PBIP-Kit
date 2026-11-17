# Guía de Instanciación y Uso — Plantilla Maestra SnowUI PBIP

Esta guía explica cómo arrancar un proyecto de consultoría nuevo desde cero usando el **Plugin Global (`snowui-pbip-kit`)** y el **Starter Kit neutro**, manteniendo libertad para diseñar páginas y ajustar el estilo por cliente.

---

## 1. Arrancar un Proyecto Nuevo para Otro Cliente

Desde cualquier carpeta destino (por ejemplo `C:\Clientes\EmpresaX`), ejecuta `scaffold_client.py` (incluido en el plugin global `~/.gemini/config/plugins/snowui-pbip-kit/skills/pbip-golden-template/scripts/scaffold_client.py` o en `.agents/skills/pbip-golden-template/scripts/scaffold_client.py`):

```powershell
python C:\Users\Acer\.gemini\config\plugins\snowui-pbip-kit\skills\pbip-golden-template\scripts\scaffold_client.py `
  --target "C:\Clientes\EmpresaX" `
  --name "AnaliticaEmpresaX" `
  --preset web-scroll `
  --git-init
```

Opciones útiles:
- `--brand-config C:\ruta\brand-config.json`: aplica inmediatamente colores, logo, moneda y diales de estilo del cliente.
- `--preset screen-16x9`: configura el lienzo en `1440 × 810` (`FitToPage`, sin scroll vertical) si el cliente prefiere vista ejecutiva de pantalla completa.
- `--copy-skills`: copia `.agents/` al repositorio del cliente para equipos que trabajan en Git sin el plugin global instalado.

> [!NOTE]
> El `starter-kit/` nace con un modelo inline autocontenido (`DimFecha`, `DimMes`, `DimMonedaSelector` y `FactBase`) sin dependencias externas de Excel, por lo que abre y refresca de inmediato en Power BI Desktop.

---

## 2. Personalizar Marca, Estilo y Moneda (`brand-config.json`)

1. Coloca el logotipo del cliente (`SVG` o `PNG`) en `assets/` dentro del proyecto.
2. Edita `brand-config.json`:
   - **`client`**: `name`, `subtitle`, `breadcrumbRoot`, `footerText`, `themeName`, `locale`.
   - **`currency`**: `code` (`USD`, `PEN`, `EUR`, etc.), `symbol` (`$`, `S/ `, `€`), `numberLocale` (`en-US`, `es-PE`), `mode: "auto"`.
   - **`style`** *(diales de diferenciación entre clientes)*:
     - `canvasPreset`: `"web-scroll"` | `"screen-16x9"`
     - `cornerRadius`: `12` (corporativo recto) | `18` (SnowUI estándar) | `24` (suave)
     - `kpiSurfaceMode`: `"gradient"` | `"solid"` | `"light-bordered"`
     - `sidebarMode`: `"light"` | `"tinted"` | `"dark"`
   - **`colors`**: `brand`, `semantic`, `surfaces`, `text`, `dataColors`.
3. Ejecuta:
   ```powershell
   python .agents/skills/brand-theming/scripts/apply_brand.py --skip-build
   ```
   *(Omite `--skip-build` si además quieres compilar los tokens en `pbiviz/_common/snowuiTokens.*` con el toolchain local o `--pbiviz-cmd`).*

---

## 3. Componer Páginas Propias del Negocio (Arquetipos PBIR)

Las páginas **no** tienen que replicar el proyecto demo. Parte de la página base `resumen` y crea tantas páginas como requiera el cliente (`ventas`, `margen`, `inventario`, `regional`, etc.) usando `manage_pages.py`:

```powershell
# Clonar una página existente/arquetipo con nuevo ID y título
python .agents/skills/pbir-report-layout/scripts/manage_pages.py clone --source resumen --target ventas --title "Ventas"

# Eliminar una página
python .agents/skills/pbir-report-layout/scripts/manage_pages.py delete --target ubicacion

# Cambiar todas las páginas a formato 16:9 sin scroll
python .agents/skills/pbir-report-layout/scripts/manage_pages.py set-preset --target all --preset screen-16x9
```

`manage_pages.py` actualiza automáticamente:
1. La carpeta `definition/pages/<page_id>/` y su `page.json`.
2. Todos los prefijos internos `<page_id>_*` de Chrome/Sidebar/Topbar.
3. `definition/pages/pages.json` (`pageOrder`, `activePageName`, `landingPageName`).
4. Los botones de navegación lateral (`actionButton`) e indicador activo en **todas** las páginas.
5. `definition/bookmarks/reset_filters.bookmark.json`.

---

## 4. Configurar Multimoneda en DAX (`brand-config.json` + `DimMonedaSelector`)

- **Modo estándar (`exposeCurrencySlicer: false`)**: declara `formatString: \$#,0.00;(\$#,0.00);\$#,0.00` en tus medidas monetarias. Al cambiar `currency.code` en `brand-config.json` (ej. `PEN`, `EUR`, `USD`), `apply_brand.py` actualiza el `formatString:` de las medidas y los 4 visuales SnowUI (`currencyMode: "auto"`) detectan automáticamente el símbolo (`$`, `S/`, `€`, `%` o conteos `#,0`).
- **Selector interactivo en vivo (opcional)**: la tabla desconectada `DimMonedaSelector.tmdl` incluye `CodigoMoneda`, `Simbolo`, `FormatoDAX` y `TipoCambioBase`. Si expones un slicer de moneda en el reporte, multiplica la medida base por `[Factor Tipo Cambio]` y usa `formatStringDefinition =` con un `SWITCH(SELECTEDVALUE(DimMonedaSelector[CodigoMoneda], ...), ...)` con cadenas literales en cada rama (sin `formatString:` simultáneo), refrescando el modelo en Power BI Desktop.

---

## 5. Verificación Final Antes de Entregar

```powershell
python .agents/skills/pbip-qa-verify/scripts/verify_all.py
```

Asegúrate de obtener `QA INTEGRAL COMPLETADA CON EXITO (0 ERRORES)` antes de abrir `<Proyecto>.pbip` en Power BI Desktop.

---

## 6. Promover Mejoras desde Cualquier Proyecto hacia el Plugin Global (Opcional)

Los ajustes específicos del cliente (`brand-config.json`, colores, moneda, páginas de negocio) **permanecen aislados** en su carpeta. Cuando desarrolles una mejora estándar (un visual mejorado, un 5.º visual nuevo en `pbiviz/`, `_common/` o skills) y quieras incorporarla al estándar para futuros proyectos:

1. Simula primero con `--dry-run` desde la carpeta del proyecto cliente:
   ```powershell
   python C:\Users\Acer\.gemini\config\plugins\snowui-pbip-kit\skills\pbip-golden-template\scripts\promote_to_plugin.py --from . --visuals snowuiPillTable --dry-run
   ```
2. Ejecuta sin `--dry-run` (agrega `--include-common` si tocaste `pbiviz/_common/`, o `--include-skills` si actualizaste scripts):
   - Copia **solo** el código del visual (`src/`, `style/`, `capabilities.json`, `assets/`, `pbiviz.json`), excluyendo `snowuiTokens.*` y `brand-config.json` del cliente.
   - Reaplica la marca neutra del `starter-kit/`, recompila usando el toolchain local/compartido (`SNOWUI_PBIVIZ_CMD` / `SNOWUI_PBIVIZ_SHARED_NM` / `%LOCALAPPDATA%\SnowUIPbipKit\`) y ejecuta `verify_all.py`.
   - Respeta `.git/` del plugin para que revises el diff y hagas `git commit` / `git push` cuando tú decidas.
