"use strict";

import powerbi from "powerbi-visuals-api";
import { FormattingSettingsService } from "powerbi-visuals-utils-formattingmodel";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;
import IVisualEventService = powerbi.extensibility.IVisualEventService;
import IVisualHost = powerbi.extensibility.visual.IVisualHost;
import ISelectionManager = powerbi.extensibility.ISelectionManager;
import ITooltipService = powerbi.extensibility.ITooltipService;
import ISelectionId = powerbi.visuals.ISelectionId;
import VisualTooltipDataItem = powerbi.extensibility.VisualTooltipDataItem;
import DataViewMetadataColumn = powerbi.DataViewMetadataColumn;

import {
    ResolvedFormatSpec,
    applyHostColorTokens,
    clearElement,
    el,
    formatFullCurrency,
    formatMetricValue,
    getAvatarColors,
    getMonogram,
    handleSelectionClick,
    resolveColumnFormatSpec,
    resolveStatusStyle,
    toNumericValue,
} from "./snowuiUtils";
import { BRAND_TOKENS } from "./snowuiTokens";
import { VisualFormattingSettingsModel } from "./settings";

type ColumnRoleKind = "primary" | "detail" | "measure" | "status";

interface TableColMeta {
    index: number;
    displayName: string;
    role: ColumnRoleKind;
    formatSpec: ResolvedFormatSpec;
    widthTrack: string;
}

interface TableRowRecord {
    rowIndex: number;
    cells: Array<string | number | null>;
    selectionId: ISelectionId;
}

export class Visual implements IVisual {
    private host: IVisualHost;
    private events: IVisualEventService;
    private selectionManager: ISelectionManager;
    private tooltipService: ITooltipService;
    private formattingSettingsService: FormattingSettingsService;
    private formattingSettings: VisualFormattingSettingsModel;

    private target: HTMLElement;
    private cardEl: HTMLDivElement;
    private titleEl: HTMLDivElement;
    private countPillEl: HTMLSpanElement;
    private colHeaderEl: HTMLDivElement;
    private rowsScrollEl: HTMLDivElement;

    private columnsMeta: TableColMeta[] = [];
    private rows: TableRowRecord[] = [];
    private sortColIdx: number = -1;
    private sortAsc: boolean = false;
    private selectedRowKey: string | null = null;
    private isCompact: boolean = false;

    constructor(options: VisualConstructorOptions) {
        this.host = options.host;
        this.events = options.host.eventService;
        this.selectionManager = options.host.createSelectionManager();
        this.tooltipService = options.host.tooltipService;
        this.formattingSettingsService = new FormattingSettingsService();
        this.formattingSettings = new VisualFormattingSettingsModel();

        this.target = options.element;
        this.target.classList.add("snow-table-host");
        applyHostColorTokens(this.target, this.host.colorPalette);

        this.cardEl = el("div", "snow-table-card");
        const card = this.cardEl;
        const hdrBar = el("div", "snow-table-header-bar");
        const titleWrap = el("div", "snow-table-title-wrap");
        this.titleEl = el("div", "snow-table-title", BRAND_TOKENS.visualDefaults.defaultTableTitle || "Registros");
        this.countPillEl = el("span", "snow-table-count-pill", "0 registros");
        titleWrap.appendChild(this.titleEl);
        titleWrap.appendChild(this.countPillEl);

        const badge = el("span", "snow-table-badge", "•••");
        hdrBar.appendChild(titleWrap);
        hdrBar.appendChild(badge);

        this.colHeaderEl = el("div", "snow-table-cols-header");
        this.rowsScrollEl = el("div", "snow-table-rows-scroll");

        card.addEventListener("click", () => {
            this.selectedRowKey = null;
            this.selectionManager.clear();
            this.renderRows();
        });

        card.appendChild(hdrBar);
        card.appendChild(this.colHeaderEl);
        card.appendChild(this.rowsScrollEl);
        this.target.appendChild(card);
    }

