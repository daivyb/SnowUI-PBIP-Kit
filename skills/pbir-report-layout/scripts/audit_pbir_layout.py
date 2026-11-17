#!/usr/bin/env python3
"""Audita integridad PBIR, geometría anti-recorte, navegación/marcadores y bindings contra TMDL."""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

SHARED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

from pbip_paths import (  # noqa: E402
    discover_pbiviz_visuals,
    discover_unpacked_custom_visuals,
    resolve_pbip_paths,
)

NATIVE_VISUALS = {
    "image", "textbox", "actionButton", "slicer", "card", "map",
    "barChart", "columnChart", "lineChart", "areaChart", "clusteredBarChart",
    "clusteredColumnChart", "donutChart", "pieChart", "pivotTable", "tableEx", "treemap",
}


def load_tmdl_symbols(model_dir: str) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    columns: dict[str, set[str]] = {}
    measures: dict[str, set[str]] = {}
    for path in glob.glob(os.path.join(model_dir, "definition", "tables", "*.tmdl")):
        tname = os.path.basename(path)[:-5]
        cols: set[str] = set()
        meas: set[str] = set()
        with open(path, encoding="utf-8") as f:
            for line in f:
                m_col = re.match(r"^\tcolumn\s+'([^']+)'|^\tcolumn\s+([^\s=]+)", line)
                if m_col:
                    cols.add((m_col.group(1) or m_col.group(2)).strip())
                m_meas = re.match(r"^\tmeasure\s+'([^']+)'|^\tmeasure\s+([^=\r\n]+?)(?:\s*=|$)", line)
                if m_meas:
                    meas.add((m_meas.group(1) or m_meas.group(2)).strip())
        columns[tname] = cols
        measures[tname] = meas
    return columns, measures


