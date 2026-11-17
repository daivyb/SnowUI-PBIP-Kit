# Referencia de `brand-config.json`

Archivo maestro ubicado en la raíz del proyecto PBIP (validado por `brand-config.schema.json`).

## Bloques Principales

- **`client`**:
  - `name` / `subtitle`: cabecera de la barra lateral (`*_brand_txt`).
  - `breadcrumbRoot`: prefijo del breadcrumb superior (`*_tb_crumb`).
  - `footerText` / `sideMetaText`: pie de página y metadatos del sidebar.
  - `themeName` / `themeDisplayName`: nombre del archivo JSON de tema generado en `RegisteredResources/`.
  - `locale`: cultura de Power BI (`es-PE`, `en-US`, etc.) aplicada a `report.json` y `model.tmdl`.
- **`assets`**:
  - `logoPath`: ruta al SVG/PNG fuente dentro del proyecto.
  - `registeredLogoName`: nombre con el que se registra en `RegisteredResources/` y `definition/report.json`.
- **`currency`**:
  - `code` / `symbol` / `numberLocale`: moneda por defecto (`USD` `$`, `PEN` `S/ `, `EUR` `€`) y formato numérico regional.
  - `mode`: `"auto"` (lee el `formatString` / `formatStringDefinition` DAX de cada medida), `"brand"` (fuerza `currency.symbol`), o `"custom"` (usa `valuePrefix` manual del visual).
  - `exposeCurrencySlicer`: indicador documental para activar o no un selector visible de `DimMonedaSelector`.
- **`style` (Diales de variación estética)**:
  - `canvasPreset`: `"web-scroll"` (`1440×1708`, `FitToWidth`) o `"screen-16x9"` (`1440×810`, `FitToPage`).
  - `cornerRadius`: radio base (`px`) aplicado al tema JSON, KPIs y tarjetas nativas.
  - `kpiSurfaceMode`: `"gradient"` (degradado SnowUI), `"solid"` (plano corporativo) o `"light-bordered"` (blanco minimalista con borde).
  - `sidebarMode`: `"light"` (blanco), `"tinted"` (tinte suave primario) o `"dark"` (oscuro con texto e iconos claros).
  - `fontFamily`: fuente principal (`"Segoe UI"` recomendada por compatibilidad Power BI).
- **`colors`**:
  - `brand`: `primary`, `secondary`, `tertiary`, `darkSurface`.
  - `semantic`: `positive`, `warning`, `negative`, `alertText`, `alertBg`, `alertBorder`.
  - `surfaces`: `canvas`, `card`, `border`, `divider`, `pillBg`, `slicerBg`, `navActiveBg`, `navActiveBorder`.
  - `text`: `primary`, `secondary`, `navInactive`, `muted`, `onDark`.
  - `dataColors`: paleta de 8 colores hexadecimales para el tema JSON y `snowuiPillBarChart`.
- **`visualDefaults` y `statusRules`**:
  - Reglas opcionales para colores de serie (`seriesColorRules`), alias amigables de columnas (`columnFriendlyNames`) y badges de estado en `snowuiPillTable`.
