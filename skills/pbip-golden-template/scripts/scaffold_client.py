#!/usr/bin/env python3
"""Instancia un nuevo proyecto cliente PBIP SnowUI desde el starter-kit neutro."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

SHARED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

from pbip_paths import find_pbiviz_executable, find_shared_visual_node_modules  # noqa: E402

PLUGIN_ROOT_DEFAULT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def find_starter_kit(explicit_kit: str | None) -> str:
    if explicit_kit:
        if os.path.isdir(explicit_kit):
            return os.path.abspath(explicit_kit)
        raise FileNotFoundError(f"No existe starter-kit en: {explicit_kit}")

    candidates = [
        os.path.join(PLUGIN_ROOT_DEFAULT, "starter-kit"),
        os.path.join(os.path.expanduser("~"), ".gemini", "config", "plugins", "snowui-pbip-kit", "starter-kit"),
    ]
    for cand in candidates:
        if os.path.isdir(cand) and os.path.exists(os.path.join(cand, "Template.pbip")):
            return os.path.abspath(cand)
    raise FileNotFoundError("No se encontró el directorio starter-kit/. Especifica --starter-kit.")


def sanitize_project_name(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", raw.strip())
    if not cleaned:
        raise ValueError("El nombre del proyecto debe contener al menos un carácter alfanumérico.")
    return cleaned


def main() -> int:
    parser = argparse.ArgumentParser(description="Crea un proyecto PBIP SnowUI nuevo para un cliente.")
    parser.add_argument("--target", required=True, help="Carpeta destino del nuevo proyecto cliente.")
    parser.add_argument("--name", required=True, help="Nombre base del archivo .pbip (ej. FinanzasAcme).")
    parser.add_argument("--starter-kit", default=None, help="Ruta opcional al starter-kit neutro.")
    parser.add_argument("--brand-config", default=None, help="Ruta opcional a un brand-config.json del cliente.")
    parser.add_argument("--preset", choices=["web-scroll", "screen-16x9"], default=None, help="Preset inicial de lienzo.")
    parser.add_argument("--copy-skills", action="store_true", help="Copia .agents/ dentro del proyecto cliente para equipos Git.")
    parser.add_argument("--skip-build", action="store_true", help="Aplica marca sin recompilar PBIVIZ (usa los precompilados).")
    parser.add_argument("--pbiviz-cmd", default=None, help="Ruta opcional a pbiviz.cmd.")
    parser.add_argument("--shared-node-modules", default=None, help="Ruta opcional a node_modules compartidos.")
    parser.add_argument("--git-init", action="store_true", help="Inicializa repositorio Git en el proyecto nuevo.")
    args = parser.parse_args()

    proj_name = sanitize_project_name(args.name)
    kit_dir = find_starter_kit(args.starter_kit)
    target_dir = os.path.abspath(args.target)

    if os.path.exists(target_dir) and any(os.scandir(target_dir)):
        # Permitir si solo existe .git o está vacío, pero bloquear si ya hay un .pbip
        existing_pbip = [f for f in os.listdir(target_dir) if f.endswith(".pbip")]
        if existing_pbip:
            print(f"ERROR: La carpeta destino ya contiene un proyecto PBIP ({existing_pbip[0]}).", file=sys.stderr)
            return 1

    os.makedirs(target_dir, exist_ok=True)

    # 1. Copiar contenido del starter-kit excluyendo node_modules/.tmp/__pycache__
    ignore = shutil.ignore_patterns("node_modules", ".tmp", "__pycache__", "*.pyc", ".pbi")
    for entry in os.listdir(kit_dir):
        src = os.path.join(kit_dir, entry)
        dst_name = entry
        if entry == "Template.pbip":
            dst_name = f"{proj_name}.pbip"
        elif entry == "Template.Report":
            dst_name = f"{proj_name}.Report"
        elif entry == "Template.SemanticModel":
            dst_name = f"{proj_name}.SemanticModel"
        dst = os.path.join(target_dir, dst_name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

    # 2. Actualizar referencias internas en <proj_name>.pbip y <proj_name>.Report/definition.pbir
    pbip_path = os.path.join(target_dir, f"{proj_name}.pbip")
    pbip_obj = json.load(open(pbip_path, encoding="utf-8"))
    for art in pbip_obj.get("artifacts", []):
        if isinstance(art, dict) and isinstance(art.get("report"), dict):
            art["report"]["path"] = f"{proj_name}.Report"
    with open(pbip_path, "w", encoding="utf-8") as f:
        json.dump(pbip_obj, f, indent=2, ensure_ascii=False)

    pbir_path = os.path.join(target_dir, f"{proj_name}.Report", "definition.pbir")
    pbir_obj = json.load(open(pbir_path, encoding="utf-8"))
    pbir_obj.setdefault("datasetReference", {}).setdefault("byPath", {})["path"] = f"../{proj_name}.SemanticModel"
    with open(pbir_path, "w", encoding="utf-8") as f:
        json.dump(pbir_obj, f, indent=2, ensure_ascii=False)

    # Actualizar .platform displayName si existen
    for folder, suffix in [(f"{proj_name}.Report", "Report"), (f"{proj_name}.SemanticModel", "SemanticModel")]:
        plat_p = os.path.join(target_dir, folder, ".platform")
        if os.path.exists(plat_p):
            plat = json.load(open(plat_p, encoding="utf-8"))
            plat.setdefault("metadata", {})["displayName"] = proj_name
            with open(plat_p, "w", encoding="utf-8") as f:
                json.dump(plat, f, indent=2, ensure_ascii=False)

    # 3. Copiar brand-config.json externo si fue proporcionado (y su logo asociado)
    if args.brand_config:
        abs_bc = os.path.abspath(args.brand_config)
        bc_obj = json.load(open(abs_bc, encoding="utf-8"))
        logo_rel = bc_obj.get("assets", {}).get("logoPath", "")
        if logo_rel:
            logo_candidates = [
                logo_rel if os.path.isabs(logo_rel) else os.path.join(os.path.dirname(abs_bc), logo_rel),
                os.path.join(os.path.dirname(abs_bc), "assets", os.path.basename(logo_rel)),
                os.path.join(os.path.dirname(abs_bc), os.path.basename(logo_rel)),
                os.path.abspath(logo_rel),
            ]
            cand_logo = next((p for p in logo_candidates if os.path.exists(p)), "")
            if cand_logo:
                os.makedirs(os.path.join(target_dir, "assets"), exist_ok=True)
                logo_basename = os.path.basename(cand_logo)
                shutil.copy2(cand_logo, os.path.join(target_dir, "assets", logo_basename))
                bc_obj["assets"]["logoPath"] = f"assets/{logo_basename}"
        with open(os.path.join(target_dir, "brand-config.json"), "w", encoding="utf-8") as f:
            json.dump(bc_obj, f, indent=2, ensure_ascii=False)

    # 4. Copiar skills locales si --copy-skills
    skills_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if args.copy_skills:
        dst_skills = os.path.join(target_dir, ".agents", "skills")
        shutil.copytree(skills_base, dst_skills, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)
        rules_src = os.path.abspath(os.path.join(skills_base, "..", "rules"))
        if os.path.isdir(rules_src):
            shutil.copytree(rules_src, os.path.join(target_dir, ".agents", "rules"), dirs_exist_ok=True)

    # 5. Aplicar preset de lienzo si se solicitó
    if args.preset:
        manage_script = os.path.join(skills_base, "pbir-report-layout", "scripts", "manage_pages.py")
        res = subprocess.run([sys.executable, manage_script, "--root", target_dir, "set-preset", "--target", "all", "--preset", args.preset], check=False)
        if res.returncode != 0:
            return res.returncode

    # 6. Aplicar marca inicial y validar QA
    apply_script = os.path.join(skills_base, "brand-theming", "scripts", "apply_brand.py")
    pbiviz_dir = os.path.join(target_dir, "pbiviz")
    pbiviz_exe = find_pbiviz_executable(pbiviz_dir, args.pbiviz_cmd)
    shared_nm = find_shared_visual_node_modules(pbiviz_dir, args.shared_node_modules)
    cmd = [sys.executable, apply_script, "--root", target_dir]
    if pbiviz_exe:
        cmd.extend(["--pbiviz-cmd", pbiviz_exe])
    if shared_nm:
        cmd.extend(["--shared-node-modules", shared_nm])
    if args.skip_build or not (pbiviz_exe and shared_nm):
        cmd.append("--skip-build")
        if not args.skip_build:
            print("NOTA: Sin toolchain completa (pbiviz + node_modules compartidos); usando paquetes precompilados (--skip-build).")
    res = subprocess.run(cmd, check=False)
    if res.returncode != 0:
        return res.returncode

    if args.git_init and not os.path.exists(os.path.join(target_dir, ".git")):
        subprocess.run(["git", "init"], cwd=target_dir, check=False)

    print(f"Proyecto '{proj_name}' creado con éxito en: {target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
