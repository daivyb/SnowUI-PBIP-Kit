#!/usr/bin/env python3
"""Utilidades compartidas para descubrir dinámicamente proyectos PBIP, Report, SemanticModel y visuales PBIVIZ."""

from __future__ import annotations

import glob
import json
import os
import shutil
from dataclasses import dataclass

IGNORED_PBIVIZ_DIRS = {
    "_common",
    "_shared",
    "_tools",
    "_tmp_home",
    "dist",
    "node_modules",
    ".tmp",
}


@dataclass(frozen=True)
class PbipProjectPaths:
    repo_root: str
    pbip_file: str
    project_name: str
    report_dir: str
    semantic_model_dir: str
    pbism_file: str
    pbir_file: str


@dataclass(frozen=True)
class PbivizVisualInfo:
    folder: str
    guid: str
    version: str
    path: str
    pbiviz_json_path: str


def find_repo_root(start: str = ".") -> str:
    """Sube desde `start` hasta localizar el primer directorio con un archivo *.pbip."""
    cur = os.path.abspath(start)
    if os.path.isfile(cur):
        cur = os.path.dirname(cur)
    while True:
        matches = sorted(glob.glob(os.path.join(cur, "*.pbip")))
        if matches:
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            raise FileNotFoundError("No se encontró ningún archivo *.pbip en este directorio ni en los superiores.")
        cur = parent


def resolve_pbip_paths(start: str = ".", pbip_name: str | None = None) -> PbipProjectPaths:
    """Resuelve rutas reales de *.pbip, *.Report y *.SemanticModel sin hardcodear nombres."""
    repo_root = find_repo_root(start)
    candidates = sorted(glob.glob(os.path.join(repo_root, "*.pbip")))
    if pbip_name:
        target = os.path.join(repo_root, pbip_name if pbip_name.endswith(".pbip") else f"{pbip_name}.pbip")
        if not os.path.exists(target):
            raise FileNotFoundError(f"No existe el archivo PBIP especificado: {target}")
        pbip_file = target
    elif len(candidates) == 1:
        pbip_file = candidates[0]
    else:
        # Si hay varios .pbip, priorizar uno distinto a Template.pbip si existe, o el primero alfabético
        non_template = [c for c in candidates if os.path.basename(c).lower() != "template.pbip"]
        pbip_file = non_template[0] if non_template else candidates[0]

    project_name = os.path.splitext(os.path.basename(pbip_file))[0]
    with open(pbip_file, encoding="utf-8") as f:
        pbip_data = json.load(f)

    report_rel = None
    for art in pbip_data.get("artifacts", []):
        if isinstance(art, dict) and isinstance(art.get("report"), dict) and art["report"].get("path"):
            report_rel = art["report"]["path"]
            break
    if not report_rel:
        report_rel = f"{project_name}.Report"

    report_dir = os.path.normpath(os.path.join(repo_root, report_rel))
    pbir_file = os.path.join(report_dir, "definition.pbir")

    model_dir = os.path.normpath(os.path.join(repo_root, f"{project_name}.SemanticModel"))
    if os.path.exists(pbir_file):
        with open(pbir_file, encoding="utf-8") as f:
            pbir_data = json.load(f)
        by_path = pbir_data.get("datasetReference", {}).get("byPath", {}).get("path")
        if by_path:
            model_dir = os.path.normpath(os.path.join(report_dir, by_path))

    pbism_file = os.path.join(model_dir, "definition.pbism")
    return PbipProjectPaths(
        repo_root=repo_root,
        pbip_file=pbip_file,
        project_name=project_name,
        report_dir=report_dir,
        semantic_model_dir=model_dir,
        pbism_file=pbism_file,
        pbir_file=pbir_file,
    )


def discover_pbiviz_visuals(pbiviz_root: str) -> list[PbivizVisualInfo]:
    """Descubre dinámicamente todos los visuales PBIVIZ con pbiviz.json dentro de pbiviz/."""
    visuals: list[PbivizVisualInfo] = []
    if not os.path.isdir(pbiviz_root):
        return visuals

    for entry in sorted(os.listdir(pbiviz_root)):
        if entry in IGNORED_PBIVIZ_DIRS or entry.startswith(".") or entry.startswith("_"):
            continue
        vpath = os.path.join(pbiviz_root, entry)
        pj_path = os.path.join(vpath, "pbiviz.json")
        if not (os.path.isdir(vpath) and os.path.exists(pj_path)):
            continue
        with open(pj_path, encoding="utf-8") as f:
            pj = json.load(f)
        vis = pj.get("visual", {})
        guid = str(vis.get("guid") or "").strip()
        if not guid:
            continue
        version = str(vis.get("version") or "1.0.0.0").strip()
        visuals.append(
            PbivizVisualInfo(
                folder=entry,
                guid=guid,
                version=version,
                path=vpath,
                pbiviz_json_path=pj_path,
            )
        )
    return visuals


