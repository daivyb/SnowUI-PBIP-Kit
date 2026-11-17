#!/usr/bin/env python3
"""Orquestador QA integral: descubre *.pbip dinámicamente, valida brand-config, TMDL, PBIR y sincronía PBIVIZ."""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import zipfile

SHARED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

from pbip_paths import discover_pbiviz_visuals, resolve_pbip_paths  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica integridad total del proyecto PBIP.")
    parser.add_argument("--root", default=".", help="Raíz del repositorio.")
    args = parser.parse_args()

    paths = resolve_pbip_paths(args.root)
    repo_root = paths.repo_root
    skills_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    errors: list[str] = []

    # 1. Validar .pbip, .pbism y .pbir
    for label, p in [
        (os.path.basename(paths.pbip_file), paths.pbip_file),
        ("definition.pbism", paths.pbism_file),
        ("definition.pbir", paths.pbir_file),
    ]:
        try:
            with open(p, encoding="utf-8") as f:
                json.load(f)
        except Exception as exc:
            errors.append(f"{label} inválido: {exc}")

    # 2. Validar brand-config.json si existe
    brand_cfg = os.path.join(repo_root, "brand-config.json")
    if os.path.exists(brand_cfg):
        try:
            bc = json.load(open(brand_cfg, encoding="utf-8"))
            for key in ("client", "assets", "currency", "style", "colors"):
                if key not in bc:
                    errors.append(f"brand-config.json sin bloque obligatorio '{key}'.")
        except Exception as exc:
            errors.append(f"brand-config.json inválido: {exc}")

    # 3. Verificar sincronía exacta pbiviz/dist/*.pbiviz vs CustomVisuals/<guid>/
    visuals = discover_pbiviz_visuals(os.path.join(repo_root, "pbiviz"))
    if not visuals:
        errors.append("No se descubrió ningún visual PBIVIZ en pbiviz/.")
    for v in visuals:
        preferred = os.path.join(repo_root, "pbiviz", "dist", f"{v.guid}.{v.version}.pbiviz")
        dist_matches = [preferred] if os.path.exists(preferred) else sorted(glob.glob(os.path.join(repo_root, "pbiviz", "dist", f"{v.guid}.*.pbiviz")))
        dist_pkg = dist_matches[-1] if dist_matches else preferred
        cv_res = os.path.join(paths.report_dir, "CustomVisuals", v.guid, "resources", f"{v.guid}.pbiviz.json")
        if not os.path.exists(dist_pkg):
            errors.append(f"Falta paquete compilado: {dist_pkg}")
            continue
        if not os.path.exists(cv_res):
            errors.append(f"Falta recurso desempaquetado: {cv_res}")
            continue
        with zipfile.ZipFile(dist_pkg, "r") as zf:
            packed_obj = json.loads(zf.read(f"resources/{v.guid}.pbiviz.json").decode("utf-8"))
        with open(cv_res, encoding="utf-8") as f:
            unpacked_obj = json.load(f)
        if packed_obj != unpacked_obj:
            errors.append(f"Desincronización PBIVIZ en {v.guid} ({v.folder}): ejecuta build_and_unpack_pbiviz.py.")

    if errors:
        for e in errors:
            print("ERROR:", e, file=sys.stderr)
        return 1
    print(f"Sincronía PBIVIZ OK ({paths.project_name}): los {len(visuals)} paquetes dist/ coinciden con CustomVisuals/.")

    # 4. Ejecutar audit_tmdl.py y audit_pbir_layout.py
    scripts = [
        os.path.join(skills_dir, "tmdl-semantic-model", "scripts", "audit_tmdl.py"),
        os.path.join(skills_dir, "pbir-report-layout", "scripts", "audit_pbir_layout.py"),
    ]
    for spath in scripts:
        res = subprocess.run([sys.executable, spath, "--root", repo_root], check=False)
        if res.returncode != 0:
            return res.returncode

    print("QA INTEGRAL COMPLETADA CON EXITO (0 ERRORES).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
