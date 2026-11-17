#!/usr/bin/env python3
"""Sincroniza _common/ (tokens + base + utils), compila con pbiviz.cmd, registra en report.json y desempaqueta en CustomVisuals."""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import stat
import subprocess
import sys
import zipfile

SHARED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

from pbip_paths import (  # noqa: E402
    discover_pbiviz_visuals,
    ensure_report_custom_visual,
    find_pbiviz_executable,
    find_shared_visual_node_modules,
    find_tools_node_modules,
    resolve_pbip_paths,
)


def remove_dir_or_junction(path: str) -> None:
    """Elimina de forma segura una copia temporal o junction NTFS sin borrar el destino del enlace."""
    if not os.path.lexists(path):
        return
    try:
        st = os.lstat(path)
        is_reparse = bool(getattr(st, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400))
        if is_reparse or os.path.islink(path):
            os.rmdir(path)
            return
    except OSError:
        pass
    shutil.rmtree(path, ignore_errors=True)


def ensure_linked_or_temp_copy(
    dst_dir: str,
    src_dir: str,
    temp_cleanup_dirs: list[str],
) -> bool:
    """Usa dst_dir si existe; si falta, enlaza (junction/symlink) o crea copia temporal desde src_dir."""
    if os.path.exists(dst_dir):
        return True
    if not src_dir or not os.path.isdir(src_dir):
        return False

    if os.name == "nt":
        res = subprocess.run(["cmd", "/c", "mklink", "/J", dst_dir, src_dir], check=False, capture_output=True)
        if res.returncode == 0 and os.path.exists(dst_dir):
            temp_cleanup_dirs.append(dst_dir)
            return True
        # Fallback rápido con robocopy si mklink /J no está permitido en el entorno
        os.makedirs(dst_dir, exist_ok=True)
        rc = subprocess.run(
            ["robocopy", src_dir, dst_dir, "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS", "/MT:16"],
            check=False,
            capture_output=True,
        )
        if rc.returncode < 8 and os.path.exists(dst_dir):
            temp_cleanup_dirs.append(dst_dir)
            return True
        shutil.rmtree(dst_dir, ignore_errors=True)
        return False

    try:
        os.symlink(src_dir, dst_dir)
        if os.path.exists(dst_dir):
            temp_cleanup_dirs.append(dst_dir)
            return True
    except OSError:
        pass
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
    temp_cleanup_dirs.append(dst_dir)
    return os.path.exists(dst_dir)


def ensure_visual_node_modules(
    vpath: str,
    pbiviz_root: str,
    explicit_shared: str | None = None,
    temp_cleanup_dirs: list[str] | None = None,
) -> bool:
    """Asegura node_modules (d3, api, typescript) para el visual objetivo."""
    v_nm = os.path.join(vpath, "node_modules")
    if os.path.exists(v_nm):
        return True
    shared_nm = find_shared_visual_node_modules(pbiviz_root, explicit_shared)
    if not shared_nm:
        return False
    return ensure_linked_or_temp_copy(v_nm, shared_nm, temp_cleanup_dirs if temp_cleanup_dirs is not None else [])


