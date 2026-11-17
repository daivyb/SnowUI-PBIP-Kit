---
name: pbiviz-custom-visual-dev
description: >-
  Compila, prueba y despliega los 4 visuales personalizados PBIVIZ de SnowUI
  (snowuiKpiCard, snowuiSplineChart, snowuiPillBarChart y snowuiPillTable).
  Úsala siempre que se editen estilos CSS/LESS, tokens, capacidades o TypeScript dentro de `pbiviz/`.
---

# Desarrollo y Empaquetado de Visuales PBIVIZ SnowUI

Flujo para editar, compilar y sincronizar los 4 visuales personalizados del proyecto (`pbiviz/` -> `pbiviz/dist/` -> `<Proyecto>.Report/CustomVisuals/`).

> [!NOTE]
> Para consultar `GUID`s, `dataRoles`, propiedades (`currencyMode`, `surfaceMode`) y helpers compartidos, revisa [visuals-architecture.md](./references/visuals-architecture.md).

## Pasos Obligatorios

1. **Edita únicamente la fuente compartida o el visual objetivo**:
   - Tokens de marca/moneda: modifica `brand-config.json` y usa `apply_brand.py` (que regenera `pbiviz/_common/snowuiTokens.*`).
   - Estilos/helpers globales: edita `pbiviz/_common/snowuiBase.less` o `pbiviz/_common/snowuiUtils.ts`.
2. **Compila y desempaqueta** (descubre dinámicamente todos los visuales en `pbiviz/`, incluyendo un 5.º visual nuevo, y lo registra en `report.json`):
   ```powershell
   python .agents/skills/pbiviz-custom-visual-dev/scripts/build_and_unpack_pbiviz.py --visual all
   ```
   - Acepta `--visual snowuiKpiCard` o múltiples separados por coma (`--visual snowuiPillTable,snowuiGauge`).
   - En proyectos cliente sin `node_modules` local, busca automáticamente `SNOWUI_PBIVIZ_CMD`, `SNOWUI_PBIVIZ_SHARED_NM` o `%LOCALAPPDATA%\SnowUIPbipKit\` (o pásalos con `--pbiviz-cmd` / `--shared-node-modules`).
3. **Ejecuta la auditoría QA integral**:
   ```powershell
   python .agents/skills/pbip-qa-verify/scripts/verify_all.py
   ```
4. **Si Power BI Desktop estaba abierto**, ciérralo sin guardar y vuelve a abrir el `.pbip`.
