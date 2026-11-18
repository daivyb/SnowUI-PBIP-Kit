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


def load_layout_cache(repo_root: str) -> dict:
    p = os.path.join(repo_root, ".snowui-page-layouts.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_layout_cache(repo_root: str, cache: dict) -> None:
    p = os.path.join(repo_root, ".snowui-page-layouts.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def sync_sidebar_svg_height(report_dir: str, page_height: int) -> None:
    sb_svg = os.path.join(report_dir, "StaticResources", "RegisteredResources", "chrome-sidebar.svg")
    if not os.path.exists(sb_svg):
        return
    txt = open(sb_svg, encoding="utf-8").read()
    sb_h = max(700, int(page_height) - 28)
    sb_div_bottom = sb_h - 82
    txt = re.sub(r'height="\d+"', f'height="{sb_h}"', txt, count=1)
    txt = re.sub(r'viewBox="0 0 212 \d+"', f'viewBox="0 0 212 {sb_h}"', txt, count=1)
    txt = re.sub(r'(<rect\b[^>]*\bheight=")\d+(")', rf"\g<1>{sb_h - 1}\g<2>", txt, count=1)
    lines = list(re.finditer(r'<line\b[^>]*/>', txt))
    if len(lines) >= 2:
        last_line = lines[-1]
        updated_line = re.sub(r'\by1="\d+"', f'y1="{sb_div_bottom}"', last_line.group(0))
        updated_line = re.sub(r'\by2="\d+"', f'y2="{sb_div_bottom}"', updated_line)
        txt = txt[:last_line.start()] + updated_line + txt[last_line.end():]
    with open(sb_svg, "w", encoding="utf-8") as f:
        f.write(txt)


def _cluster_rows(items: list[dict], tol: float = 32.0) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for item in sorted(items, key=lambda it: (it["pos"].get("y", 0), it["pos"].get("x", 0))):
        y = float(item["pos"].get("y", 0))
        if not rows or abs(y - float(rows[-1][0]["pos"].get("y", 0))) > tol:
            rows.append([item])
        else:
            rows[-1].append(item)
    for row in rows:
        row.sort(key=lambda it: it["pos"].get("x", 0))
    return rows


def _layout_bento_row(row_items: list[dict], y: int, h: int, body_x: int = 244, body_w: int = 1180, gap_x: int = 16) -> None:
    if not row_items:
        return
    weights: list[float] = []
    for it in row_items:
        vtype = it["data"].get("visual", {}).get("visualType", "")
        if vtype in ("snowuiSplineChartE1A4B802", "lineChart", "areaChart", "map"):
            weights.append(2.0)
        elif vtype in ("snowuiPillTableE1A4B804", "tableEx", "pivotTable"):
            weights.append(1.38)
        else:
            weights.append(1.0)
    avail_w = body_w - gap_x * (len(row_items) - 1)
    total_w_weight = sum(weights) or 1.0
    cur_x = body_x
    for idx, it in enumerate(row_items):
        if idx == len(row_items) - 1:
            w = (body_x + body_w) - cur_x
        else:
            w = max(120, round(avail_w * (weights[idx] / total_w_weight)))
        it["pos"]["x"] = cur_x
        it["pos"]["y"] = y
        it["pos"]["width"] = w
        it["pos"]["height"] = h
        cur_x += w + gap_x


def apply_canvas_preset(repo_root: str, report_dir: str, page_dir: str, pid: str, preset: str) -> None:
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

    vroot = os.path.join(page_dir, "visuals")
    records: list[dict] = []
    for vid in sorted(os.listdir(vroot)):
        vfile = os.path.join(vroot, vid, "visual.json")
        if not os.path.exists(vfile):
            continue
        vdata = json.load(open(vfile, encoding="utf-8"))
        vname = vdata.get("name", vid)
        records.append({"vid": vid, "file": vfile, "name": vname, "data": vdata, "pos": vdata.get("position", {})})

    # Respaldar layout original web-scroll antes de comprimir/reorganizar en Bento 16:9
    cache = load_layout_cache(repo_root)
    if old_h >= 1200 and preset == "screen-16x9":
        cache.setdefault(pid, {})["web-scroll"] = {
            r["name"]: {k: r["pos"][k] for k in ("x", "y", "width", "height") if k in r["pos"]}
            for r in records
        }
        save_layout_cache(repo_root, cache)

    # Ajustar Chrome lateral, pie de página y título de sección
    body_items: list[dict] = []
    for r in records:
        vname = r["name"]
        pos = r["pos"]
        if vname == f"{pid}_bg_sidebar":
            pos["height"] = int(new_h - 28)
        elif vname == f"{pid}_side_meta":
            pos["y"] = int(new_h - 90) if preset == "screen-16x9" else int(new_h - 82)
            pos["height"] = 64
        elif vname == f"{pid}_footer":
            pos["y"] = int(new_h - 37) if preset == "screen-16x9" else int(new_h - 48)
            pos["height"] = 34 if preset == "screen-16x9" else 36
        elif vname.endswith("_sec_title") or (
            r["data"].get("visual", {}).get("visualType") == "textbox"
            and 96 <= float(pos.get("y", 0)) < 138
            and float(pos.get("x", 0)) >= 230
            and not any(vname.endswith(s) for s in SHELL_SUFFIXES)
        ):
            pos["y"] = 102 if preset == "screen-16x9" else 104
            pos["height"] = 34 if preset == "screen-16x9" else 40
        elif pos.get("y", 0) >= 100 and "_nav_" not in vname and not any(vname.endswith(s) for s in SHELL_SUFFIXES):
            body_items.append(r)

    if preset == "web-scroll":
        saved = cache.get(pid, {}).get("web-scroll")
        if isinstance(saved, dict):
            for r in records:
                if r["name"] in saved:
                    r["pos"].update(saved[r["name"]])
        else:
            # Expansión limpia fila a fila si la página nació directamente en 16:9
            rows = _cluster_rows(body_items)
            cur_y = 148
            for row in rows:
                is_kpi = all(it["data"].get("visual", {}).get("visualType") == "snowuiKpiCardE1A4B801" for it in row)
                row_h = 156 if is_kpi else (340 if len(row) <= 2 else 300)
                if not is_kpi and len(row) >= 3:
                    # Desempacar filas Bento anchas en bloques cómodos de 1180px / 580px
                    for it in row:
                        vtype = it["data"].get("visual", {}).get("visualType", "")
                        it["pos"]["x"] = 244
                        it["pos"]["y"] = cur_y
                        it["pos"]["width"] = 1180
                        it["pos"]["height"] = 330 if vtype != "snowuiPillTableE1A4B804" else 360
                        cur_y += it["pos"]["height"] + 20
                else:
                    for it in row:
                        it["pos"]["y"] = cur_y
                        it["pos"]["height"] = row_h
                    cur_y += row_h + 20
    else:
        # Diseño ejecutivo Bento widescreen para screen-16x9 (1440x810)
        rows = _cluster_rows(body_items)
        kpi_rows = [row for row in rows if all(it["data"].get("visual", {}).get("visualType") == "snowuiKpiCardE1A4B801" for it in row)]
        content_rows = [row for row in rows if row not in kpi_rows]

        if kpi_rows:
            for kpi in kpi_rows[0]:
                kpi["pos"]["y"] = 140
                kpi["pos"]["height"] = 84
            chart_top = 236
        else:
            chart_top = 140

        chart_bottom = 766
        avail_h = max(200, chart_bottom - chart_top)

        if len(content_rows) <= 2:
            gap_y = 14
            row_h = (avail_h - gap_y * max(0, len(content_rows) - 1)) // max(1, len(content_rows))
            cur_y = chart_top
            for row in content_rows:
                for it in row:
                    it["pos"]["y"] = cur_y
                    it["pos"]["height"] = row_h
                cur_y += row_h + gap_y
        else:
            # Agrupar 3+ filas en 2 filas Bento amplias (>= 250px cada fila)
            all_content = [it for row in content_rows for it in row]
            tables = [it for it in all_content if it["data"].get("visual", {}).get("visualType") in ("snowuiPillTableE1A4B804", "tableEx", "pivotTable")]
            non_tables = [it for it in all_content if it not in tables]

            bottom_items = list(tables)
            top_items = list(non_tables)
            if not bottom_items and len(top_items) >= 2:
                half = (len(top_items) + 1) // 2
                bottom_items = top_items[half:]
                top_items = top_items[:half]
            elif len(bottom_items) == 1 and len(top_items) >= 3:
                if len(top_items) >= 4 or top_items[-1]["pos"].get("width", 0) >= 900:
                    bottom_items.insert(0, top_items.pop())

            gap_y = 14
            top_h = 250
            bot_h = avail_h - top_h - gap_y
            _layout_bento_row(top_items, chart_top, top_h)
            _layout_bento_row(bottom_items, chart_top + top_h + gap_y, bot_h)

    for r in records:
        with open(r["file"], "w", encoding="utf-8") as f:
            json.dump(r["data"], f, indent=2, ensure_ascii=False)

    sync_sidebar_svg_height(report_dir, int(new_h))


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
        apply_canvas_preset(paths.repo_root, paths.report_dir, dst_dir, args.target, args.preset)
    else:
        cache = load_layout_cache(paths.repo_root)
        if args.source in cache and isinstance(cache[args.source], dict):
            src_map = cache[args.source].get("web-scroll", {})
            if src_map:
                dst_map = {}
                for k, v in src_map.items():
                    new_k = f"{args.target}_{k[len(args.source) + 1:]}" if k.startswith(f"{args.source}_") else f"{args.target}_{k}"
                    dst_map[new_k] = v
                cache.setdefault(args.target, {})["web-scroll"] = dst_map
                save_layout_cache(paths.repo_root, cache)

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
            apply_canvas_preset(paths.repo_root, paths.report_dir, pdir, pid, args.preset)
    if args.target == "all":
        bc_path = os.path.join(paths.repo_root, "brand-config.json")
        if os.path.exists(bc_path):
            bc = json.load(open(bc_path, encoding="utf-8"))
            bc.setdefault("style", {})["canvasPreset"] = args.preset
            with open(bc_path, "w", encoding="utf-8") as f:
                json.dump(bc, f, indent=2, ensure_ascii=False)
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