def resolve_targets(discovered: list, raw_visual_arg: str) -> list:
    by_folder = {v.folder: v for v in discovered}
    if raw_visual_arg.strip().lower() == "all":
        return discovered
    selected = []
    for token in [p.strip() for p in raw_visual_arg.split(",") if p.strip()]:
        if token not in by_folder:
            avail = ", ".join(by_folder.keys()) or "(ninguno)"
            raise KeyError(f"Visual '{token}' no encontrado en pbiviz/. Disponibles: {avail}")
        selected.append(by_folder[token])
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Compila y desempaqueta visuales PBIVIZ de SnowUI.")
    parser.add_argument(
        "--visual",
        default="all",
        help="Nombre(s) de carpeta en pbiviz/ separados por coma, o 'all' para todos.",
    )
    parser.add_argument(
        "--no-sync-common",
        action="store_true",
        help="Omitir la copia automática de pbiviz/_common/{snowuiTokens,snowuiBase,snowuiUtils}.",
    )
    parser.add_argument("--pbiviz-cmd", default=None, help="Ruta opcional a pbiviz.cmd.")
    parser.add_argument("--shared-node-modules", default=None, help="Ruta a node_modules compartidos (d3, api, typescript).")
    parser.add_argument("--root", default=".", help="Ruta raíz del repositorio (por defecto '.').")
    args = parser.parse_args()

    paths = resolve_pbip_paths(args.root)
    repo_root = paths.repo_root
    pbiviz_root = os.path.join(repo_root, "pbiviz")
    discovered = discover_pbiviz_visuals(pbiviz_root)
    if not discovered:
        print(f"ERROR: No se encontraron visuales con pbiviz.json en {pbiviz_root}.", file=sys.stderr)
        return 1

    try:
        targets = resolve_targets(discovered, args.visual)
    except KeyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    pbiviz_exe = find_pbiviz_executable(pbiviz_root, args.pbiviz_cmd)
    if not pbiviz_exe:
        print(
            "ERROR: No se encontró pbiviz CLI. Configura SNOWUI_PBIVIZ_CMD, --pbiviz-cmd o instala pbiviz global.",
            file=sys.stderr,
        )
        return 1

    common_dir = os.path.join(pbiviz_root, "_common")
    dist_dir = os.path.join(pbiviz_root, "dist")
    tmp_home = os.path.join(pbiviz_root, "_tmp_home")
    os.makedirs(tmp_home, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)

    env = os.environ.copy()
    env["USERPROFILE"] = tmp_home
    env["HOME"] = tmp_home

    temp_cleanup_dirs: list[str] = []
    temp_cleanup_dirs: list[str] = []
    try:
        tools_nm = find_tools_node_modules(pbiviz_root, pbiviz_exe)
        if tools_nm:
            ensure_linked_or_temp_copy(os.path.join(pbiviz_root, "node_modules"), tools_nm, temp_cleanup_dirs)

        for vinfo in targets:
            vname = vinfo.folder
            guid = vinfo.guid
            vpath = vinfo.path
            if not ensure_visual_node_modules(vpath, pbiviz_root, args.shared_node_modules, temp_cleanup_dirs):
                print(
                    f"ERROR: {vname} no tiene node_modules ni se encontró toolchain compartida "
                    "(pbiviz/_shared/node_modules, SNOWUI_PBIVIZ_SHARED_NM o --shared-node-modules).",
                    file=sys.stderr,
                )
                return 1

            if not args.no_sync_common and os.path.isdir(common_dir):
                for fname, subdir in [
                    ("snowuiTokens.less", "style"),
                    ("snowuiBase.less", "style"),
                    ("snowuiTokens.ts", "src"),
                    ("snowuiUtils.ts", "src"),
                ]:
                    src_f = os.path.join(common_dir, fname)
                    if os.path.exists(src_f):
                        os.makedirs(os.path.join(vpath, subdir), exist_ok=True)
                        shutil.copy2(src_f, os.path.join(vpath, subdir, fname))

            for old_pkg in glob.glob(os.path.join(vpath, "dist", "*.pbiviz")):
                os.remove(old_pkg)

            print(f"=== Empaquetando {vname} ({guid}) ===", flush=True)
            res = subprocess.run(
                [pbiviz_exe, "package", "--skip-api", "--verbose"],
                cwd=vpath,
                env=env,
                capture_output=True,
                text=True,
                shell=True,
            )
            if res.returncode != 0:
                print(res.stdout[-2000:], file=sys.stderr)
                print(res.stderr[-1000:], file=sys.stderr)
                print(f"ERROR: pbiviz package falló en {vname} (rc={res.returncode}).", file=sys.stderr)
                return res.returncode

            pkgs = glob.glob(os.path.join(vpath, "dist", "*.pbiviz"))
            if len(pkgs) != 1:
                print(f"ERROR: Se esperaba 1 .pbiviz en {vpath}/dist, encontrado: {pkgs}", file=sys.stderr)
                return 1
            pkg_file = pkgs[0]
            for old_dist in glob.glob(os.path.join(dist_dir, f"{guid}.*.pbiviz")):
                os.remove(old_dist)
            shutil.copy2(pkg_file, os.path.join(dist_dir, os.path.basename(pkg_file)))

            cv_dir = os.path.join(paths.report_dir, "CustomVisuals", guid)
            os.makedirs(os.path.join(cv_dir, "resources"), exist_ok=True)
            res_json_member = f"resources/{guid}.pbiviz.json"
            with zipfile.ZipFile(pkg_file, "r") as zf:
                names = zf.namelist()
                if "package.json" not in names or res_json_member not in names:
                    print(f"ERROR: El paquete {pkg_file} no contiene package.json o {res_json_member}.", file=sys.stderr)
                    return 1
                with open(os.path.join(cv_dir, "package.json"), "wb") as f:
                    f.write(zf.read("package.json"))
                with open(os.path.join(cv_dir, "resources", f"{guid}.pbiviz.json"), "wb") as f:
                    f.write(zf.read(res_json_member))

            registered = ensure_report_custom_visual(paths.report_dir, guid)
            extra_msg = " (+ registrado en report.json)" if registered else ""
            print(f"OK: {os.path.basename(pkg_file)} -> {cv_dir}{extra_msg}", flush=True)
    finally:
        for temp_dir in temp_cleanup_dirs:
            remove_dir_or_junction(temp_dir)
        shutil.rmtree(tmp_home, ignore_errors=True)

    print("Empaquetado y despliegue PBIVIZ completados (0 errores).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
