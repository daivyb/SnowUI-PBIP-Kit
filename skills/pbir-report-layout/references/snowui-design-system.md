# Sistema de Diseño SnowUI y Arquetipos PBIR

## Presets de Lienzo

| Preset | Dimensiones | `displayOption` | Uso recomendado |
| :--- | :--- | :--- | :--- |
| `web-scroll` | `1440 × 1708` | `FitToWidth` | Dashboards tipo app web con scroll vertical amplio. |
| `screen-16x9` | `1440 × 810` | `FitToPage` | Pantallas ejecutivas de una sola vista sin scroll vertical. |

## Geometría del Shell Maestro (`web-scroll`)

- **Sidebar izquierda**: `x: 16..228` (`212 × 1680`), incluye logotipo, cabecera (`_brand_txt` `h: 66`), etiqueta `PANELES` (`h: 38`), botones `nav_btn_0..N` (`y = 140 + idx * 54`, `h: 46`) y pie técnico (`_side_meta`).
- **Topbar**: `x: 244..1424, y: 14..94` (`1180 × 80`), incluye breadcrumb, `2` slicers Dropdown (`y: 21, h: 66`), píldora de alertas (`_alrt_*`), botón `Restablecer` (`_rst_*`) y píldora decorativa (`_sun_*`).
- **Footer**: `x: 244, y: 1652, w: 1180, h: 40`.

## Arquetipos de Contenido (`y: 104..1640`)

1. **Arquetipo A — Resumen Ejecutivo** (ref. `overview`):
   - Título (`y: 104, h: 40`) + 4 KPIs (`y: 148, w: 280, h: 156`) + Spline ancho (`y: 320, w: 1180, h: 356`) + 2 PillBar 50/50 (`y: 696, w: 580, h: 328`) + Micro-Stacked ancho (`y: 1044, w: 1180, h: 274`) + PillTable resumen (`y: 1338, w: 1180, h: 302`).
2. **Arquetipo B — Detalle Analítico / Cartera** (ref. `proyectos` / `ejecutores_donantes`):
   - **B1**: 4 KPIs + 2 PillBar 50/50 (`y: 320, w: 580, h: 344`) + PillTable extendida (`y: 684, w: 1180, h: 956`).
   - **B2**: 4 KPIs + 2 PillBar 50/50 (`y: 320, h: 344`) + 1 PillBar ancho (`y: 684, h: 306`) + PillTable media (`y: 1010, h: 630`).
3. **Arquetipo C — Análisis Geográfico / Comparativo** (ref. `ubicacion`):
   - 4 KPIs + Mapa nativo (`y: 320, w: 620, h: 520`) + PillBar Top N (`x: 884, y: 320, w: 540, h: 520`) + PillTable inferior (`y: 860, w: 1180, h: 780`).

## Literales PBIR

- Texto: `{"expr": {"Literal": {"Value": "'Mi Texto'"}}}` (comillas simples escapadas como `''`).
- Booleano: `"true"` / `"false"`.
- Decimal: `"18D"`, `"560D"`. Entero largo (`roundEdge`): `"12L"`.