def check_query_fields(obj: object, columns: dict[str, set[str]], measures: dict[str, set[str]], ctx: str, errors: list[str]) -> None:
    if isinstance(obj, dict):
        for key, expected_map, kind in [("Column", columns, "Columna"), ("Measure", measures, "Medida")]:
            if key in obj and isinstance(obj[key], dict):
                node = obj[key]
                entity = node.get("Expression", {}).get("SourceRef", {}).get("Entity")
                prop = node.get("Property")
                if not entity or not prop:
                    errors.append(f"{ctx}: {kind} incompleta ({node}).")
                elif prop not in expected_map.get(entity, set()):
                    errors.append(f"{ctx}: {kind} inexistente '{entity}.{prop}'.")
        for v in obj.values():
            check_query_fields(v, columns, measures, ctx, errors)
    elif isinstance(obj, list):
        for item in obj:
            check_query_fields(item, columns, measures, ctx, errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita páginas, visuales y enlaces PBIR.")
    parser.add_argument("--root", default=".", help="Raíz del repositorio PBIP.")
    args = parser.parse_args()

    paths = resolve_pbip_paths(args.root)
    report_dir = paths.report_dir
    model_dir = paths.semantic_model_dir
    reg_dir = os.path.join(report_dir, "StaticResources", "RegisteredResources")
    pages_dir = os.path.join(report_dir, "definition", "pages")
    bm_dir = os.path.join(report_dir, "definition", "bookmarks")

    errors: list[str] = []
    warnings: list[str] = []

    columns, measures = load_tmdl_symbols(model_dir)
    reg_files = set(os.listdir(reg_dir)) if os.path.isdir(reg_dir) else set()
    cv_dirs = set(os.listdir(os.path.join(report_dir, "CustomVisuals"))) if os.path.isdir(os.path.join(report_dir, "CustomVisuals")) else set()
    pbiviz_guids = {v.guid for v in discover_pbiviz_visuals(os.path.join(paths.repo_root, "pbiviz"))}
    custom_visuals = pbiviz_guids | discover_unpacked_custom_visuals(report_dir)

    for req_cv in sorted(custom_visuals):
        pkg_p = os.path.join(report_dir, "CustomVisuals", req_cv, "package.json")
        res_p = os.path.join(report_dir, "CustomVisuals", req_cv, "resources", f"{req_cv}.pbiviz.json")
        if not (os.path.exists(pkg_p) and os.path.exists(res_p)):
            errors.append(f"CustomVisual incompleto o faltante: {req_cv}")

    report_json_path = os.path.join(report_dir, "definition", "report.json")
    registered_declared: set[str] = set()
    if os.path.exists(report_json_path):
        rj = json.load(open(report_json_path, encoding="utf-8"))
        for pkg in rj.get("resourcePackages", []):
            if pkg.get("name") == "RegisteredResources":
                for item in pkg.get("items", []):
                    if item.get("path"):
                        registered_declared.add(item["path"])
                        if item["path"] not in reg_files:
                            errors.append(f"report.json declara recurso faltante en RegisteredResources/: {item['path']}")

    pages_meta_path = os.path.join(pages_dir, "pages.json")
    if not os.path.exists(pages_meta_path):
        errors.append("Falta definition/pages/pages.json")
        page_ids: list[str] = []
    else:
        pages_meta = json.load(open(pages_meta_path, encoding="utf-8"))
        page_ids = pages_meta.get("pageOrder", [])

    bm_names: set[str] = set()
    reset_sections: dict[str, object] = {}
    bm_meta_path = os.path.join(bm_dir, "bookmarks.json")
    if os.path.exists(bm_meta_path):
        bm_meta = json.load(open(bm_meta_path, encoding="utf-8"))
        bm_names = {item["name"] for item in bm_meta.get("items", []) if "name" in item}
        reset_bm_path = os.path.join(bm_dir, "reset_filters.bookmark.json")
        if os.path.exists(reset_bm_path):
            rbm = json.load(open(reset_bm_path, encoding="utf-8"))
            reset_sections = rbm.get("explorationState", {}).get("sections", {})

    total_visuals = 0
    for pid in page_ids:
        pjson = os.path.join(pages_dir, pid, "page.json")
        if not os.path.exists(pjson):
            errors.append(f"Página '{pid}' declarada en pages.json pero falta page.json")
            continue
        page_obj = json.load(open(pjson, encoding="utf-8"))
        pw = page_obj.get("width", 1440)
        ph = page_obj.get("height", 1708)

        vroot = os.path.join(pages_dir, pid, "visuals")
        if not os.path.isdir(vroot):
            errors.append(f"Página '{pid}' sin carpeta visuals/")
            continue

        page_slicers: set[str] = set()
        page_nav_targets: set[str] = set()

        for vid in sorted(os.listdir(vroot)):
            vfile = os.path.join(vroot, vid, "visual.json")
            if not os.path.exists(vfile):
                continue
            total_visuals += 1
            vdata = json.load(open(vfile, encoding="utf-8"))
            ctx = f"{pid}/{vid}"
            pos = vdata.get("position", {})
            x, y, w, h = pos.get("x", 0), pos.get("y", 0), pos.get("width", 0), pos.get("height", 0)
            if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > pw or y + h > ph:
                errors.append(f"{ctx}: posición fuera de lienzo ({x},{y},{w}x{h}) vs ({pw}x{ph}).")

            vis = vdata.get("visual", {})
            vtype = vis.get("visualType", "")
            if vtype not in NATIVE_VISUALS and vtype not in custom_visuals:
                errors.append(f"{ctx}: visualType desconocido '{vtype}'.")
            if vtype in custom_visuals and vtype not in cv_dirs:
                errors.append(f"{ctx}: CustomVisual '{vtype}' no desempaquetado.")

            if vtype == "textbox" and h < 34:
                errors.append(f"{ctx}: textbox con height={h} < 34px puede provocar barra de desplazamiento/recorte.")
            if vtype == "slicer":
                page_slicers.add(vdata.get("name", vid))
                if h < 60:
                    errors.append(f"{ctx}: slicer con height={h} < 60px puede recortar el control Dropdown.")

            if vtype == "image":
                src = vis.get("objects", {}).get("image", [{}])[0].get("properties", {}).get("sourceFile", {}).get("image", {})
                item_name = src.get("url", {}).get("expr", {}).get("ResourcePackageItem", {}).get("ItemName")
                if item_name and item_name not in reg_files:
                    errors.append(f"{ctx}: imagen '{item_name}' no existe en RegisteredResources.")
                if item_name and registered_declared and item_name not in registered_declared:
                    errors.append(f"{ctx}: imagen '{item_name}' no está declarada en report.json -> RegisteredResources.")

            if vtype == "actionButton":
                vlink = vis.get("visualContainerObjects", {}).get("visualLink", [{}])[0].get("properties", {})
                ltype = vlink.get("type", {}).get("expr", {}).get("Literal", {}).get("Value", "").strip("'")
                if ltype == "PageNavigation":
                    target = vlink.get("navigationSection", {}).get("expr", {}).get("Literal", {}).get("Value", "").strip("'")
                    page_nav_targets.add(target)
                    if target not in page_ids:
                        errors.append(f"{ctx}: navegación hacia página inexistente '{target}'.")
                elif ltype == "Bookmark":
                    target = vlink.get("bookmark", {}).get("expr", {}).get("Literal", {}).get("Value", "").strip("'")
                    if target not in bm_names:
                        errors.append(f"{ctx}: marcador inexistente '{target}'.")

            check_query_fields(vis.get("query", {}), columns, measures, ctx, errors)

        if "reset_filters" in bm_names and page_slicers:
            if pid not in reset_sections:
                errors.append(f"reset_filters.bookmark.json no incluye sección para la página '{pid}'.")
            else:
                bm_vc = set(reset_sections[pid].get("visualContainers", {}).keys())
                missing_slicers = page_slicers - bm_vc
                if missing_slicers:
                    warnings.append(f"reset_filters.bookmark.json en '{pid}' omite slicers: {sorted(missing_slicers)}")

        if page_nav_targets and set(page_ids) - page_nav_targets:
            missing_nav = sorted(set(page_ids) - page_nav_targets)
            warnings.append(f"Página '{pid}': navegación sidebar no apunta a {missing_nav}")

    if reset_sections:
        orphan_bm = set(reset_sections.keys()) - set(page_ids)
        if orphan_bm:
            errors.append(f"reset_filters.bookmark.json referencia páginas eliminadas: {sorted(orphan_bm)}")

    for w in warnings:
        print("WARN:", w)
    if errors:
        for err in errors:
            print("ERROR:", err, file=sys.stderr)
        print(f"Auditoría PBIR fallida: {len(errors)} error(es).", file=sys.stderr)
        return 1

    print(f"Auditoría PBIR OK: {len(page_ids)} páginas, {total_visuals} visuales, {len(bm_names)} marcador(es), 0 errores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
