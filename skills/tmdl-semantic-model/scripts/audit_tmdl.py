#!/usr/bin/env python3
"""Audita integridad TMDL: lineageTags, colisiones columna/medida, sortByColumn, relaciones, formato y refs DAX."""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys

SHARED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

from pbip_paths import resolve_pbip_paths  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita archivos TMDL del modelo semántico.")
    parser.add_argument("--root", default=".", help="Raíz del repositorio PBIP.")
    args = parser.parse_args()

    paths = resolve_pbip_paths(args.root)
    def_dir = os.path.join(paths.semantic_model_dir, "definition")
    tables_dir = os.path.join(def_dir, "tables")

    errors: list[str] = []
    lineage_tags: dict[str, list[str]] = {}
    table_cols: dict[str, set[str]] = {}
    table_meas: dict[str, set[str]] = {}
    all_meas_global: dict[str, list[str]] = {}
    tmdl_files = sorted(glob.glob(os.path.join(def_dir, "**", "*.tmdl"), recursive=True))

    for path in tmdl_files:
        rel = os.path.relpath(path, paths.repo_root)
        txt = open(path, encoding="utf-8").read()
        for m in re.finditer(r"lineageTag:\s*([0-9a-fA-F-]+)", txt):
            tag = m.group(1).lower()
            lineage_tags.setdefault(tag, []).append(rel)

    for tag, files in lineage_tags.items():
        if len(files) > 1:
            errors.append(f"lineageTag duplicado '{tag}' en: {files}")

    for path in sorted(glob.glob(os.path.join(tables_dir, "*.tmdl"))):
        tname = os.path.basename(path)[:-5]
        lines = open(path, encoding="utf-8").read().splitlines()
        cols: set[str] = set()
        meas: set[str] = set()

        current_measure: str | None = None
        has_static_fmt = False
        has_dynamic_fmt = False

        def flush_measure_fmt() -> None:
            if current_measure and has_static_fmt and has_dynamic_fmt:
                errors.append(f"{tname}.{current_measure}: no puede declarar formatString y formatStringDefinition simultáneamente.")

        for line in lines:
            m_col = re.match(r"^\tcolumn\s+'([^']+)'|^\tcolumn\s+([^\s=]+)", line)
            if m_col:
                flush_measure_fmt()
                current_measure = None
                has_static_fmt = False
                has_dynamic_fmt = False
                cname = (m_col.group(1) or m_col.group(2)).strip()
                cols.add(cname)
                continue

            m_meas = re.match(r"^\tmeasure\s+'([^']+)'|^\tmeasure\s+([^=\r\n]+?)(?:\s*=|$)", line)
            if m_meas:
                flush_measure_fmt()
                mname = (m_meas.group(1) or m_meas.group(2)).strip()
                meas.add(mname)
                all_meas_global.setdefault(mname.lower(), []).append(f"{tname}.{mname}")
                current_measure = mname
                has_static_fmt = False
                has_dynamic_fmt = False
                continue

            if re.match(r"^\t(partition|hierarchy|annotation)\b", line):
                flush_measure_fmt()
                current_measure = None
                has_static_fmt = False
                has_dynamic_fmt = False
                continue

            if current_measure:
                if re.match(r"^\t\tformatString\s*:", line):
                    has_static_fmt = True
                elif re.match(r"^\t\tformatStringDefinition\s*=", line):
                    has_dynamic_fmt = True

        flush_measure_fmt()
        table_cols[tname] = cols
        table_meas[tname] = meas

        cols_lower = {c.lower(): c for c in cols}
        for m in meas:
            if m.lower() in cols_lower:
                errors.append(f"{tname}: colisión columna '{cols_lower[m.lower()]}' vs medida '{m}'.")

    for m_low, locs in all_meas_global.items():
        if len(locs) > 1:
            errors.append(f"Medida duplicada entre tablas ({m_low}): {locs}")

    dax_refs = 0
    for path in sorted(glob.glob(os.path.join(tables_dir, "*.tmdl"))):
        tname = os.path.basename(path)[:-5]
        txt = open(path, encoding="utf-8").read()
        for m_sort in re.finditer(r"^\t\tsortByColumn:\s*(.+)$", txt, re.M):
            target_col = m_sort.group(1).strip().strip("'")
            if target_col not in table_cols.get(tname, set()):
                errors.append(f"{tname}: sortByColumn apunta a columna inexistente '{target_col}'.")

        for m_ref in re.finditer(r"(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_]*))\[([^\]]+)\]", txt):
            ref_tbl = (m_ref.group(1) or m_ref.group(2)).strip()
            ref_col = m_ref.group(3).strip()
            if ref_tbl in table_cols:
                dax_refs += 1
                if ref_col not in table_cols[ref_tbl] and ref_col not in table_meas.get(ref_tbl, set()):
                    errors.append(f"{tname}: referencia DAX '{ref_tbl}[{ref_col}]' no encontrada en TMDL.")

    rel_path = os.path.join(def_dir, "relationships.tmdl")
    rel_count = 0
    if os.path.exists(rel_path):
        rel_txt = open(rel_path, encoding="utf-8").read()
        for block in re.split(r"(?m)^relationship\s+", rel_txt):
            block = block.strip()
            if not block:
                continue
            rel_count += 1
            m_from = re.search(r"fromColumn:\s*([^\.\s]+)\.([^\r\n]+)", block)
            m_to = re.search(r"toColumn:\s*([^\.\s]+)\.([^\r\n]+)", block)
            if not (m_from and m_to):
                errors.append(f"Relación mal formada en relationships.tmdl: {block.splitlines()[0]}")
                continue
            ft, fc = m_from.group(1).strip("'"), m_from.group(2).strip().strip("'")
            tt, tc = m_to.group(1).strip("'"), m_to.group(2).strip().strip("'")
            if fc not in table_cols.get(ft, set()):
                errors.append(f"Relación origen inválida: {ft}.{fc}")
            if tc not in table_cols.get(tt, set()):
                errors.append(f"Relación destino inválida: {tt}.{tc}")

    if errors:
        for err in errors:
            print("ERROR:", err, file=sys.stderr)
        print(f"Auditoría TMDL fallida: {len(errors)} error(es).", file=sys.stderr)
        return 1

    print(f"Auditoría TMDL OK: {len(table_cols)} tablas, {sum(len(v) for v in table_meas.values())} medidas, {rel_count} relaciones, {dax_refs} refs DAX, 0 errores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
