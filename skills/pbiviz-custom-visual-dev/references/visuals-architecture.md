# Arquitectura de Visuales PBIVIZ SnowUI

Todos los visuales declaran `apiVersion: "5.11.1"`, utilizan `powerbi-visuals-utils-formattingmodel` (`6.0.4`) y `d3` (`7.9.0`), y consumen tokens desde `pbiviz/_common/snowuiTokens.*` + `options.host.colorPalette` + parser multimoneda `resolveColumnFormatSpec()`.

## Inventario de Visuales

| Carpeta | GUID (`visualType` PBIR) | `dataViewMappings` | Roles de Datos (`dataRoles`) | Tarjetas de Formato (`objects`) |
| :--- | :--- | :--- | :--- | :--- |
| `pbiviz/snowuiKpiCard` | `snowuiKpiCardE1A4B801` | `table` (fallback `categorical`) | `value`, `delta`, `tooltipFields` (`Measure`) | `cardStyle` (`themeVariant`, `surfaceMode`, `titleOverride`, `subtitleText`, `cornerRadius`, `animationMs`), `numberFormat` (`currencyMode`, `valuePrefix`, `valueSuffix`, `displayUnits`, `decimals`, `deltaIsRatio`, `deltaSuffix`) |
| `pbiviz/snowuiSplineChart` | `snowuiSplineChartE1A4B802` | `categorical` (`categories` + `values`) | `category`, `altCategory` (`Grouping`), `measures`, `altMeasures` (`Measure`) | `chartStyle` (`lineColor`, `defaultChartMode`, `defaultGranularity`, `primaryAxisLabel`, `secondaryAxisLabel`, `currencyMode`, `valuePrefix`, `animationMs`) |
| `pbiviz/snowuiPillBarChart` | `snowuiPillBarChartE1A4B803` | `categorical` (`categories` + `values` agrupado por `series`) | `category`, `subCategory`, `series` (`Grouping`), `measure` (`Measure`) | `barStyle` (`displayMode`, `titleOverride`, `accentColor`, `topN`, `sortOrder`, `currencyMode`, `valuePrefix`, `showFloatingCallout`, `animationMs`) |
| `pbiviz/snowuiPillTable` | `snowuiPillTableE1A4B804` | `table` (`top: 200`) | `primaryColumn`, `detailColumns`, `statusColumn` (`Grouping`), `measures` (`Measure`) | `tableStyle` (`titleOverride`, `maxRows`, `currencyMode`, `valuePrefix`, `showAvatars`, `staggerMs`) |

## Helpers Compartidos (`pbiviz/_common/`)

- **`snowuiTokens.less` / `snowuiTokens.ts`**: tokens generados por `apply_brand.py` desde `brand-config.json` (paleta, variantes KPI, moneda base, `style`, `statusRules`, `seriesColorRules`, `columnFriendlyNames`).
- **`snowuiBase.less`**: CSS Custom Properties (`--snow-*`), `html, body` transparentes al `100%`, `.snow-root-reset()` y `.snow-empty-state`.
- **`snowuiUtils.ts`**: `applyHostColorTokens()` (High Contrast + tokens), `resolveHostSeriesColor()`, `resolveColumnFormatSpec()` (parser de formatos DAX `$`, `S/`, `€`, `%`, conteos), `formatMetricValue`, `formatFullCurrency`, `measureTextWidth`, `wrapLabelLines`, `calcDynamicLeftMargin`, `clamp`, `RafAnimator`, tooltips y selección.
