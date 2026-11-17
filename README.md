# SnowUI PBIP Kit

Plugin global para **Google Antigravity** y plantilla maestra de consultoría **Power BI Desktop (`PBIP / PBIR / TMDL / PBIVIZ`)** bajo el sistema de diseño **SnowUI**.

Permite crear reportes corporativos estandarizados donde la arquitectura visual, la navegación, el modelo estrella y los visuales personalizados son reutilizables, mientras que la marca, logotipo, moneda y diales de estilo de cada cliente se controlan desde un único archivo `brand-config.json`.

---

## Estructura del Repositorio

```text
snowui-pbip-kit/
├── plugin.json                        # Manifiesto del plugin Antigravity
├── rules/
│   └── AGENTS.md                      # Reglas globales operativas (TMDL, PBIR, QA)
├── skills/                            # Skills y scripts reutilizables
│   ├── _shared/pbip_paths.py          # Descubrimiento dinámico de *.pbip, visuales PBIVIZ y toolchain
│   ├── pbip-golden-template/          # scaffold_client.py y promote_to_plugin.py
│   ├── brand-theming/                 # apply_brand.py (SVGs, tema JSON, PBIR, tokens PBIVIZ y TMDL)
│   ├── pbir-report-layout/            # manage_pages.py (clone/delete/set-preset/sync) y audit_pbir_layout.py
│   ├── pbiviz-custom-visual-dev/      # build_and_unpack_pbiviz.py (compila y registra visuales)
│   ├── tmdl-semantic-model/           # audit_tmdl.py y catálogo base
│   └── pbip-qa-verify/                # verify_all.py (orquestador integral QA)
└── starter-kit/                       # Plantilla neutra lista para clonar en nuevos clientes
    ├── Template.pbip
    ├── Template.Report/               # Página base 'resumen', marcadores y CustomVisuals desempaquetados
    ├── Template.SemanticModel/        # Modelo inline autocontenido (DimFecha, DimMes, DimMonedaSelector, FactBase)
    ├── pbiviz/                        # Código TypeScript/LESS y dist/ de los visuales SnowUI
    ├── brand-config.json              # Tokens neutros base (USD $, #007AFF)
    ├── brand-config.schema.json
    └── TEMPLATE_GUIDE.md
```

### Visuales Personalizados Base (`starter-kit/pbiviz/`)

| Carpeta | `visualType` (GUID) | Propósito |
| :--- | :--- | :--- |
| `snowuiKpiCard` | `snowuiKpiCardE1A4B801` | Tarjeta KPI animada con variantes de superficie (`gradient`, `solid`, `light-bordered`), delta `%` y autoajuste tipográfico |
| `snowuiSplineChart` | `snowuiSplineChartE1A4B802` | Curva suavizada Área/Línea con pestañas de métricas, cambio de granularidad (`measures` + `altMeasures`) y callout flotante |
| `snowuiPillBarChart` | `snowuiPillBarChartE1A4B803` | Barras tipo cápsula (`pill`) y micro-barras apiladas (`microStacked`) con leyenda interactiva y etiquetas de eje con ajuste de líneas |
| `snowuiPillTable` | `snowuiPillTableE1A4B804` | Tabla ejecutiva en filas cápsula con avatares monograma, ordenamiento por columna, badges de estado e indicador de filas |

> El kit descubre dinámicamente todos los visuales en `pbiviz/*/pbiviz.json`, por lo que puedes agregar un 5.º o N.º visual nuevo y entrará automáticamente en compilación, branding, registro en `report.json` y auditoría QA.

---

## Requisitos e Instalación en un Equipo Nuevo

* **Power BI Desktop** (con formato **PBIP/PBIR** habilitado).
* **Python 3.10+**.
* **Git**.
* *(Solo si deseas recompilar o crear visuales `.pbiviz`)* **Node.js + `powerbi-visuals-tools`**.

### 1. Instalar o actualizar el plugin desde GitHub

**Git Bash:**
```bash
git clone https://github.com/daivyb/SnowUI-PBIP-Kit.git /c/Users/Acer/.gemini/config/plugins/snowui-pbip-kit
```
*(En otra PC reemplaza la ruta por `~/.gemini/config/plugins/snowui-pbip-kit`.)*

Para actualizar a la última versión en cualquier momento:
```bash
git -C ~/.gemini/config/plugins/snowui-pbip-kit pull --rebase origin main
```

### 2. Toolchain PBIVIZ compartida (opcional, 1 sola vez por equipo)

Los proyectos generados para clientes no copian `node_modules/` (~113 MB). Para compilar gráficos desde cualquier carpeta cliente sin reinstalar paquetes en cada proyecto, coloca una sola vez `_tools/` y `_shared/` en `%LOCALAPPDATA%\SnowUIPbipKit\`:

```text
%LOCALAPPDATA%\SnowUIPbipKit\
├── _tools\node_modules\.bin\pbiviz.cmd    # powerbi-visuals-tools + loaders webpack (ts-loader, less-loader)
└── _shared\node_modules\                  # d3, powerbi-visuals-api, formattingmodel, typescript
```

También puedes apuntar explícitamente con variables de entorno (`SNOWUI_PBIVIZ_CMD`, `SNOWUI_PBIVIZ_SHARED_NM`, `SNOWUI_PBIVIZ_TOOLS_NM`) o flags `--pbiviz-cmd` / `--shared-node-modules`.

---

## Flujo de Trabajo en Proyectos de Clientes

### 1. Crear un proyecto nuevo (`scaffold_client.py`)

```powershell
python "$HOME\.gemini\config\plugins\snowui-pbip-kit\skills\pbip-golden-template\scripts\scaffold_client.py" `
  --target "C:\Clientes\EmpresaX" `
  --name "FinanzasEmpresaX" `
  --preset web-scroll `
  --copy-skills `
  --git-init
```

