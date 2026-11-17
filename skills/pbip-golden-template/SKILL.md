---
name: pbip-golden-template
description: >-
  Instancia un nuevo proyecto Power BI PBIP/PBIR SnowUI limpio para un cliente
  en cualquier carpeta destino desde el `starter-kit/` global o plantilla local,
  renombrando artefactos y aplicando `brand-config.json`. Úsala al iniciar un
  nuevo proyecto Power BI de consultoría.
---

# Scaffolding de Nuevo Proyecto Cliente (`pbip-golden-template`)

Crea la estructura inicial completa de un nuevo proyecto Power BI (`.pbip`, `.Report`, `.SemanticModel`, `pbiviz/`, `brand-config.json` y `.gitignore`) lista para abrir en Power BI Desktop y adaptar sus páginas y modelo al negocio del cliente.

## Pasos

1. **Define los parámetros del cliente**:
   - Nombre técnico del proyecto (PascalCase sin espacios, ej. `VentasAcme`).
   - Carpeta destino (`--target`).
   - Opcionalmente su archivo `brand-config.json` y logo SVG/PNG, más preset de lienzo (`web-scroll` o `screen-16x9`).
2. **Ejecuta el generador**:
   ```powershell
   python .agents/skills/pbip-golden-template/scripts/scaffold_client.py --target "C:\Clientes\Acme" --name "VentasAcme" --preset web-scroll
   ```
   - Puedes añadir `--brand-config <ruta>` para aplicar la marca inmediatamente, `--copy-skills` si el equipo del cliente compartirá `.agents/` vía Git, y `--git-init` para crear el repositorio inicial.
3. **Compone las páginas del negocio del cliente**:
   - Parte de la página limpia `resumen` y usa `manage_pages.py` (`clone`, `delete`, `set-preset`, `sync`) para construir tantas hojas como requiera el proyecto (Resumen Ejecutivo, Detalle Analítico, Geográfico, etc.).
4. **Valida siempre al cerrar**:
   ```powershell
   python <ruta_qa>\verify_all.py --root "C:\Clientes\Acme"
   ```
5. **Promover mejoras al estándar global (opcional, opt-in)**:
   - Si en un proyecto cliente mejoras un visual o agregas un 5.º PBIVIZ y quieres estandarizarlo para futuros clientes sin arrastrar la marca/colores del cliente:
   ```powershell
   python <ruta_plugin>\skills\pbip-golden-template\scripts\promote_to_plugin.py --from "C:\Clientes\Acme" --visuals snowuiPillTable --dry-run
   ```
   - Añade `--include-common` si cambiaste `pbiviz/_common/` (recompila todos los visuales) o `--include-skills` para actualizar skills; omite `--dry-run` al confirmar. Nunca modifica `.git/` ni copia `brand-config.json` del cliente.
