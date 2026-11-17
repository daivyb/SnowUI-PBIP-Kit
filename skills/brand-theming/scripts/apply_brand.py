#!/usr/bin/env python3
"""Inyecta brand-config.json en SVGs, tema JSON, overrides PBIR, tokens PBIVIZ, TMDL y ejecuta QA."""

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

from pbip_paths import (  # noqa: E402
    discover_pbiviz_visuals,
    discover_unpacked_custom_visuals,
    resolve_pbip_paths,
)

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

DEFAULT_DAX_FORMATS = {
    "USD": r'"\$#,0.00;(\$#,0.00);\$#,0.00"',
    "PEN": '"""S/ ""#,0.00;(""S/ ""#,0.00);""S/ ""#,0.00"',
    "EUR": '"""€""#,0.00;(""€""#,0.00);""€""#,0.00"',
    "GBP": '"""£""#,0.00;(""£""#,0.00);""£""#,0.00"',
}

TMDL_STATIC_FORMATS = {
    "USD": r"\$#,0.00;(\$#,0.00);\$#,0.00",
    "PEN": '"S/ "#,0.00;("S/ "#,0.00);"S/ "#,0.00',
    "EUR": '"€"#,0.00;("€"#,0.00);"€"#,0.00',
    "GBP": '"£"#,0.00;("£"#,0.00);"£"#,0.00',
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    clamp = lambda v: max(0, min(255, round(v)))
    return f"#{clamp(r):02X}{clamp(g):02X}{clamp(b):02X}"


def mix_hex(hex_a: str, hex_b: str, t: float) -> str:
    ra, ga, ba = hex_to_rgb(hex_a)
    rb, gb, bb = hex_to_rgb(hex_b)
    return rgb_to_hex(ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t)


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    r, g, b = hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def kpi_gradient_stops(base_hex: str, is_dark: bool = False) -> tuple[str, str, str]:
    if is_dark:
        return base_hex.upper(), mix_hex(base_hex, "#FFFFFF", 0.08), mix_hex(base_hex, "#FFFFFF", 0.24)
    return mix_hex(base_hex, "#000000", 0.06), base_hex.upper(), mix_hex(base_hex, "#FFFFFF", 0.32)


def validate_config(cfg: dict, repo_root: str) -> list[str]:
    errors: list[str] = []
    for req in ("client", "assets", "currency", "style", "colors"):
        if req not in cfg or not isinstance(cfg[req], dict):
            errors.append(f"Falta sección obligatoria '{req}' en brand-config.json.")
    if errors:
        return errors

    logo_path = cfg["assets"].get("logoPath", "")
    abs_logo = logo_path if os.path.isabs(logo_path) else os.path.join(repo_root, logo_path)
    if not logo_path or not os.path.exists(abs_logo):
        errors.append(f"No existe el logo configurado en assets.logoPath: {abs_logo}")

    colors = cfg["colors"]
    for group in ("brand", "semantic", "surfaces", "text"):
        for k, v in colors.get(group, {}).items():
            if not isinstance(v, str) or not HEX_RE.match(v):
                errors.append(f"Color inválido en colors.{group}.{k}: '{v}'")
    for idx, c in enumerate(colors.get("dataColors", [])):
        if not isinstance(c, str) or not HEX_RE.match(c):
            errors.append(f"Color inválido en colors.dataColors[{idx}]: '{c}'")

    return errors


def resolve_token_color(raw: str, cfg: dict) -> str:
    if not raw:
        return cfg["colors"]["brand"]["primary"]
    if HEX_RE.match(raw):
        return raw.upper()
    mapping = {
        "primary": cfg["colors"]["brand"]["primary"],
        "secondary": cfg["colors"]["brand"]["secondary"],
        "tertiary": cfg["colors"]["brand"]["tertiary"],
        "darkSurface": cfg["colors"]["brand"]["darkSurface"],
        "positive": cfg["colors"]["semantic"]["positive"],
        "warning": cfg["colors"]["semantic"]["warning"],
        "negative": cfg["colors"]["semantic"]["negative"],
    }
    return mapping.get(raw, cfg["colors"]["brand"]["primary"]).upper()


def make_theme_json(cfg: dict) -> dict:
    colors = cfg["colors"]
    style = cfg["style"]
    font = style.get("fontFamily", "Segoe UI")
    semi = f"{font} Semibold" if font == "Segoe UI" else font
    bold = f"{font} Bold" if font == "Segoe UI" else font
    radius = int(style.get("cornerRadius", 18))
    data_colors = colors["dataColors"]
    center_color = data_colors[6] if len(data_colors) > 6 else mix_hex(colors["brand"]["primary"], "#FFFFFF", 0.35)

    return {
        "name": cfg["client"].get("themeDisplayName") or cfg["client"]["themeName"],
        "dataColors": data_colors,
        "background": colors["surfaces"]["card"],
        "foreground": colors["text"]["primary"],
        "tableAccent": colors["brand"]["primary"],
        "good": colors["semantic"]["positive"],
        "neutral": colors["semantic"]["warning"],
        "bad": colors["semantic"]["negative"],
        "maximum": colors["brand"]["primary"],
        "center": center_color,
        "minimum": colors["surfaces"]["border"],
        "null": colors["surfaces"]["divider"],
        "textClasses": {
            "title": {"fontFace": semi, "fontSize": 14, "color": colors["text"]["primary"]},
            "label": {"fontFace": font, "fontSize": 11, "color": colors["text"]["secondary"]},
            "header": {"fontFace": semi, "fontSize": 12, "color": colors["text"]["primary"]},
            "callout": {"fontFace": bold, "fontSize": 24, "color": colors["text"]["primary"]},
        },
        "visualStyles": {
            "*": {
                "*": {
                    "background": [{"color": {"solid": {"color": colors["surfaces"]["card"]}}, "transparency": 0}],
                    "border": [{"show": False, "radius": radius}],
                    "visualHeader": [{"show": False}],
                }
            },
            "page": {
                "*": {
                    "background": [{"color": {"solid": {"color": colors["surfaces"]["canvas"]}}, "transparency": 0}],
                    "outspace": [{"color": {"solid": {"color": colors["surfaces"]["canvas"]}}, "transparency": 0}],
                }
            },
        },
    }


def sidebar_palette(cfg: dict) -> dict[str, str]:
    mode = cfg["style"].get("sidebarMode", "light")
    colors = cfg["colors"]
    if mode == "dark":
        dark = colors["brand"]["darkSurface"]
        return {
            "bg": dark,
            "border": mix_hex(dark, "#FFFFFF", 0.14),
            "divider": mix_hex(dark, "#FFFFFF", 0.16),
            "nav_active_bg": mix_hex(dark, "#FFFFFF", 0.14),
            "nav_active_border": mix_hex(dark, "#FFFFFF", 0.24),
            "brand_title": colors["text"]["onDark"],
            "brand_sub": mix_hex(dark, "#FFFFFF", 0.65),
            "nav_inactive": mix_hex(dark, "#FFFFFF", 0.78),
            "nav_active_txt": mix_hex(colors["brand"]["primary"], "#FFFFFF", 0.35),
            "icon_stroke": colors["text"]["onDark"],
            "muted": mix_hex(dark, "#FFFFFF", 0.55),
        }
    if mode == "tinted":
        card = colors["surfaces"]["card"]
        pri = colors["brand"]["primary"]
        return {
            "bg": mix_hex(card, pri, 0.05),
            "border": colors["surfaces"]["border"],
            "divider": mix_hex(card, pri, 0.12),
            "nav_active_bg": mix_hex(card, pri, 0.14),
            "nav_active_border": mix_hex(card, pri, 0.28),
            "brand_title": colors["text"]["primary"],
            "brand_sub": colors["text"]["secondary"],
            "nav_inactive": colors["text"]["navInactive"],
            "nav_active_txt": pri,
            "icon_stroke": colors["text"]["primary"],
            "muted": colors["text"]["muted"],
        }
    return {
        "bg": colors["surfaces"]["card"],
        "border": colors["surfaces"]["border"],
        "divider": colors["surfaces"]["divider"],
        "nav_active_bg": colors["surfaces"]["navActiveBg"],
        "nav_active_border": colors["surfaces"]["navActiveBorder"],
        "brand_title": colors["text"]["primary"],
        "brand_sub": colors["text"]["secondary"],
        "nav_inactive": colors["text"]["navInactive"],
        "nav_active_txt": colors["brand"]["primary"],
        "icon_stroke": colors["text"]["primary"],
        "muted": colors["text"]["muted"],
    }


def write_svg_resources(cfg: dict, reg_dir: str, repo_root: str, dry_run: bool) -> list[str]:
    colors = cfg["colors"]
    sb = sidebar_palette(cfg)
    radius = int(cfg["style"].get("cornerRadius", 18))
    sb_radius = max(12, min(26, radius + 4))
    tb_radius = max(12, min(24, radius + 2))
    primary = colors["brand"]["primary"]
    ink = colors["text"]["primary"]
    neg = colors["semantic"]["negative"]

    svgs: dict[str, str] = {
        "chrome-sidebar.svg": (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="212" height="1680" viewBox="0 0 212 1680" fill="none">\n'
            f'  <rect x="0.5" y="0.5" width="211" height="1679" rx="{sb_radius}" fill="{sb["bg"]}" stroke="{sb["border"]}"/>\n'
            f'  <line x1="20" y1="92" x2="192" y2="92" stroke="{sb["divider"]}" stroke-width="1"/>\n'
            f'  <line x1="20" y1="1598" x2="192" y2="1598" stroke="{sb["divider"]}" stroke-width="1"/>\n'
            f'</svg>\n'
        ),
        "chrome-topbar.svg": (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="80" viewBox="0 0 1180 80" fill="none">\n'
            f'  <rect x="0.5" y="0.5" width="1179" height="79" rx="{tb_radius}" fill="{colors["surfaces"]["card"]}" stroke="{colors["surfaces"]["border"]}"/>\n'
            f'</svg>\n'
        ),
        "nav-pill-active.svg": (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="188" height="46" viewBox="0 0 188 46" fill="none">\n'
            f'  <rect x="0.5" y="0.5" width="187" height="45" rx="12" fill="{sb["nav_active_bg"]}" stroke="{sb["nav_active_border"]}"/>\n'
            f'  <rect x="4" y="11" width="3.5" height="24" rx="1.75" fill="{primary}"/>\n'
            f'</svg>\n'
        ),
        "pill-surface.svg": (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="164" height="44" viewBox="0 0 164 44" fill="none">\n'
            f'  <rect x="0.5" y="0.5" width="163" height="43" rx="12" fill="{colors["surfaces"]["pillBg"]}" stroke="{colors["surfaces"]["border"]}"/>\n'
            f'</svg>\n'
        ),
        "pill-alert.svg": (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="172" height="44" viewBox="0 0 172 44" fill="none">\n'
            f'  <rect x="0.5" y="0.5" width="171" height="43" rx="12" fill="{colors["semantic"]["alertBg"]}" stroke="{colors["semantic"]["alertBorder"]}"/>\n'
            f'</svg>\n'
        ),
        "icon-alert.svg": (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 20 20" fill="none">\n'
            f'  <path d="M5.5 13.8V8.8C5.5 6.3 7.5 4.3 10 4.3C12.5 4.3 14.5 6.3 14.5 8.8V13.8L16 15.2H4L5.5 13.8Z" stroke="{ink}" stroke-width="1.5" stroke-linejoin="round"/>\n'
            f'  <path d="M8.4 16.5C8.7 17.2 9.3 17.6 10 17.6C10.7 17.6 11.3 17.2 11.6 16.5" stroke="{ink}" stroke-width="1.5" stroke-linecap="round"/>\n'
            f'  <circle cx="14.5" cy="5" r="2.6" fill="{neg}"/>\n'
            f'</svg>\n'
        ),
    }

    sidebar_icons = {"icon-overview.svg", "icon-proyectos.svg", "icon-ejecutores.svg", "icon-ubicacion.svg"}
    topbar_icons = {"icon-reset.svg", "icon-sidebar-toggle.svg", "icon-star.svg", "icon-sun.svg"}

    updated: list[str] = []
    if not dry_run:
        os.makedirs(reg_dir, exist_ok=True)
        for fname, content in svgs.items():
            with open(os.path.join(reg_dir, fname), "w", encoding="utf-8") as f:
                f.write(content)
            updated.append(fname)

        for fname in os.listdir(reg_dir):
            if fname in sidebar_icons:
                fpath = os.path.join(reg_dir, fname)
                txt = open(fpath, encoding="utf-8").read()
                txt = re.sub(r'stroke="#[0-9A-Fa-f]{6}"', f'stroke="{sb["icon_stroke"]}"', txt)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(txt)
                updated.append(fname)
            elif fname in topbar_icons:
                fpath = os.path.join(reg_dir, fname)
                txt = open(fpath, encoding="utf-8").read()
                txt = re.sub(r'stroke="#[0-9A-Fa-f]{6}"', f'stroke="{ink}"', txt)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(txt)
                updated.append(fname)

        # Copiar logo configurado
        logo_src = cfg["assets"]["logoPath"]
        abs_logo = logo_src if os.path.isabs(logo_src) else os.path.join(repo_root, logo_src)
        reg_logo = cfg["assets"]["registeredLogoName"]
        shutil.copy2(abs_logo, os.path.join(reg_dir, reg_logo))
        updated.append(reg_logo)

    return updated


def update_report_json(cfg: dict, report_dir: str, reg_dir: str, dry_run: bool) -> None:
    report_json_path = os.path.join(report_dir, "definition", "report.json")
    rj = json.load(open(report_json_path, encoding="utf-8"))

    theme_file = f"{cfg['client']['themeName']}.json"
    reg_logo = cfg["assets"]["registeredLogoName"]
    theme_obj = make_theme_json(cfg)

    old_theme = rj.get("themeCollection", {}).get("customTheme", {}).get("name")
    rj.setdefault("themeCollection", {}).setdefault("customTheme", {})["name"] = theme_file
    rj["themeCollection"]["customTheme"]["type"] = "RegisteredResources"
    rj.setdefault("settings", {})["locale"] = cfg["client"].get("locale", "es-PE")

    # Sincronizar RegisteredResources en report.json
    for pkg in rj.get("resourcePackages", []):
        if pkg.get("name") == "RegisteredResources":
            items = pkg.get("items", [])
            new_items = []
            has_theme = False
            has_logo = False
            for item in items:
                if item.get("type") == "CustomTheme":
                    if not has_theme:
                        new_items.append({"name": theme_file, "path": theme_file, "type": "CustomTheme"})
                        has_theme = True
                elif item.get("path", "").endswith("-logo.svg") or "logo" in item.get("path", "").lower():
                    if not has_logo:
                        new_items.append({"name": reg_logo, "path": reg_logo, "type": "Image"})
                        has_logo = True
                else:
                    new_items.append(item)
            if not has_theme:
                new_items.insert(0, {"name": theme_file, "path": theme_file, "type": "CustomTheme"})
            if not has_logo:
                new_items.append({"name": reg_logo, "path": reg_logo, "type": "Image"})
            pkg["items"] = new_items

    if not dry_run:
        if old_theme and old_theme != theme_file:
            old_path = os.path.join(reg_dir, old_theme)
            if os.path.exists(old_path):
                os.remove(old_path)
        with open(os.path.join(reg_dir, theme_file), "w", encoding="utf-8") as f:
            json.dump(theme_obj, f, indent=2, ensure_ascii=False)
        with open(report_json_path, "w", encoding="utf-8") as f:
            json.dump(rj, f, indent=2, ensure_ascii=False)


def set_lit(node: dict, prop: str, lit_val: str) -> None:
    node[prop] = {"expr": {"Literal": {"Value": lit_val}}}


def set_solid_color(node: dict, prop: str, hex_color: str) -> None:
    node[prop] = {"solid": {"color": {"expr": {"Literal": {"Value": f"'{hex_color}'"}}}}}


def map_semantic_accent(current_hex: str, cfg: dict) -> str:
    """Mapea coloresSnowUI estándar antiguos hacia los tokens actuales del cliente."""
    h = current_hex.strip("'").upper()
    b = cfg["colors"]["brand"]
    s = cfg["colors"]["semantic"]
    mapping = {
        "#007AFF": b["primary"],
        "#AF52DE": b["secondary"],
        "#00C7BE": b["tertiary"],
        "#1C1C1E": b["darkSurface"],
        "#34C759": s["positive"],
        "#FF9500": s["warning"],
        "#FF3B30": s["negative"],
        "#DC2626": s["alertText"],
    }
    return mapping.get(h, h)


def update_pbir_visuals(cfg: dict, report_dir: str, pbiviz_root: str, dry_run: bool) -> int:
    pages_dir = os.path.join(report_dir, "definition", "pages")
    pages_meta = json.load(open(os.path.join(pages_dir, "pages.json"), encoding="utf-8"))
    page_ids = pages_meta.get("pageOrder", [])
    custom_visual_guids = {v.guid for v in discover_pbiviz_visuals(pbiviz_root)} | discover_unpacked_custom_visuals(report_dir)

    colors = cfg["colors"]
    style = cfg["style"]
    sb = sidebar_palette(cfg)
    font = style.get("fontFamily", "Segoe UI")
    semi = f"{font} Semibold" if font == "Segoe UI" else font
    radius = int(style.get("cornerRadius", 18))
    reg_logo = cfg["assets"]["registeredLogoName"]
    currency_mode = cfg["currency"].get("mode", "auto")
    currency_symbol = cfg["currency"].get("symbol", "$")
    prefix_lit = "''" if currency_mode == "auto" else f"'{currency_symbol}'"

    updated_count = 0
    for page_idx, pid in enumerate(page_ids):
        vroot = os.path.join(pages_dir, pid, "visuals")
        if not os.path.isdir(vroot):
            continue

        # Determinar qué índice de botón está activo en esta página
        active_nav_idx = page_idx
        for vid in os.listdir(vroot):
            m = re.match(rf"^{re.escape(pid)}_nav_act_(\d+)$", vid)
            if m:
                active_nav_idx = int(m.group(1))
                break

        for vid in sorted(os.listdir(vroot)):
            vpath = os.path.join(vroot, vid, "visual.json")
            if not os.path.exists(vpath):
                continue
            vdata = json.load(open(vpath, encoding="utf-8"))
            vis = vdata.get("visual", {})
            vtype = vis.get("visualType", "")
            vname = vdata.get("name", vid)
            changed = False

            # 1. Logo
            if vname.endswith("_logo") and vtype == "image":
                img_props = vis.get("objects", {}).get("image", [{}])[0].get("properties", {}).get("sourceFile", {}).get("image", {})
                if img_props:
                    set_lit(img_props, "name", f"'{reg_logo}'")
                    img_props.setdefault("url", {}).setdefault("expr", {}).setdefault("ResourcePackageItem", {})["ItemName"] = reg_logo
                    changed = True

            # 2. Textboxes de marca, footer, meta, nav, breadcrumb, reset
            elif vtype == "textbox":
                runs = vis.get("objects", {}).get("general", [{}])[0].get("properties", {}).get("paragraphs", [{}])[0].get("textRuns", [])
                if vname.endswith("_brand_txt") and len(runs) >= 2:
                    runs[0]["value"] = f"{cfg['client']['name']}\n"
                    runs[0].setdefault("textStyle", {})["color"] = sb["brand_title"]
                    runs[0]["textStyle"]["fontFamily"] = font
                    runs[1]["value"] = cfg["client"].get("subtitle", "")
                    runs[1].setdefault("textStyle", {})["color"] = sb["brand_sub"]
                    runs[1]["textStyle"]["fontFamily"] = font
                    changed = True
                elif vname.endswith("_footer") and runs:
                    runs[0]["value"] = cfg["client"].get("footerText", "")
                    runs[0].setdefault("textStyle", {})["color"] = colors["text"]["muted"]
                    runs[0]["textStyle"]["fontFamily"] = font
                    changed = True
                elif vname.endswith("_side_meta") and runs:
                    runs[0]["value"] = cfg["client"].get("sideMetaText", "")
                    runs[0].setdefault("textStyle", {})["color"] = sb["muted"]
                    runs[0]["textStyle"]["fontFamily"] = font
                    changed = True
                elif vname.endswith("_tb_crumb") and len(runs) >= 2:
                    runs[0]["value"] = f"{cfg['client'].get('breadcrumbRoot', 'Panel')}  /  "
                    runs[0].setdefault("textStyle", {})["color"] = colors["text"]["muted"]
                    runs[0]["textStyle"]["fontFamily"] = font
                    runs[1].setdefault("textStyle", {})["color"] = colors["text"]["primary"]
                    runs[1]["textStyle"]["fontFamily"] = font
                    changed = True
                elif vname.endswith("_nav_hdr") and runs:
                    runs[0].setdefault("textStyle", {})["color"] = sb["muted"]
                    runs[0]["textStyle"]["fontFamily"] = font
                    changed = True
                elif "_nav_lbl_" in vname and runs:
                    lbl_idx = int(vname.rsplit("_", 1)[-1])
                    is_active = lbl_idx == active_nav_idx
                    runs[0].setdefault("textStyle", {})["color"] = sb["nav_active_txt"] if is_active else sb["nav_inactive"]
                    runs[0]["textStyle"]["fontWeight"] = "bold" if is_active else "normal"
                    runs[0]["textStyle"]["fontFamily"] = font
                    changed = True
                elif vname.endswith("_rst_txt") and runs:
                    runs[0].setdefault("textStyle", {})["color"] = colors["text"]["primary"]
                    runs[0]["textStyle"]["fontFamily"] = font
                    changed = True
                elif runs:
                    for r in runs:
                        ts = r.setdefault("textStyle", {})
                        ts["fontFamily"] = font
                        if "color" in ts:
                            ts["color"] = colors["text"]["primary"]
                    changed = True

            # 3. Alerta Card
            elif vname.endswith("_alrt_val") and vtype == "card":
                lbl_props = vis.get("objects", {}).get("labels", [{}])[0].get("properties", {})
                set_solid_color(lbl_props, "color", colors["semantic"]["alertText"])
                set_lit(lbl_props, "fontFamily", f"'{semi}'")
                changed = True

            # 4. Slicers Topbar
            elif vtype == "slicer":
                objs = vis.get("objects", {})
                hdr = objs.get("header", [{}])[0].get("properties", {})
                items = objs.get("items", [{}])[0].get("properties", {})
                if hdr:
                    set_solid_color(hdr, "fontColor", colors["text"]["secondary"])
                    set_lit(hdr, "fontFamily", f"'{semi}'")
                if items:
                    set_solid_color(items, "fontColor", colors["text"]["primary"])
                    set_lit(items, "fontFamily", f"'{font}'")
                vco = vis.get("visualContainerObjects", {})
                if "background" in vco:
                    set_solid_color(vco["background"][0].setdefault("properties", {}), "color", colors["surfaces"]["slicerBg"])
                if "border" in vco:
                    bprops = vco["border"][0].setdefault("properties", {})
                    set_solid_color(bprops, "color", colors["surfaces"]["border"])
                    set_lit(bprops, "radius", f"{min(12, radius)}D")
                changed = True

            # 5. Visuales personalizados SnowUI
            elif vtype in custom_visual_guids:
                objs = vis.setdefault("objects", {})
                if vtype == "snowuiKpiCardE1A4B801":
                    cs = objs.setdefault("cardStyle", [{}])[0].setdefault("properties", {})
                    set_lit(cs, "cornerRadius", f"{radius}D")
                    set_lit(cs, "surfaceMode", f"'{style.get('kpiSurfaceMode', 'gradient')}'")
                    nf = objs.setdefault("numberFormat", [{}])[0].setdefault("properties", {})
                    set_lit(nf, "currencyMode", f"'{currency_mode}'")
                    set_lit(nf, "valuePrefix", prefix_lit)
                    changed = True
                elif vtype == "snowuiSplineChartE1A4B802":
                    chs = objs.setdefault("chartStyle", [{}])[0].setdefault("properties", {})
                    set_solid_color(chs, "lineColor", resolve_token_color(cfg.get("visualDefaults", {}).get("splineLineColor", "secondary"), cfg))
                    set_lit(chs, "currencyMode", f"'{currency_mode}'")
                    set_lit(chs, "valuePrefix", prefix_lit)
                    changed = True
                elif vtype == "snowuiPillBarChartE1A4B803":
                    bs = objs.setdefault("barStyle", [{}])[0].setdefault("properties", {})
                    if "accentColor" in bs:
                        cur = bs["accentColor"].get("solid", {}).get("color", {}).get("expr", {}).get("Literal", {}).get("Value", "")
                        if cur:
                            set_solid_color(bs, "accentColor", map_semantic_accent(cur, cfg))
                    set_lit(bs, "currencyMode", f"'{currency_mode}'")
                    set_lit(bs, "valuePrefix", prefix_lit)
                    changed = True
                elif vtype == "snowuiPillTableE1A4B804":
                    ts = objs.setdefault("tableStyle", [{}])[0].setdefault("properties", {})
                    set_lit(ts, "currencyMode", f"'{currency_mode}'")
                    set_lit(ts, "valuePrefix", prefix_lit)
                    changed = True
                else:
                    # Visual personalizado adicional (5.º+): actualizar currencyMode/valuePrefix si declara esos objetos
                    for card_key, entries in objs.items():
                        if isinstance(entries, list) and entries and isinstance(entries[0], dict):
                            props = entries[0].get("properties", {})
                            if "currencyMode" in props:
                                set_lit(props, "currencyMode", f"'{currency_mode}'")
                                changed = True
                            if "valuePrefix" in props:
                                set_lit(props, "valuePrefix", prefix_lit)
                                changed = True

            # 6. Nativos (map, charts)
            elif vtype not in ("actionButton", "image"):
                vco = vis.get("visualContainerObjects", {})
                if "background" in vco and vco["background"][0].get("properties", {}).get("show", {}).get("expr", {}).get("Literal", {}).get("Value") == "true":
                    set_solid_color(vco["background"][0]["properties"], "color", colors["surfaces"]["card"])
                if "border" in vco and vco["border"][0].get("properties", {}).get("show", {}).get("expr", {}).get("Literal", {}).get("Value") == "true":
                    bprops = vco["border"][0]["properties"]
                    set_solid_color(bprops, "color", colors["surfaces"]["border"])
                    set_lit(bprops, "radius", f"{radius}D")
                if "title" in vco and vco["title"][0].get("properties", {}).get("show", {}).get("expr", {}).get("Literal", {}).get("Value") == "true":
                    tprops = vco["title"][0]["properties"]
                    set_solid_color(tprops, "fontColor", colors["text"]["primary"])
                    set_lit(tprops, "fontFamily", f"'{semi}'")
                changed = True

            if changed:
                updated_count += 1
                if not dry_run:
                    with open(vpath, "w", encoding="utf-8") as f:
                        json.dump(vdata, f, indent=2, ensure_ascii=False)

    return updated_count


def generate_pbiviz_tokens(cfg: dict, pbiviz_root: str, dry_run: bool) -> None:
    colors = cfg["colors"]
    style = cfg["style"]
    currency = cfg["currency"]
    vdefs = cfg.get("visualDefaults", {})
    b = colors["brand"]
    s = colors["semantic"]
    surf = colors["surfaces"]
    txt = colors["text"]

    pri_stops = kpi_gradient_stops(b["primary"])
    dark_stops = kpi_gradient_stops(b["darkSurface"], is_dark=True)
    ter_stops = kpi_gradient_stops(b["tertiary"])
    pos_stops = kpi_gradient_stops(s["positive"])
    sec_stops = kpi_gradient_stops(b["secondary"])

    less_content = f"""// Archivo generado por apply_brand.py desde brand-config.json
@snow-font-family: "{style.get("fontFamily", "Segoe UI")}";
@snow-font: @snow-font-family, -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", Roboto, Helvetica, Arial, sans-serif;

@snow-ink: {txt["primary"]};
@snow-secondary: {txt["secondary"]};
@snow-muted: {txt["muted"]};
@snow-on-dark: {txt["onDark"]};
@snow-card-bg: {surf["card"]};
@snow-border: {surf["border"]};

@snow-primary: {b["primary"]};
@snow-secondary-brand: {b["secondary"]};
@snow-tertiary: {b["tertiary"]};
@snow-positive: {s["positive"]};
@snow-warning: {s["warning"]};
@snow-negative: {s["negative"]};
@snow-dark: {b["darkSurface"]};

@snow-blue: @snow-primary;
@snow-purple: @snow-secondary-brand;
@snow-green: @snow-positive;
@snow-red: @snow-negative;
@snow-teal: @snow-tertiary;
@snow-orange: @snow-warning;

@snow-radius: {int(style.get("cornerRadius", 18))}px;
@snow-ease: cubic-bezier(0.22, 1, 0.36, 1);

@snow-hover-bg: {hex_to_rgba(b["primary"], 0.055)};
@snow-hover-border: {hex_to_rgba(b["primary"], 0.14)};
@snow-selected-bg: {hex_to_rgba(b["primary"], 0.09)};
@snow-selected-border: {hex_to_rgba(b["primary"], 0.35)};

@snow-kpi-blue-start: {pri_stops[0]};
@snow-kpi-blue-mid: {pri_stops[1]};
@snow-kpi-blue-end: {pri_stops[2]};

@snow-kpi-dark-start: {dark_stops[0]};
@snow-kpi-dark-mid: {dark_stops[1]};
@snow-kpi-dark-end: {dark_stops[2]};

@snow-kpi-teal-start: {ter_stops[0]};
@snow-kpi-teal-mid: {ter_stops[1]};
@snow-kpi-teal-end: {ter_stops[2]};

@snow-kpi-green-start: {pos_stops[0]};
@snow-kpi-green-mid: {pos_stops[1]};
@snow-kpi-green-end: {pos_stops[2]};

@snow-kpi-purple-start: {sec_stops[0]};
@snow-kpi-purple-mid: {sec_stops[1]};
@snow-kpi-purple-end: {sec_stops[2]};
"""

    series_rules = []
    for r in vdefs.get("seriesColorRules", []):
        series_rules.append({
            "match": r.get("match", []),
            "color": resolve_token_color(r.get("color", ""), cfg),
            **({"stackOrder": r["stackOrder"]} if "stackOrder" in r else {}),
        })

    tokens_obj = {
        "currency": {
            "code": currency.get("code", "USD"),
            "symbol": currency.get("symbol", "$"),
            "numberLocale": currency.get("numberLocale", "en-US"),
            "defaultDecimals": int(currency.get("defaultDecimals", 1)),
            "mode": currency.get("mode", "auto"),
        },
        "style": {
            "cornerRadius": int(style.get("cornerRadius", 18)),
            "kpiSurfaceMode": style.get("kpiSurfaceMode", "gradient"),
            "sidebarMode": style.get("sidebarMode", "light"),
            "fontFamily": style.get("fontFamily", "Segoe UI"),
            "density": style.get("density", "comfortable"),
        },
        "colors": {
            "brand": b,
            "semantic": {
                "positive": s["positive"],
                "warning": s["warning"],
                "negative": s["negative"],
                "alertText": s["alertText"],
            },
            "surfaces": {
                "canvas": surf["canvas"],
                "card": surf["card"],
                "border": surf["border"],
                "pillBg": surf["pillBg"],
            },
            "text": {
                "primary": txt["primary"],
                "secondary": txt["secondary"],
                "muted": txt["muted"],
                "onDark": txt["onDark"],
            },
            "dataColors": colors["dataColors"],
        },
        "visualDefaults": {
            "splineLineColor": resolve_token_color(vdefs.get("splineLineColor", "secondary"), cfg),
            "barDefaultAccent": resolve_token_color(vdefs.get("barDefaultAccent", "primary"), cfg),
            "defaultTableTitle": vdefs.get("defaultTableTitle", "Registros"),
            "defaultEmptyMessage": vdefs.get("defaultEmptyMessage", "Ajusta los filtros superiores para visualizar registros."),
            "seriesColorRules": series_rules,
            "columnFriendlyNames": vdefs.get("columnFriendlyNames", {}),
        },
        "statusRules": cfg.get("statusRules", []),
    }

    ts_content = (
        "// Archivo generado por apply_brand.py desde brand-config.json\n"
        "export interface SeriesColorRule {\n"
        "    match: string[];\n"
        "    color: string;\n"
        "    stackOrder?: number;\n"
        "}\n\n"
        "export interface StatusRuleConfig {\n"
        "    match: string[];\n"
        '    tone: "positive" | "negative" | "warning" | "primary" | "secondary" | "muted";\n'
        "    label?: string;\n"
        "}\n\n"
        "export interface BrandTokensConfig {\n"
        '    currency: { code: string; symbol: string; numberLocale: string; defaultDecimals: number; mode: "auto" | "brand" | "custom" };\n'
        '    style: { cornerRadius: number; kpiSurfaceMode: "gradient" | "solid" | "light-bordered"; sidebarMode: "light" | "tinted" | "dark"; fontFamily: string; density: "comfortable" | "compact" };\n'
        "    colors: {\n"
        "        brand: { primary: string; secondary: string; tertiary: string; darkSurface: string };\n"
        "        semantic: { positive: string; warning: string; negative: string; alertText: string };\n"
        "        surfaces: { canvas: string; card: string; border: string; pillBg: string };\n"
        "        text: { primary: string; secondary: string; muted: string; onDark: string };\n"
        "        dataColors: string[];\n"
        "    };\n"
        "    visualDefaults: {\n"
        "        splineLineColor: string;\n"
        "        barDefaultAccent: string;\n"
        "        defaultTableTitle: string;\n"
        "        defaultEmptyMessage: string;\n"
        "        seriesColorRules: SeriesColorRule[];\n"
        "        columnFriendlyNames: Record<string, string>;\n"
        "    };\n"
        "    statusRules: StatusRuleConfig[];\n"
        "}\n\n"
        f"export const BRAND_TOKENS: BrandTokensConfig = {json.dumps(tokens_obj, indent=4, ensure_ascii=False)};\n"
    )

    if not dry_run:
        common_dir = os.path.join(pbiviz_root, "_common")
        with open(os.path.join(common_dir, "snowuiTokens.less"), "w", encoding="utf-8") as f:
            f.write(less_content)
        with open(os.path.join(common_dir, "snowuiTokens.ts"), "w", encoding="utf-8") as f:
            f.write(ts_content)

        for vinfo in discover_pbiviz_visuals(pbiviz_root):
            pj_path = vinfo.pbiviz_json_path
            if os.path.exists(pj_path):
                pj = json.load(open(pj_path, encoding="utf-8"))
                if cfg["client"].get("supportUrl"):
                    pj["visual"]["supportUrl"] = cfg["client"]["supportUrl"]
                if cfg["client"].get("authorName"):
                    pj.setdefault("author", {})["name"] = cfg["client"]["authorName"]
                if cfg["client"].get("authorEmail"):
                    pj.setdefault("author", {})["email"] = cfg["client"]["authorEmail"]
                with open(pj_path, "w", encoding="utf-8") as f:
                    json.dump(pj, f, indent=2, ensure_ascii=False)


def sync_tmdl_currency_and_culture(cfg: dict, model_dir: str, dry_run: bool) -> None:
    import glob

    locale = cfg["client"].get("locale", "es-PE")
    code = cfg["currency"].get("code", "USD")
    symbol = cfg["currency"].get("symbol", "$").strip() or "$"
    static_fmt = TMDL_STATIC_FORMATS.get(code, f'"{symbol} "#,0.00;("{symbol} "#,0.00);"{symbol} "#,0.00')

    model_path = os.path.join(model_dir, "definition", "model.tmdl")
    if os.path.exists(model_path):
        mtxt = open(model_path, encoding="utf-8").read()
        mtxt = re.sub(r"^\tculture:\s*.+$", lambda _m: f"\tculture: {locale}", mtxt, flags=re.M)
        mtxt = re.sub(r"^\tsourceQueryCulture:\s*.+$", lambda _m: f"\tsourceQueryCulture: {locale}", mtxt, flags=re.M)
        if not dry_run:
            with open(model_path, "w", encoding="utf-8") as f:
                f.write(mtxt)

    moneda_path = os.path.join(model_dir, "definition", "tables", "DimMonedaSelector.tmdl")
    if os.path.exists(moneda_path):
        dtxt = open(moneda_path, encoding="utf-8").read()
        dtxt = re.sub(
            r'SELECTEDVALUE\(DimMonedaSelector\[CodigoMoneda\], "[^"]*"\)',
            lambda _m: f'SELECTEDVALUE(DimMonedaSelector[CodigoMoneda], "{code}")',
            dtxt,
        )
        if not dry_run:
            with open(moneda_path, "w", encoding="utf-8") as f:
                f.write(dtxt)

    # Actualizar formatString monetario estático en todas las tablas de hechos/dimensiones (excepto DimMonedaSelector)
    currency_fmt_re = re.compile(
        r"^(\t\tformatString:\s*)(?:\\\$|\"S/ \"|\"€\"|\"£\"|\"US\$\")[^\r\n]*$",
        flags=re.M,
    )
    for tpath in glob.glob(os.path.join(model_dir, "definition", "tables", "*.tmdl")):
        if os.path.basename(tpath) == "DimMonedaSelector.tmdl":
            continue
        ttxt = open(tpath, encoding="utf-8").read()
        new_ttxt = currency_fmt_re.sub(lambda m: f"{m.group(1)}{static_fmt}", ttxt)
        if new_ttxt != ttxt and not dry_run:
            with open(tpath, "w", encoding="utf-8") as f:
                f.write(new_ttxt)


def main() -> int:
    parser = argparse.ArgumentParser(description="Aplica brand-config.json a todo el proyecto PBIP SnowUI.")
    parser.add_argument("--root", default=".", help="Raíz del proyecto PBIP.")
    parser.add_argument("--config", default=None, help="Ruta a brand-config.json.")
    parser.add_argument("--skip-build", action="store_true", help="No recompila los paquetes PBIVIZ.")
    parser.add_argument("--skip-qa", action="store_true", help="Omite la ejecución final de verify_all.py.")
    parser.add_argument("--visual", default="all", help="Visual(es) a recompilar (por defecto 'all').")
    parser.add_argument("--pbiviz-cmd", default=None, help="Ruta opcional a pbiviz.cmd.")
    parser.add_argument("--shared-node-modules", default=None, help="Ruta opcional a node_modules compartidos.")
    parser.add_argument("--dry-run", action="store_true", help="Valida y simula sin escribir archivos.")
    args = parser.parse_args()

    paths = resolve_pbip_paths(args.root)
    cfg_path = args.config or os.path.join(paths.repo_root, "brand-config.json")
    if not os.path.exists(cfg_path):
        print(f"ERROR: No existe {cfg_path}", file=sys.stderr)
        return 1

    cfg = json.load(open(cfg_path, encoding="utf-8"))
    errors = validate_config(cfg, paths.repo_root)
    if errors:
        for e in errors:
            print("ERROR:", e, file=sys.stderr)
        return 1

    reg_dir = os.path.join(paths.report_dir, "StaticResources", "RegisteredResources")
    pbiviz_root = os.path.join(paths.repo_root, "pbiviz")

    svgs = write_svg_resources(cfg, reg_dir, paths.repo_root, args.dry_run)
    update_report_json(cfg, paths.report_dir, reg_dir, args.dry_run)
    vis_count = update_pbir_visuals(cfg, paths.report_dir, pbiviz_root, args.dry_run)
    generate_pbiviz_tokens(cfg, pbiviz_root, args.dry_run)
    sync_tmdl_currency_and_culture(cfg, paths.semantic_model_dir, args.dry_run)

    print(
        f"Marca '{cfg['client']['name']}' ({cfg['currency']['code']} {cfg['currency']['symbol']}) "
        f"{'[DRY-RUN]' if args.dry_run else 'aplicada'}: {len(svgs)} SVGs/logo, {vis_count} visuales PBIR."
    )

    if args.dry_run:
        return 0

    skills_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if not args.skip_build:
        build_script = os.path.join(skills_root, "pbiviz-custom-visual-dev", "scripts", "build_and_unpack_pbiviz.py")
        cmd = [sys.executable, build_script, "--root", paths.repo_root, "--visual", args.visual]
        if args.pbiviz_cmd:
            cmd.extend(["--pbiviz-cmd", args.pbiviz_cmd])
        if args.shared_node_modules:
            cmd.extend(["--shared-node-modules", args.shared_node_modules])
        res = subprocess.run(cmd, check=False)
        if res.returncode != 0:
            return res.returncode

    if not args.skip_qa:
        qa_script = os.path.join(skills_root, "pbip-qa-verify", "scripts", "verify_all.py")
        res = subprocess.run([sys.executable, qa_script, "--root", paths.repo_root], check=False)
        if res.returncode != 0:
            return res.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
