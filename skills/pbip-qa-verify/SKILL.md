---
name: pbip-qa-verify
description: >-
  Ejecuta la verificación integral del proyecto Power BI (descubrimiento dinámico
  de *.pbip, brand-config.json, TMDL, PBIR, layout anti-recorte, navegación y
  sincronía PBIVIZ) antes de abrir o entregar cambios. Úsala al finalizar cualquier mejora.
---

# Auditoría Integral QA del Proyecto PBIP

Orquesta todas las validaciones estructurales en un solo comando sin importar el nombre del `.pbip` del cliente:

```powershell
python .agents/skills/pbip-qa-verify/scripts/verify_all.py
```

## Validaciones Ejecutadas

1. **Descubrimiento dinámico**: localiza `*.pbip`, `.Report` y `.SemanticModel` en el proyecto.
2. **Esquemas JSON**: verifica sintaxis de `*.pbip`, `definition.pbism`, `definition.pbir` y `brand-config.json`.
3. **Sincronía PBIVIZ**: compara byte a byte `resources/<guid>.pbiviz.json` entre `pbiviz/dist/*.pbiviz` y `<Proyecto>.Report/CustomVisuals/<guid>/`.
4. **Integridad TMDL (`audit_tmdl.py`)**: `lineageTag`s únicos, cero colisiones columna/medida, exclusividad `formatString` vs `formatStringDefinition`, `sortByColumn`, relaciones y referencias `Tabla[Columna]`.
5. **Integridad PBIR (`audit_pbir_layout.py`)**: coordenadas dentro de lienzo dinámico (`page.width × page.height`), alturas mínimas (`textbox >= 34`, `slicer >= 60`), recursos registrados, enlaces `PageNavigation`, cobertura de `reset_filters.bookmark.json` y campos existentes en TMDL.
