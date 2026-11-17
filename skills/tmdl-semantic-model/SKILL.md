---
name: tmdl-semantic-model
description: >-
  Crea, edita y audita tablas, medidas DAX, formato dinámico multimoneda,
  columnas calculadas, expresiones M y relaciones dentro del modelo semántico
  TMDL (`<Proyecto>.SemanticModel/`). Úsala al añadir indicadores o ajustar el esquema estrella.
---

# Modelo Semántico TMDL

Flujo para extender medidas DAX, multimoneda (`DimMonedaSelector`), columnas o relaciones sin romper Power BI Desktop ni los visuales PBIR.

> [!NOTE]
> Consulta el catálogo del modelo demo actual en [model-catalog.md](./references/model-catalog.md).

## Procedimiento

1. **Cierra Power BI Desktop** antes de editar `definition/`.
2. **Al agregar una medida DAX**:
   - Mantén indentación por tabulador (`\t`) y asigna un `lineageTag` UUID v4 **único**.
   - Nunca reutilices el nombre exacto (case-insensitive) de una `column` en la misma tabla.
   - Para medidas monetarias estándar, declara `formatString: \$#,0.00;(\$#,0.00);\$#,0.00` (o la moneda activa; `apply_brand.py` lo actualiza según `brand-config.json`). Si implementas formato dinámico con `formatStringDefinition =`, usa un `SWITCH(...)` con ramas de cadena literal explícitas y **no** declares `formatString:` estático en esa misma medida.
   - Para porcentajes usa `formatString: 0.0%` o `+0.0%;-0.0%;0.0%`; para conteos usa `formatString: #,0`.
3. **Al renombrar columnas o medidas**: actualiza `queryRef` y `Column`/`Measure` en los `visual.json` afectados.
4. **Valida la integridad TMDL**:
   ```powershell
   python .agents/skills/tmdl-semantic-model/scripts/audit_tmdl.py
   ```
