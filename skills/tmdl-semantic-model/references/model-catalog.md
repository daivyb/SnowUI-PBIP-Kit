# Catálogo Base del Modelo Semántico TMDL (`starter-kit`)

Cultura por defecto: `es-PE` (parametrizable en `brand-config.json`). Las tablas base vienen autocontenidas con Power Query M inline (`#table` / `List.Dates`) para abrir sin dependencias externas.

## Tablas Base (`<Proyecto>.SemanticModel/definition/tables/`)

- **`DimFecha`** (`3` cols): `IdFecha` (clave), `Fecha`, `Anio`.
- **`DimMes`** (`4` cols): `MesNum` (clave), `MesCorto`, `MesNombre`, `Trimestre` (ordenadas por `MesNum`).
- **`DimMonedaSelector`** (`6` cols, `4` medidas): `CodigoMoneda` (`USD`, `PEN`, `EUR`), `Simbolo`, `NombreMoneda`, `FormatoDAX`, `TipoCambioBase`, `Orden`.
  - Medidas auxiliares: `Moneda Activa`, `Simbolo Moneda Activa`, `Formato Moneda Activa`, `Factor Tipo Cambio`.
- **`FactBase`** (`8` cols, `7` medidas ejemplo): `IdFecha`, `MesNum`, `Iniciativa`, `Categoria`, `Region`, `Estado`, `Presupuesto_Base`, `Monto_Base`.
  - Medidas ejemplo: `Presupuesto`, `Ejecutado`, `Saldo`, `% Avance`, `Variación YoY %`, `Registros`, `Etiqueta Alertas`.
  - Al conectar las fuentes reales del cliente, reemplaza o amplía `FactBase` y agrega tus dimensiones manteniendo las columnas clave y medidas limpias sin colisión de nombres.