Opciones útiles:
* `--brand-config C:\ruta\brand-config.json`: inyecta colores, logo, cultura y moneda desde el inicio.
* `--preset screen-16x9`: lienzo `1440×810` (`FitToPage`) para vista ejecutiva sin scroll vertical (por defecto `web-scroll` de `1440×1708`).
* `--copy-skills`: incluye `.agents/` dentro del proyecto cliente si el equipo colaborará por Git.

### 2. Personalizar identidad y moneda (`brand-config.json` + `apply_brand.py`)

1. Coloca el logo (`SVG` o `PNG`) en `assets/` dentro del proyecto cliente y referencia su ruta en `brand-config.json`.
2. Ajusta colores, moneda (`USD $`, `PEN S/`, `EUR €`, `GBP £`) y diales en `brand-config.json` (`cornerRadius`, `kpiSurfaceMode`, `sidebarMode`, `fontFamily`).
3. Ejecuta:
   ```powershell
   python .agents\skills\brand-theming\scripts\apply_brand.py --skip-build
   ```
   *(Omite `--skip-build` si quieres recompilar además `pbiviz/_common/snowuiTokens.*` dentro de los `.pbiviz`.)*

### 3. Componer páginas de negocio (`manage_pages.py`)

Parte de la página base `resumen` para construir tantas hojas como requiera el cliente sin romper la barra lateral ni el marcador de reseteo:

```powershell
python .agents\skills\pbir-report-layout\scripts\manage_pages.py clone --source resumen --target ventas --title "Ventas"
python .agents\skills\pbir-report-layout\scripts\manage_pages.py set-preset --target all --preset screen-16x9
python .agents\skills\pbir-report-layout\scripts\manage_pages.py delete --target ventas
python .agents\skills\pbir-report-layout\scripts\manage_pages.py sync
```

### 4. Editar o agregar visuales PBIVIZ (`build_and_unpack_pbiviz.py`)

Tras modificar `pbiviz/_common/` o agregar un visual nuevo en `pbiviz/<nombreVisual>/`:

```powershell
python .agents\skills\pbiviz-custom-visual-dev\scripts\build_and_unpack_pbiviz.py --visual all
```
* Acepta un visual o varios separados por coma (`--visual snowuiPillTable,snowuiGauge`).
* Empaqueta `.pbiviz` hacia `pbiviz/dist/`, desempaqueta hacia `<Proyecto>.Report/CustomVisuals/<guid>/` y registra automáticamente visuales nuevos en `definition/report.json`.

### 5. Auditoría QA obligatoria (`verify_all.py`)

Antes de abrir el `.pbip` en Power BI Desktop o entregar cambios:

```powershell
python .agents\skills\pbip-qa-verify\scripts\verify_all.py
```

Valida sintaxis JSON, sincronía byte a byte `pbiviz/dist/*.pbiviz` vs `CustomVisuals/`, reglas TMDL (tabuladores, `lineageTag`s únicos, cero colisiones columna/medida, exclusividad `formatString` vs `formatStringDefinition =`) y layout PBIR anti-recorte (`textbox height >= 34`, `slicer height >= 60`, enlaces, recursos y bookmarks).

---

## Promover Mejoras al Estándar (Control Opt-In)

Los cambios propios de un cliente (paleta, logo, moneda, páginas, modelo de negocio) **permanecen aislados en su proyecto**.

Cuando desarrolles una mejora reutilizable (un visual nuevo o mejorado, `_common/` o una skill) en **cualquier proyecto local** y decidas convertirla en estándar del plugin:

```powershell
# 1. Previsualizar sin modificar archivos
python "$HOME\.gemini\config\plugins\snowui-pbip-kit\skills\pbip-golden-template\scripts\promote_to_plugin.py" `
  --from . --visuals snowuiPillTable --dry-run

# 2. Promover limpiamente (añade --include-common si editaste _common/ o --include-skills si editaste .agents/skills/)
python "$HOME\.gemini\config\plugins\snowui-pbip-kit\skills\pbip-golden-template\scripts\promote_to_plugin.py" `
  --from . --visuals snowuiPillTable
```

`promote_to_plugin.py`:
1. Copia **solo** código de gráfico (`src/`, `style/`, `capabilities.json`, `assets/`, `pbiviz.json`), excluyendo `brand-config.json` y `snowuiTokens.*` del cliente.
2. Neutraliza `author`/`supportUrl` y reaplica el `brand-config.json` neutro (`USD $`) del `starter-kit/`.
3. Recompila en `starter-kit/`, ejecuta `verify_all.py` y **no toca `.git/`**, dejándote el diff listo para versionar manualmente:

```bash
cd /c/Users/Acer/.gemini/config/plugins/snowui-pbip-kit
git status
git add -A
git commit -m "feat: describir mejora del estandar SnowUI" -m "- Detalle 1
- Detalle 2"
git push
```

---

## Reglas Operativas Críticas

1. **Cierra Power BI Desktop** antes de modificar `.tmdl`, `.json` PBIR o `CustomVisuals/`.
2. **Una sola fuente de verdad visual**: cambia marca/moneda en `brand-config.json` y ejecuta `apply_brand.py`.
3. **TMDL estricto**: indentación con tabuladores (`\t`), nunca nombrar igual una `measure` y una `column` en la misma tabla, y nunca declarar `formatString:` y `formatStringDefinition =` a la vez (si usas `formatStringDefinition =`, escribe el `SWITCH(...)` literal inline, no apuntando a otra medida).
4. **Geometría anti-recorte**: `textbox` con `height >= 34` y `slicer` Dropdown con `height >= 60`.
