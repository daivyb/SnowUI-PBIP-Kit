#!/usr/bin/env python3
"""Gestiona páginas PBIR (clone, delete, set-preset, sync) manteniendo navegación y marcadores sincronizados."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys

SHARED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

from pbip_paths import resolve_pbip_paths  # noqa: E402

SHELL_SUFFIXES = (
    "_alrt_bg", "_alrt_btn", "_alrt_ico", "_alrt_val",
    "_bg_sidebar", "_bg_topbar", "_brand_txt", "_footer",
    "_logo", "_nav_hdr", "_rst_bg", "_rst_btn", "_rst_ico",
    "_rst_txt", "_side_meta", "_slicer_1", "_slicer_2",
    "_sun_bg", "_sun_ico", "_tb_crumb", "_tb_star", "_tb_toggle",
)

PRESET_DIMS = {
    "web-scroll": {"width": 1440, "height": 1708, "displayOption": "FitToWidth"},
    "screen-16x9": {"width": 1440, "height": 810, "displayOption": "FitToPage"},
}


def load_brand_colors(repo_root: str) -> dict:
    cfg_path = os.path.join(repo_root, "brand-config.json")
    if os.path.exists(cfg_path):
        cfg = json.load(open(cfg_path, encoding="utf-8"))
        sb_mode = cfg.get("style", {}).get("sidebarMode", "light")
        colors = cfg.get("colors", {})
        primary = colors.get("brand", {}).get("primary", "#007AFF")
        font = cfg.get("style", {}).get("fontFamily", "Segoe UI")
        if sb_mode == "dark":
            return {"active": primary, "inactive": "#CBD5E1", "font": font, "crumb": colors.get("text", {}).get("primary", "#111827")}
        return {
            "active": primary,
            "inactive": colors.get("text", {}).get("navInactive", "#1F2937"),
            "font": font,
            "crumb": colors.get("text", {}).get("primary", "#111827"),
        }
    return {"active": "#007AFF", "inactive": "#1F2937", "font": "Segoe UI", "crumb": "#111827"}


def make_nav_icon_visual(pid: str, idx: int, icon_name: str, y_pos: int) -> dict:
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json",
        "name": f"{pid}_nav_ico_{idx}",
        "position": {"x": 38, "y": y_pos + 13, "z": 20000 + idx, "height": 20, "width": 20, "tabOrder": 20000 + idx},
        "visual": {
            "visualType": "image",
            "objects": {
                "image": [{
                    "properties": {
                        "sourceFile": {
                            "image": {
                                "name": {"expr": {"Literal": {"Value": f"'{icon_name}'"}}},
                                "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1, "ItemName": icon_name}}},
                                "scaling": {"expr": {"Literal": {"Value": "'Normal'"}}},
                            }
                        },
                        "fit": {"expr": {"Literal": {"Value": "'Fit'"}}},
                    }
                }]
            },
            "visualContainerObjects": {k: [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}] for k in ("visualHeader", "background", "border", "dropShadow", "title")},
        },
    }


def make_nav_label_visual(pid: str, idx: int, label: str, y_pos: int, is_active: bool, palette: dict) -> dict:
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json",
        "name": f"{pid}_nav_lbl_{idx}",
        "position": {"x": 68, "y": y_pos + 4, "z": 21000 + idx, "height": 38, "width": 142, "tabOrder": 21000 + idx},
        "visual": {
            "visualType": "textbox",
            "objects": {
                "general": [{
                    "properties": {
                        "paragraphs": [{
                            "textRuns": [{
                                "value": label,
                                "textStyle": {
                                    "fontFamily": palette["font"],
                                    "fontSize": "10pt",
                                    "fontWeight": "bold" if is_active else "normal",
                                    "color": palette["active"] if is_active else palette["inactive"],
                                },
                            }],
                            "horizontalTextAlignment": "left",
                        }]
                    }
                }]
            },
            "visualContainerObjects": {k: [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}] for k in ("visualHeader", "background", "border", "dropShadow", "title")},
        },
    }


def make_nav_button_visual(pid: str, idx: int, target_pid: str, target_label: str, y_pos: int) -> dict:
    safe_label = target_label.replace("'", "''")
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json",
        "name": f"{pid}_nav_btn_{idx}",
        "position": {"x": 28, "y": y_pos, "z": 29000 + idx, "height": 46, "width": 188, "tabOrder": 29000 + idx},
        "visual": {
            "visualType": "actionButton",
            "objects": {
                "outline": [
                    {"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}},
                    {"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}, "selector": {"id": "default"}},
                ],
                "fill": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
                "text": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
                "icon": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
                "shape": [{"properties": {"roundEdge": {"expr": {"Literal": {"Value": "12L"}}}}, "selector": {"id": "default"}}],
            },
            "visualContainerObjects": {
                **{k: [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}] for k in ("visualHeader", "background", "border", "dropShadow", "title")},
                "visualLink": [{
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "type": {"expr": {"Literal": {"Value": "'PageNavigation'"}}},
                        "navigationSection": {"expr": {"Literal": {"Value": f"'{target_pid}'"}}},
                        "tooltip": {"expr": {"Literal": {"Value": f"'Ir a {safe_label}'"}}},
                    }
                }],
            },
        },
    }


def make_nav_active_pill(pid: str, idx: int, y_pos: int) -> dict:
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json",
        "name": f"{pid}_nav_act_{idx}",
        "position": {"x": 28, "y": y_pos, "z": 3000, "height": 46, "width": 188, "tabOrder": 3000},
        "visual": {
            "visualType": "image",
            "objects": {
                "image": [{
                    "properties": {
                        "sourceFile": {
                            "image": {
                                "name": {"expr": {"Literal": {"Value": "'nav-pill-active.svg'"}}},
                                "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1, "ItemName": "nav-pill-active.svg"}}},
                                "scaling": {"expr": {"Literal": {"Value": "'Normal'"}}},
                            }
                        },
                        "fit": {"expr": {"Literal": {"Value": "'Fill'"}}},
                    }
                }]
            },
            "visualContainerObjects": {k: [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}] for k in ("visualHeader", "background", "border", "dropShadow", "title")},
        },
    }


def detect_page_icons(pages_dir: str, page_ids: list[str], reg_dir: str) -> dict[str, str]:
    """Descubre qué icono usa cada página según los visuales existentes o convenciones icon-*.svg."""
    icons: dict[str, str] = {}
    avail = set(os.listdir(reg_dir)) if os.path.isdir(reg_dir) else set()
    # Buscar mapeo existente en la primera página que tenga nav_btn_* y nav_ico_*
    for pid in page_ids:
        vroot = os.path.join(pages_dir, pid, "visuals")
        if not os.path.isdir(vroot):
            continue
        for vid in os.listdir(vroot):
            m = re.match(rf"^{re.escape(pid)}_nav_btn_(\d+)$", vid)
            if not m:
                continue
            idx = m.group(1)
            btn_p = os.path.join(vroot, vid, "visual.json")
            ico_p = os.path.join(vroot, f"{pid}_nav_ico_{idx}", "visual.json")
            if os.path.exists(btn_p) and os.path.exists(ico_p):
                bdata = json.load(open(btn_p, encoding="utf-8"))
                idata = json.load(open(ico_p, encoding="utf-8"))
                target = bdata.get("visual", {}).get("visualContainerObjects", {}).get("visualLink", [{}])[0].get("properties", {}).get("navigationSection", {}).get("expr", {}).get("Literal", {}).get("Value", "").strip("'")
                iname = idata.get("visual", {}).get("objects", {}).get("image", [{}])[0].get("properties", {}).get("sourceFile", {}).get("image", {}).get("url", {}).get("expr", {}).get("ResourcePackageItem", {}).get("ItemName")
                if target and iname and target not in icons:
                    icons[target] = iname

    for pid in page_ids:
        if pid not in icons:
            candidate = f"icon-{pid}.svg"
            icons[pid] = candidate if candidate in avail else "icon-overview.svg"
    return icons


def sync_all_pages(repo_root: str, report_dir: str, custom_icons: dict[str, str] | None = None) -> None:
    pages_dir = os.path.join(report_dir, "definition", "pages")
    reg_dir = os.path.join(report_dir, "StaticResources", "RegisteredResources")
    pages_meta_path = os.path.join(pages_dir, "pages.json")
    pages_meta = json.load(open(pages_meta_path, encoding="utf-8"))
    page_ids: list[str] = pages_meta.get("pageOrder", [])
    palette = load_brand_colors(repo_root)

    display_names: dict[str, str] = {}
    for pid in page_ids:
        pjson = os.path.join(pages_dir, pid, "page.json")
        pobj = json.load(open(pjson, encoding="utf-8"))
        display_names[pid] = pobj.get("displayName", pid.title())

    icons = detect_page_icons(pages_dir, page_ids, reg_dir)
    if custom_icons:
        icons.update(custom_icons)

    # 1. Reconstruir barra lateral de navegación en TODAS las páginas
    for page_idx, pid in enumerate(page_ids):
        vroot = os.path.join(pages_dir, pid, "visuals")
        if not os.path.isdir(vroot):
            continue

        # Eliminar nav_btn_*, nav_ico_*, nav_lbl_*, nav_act_* anteriores
        for vid in list(os.listdir(vroot)):
            if re.match(rf"^{re.escape(pid)}_nav_(btn|ico|lbl|act)_\d+$", vid):
                shutil.rmtree(os.path.join(vroot, vid), ignore_errors=True)

        # Crear indicador activo
        active_y = 140 + page_idx * 54
        act_dir = os.path.join(vroot, f"{pid}_nav_act_{page_idx}")
        os.makedirs(act_dir, exist_ok=True)
        with open(os.path.join(act_dir, "visual.json"), "w", encoding="utf-8") as f:
            json.dump(make_nav_active_pill(pid, page_idx, active_y), f, indent=2, ensure_ascii=False)

        for idx, target_pid in enumerate(page_ids):
            y_pos = 140 + idx * 54
            is_act = idx == page_idx
            for vobj in (
                make_nav_icon_visual(pid, idx, icons[target_pid], y_pos),
                make_nav_label_visual(pid, idx, display_names[target_pid], y_pos, is_act, palette),
                make_nav_button_visual(pid, idx, target_pid, display_names[target_pid], y_pos),
            ):
                vdir = os.path.join(vroot, vobj["name"])
                os.makedirs(vdir, exist_ok=True)
                with open(os.path.join(vdir, "visual.json"), "w", encoding="utf-8") as f:
                    json.dump(vobj, f, indent=2, ensure_ascii=False)

        # Verificar que *_alrt_btn apunte a una página existente
        alrt_btn_p = os.path.join(vroot, f"{pid}_alrt_btn", "visual.json")
        if os.path.exists(alrt_btn_p) and page_ids:
            ab = json.load(open(alrt_btn_p, encoding="utf-8"))
            vlink = ab.get("visual", {}).get("visualContainerObjects", {}).get("visualLink", [{}])[0].get("properties", {})
            cur_target = vlink.get("navigationSection", {}).get("expr", {}).get("Literal", {}).get("Value", "").strip("'")
            if cur_target not in page_ids:
                fallback_pid = page_ids[1] if len(page_ids) > 1 else page_ids[0]
                vlink.setdefault("navigationSection", {})["expr"] = {"Literal": {"Value": f"'{fallback_pid}'"}}
                if "tooltip" in vlink:
                    vlink["tooltip"] = {"expr": {"Literal": {"Value": f"'Ver detalle en {display_names[fallback_pid]}'"}}}
                with open(alrt_btn_p, "w", encoding="utf-8") as f:
                    json.dump(ab, f, indent=2, ensure_ascii=False)

    # 2. Sincronizar reset_filters.bookmark.json
    bm_path = os.path.join(report_dir, "definition", "bookmarks", "reset_filters.bookmark.json")
    if os.path.exists(bm_path):
        bm = json.load(open(bm_path, encoding="utf-8"))
        sections = bm.setdefault("explorationState", {}).setdefault("sections", {})
        new_sections = {}
        for pid in page_ids:
            vroot = os.path.join(pages_dir, pid, "visuals")
            slicer_containers = {}
            if os.path.isdir(vroot):
                for vid in sorted(os.listdir(vroot)):
                    vfile = os.path.join(vroot, vid, "visual.json")
                    if not os.path.exists(vfile):
                        continue
                    vdata = json.load(open(vfile, encoding="utf-8"))
                    if vdata.get("visual", {}).get("visualType") == "slicer":
                        cname = vdata.get("name", vid)
                        slicer_containers[cname] = {"singleVisual": {"visualType": "slicer", "objects": {}}}
            new_sections[pid] = {"filters": {"byExpr": []}, "visualContainers": slicer_containers}
        bm["explorationState"]["sections"] = new_sections
        if bm["explorationState"].get("activeSection") not in page_ids and page_ids:
            bm["explorationState"]["activeSection"] = page_ids[0]
        with open(bm_path, "w", encoding="utf-8") as f:
            json.dump(bm, f, indent=2, ensure_ascii=False)


def apply_canvas_preset(page_dir: str, pid: str, preset: str) -> None:
    if preset not in PRESET_DIMS:
        raise ValueError(f"Preset desconocido: {preset}")
    pjson_path = os.path.join(page_dir, "page.json")
    pobj = json.load(open(pjson_path, encoding="utf-8"))
    old_h = float(pobj.get("height", 1708))
    target_dim = PRESET_DIMS[preset]
    new_h = float(target_dim["height"])
    pobj["width"] = target_dim["width"]
    pobj["height"] = target_dim["height"]
    pobj["displayOption"] = target_dim["displayOption"]
    with open(pjson_path, "w", encoding="utf-8") as f:
        json.dump(pobj, f, indent=2, ensure_ascii=False)

    if abs(old_h - new_h) < 1:
        return

    # Escalar región de contenido y ajustar sidebar/footer manteniendo topbar fija (y: 14..94)
    vroot = os.path.join(page_dir, "visuals")
    old_body_top = 104.0
    old_body_bottom = old_h - 68.0
    new_body_top = 104.0
    new_body_bottom = new_h - 48.0
    scale_y = (new_body_bottom - new_body_top) / max(100.0, old_body_bottom - old_body_top)

    for vid in sorted(os.listdir(vroot)):
        vfile = os.path.join(vroot, vid, "visual.json")
        if not os.path.exists(vfile):
            continue
        vdata = json.load(open(vfile, encoding="utf-8"))
        vname = vdata.get("name", vid)
        pos = vdata.get("position", {})
        if vname == f"{pid}_bg_sidebar":
            pos["height"] = int(new_h - 28)
        elif vname == f"{pid}_side_meta":
            pos["y"] = int(new_h - 82)
            pos["height"] = 48 if preset == "screen-16x9" else 64
        elif vname == f"{pid}_footer":
            pos["y"] = int(new_h - 42)
            pos["height"] = 36
        elif pos.get("y", 0) >= old_body_top and "_nav_" not in vname:
            rel_y = pos["y"] - old_body_top
            new_y = round(new_body_top + rel_y * scale_y)
            new_vh = max(34 if vdata.get("visual", {}).get("visualType") == "textbox" else 60, round(pos["height"] * scale_y))
            if new_y + new_vh > new_body_bottom:
                new_vh = max(34, int(new_body_bottom - new_y))
            pos["y"] = new_y
            pos["height"] = new_vh
        with open(vfile, "w", encoding="utf-8") as f:
            json.dump(vdata, f, indent=2, ensure_ascii=False)


def cmd_clone(args: argparse.Namespace, paths) -> int:
    pages_dir = os.path.join(paths.report_dir, "definition", "pages")
    src_dir = os.path.join(pages_dir, args.source)
    dst_dir = os.path.join(pages_dir, args.target)
    if not os.path.isdir(src_dir):
        print(f"ERROR: Página origen inexistente: {args.source}", file=sys.stderr)
        return 1
    if os.path.exists(dst_dir):
        print(f"ERROR: La página destino ya existe: {args.target}", file=sys.stderr)
        return 1

    shutil.copytree(src_dir, dst_dir)
    pjson_path = os.path.join(dst_dir, "page.json")
    pobj = json.load(open(pjson_path, encoding="utf-8"))
    pobj["name"] = args.target
    pobj["displayName"] = args.title
    with open(pjson_path, "w", encoding="utf-8") as f:
        json.dump(pobj, f, indent=2, ensure_ascii=False)

    # Renombrar todos los visuales de shell y prefijos internos
    vroot = os.path.join(dst_dir, "visuals")
    for vid in list(os.listdir(vroot)):
        old_vdir = os.path.join(vroot, vid)
        vfile = os.path.join(old_vdir, "visual.json")
        if not os.path.exists(vfile):
            continue
        vdata = json.load(open(vfile, encoding="utf-8"))
        if vid.startswith(f"{args.source}_"):
            new_vid = f"{args.target}_{vid[len(args.source) + 1:]}"
        else:
            new_vid = f"{args.target}_{vid}"
        vdata["name"] = new_vid
        if new_vid == f"{args.target}_tb_crumb":
            runs = vdata.get("visual", {}).get("objects", {}).get("general", [{}])[0].get("properties", {}).get("paragraphs", [{}])[0].get("textRuns", [])
            if len(runs) >= 2:
                runs[1]["value"] = args.title
        new_vdir = os.path.join(vroot, new_vid)
        with open(vfile, "w", encoding="utf-8") as f:
            json.dump(vdata, f, indent=2, ensure_ascii=False)
        if new_vdir != old_vdir:
            os.rename(old_vdir, new_vdir)

    if args.preset:
        apply_canvas_preset(dst_dir, args.target, args.preset)

    pages_meta_path = os.path.join(pages_dir, "pages.json")
    pages_meta = json.load(open(pages_meta_path, encoding="utf-8"))
    order: list[str] = pages_meta.get("pageOrder", [])
    if args.target not in order:
        order.append(args.target)
    pages_meta["pageOrder"] = order
    with open(pages_meta_path, "w", encoding="utf-8") as f:
        json.dump(pages_meta, f, indent=2, ensure_ascii=False)

    custom_icons = {args.target: args.icon} if args.icon else None
    sync_all_pages(paths.repo_root, paths.report_dir, custom_icons)
    print(f"Página '{args.target}' ({args.title}) clonada desde '{args.source}' y sincronizada.")
    return 0


def cmd_delete(args: argparse.Namespace, paths) -> int:
    pages_dir = os.path.join(paths.report_dir, "definition", "pages")
    pages_meta_path = os.path.join(pages_dir, "pages.json")
    pages_meta = json.load(open(pages_meta_path, encoding="utf-8"))
    order: list[str] = pages_meta.get("pageOrder", [])
    if args.target not in order:
        print(f"ERROR: La página '{args.target}' no está en pageOrder.", file=sys.stderr)
        return 1
    if len(order) <= 1:
        print("ERROR: No se puede eliminar la única página restante del reporte.", file=sys.stderr)
        return 1

    order.remove(args.target)
    pages_meta["pageOrder"] = order
    if pages_meta.get("activePageName") == args.target:
        pages_meta["activePageName"] = order[0]
    if pages_meta.get("landingPageName") == args.target:
        pages_meta["landingPageName"] = order[0]
    with open(pages_meta_path, "w", encoding="utf-8") as f:
        json.dump(pages_meta, f, indent=2, ensure_ascii=False)

    target_dir = os.path.join(pages_dir, args.target)
    if os.path.isdir(target_dir):
        shutil.rmtree(target_dir)

    sync_all_pages(paths.repo_root, paths.report_dir)
    print(f"Página '{args.target}' eliminada y navegación sincronizada ({len(order)} páginas restantes).")
    return 0


def cmd_set_preset(args: argparse.Namespace, paths) -> int:
    pages_dir = os.path.join(paths.report_dir, "definition", "pages")
    pages_meta = json.load(open(os.path.join(pages_dir, "pages.json"), encoding="utf-8"))
    targets = pages_meta.get("pageOrder", []) if args.target == "all" else [args.target]
    for pid in targets:
        pdir = os.path.join(pages_dir, pid)
        if os.path.isdir(pdir):
            apply_canvas_preset(pdir, pid, args.preset)
    print(f"Preset '{args.preset}' aplicado a: {', '.join(targets)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Gestiona páginas modulares PBIR sin romper enlaces ni marcadores.")
    parser.add_argument("--root", default=".", help="Raíz del proyecto PBIP.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_clone = sub.add_parser("clone", help="Duplica una página arquetipo con nuevo ID y título.")
    p_clone.add_argument("--source", required=True, help="ID de la página origen (ej. overview, proyectos).")
    p_clone.add_argument("--target", required=True, help="Nuevo ID de página (snake_case).")
    p_clone.add_argument("--title", required=True, help="Título visible en sidebar y breadcrumb.")
    p_clone.add_argument("--icon", default=None, help="SVG registrado (ej. icon-overview.svg).")
    p_clone.add_argument("--preset", choices=list(PRESET_DIMS.keys()), default=None)

    p_del = sub.add_parser("delete", help="Elimina una página de forma segura.")
    p_del.add_argument("--target", required=True, help="ID de la página a eliminar.")

    p_pre = sub.add_parser("set-preset", help="Ajusta una o todas las páginas a web-scroll o screen-16x9.")
    p_pre.add_argument("--target", default="all", help="ID de página o 'all'.")
    p_pre.add_argument("--preset", required=True, choices=list(PRESET_DIMS.keys()))

    sub.add_parser("sync", help="Resincroniza barra lateral y reset_filters.bookmark.json en todas las páginas.")

    args = parser.parse_args()
    paths = resolve_pbip_paths(args.root)

    if args.cmd == "clone":
        return cmd_clone(args, paths)
    if args.cmd == "delete":
        return cmd_delete(args, paths)
    if args.cmd == "set-preset":
        return cmd_set_preset(args, paths)
    if args.cmd == "sync":
        sync_all_pages(paths.repo_root, paths.report_dir)
        print("Sincronización de navegación y marcadores completada.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
