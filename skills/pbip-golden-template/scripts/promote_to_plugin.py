#!/usr/bin/env python3
"""Promueve selectivamente visuales PBIVIZ, _common/ o skills desde cualquier proyecto hacia el plugin global."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

SHARED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

from pbip_paths import (  # noqa: E402
    discover_pbiviz_visuals,
    find_pbiviz_executable,
    find_shared_visual_node_modules,
)

EXCLUDED_SRC_FILES = {"snowuitokens.ts", "snowuiutils.ts"}
EXCLUDED_STYLE_FILES = {"snowuitokens.less", "snowuibase.less"}
ROOT_META_FILES = ("package.json", "pbiviz.json", "tsconfig.json", "capabilities.json")
COMMON_SHAREABLE_FILES = ("snowuiUtils.ts", "snowuiBase.less")


def resolve_plugin_root(explicit_plugin: str | None) -> str:
    if explicit_plugin:
        p = os.path.abspath(explicit_plugin)
        if os.path.isdir(os.path.join(p, "starter-kit")):
            return p
        raise FileNotFoundError(f"La ruta --plugin no contiene starter-kit/: {p}")

    env_plugin = os.environ.get("SNOWUI_PLUGIN_DIR", "").strip()
    candidates = [
        env_plugin,
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
        os.path.join(os.path.expanduser("~"), ".gemini", "config", "plugins", "snowui-pbip-kit"),
    ]
    for cand in candidates:
        if cand and os.path.exists(os.path.join(cand, "starter-kit", "Template.pbip")):
            return os.path.abspath(cand)
    raise FileNotFoundError(
        "No se encontró el directorio del plugin global con starter-kit/Template.pbip. "
        "Especifica --plugin <ruta> o define SNOWUI_PLUGIN_DIR."
    )


def copy_clean_dir(src_dir: str, dst_dir: str, excluded_lower: set[str], preserve_lower: set[str]) -> list[str]:
    copied: list[str] = []
    if not os.path.isdir(src_dir):
        return copied
    os.makedirs(dst_dir, exist_ok=True)
    # Limpiar archivos obsoletos salvo los protegidos que se regeneran desde _common
    for existing in os.listdir(dst_dir):
        if existing.lower() in preserve_lower:
            continue
        ep = os.path.join(dst_dir, existing)
        if os.path.isdir(ep):
            shutil.rmtree(ep)
        else:
            os.remove(ep)

    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".tmp", "__pycache__")]
        rel_root = os.path.relpath(root, src_dir)
        target_root = dst_dir if rel_root == "." else os.path.join(dst_dir, rel_root)
        os.makedirs(target_root, exist_ok=True)
        for fname in files:
            if fname.lower() in excluded_lower:
                continue
            src_f = os.path.join(root, fname)
            dst_f = os.path.join(target_root, fname)
            shutil.copy2(src_f, dst_f)
            copied.append(os.path.relpath(dst_f, dst_dir))
    return copied


def promote_visual(vinfo, dst_visual_dir: str, neutral_brand: dict, dry_run: bool) -> None:
    if dry_run:
        return
    os.makedirs(dst_visual_dir, exist_ok=True)
    for meta_name in ROOT_META_FILES:
        src_m = os.path.join(vinfo.path, meta_name)
        if os.path.exists(src_m):
            shutil.copy2(src_m, os.path.join(dst_visual_dir, meta_name))

    # Neutralizar autor/supportUrl en pbiviz.json usando el brand-config del starter-kit
    dst_pj = os.path.join(dst_visual_dir, "pbiviz.json")
    if os.path.exists(dst_pj):
        with open(dst_pj, encoding="utf-8") as f:
            pj = json.load(f)
        client_cfg = neutral_brand.get("client", {})
        if client_cfg.get("supportUrl"):
            pj.setdefault("visual", {})["supportUrl"] = client_cfg["supportUrl"]
        if client_cfg.get("authorName") or client_cfg.get("authorEmail"):
            pj.setdefault("author", {})
            if client_cfg.get("authorName"):
                pj["author"]["name"] = client_cfg["authorName"]
            if client_cfg.get("authorEmail"):
                pj["author"]["email"] = client_cfg["authorEmail"]
        with open(dst_pj, "w", encoding="utf-8") as f:
            json.dump(pj, f, indent=2, ensure_ascii=False)

    copy_clean_dir(os.path.join(vinfo.path, "assets"), os.path.join(dst_visual_dir, "assets"), set(), set())
    copy_clean_dir(
        os.path.join(vinfo.path, "src"),
        os.path.join(dst_visual_dir, "src"),
        EXCLUDED_SRC_FILES,
        EXCLUDED_SRC_FILES,
    )
    copy_clean_dir(
        os.path.join(vinfo.path, "style"),
        os.path.join(dst_visual_dir, "style"),
        EXCLUDED_STYLE_FILES,
        EXCLUDED_STYLE_FILES,
    )


def promote_skills(src_skills_dir: str, dst_skills_dir: str, dry_run: bool) -> list[str]:
    if not os.path.isdir(src_skills_dir):
        raise FileNotFoundError(f"No existe carpeta de skills en origen: {src_skills_dir}")
    catalog_rel = os.path.join("tmdl-semantic-model", "references", "model-catalog.md")
    dst_catalog_p = os.path.join(dst_skills_dir, catalog_rel)
    preserved_catalog = None
    if os.path.exists(dst_catalog_p):
        with open(dst_catalog_p, encoding="utf-8") as f:
            preserved_catalog = f.read()

    if not dry_run:
        shutil.copytree(
            src_skills_dir,
            dst_skills_dir,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            dirs_exist_ok=True,
        )
        # Conservar el catálogo neutro del starter-kit (DimFecha, DimMes, DimMonedaSelector, FactBase)
        if preserved_catalog is not None:
            os.makedirs(os.path.dirname(dst_catalog_p), exist_ok=True)
            with open(dst_catalog_p, "w", encoding="utf-8") as f:
                f.write(preserved_catalog)

    return sorted(
        d for d in os.listdir(src_skills_dir)
        if os.path.isdir(os.path.join(src_skills_dir, d)) and not d.startswith("__")
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Promueve selectivamente mejoras de visuales, _common/ o skills hacia el plugin SnowUI."
    )
    parser.add_argument("--from", dest="src_root", default=".", help="Carpeta raíz del proyecto origen (por defecto '.').")
    parser.add_argument("--plugin", default=None, help="Ruta raíz del plugin global destino (snowui-pbip-kit).")
    parser.add_argument(
        "--visuals",
        default="",
        help="Visual(es) en pbiviz/ a promover separados por coma, o 'all'. No copia tokens del cliente.",
    )
    parser.add_argument(
        "--include-common",
        action="store_true",
        help="Promueve pbiviz/_common/{snowuiUtils.ts,snowuiBase.less} (excluyendo snowuiTokens.*) y recompila todos.",
    )
    parser.add_argument(
        "--include-skills",
        action="store_true",
        help="Promueve .agents/skills/ hacia skills/ del plugin preservando el model-catalog neutro del starter-kit.",
    )
    parser.add_argument("--pbiviz-cmd", default=None, help="Ruta opcional a pbiviz.cmd.")
    parser.add_argument("--shared-node-modules", default=None, help="Ruta opcional a node_modules compartidos.")
    parser.add_argument("--skip-build", action="store_true", help="Copia fuentes sin recompilar los paquetes .pbiviz.")
    parser.add_argument("--dry-run", action="store_true", help="Muestra qué se promovería sin escribir cambios.")
    args = parser.parse_args()

    if not args.visuals.strip() and not args.include_common and not args.include_skills:
        print(
            "ERROR: Especifica qué deseas promover usando al menos uno de: "
            "--visuals <nombre|all>, --include-common o --include-skills.",
            file=sys.stderr,
        )
        return 1

    src_root = os.path.abspath(args.src_root)
    src_pbiviz = os.path.join(src_root, "pbiviz")
    plugin_root = resolve_plugin_root(args.plugin)
    kit_dir = os.path.join(plugin_root, "starter-kit")
    dst_pbiviz = os.path.join(kit_dir, "pbiviz")
    kit_brand_path = os.path.join(kit_dir, "brand-config.json")
    if not os.path.exists(kit_brand_path):
        print(f"ERROR: Falta brand-config.json neutro en {kit_dir}.", file=sys.stderr)
        return 1
    with open(kit_brand_path, encoding="utf-8") as f:
        neutral_brand = json.load(f)

    # Resolver visuales solicitados en origen
    selected_visuals = []
    if args.visuals.strip():
        discovered_src = discover_pbiviz_visuals(src_pbiviz)
        by_folder = {v.folder: v for v in discovered_src}
        if args.visuals.strip().lower() == "all":
            selected_visuals = discovered_src
        else:
            for token in [t.strip() for t in args.visuals.split(",") if t.strip()]:
                if token not in by_folder:
                    avail = ", ".join(by_folder.keys()) or "(ninguno)"
                    print(f"ERROR: Visual '{token}' no existe en {src_pbiviz}. Disponibles: {avail}", file=sys.stderr)
                    return 1
                selected_visuals.append(by_folder[token])

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(f"{prefix}Origen: {src_root}")
    print(f"{prefix}Plugin destino: {plugin_root}")

    # 1. Promover _common shareable si --include-common
    if args.include_common:
        src_common = os.path.join(src_pbiviz, "_common")
        dst_common = os.path.join(dst_pbiviz, "_common")
        for fname in COMMON_SHAREABLE_FILES:
            sf = os.path.join(src_common, fname)
            if not os.path.exists(sf):
                print(f"ERROR: Falta {sf} para --include-common.", file=sys.stderr)
                return 1
            if not args.dry_run:
                os.makedirs(dst_common, exist_ok=True)
                shutil.copy2(sf, os.path.join(dst_common, fname))
            print(f"{prefix}Promovido _common/{fname} (sin snowuiTokens.*)")

    # 2. Promover visuales seleccionados (aislados de tokens/marca del cliente)
    for vinfo in selected_visuals:
        dst_vdir = os.path.join(dst_pbiviz, vinfo.folder)
        is_new = not os.path.exists(dst_vdir)
        promote_visual(vinfo, dst_vdir, neutral_brand, args.dry_run)
        tag = "NUEVO" if is_new else "ACTUALIZADO"
        print(f"{prefix}Visual [{tag}]: {vinfo.folder} ({vinfo.guid})")

    # 3. Promover skills si --include-skills
    if args.include_skills:
        skill_names = promote_skills(
            os.path.join(src_root, ".agents", "skills"),
            os.path.join(plugin_root, "skills"),
            args.dry_run,
        )
        print(f"{prefix}Skills sincronizadas ({len(skill_names)}): {', '.join(skill_names)} (model-catalog neutro preservado)")

    if args.dry_run:
        print("[DRY-RUN] Simulación completada. No se modificó ningún archivo.")
        return 0

    # 4. Reaplicar marca neutra del starter-kit, recompilar y pasar QA
    plugin_skills = os.path.join(plugin_root, "skills")
    apply_script = os.path.join(plugin_skills, "brand-theming", "scripts", "apply_brand.py")
    build_script = os.path.join(plugin_skills, "pbiviz-custom-visual-dev", "scripts", "build_and_unpack_pbiviz.py")
    qa_script = os.path.join(plugin_skills, "pbip-qa-verify", "scripts", "verify_all.py")

    if selected_visuals or args.include_common:
        # Regenerar snowuiTokens.* neutros antes de compilar
        res = subprocess.run([sys.executable, apply_script, "--root", kit_dir, "--skip-build", "--skip-qa"], check=False)
        if res.returncode != 0:
            return res.returncode

        if not args.skip_build:
            pbiviz_exe = find_pbiviz_executable(dst_pbiviz, args.pbiviz_cmd) or find_pbiviz_executable(src_pbiviz, args.pbiviz_cmd)
            shared_nm = find_shared_visual_node_modules(dst_pbiviz, args.shared_node_modules) or find_shared_visual_node_modules(src_pbiviz, args.shared_node_modules)
            if not pbiviz_exe or not shared_nm:
                print(
                    "ERROR: No se encontró toolchain completa (pbiviz CLI + node_modules compartidos) para recompilar en starter-kit. "
                    "Configura SNOWUI_PBIVIZ_CMD / SNOWUI_PBIVIZ_SHARED_NM o pasa --pbiviz-cmd y --shared-node-modules.",
                    file=sys.stderr,
                )
                return 1
            build_target = "all" if args.include_common else ",".join(v.folder for v in selected_visuals)
            res = subprocess.run(
                [
                    sys.executable,
                    build_script,
                    "--root",
                    kit_dir,
                    "--visual",
                    build_target,
                    "--pbiviz-cmd",
                    pbiviz_exe,
                    "--shared-node-modules",
                    shared_nm,
                ],
                check=False,
            )
            if res.returncode != 0:
                return res.returncode

    res = subprocess.run([sys.executable, qa_script, "--root", kit_dir], check=False)
    if res.returncode != 0:
        return res.returncode

    print("\nPromoción al plugin completada con éxito (0 errores). El repo .git del plugin no fue commiteado ni pusheado:")
    print(f'  git -C "{plugin_root}" status')
    print(f'  git -C "{plugin_root}" add -A && git -C "{plugin_root}" commit -m "feat: ..." -m "- ..." && git -C "{plugin_root}" push')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