    public update(options: VisualUpdateOptions): void {
        this.events.renderingStarted(options);
        try {
            applyHostColorTokens(this.target, this.host.colorPalette);
            const vpW = Math.floor(options.viewport?.width || 0);
            const vpH = Math.floor(options.viewport?.height || 0);
            if (vpW > 0) {
                this.target.style.width = `${vpW}px`;
            }
            if (vpH > 0) {
                this.target.style.height = `${vpH}px`;
                this.cardEl.style.height = `${vpH}px`;
            }
            this.isCompact = (vpH > 0 && vpH < 290) || (vpW > 0 && vpW < 780);
            this.cardEl.classList.toggle("is-compact", this.isCompact);

            const dataView = options.dataViews?.[0];
            this.formattingSettings = this.formattingSettingsService.populateFormattingSettingsModel(
                VisualFormattingSettingsModel,
                dataView,
            );

            this.extractTable(dataView);
            this.renderHeaders();
            this.renderRows();

            this.events.renderingFinished(options);
        } catch (err) {
            this.events.renderingFailed(options, String(err));
        }
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return this.formattingSettingsService.buildFormattingModel(this.formattingSettings);
    }

    private classifyColumn(col: DataViewMetadataColumn, idx: number): ColumnRoleKind {
        const roles = col.roles || {};
        if (roles["primaryColumn"]) return "primary";
        if (roles["statusColumn"]) return "status";
        if (roles["measures"] || col.isMeasure) return "measure";
        if (idx === 0) return "primary";
        return "detail";
    }

    private extractTable(dataView?: powerbi.DataView): void {
        this.columnsMeta = [];
        this.rows = [];

        const defaultTitle = BRAND_TOKENS.visualDefaults.defaultTableTitle || "Registros";
        const table = dataView?.table;
        if (!table || !table.columns || !table.rows) {
            this.titleEl.textContent = (this.formattingSettings.tableStyle.titleOverride.value || "").trim() || defaultTitle;
            this.countPillEl.textContent = "0 registros";
            return;
        }

        const currencyMode = String(this.formattingSettings.tableStyle.currencyMode.value || BRAND_TOKENS.currency.mode);
        const customPrefix = this.formattingSettings.tableStyle.valuePrefix.value ?? "";
        const friendlyMap = BRAND_TOKENS.visualDefaults.columnFriendlyNames || {};

        const rawCols = table.columns;
        const orderedIndices: number[] = [];

        const byRole: Record<ColumnRoleKind, number[]> = { primary: [], detail: [], measure: [], status: [] };
        rawCols.forEach((col, i) => {
            byRole[this.classifyColumn(col, i)].push(i);
        });
        orderedIndices.push(...byRole.primary, ...byRole.detail, ...byRole.measure, ...byRole.status);

        this.columnsMeta = orderedIndices.map((origIdx) => {
            const c = rawCols[origIdx];
            const role = this.classifyColumn(c, origIdx);
            const rawName = c.displayName || `Col ${origIdx + 1}`;
            const name = friendlyMap[rawName] || rawName;
            const formatSpec = resolveColumnFormatSpec(c.format, name, {
                currencyMode,
                customPrefix,
            });
            let widthTrack = this.isCompact ? "minmax(58px, 0.92fr)" : "minmax(72px, 1.05fr)";
            if (role === "primary") {
                widthTrack = this.isCompact ? "minmax(108px, 1.8fr)" : "minmax(128px, 2.2fr)";
            } else if (role === "measure") {
                widthTrack = this.isCompact ? "minmax(72px, 1.05fr)" : "minmax(68px, 0.9fr)";
            } else if (role === "status") {
                widthTrack = this.isCompact ? "minmax(74px, 0.92fr)" : "minmax(82px, 0.9fr)";
            }
            return {
                index: origIdx,
                displayName: name,
                role,
                formatSpec,
                widthTrack,
            };
        });

        if (this.sortColIdx < 0 || this.sortColIdx >= this.columnsMeta.length) {
            const firstMeasure = this.columnsMeta.findIndex((c) => c.role === "measure");
            this.sortColIdx = firstMeasure >= 0 ? firstMeasure : -1;
            this.sortAsc = false;
        }

        this.rows = table.rows.map((r, rIdx) => ({
            rowIndex: rIdx,
            cells: orderedIndices.map((idx) => {
                const v = r[idx];
                if (v === null || v === undefined) return null;
                if (typeof v === "number" || typeof v === "string") return v;
                return String(v);
            }),
            selectionId: this.host.createSelectionIdBuilder().withTable(table, rIdx).createSelectionId(),
        }));

        if (this.selectedRowKey && !this.rows.some((r) => String(r.cells[0] ?? r.rowIndex) === this.selectedRowKey)) {
            this.selectedRowKey = null;
        }

        const primaryColName = this.columnsMeta.find((c) => c.role === "primary")?.displayName;
        const titleTxt = (this.formattingSettings.tableStyle.titleOverride.value || "").trim() || primaryColName || defaultTitle;
        this.titleEl.textContent = titleTxt;
        this.countPillEl.textContent = `${this.rows.length} registros`;
    }