def discover_unpacked_custom_visuals(report_dir: str) -> set[str]:
    """Devuelve el conjunto de GUIDs desempaquetados válidamente en CustomVisuals/."""
    cv_root = os.path.join(report_dir, "CustomVisuals")
    found: set[str] = set()
    if not os.path.isdir(cv_root):
        return found

    for guid in sorted(os.listdir(cv_root)):
        cv_dir = os.path.join(cv_root, guid)
        if not os.path.isdir(cv_dir):
            continue
        pkg_p = os.path.join(cv_dir, "package.json")
        res_p = os.path.join(cv_dir, "resources", f"{guid}.pbiviz.json")
        if os.path.exists(pkg_p) and os.path.exists(res_p):
            found.add(guid)
    return found


def ensure_report_custom_visual(report_dir: str, guid: str) -> bool:
    """Registra el CustomVisual en definition/report.json -> resourcePackages si falta."""
    report_json_path = os.path.join(report_dir, "definition", "report.json")
    if not os.path.exists(report_json_path):
        return False

    with open(report_json_path, encoding="utf-8") as f:
        rj = json.load(f)

    pkgs = rj.setdefault("resourcePackages", [])
    for pkg in pkgs:
        if pkg.get("type") == "CustomVisual" and pkg.get("name") == guid:
            return False

    pkgs.append(
        {
            "name": guid,
            "type": "CustomVisual",
            "items": [
                {
                    "name": f"{guid}.pbiviz.json",
                    "path": f"{guid}.pbiviz.json",
                    "type": "CustomVisualMetadata",
                }
            ],
        }
    )
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(rj, f, indent=2, ensure_ascii=False)
    return True


def _laptop_toolchain_roots() -> list[str]:
    roots: list[str] = []
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        roots.append(os.path.join(local_app, "SnowUIPbipKit"))
    roots.append(os.path.join(os.path.expanduser("~"), ".snowui-pbip-kit"))
    return roots


def find_pbiviz_executable(pbiviz_root: str, explicit_cmd: str | None = None) -> str:
    """Localiza pbiviz CLI en el proyecto actual, variables de entorno o caché global del equipo."""
    bin_names = ("pbiviz.cmd", "pbiviz") if os.name == "nt" else ("pbiviz",)
    candidates: list[str] = []
    if explicit_cmd:
        candidates.append(explicit_cmd)

    for bname in bin_names:
        candidates.append(os.path.join(pbiviz_root, "node_modules", ".bin", bname))
        candidates.append(os.path.join(pbiviz_root, "_tools", "node_modules", ".bin", bname))

    env_cmd = os.environ.get("SNOWUI_PBIVIZ_CMD", "").strip()
    if env_cmd:
        candidates.append(env_cmd)

    for root in _laptop_toolchain_roots():
        for bname in bin_names:
            candidates.append(os.path.join(root, "toolchain", "node_modules", ".bin", bname))
            candidates.append(os.path.join(root, "_tools", "node_modules", ".bin", bname))

    for cand in candidates:
        if cand and os.path.exists(cand):
            return os.path.abspath(cand)

    for bname in bin_names:
        found = shutil.which(bname)
        if found:
            return found
    return ""


def find_shared_visual_node_modules(pbiviz_root: str, explicit_dir: str | None = None) -> str:
    """Localiza node_modules compartidos (d3, powerbi-visuals-api, typescript) en proyecto o equipo."""
    candidates: list[str] = []
    if explicit_dir:
        candidates.append(explicit_dir)
    candidates.append(os.path.join(pbiviz_root, "_shared", "node_modules"))

    env_nm = os.environ.get("SNOWUI_PBIVIZ_SHARED_NM", "").strip()
    if env_nm:
        candidates.append(env_nm)

    for root in _laptop_toolchain_roots():
        candidates.append(os.path.join(root, "shared_node_modules"))
        candidates.append(os.path.join(root, "_shared", "node_modules"))

    for cand in candidates:
        if cand and os.path.isdir(cand):
            return os.path.abspath(cand)
    return ""


def find_tools_node_modules(
    pbiviz_root: str,
    pbiviz_exe: str = "",
    explicit_dir: str | None = None,
) -> str:
    """Localiza node_modules del toolchain (ts-loader, less-loader, etc.) para webpack de pbiviz."""
    candidates: list[str] = []
    if explicit_dir:
        candidates.append(explicit_dir)
    candidates.append(os.path.join(pbiviz_root, "node_modules"))
    candidates.append(os.path.join(pbiviz_root, "_tools", "node_modules"))

    if pbiviz_exe:
        exe_abs = os.path.abspath(pbiviz_exe)
        parent = os.path.dirname(exe_abs)
        if os.path.basename(parent).lower() == ".bin":
            candidates.append(os.path.dirname(parent))
        candidates.append(os.path.join(parent, "node_modules", "powerbi-visuals-tools", "node_modules"))
        candidates.append(os.path.join(parent, "node_modules"))

    env_nm = os.environ.get("SNOWUI_PBIVIZ_TOOLS_NM", "").strip()
    if env_nm:
        candidates.append(env_nm)

    for root in _laptop_toolchain_roots():
        candidates.append(os.path.join(root, "toolchain", "node_modules"))
        candidates.append(os.path.join(root, "_tools", "node_modules"))

    for cand in candidates:
        if cand and os.path.isdir(os.path.join(cand, "ts-loader")):
            return os.path.abspath(cand)
    return ""