    private renderHeaders(): void {
        clearElement(this.colHeaderEl);
        if (!this.columnsMeta.length) return;

        const templateCols = this.columnsMeta.map((c) => c.widthTrack).join(" ");
        this.colHeaderEl.style.gridTemplateColumns = templateCols;

        this.columnsMeta.forEach((col, colPos) => {
            const isSorted = this.sortColIdx === colPos;
            const btn = el(
                "button",
                `snow-col-hdr-btn${col.role === "measure" ? " is-numeric" : ""}${col.role === "status" ? " is-status" : ""}${isSorted ? " is-sorted" : ""}`,
            ) as HTMLButtonElement;
            btn.type = "button";
            btn.title = col.displayName;
            btn.appendChild(el("span", "snow-col-hdr-label", col.displayName));
            if (isSorted) {
                btn.appendChild(el("span", "snow-col-hdr-arrow", this.sortAsc ? "↑" : "↓"));
            }
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                if (this.sortColIdx === colPos) {
                    this.sortAsc = !this.sortAsc;
                } else {
                    this.sortColIdx = colPos;
                    this.sortAsc = col.role !== "measure";
                }
                this.renderHeaders();
                this.renderRows();
            });
            this.colHeaderEl.appendChild(btn);
        });
    }

    private renderRows(): void {
        clearElement(this.rowsScrollEl);
        if (!this.rows.length || !this.columnsMeta.length) {
            const empty = el("div", "snow-empty-state");
            empty.appendChild(el("div", "snow-empty-title", "Sin registros para mostrar"));
            empty.appendChild(el("div", undefined, BRAND_TOKENS.visualDefaults.defaultEmptyMessage || "Ajusta los filtros superiores para visualizar registros."));
            this.rowsScrollEl.appendChild(empty);
            return;
        }

        const showAvatars = this.formattingSettings.tableStyle.showAvatars.value ?? true;
        const maxRows = Math.max(1, Math.min(200, Math.round(this.formattingSettings.tableStyle.maxRows.value ?? 15)));
        const staggerMs = Math.max(0, Math.min(80, Math.round(this.formattingSettings.tableStyle.staggerMs.value ?? 28)));
        const templateCols = this.columnsMeta.map((c) => c.widthTrack).join(" ");

        const sorted = this.rows.slice();
        if (this.sortColIdx >= 0 && this.sortColIdx < this.columnsMeta.length) {
            const colMeta = this.columnsMeta[this.sortColIdx];
            const dir = this.sortAsc ? 1 : -1;
            sorted.sort((a, b) => {
                const va = a.cells[this.sortColIdx];
                const vb = b.cells[this.sortColIdx];
                if (colMeta.role === "measure" || (typeof va === "number" && typeof vb === "number")) {
                    return (toNumericValue(va) - toNumericValue(vb)) * dir;
                }
                return String(va ?? "").localeCompare(String(vb ?? ""), "es", { sensitivity: "base" }) * dir;
            });
        }

        const visibleRows = sorted.slice(0, maxRows);
        this.countPillEl.textContent = this.rows.length > visibleRows.length
            ? `${visibleRows.length} de ${this.rows.length} registros`
            : `${this.rows.length} registros`;
        visibleRows.forEach((rec, visIdx) => {
            const rowKey = String(rec.cells[0] ?? rec.rowIndex);
            const isSelected = this.selectedRowKey === rowKey;
            const isDimmed = Boolean(this.selectedRowKey && !isSelected);

            const rowEl = el(
                "div",
                `snow-table-pill-row${isSelected ? " is-selected" : ""}${isDimmed ? " is-dimmed" : ""}`,
            );
            rowEl.style.gridTemplateColumns = templateCols;
            rowEl.style.animationDelay = `${Math.min(400, visIdx * staggerMs)}ms`;

            this.columnsMeta.forEach((col, cIdx) => {
                const rawVal = rec.cells[cIdx];
                if (col.role === "primary") {
                    const txt = String(rawVal ?? "—");
                    const cell = el("div", "snow-cell-primary");
                    if (showAvatars) {
                        const colors = getAvatarColors(txt);
                        const avatar = el("span", "snow-avatar", getMonogram(txt));
                        avatar.style.backgroundColor = colors.bg;
                        avatar.style.color = colors.fg;
                        cell.appendChild(avatar);
                    }
                    cell.appendChild(el("span", "snow-cell-primary-text", txt));
                    rowEl.appendChild(cell);
                } else if (col.role === "measure") {
                    const num = toNumericValue(rawVal);
                    const spec = col.formatSpec;
                    const formatted = rawVal === null
                        ? "—"
                        : spec.isPercent
                            ? formatMetricValue(num, { displayUnits: "percent", decimals: 1, numberLocale: spec.numberLocale })
                            : formatMetricValue(num, {
                                prefix: spec.prefix,
                                suffix: spec.suffix,
                                displayUnits: "auto",
                                decimals: spec.decimals,
                                numberLocale: spec.numberLocale,
                            });
                    rowEl.appendChild(el("div", "snow-cell-num", formatted));
                } else if (col.role === "status") {
                    const statusStyle = resolveStatusStyle(String(rawVal ?? ""));
                    const pill = el("span", "snow-status-pill");
                    pill.style.backgroundColor = statusStyle.bg;
                    pill.style.color = statusStyle.fg;
                    const dot = el("span", "snow-status-dot");
                    dot.style.backgroundColor = statusStyle.dot;
                    pill.appendChild(dot);
                    pill.appendChild(el("span", undefined, statusStyle.label));
                    rowEl.appendChild(pill);
                } else {
                    rowEl.appendChild(el("div", "snow-cell-text", String(rawVal ?? "—")));
                }
            });

            const getTooltips = (): VisualTooltipDataItem[] =>
                this.columnsMeta.map((col, cIdx) => {
                    const rawVal = rec.cells[cIdx];
                    let valStr = String(rawVal ?? "—");
                    if (col.role === "measure" && rawVal !== null) {
                        const num = toNumericValue(rawVal);
                        const spec = col.formatSpec;
                        valStr = spec.isPercent
                            ? `${(num * (Math.abs(num) <= 2 ? 100 : 1)).toFixed(1)}%`
                            : formatFullCurrency(num, spec.prefix, spec.suffix, spec.numberLocale);
                    }
                    return { displayName: col.displayName, value: valStr };
                });

            rowEl.addEventListener("mouseenter", (evt: MouseEvent) => {
                this.tooltipService.show({
                    coordinates: [evt.clientX, evt.clientY],
                    isTouchEvent: false,
                    dataItems: getTooltips(),
                    identities: [rec.selectionId],
                });
            });
            rowEl.addEventListener("mousemove", (evt: MouseEvent) => {
                this.tooltipService.move({
                    coordinates: [evt.clientX, evt.clientY],
                    isTouchEvent: false,
                    dataItems: getTooltips(),
                    identities: [rec.selectionId],
                });
            });
            rowEl.addEventListener("mouseleave", () => {
                this.tooltipService.hide({ immediately: true, isTouchEvent: false });
            });
            rowEl.addEventListener("click", (evt: MouseEvent) => {
                this.selectedRowKey = this.selectedRowKey === rowKey ? null : rowKey;
                handleSelectionClick(evt, this.selectionManager, this.selectedRowKey ? rec.selectionId : undefined);
                this.renderRows();
            });

            this.rowsScrollEl.appendChild(rowEl);
        });
    }
}
