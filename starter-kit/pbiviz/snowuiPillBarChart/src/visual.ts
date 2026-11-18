"use strict";

import powerbi from "powerbi-visuals-api";
import * as d3 from "d3";
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

import {
    RafAnimator,
    ResolvedFormatSpec,
    SNOW_COLORS,
    applyHostColorTokens,
    calcDynamicLeftMargin,
    clamp,
    clearElement,
    easeOutCubic,
    el,
    formatFullCurrency,
    formatMetricValue,
    getSeriesStackRank,
    handleSelectionClick,
    measureTextWidth,
    resolveColumnFormatSpec,
    resolveHostSeriesColor,
    svgEl,
    toNumericValue,
    wrapLabelLines,
} from "./snowuiUtils";
import { BRAND_TOKENS } from "./snowuiTokens";
import { VisualFormattingSettingsModel } from "./settings";

interface PillItem {
    category: string;
    value: number;
    selectionId?: ISelectionId;
}

interface SegmentValue {
    seriesName: string;
    value: number;
    color: string;
    selectionId?: ISelectionId;
}

interface SubBarGroup {
    subCategory: string;
    total: number;
    segments: SegmentValue[];
}

interface MicroCategoryGroup {
    category: string;
    subBars: SubBarGroup[];
    total: number;
    selectionId?: ISelectionId;
}

export class Visual implements IVisual {
    private static instanceSeq = 0;
    private readonly instanceId = ++Visual.instanceSeq;
    private host: IVisualHost;
    private events: IVisualEventService;
    private selectionManager: ISelectionManager;
    private tooltipService: ITooltipService;
    private formattingSettingsService: FormattingSettingsService;
    private formattingSettings: VisualFormattingSettingsModel;
    private animator: RafAnimator;

    private target: HTMLElement;
    private cardEl: HTMLDivElement;
    private titleEl: HTMLDivElement;
    private legendEl: HTMLDivElement;
    private badgeEl: HTMLSpanElement;
    private bodyEl: HTMLDivElement;
    private svgRoot: SVGSVGElement;
    private calloutEl: HTMLDivElement;

    private pillItems: PillItem[] = [];
    private microGroups: MicroCategoryGroup[] = [];
    private seriesLegend: Array<{ name: string; color: string }> = [];
    private hiddenSeries: Set<string> = new Set();
    private hoveredCategory: string | null = null;
    private selectedCategory: string | null = null;
    private hoverResetTimer: number | null = null;
    private measureName: string = "Valor";
    private measureFormatSpec: ResolvedFormatSpec = resolveColumnFormatSpec();
    private hasData: boolean = false;
    private lastViewportWidth: number = 580;
    private lastViewportHeight: number = 328;

    constructor(options: VisualConstructorOptions) {
        this.host = options.host;
        this.events = options.host.eventService;
        this.selectionManager = options.host.createSelectionManager();
        this.tooltipService = options.host.tooltipService;
        this.formattingSettingsService = new FormattingSettingsService();
        this.formattingSettings = new VisualFormattingSettingsModel();
        this.animator = new RafAnimator();

        this.target = options.element;
        this.target.classList.add("snow-pillbar-host");
        applyHostColorTokens(this.target, this.host.colorPalette);

        this.cardEl = el("div", "snow-pillbar-card");
        const card = this.cardEl;
        const header = el("div", "snow-pillbar-header");
        const headerLeft = el("div", "snow-pillbar-header-left");
        this.titleEl = el("div", "snow-pillbar-title", "Distribución");
        this.legendEl = el("div", "snow-pillbar-legend");
        headerLeft.appendChild(this.titleEl);
        headerLeft.appendChild(this.legendEl);

        this.badgeEl = el("span", "snow-pillbar-badge", "•••");
        header.appendChild(headerLeft);
        header.appendChild(this.badgeEl);

        this.bodyEl = el("div", "snow-pillbar-body");
        this.svgRoot = svgEl("svg", { class: "snow-pillbar-svg" });
        this.calloutEl = el("div", "snow-pillbar-callout");
        this.bodyEl.appendChild(this.svgRoot);
        this.bodyEl.appendChild(this.calloutEl);

        card.addEventListener("click", () => {
            this.selectedCategory = null;
            this.selectionManager.clear();
            this.renderVisual(false);
        });

        card.appendChild(header);
        card.appendChild(this.bodyEl);
        this.target.appendChild(card);
    }

    public update(options: VisualUpdateOptions): void {
        this.events.renderingStarted(options);
        try {
            applyHostColorTokens(this.target, this.host.colorPalette);
            if (options.viewport?.width > 0) {
                this.lastViewportWidth = Math.floor(options.viewport.width);
                this.target.style.width = `${this.lastViewportWidth}px`;
            }
            if (options.viewport?.height > 0) {
                this.lastViewportHeight = Math.floor(options.viewport.height);
                this.target.style.height = `${this.lastViewportHeight}px`;
                this.cardEl.style.height = `${this.lastViewportHeight}px`;
            }
            this.cardEl.classList.toggle("is-compact", this.lastViewportHeight < 255 || this.lastViewportWidth < 360);

            const dataView = options.dataViews?.[0];
            this.formattingSettings = this.formattingSettingsService.populateFormattingSettingsModel(
                VisualFormattingSettingsModel,
                dataView,
            );

            this.extractData(dataView);
            this.renderHeader();
            this.renderVisual(true);

            this.events.renderingFinished(options);
        } catch (err) {
            this.events.renderingFailed(options, String(err));
        }
    }

    public destroy(): void {
        this.clearHoverResetTimer();
        this.animator.cancel();
    }

    private clearHoverResetTimer(): void {
        if (this.hoverResetTimer !== null) {
            window.clearTimeout(this.hoverResetTimer);
            this.hoverResetTimer = null;
        }
    }

    private scheduleHoverReset(delayMs: number, onReset: () => void): void {
        this.clearHoverResetTimer();
        this.hoverResetTimer = window.setTimeout(() => {
            this.hoverResetTimer = null;
            onReset();
        }, delayMs);
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return this.formattingSettingsService.buildFormattingModel(this.formattingSettings);
    }

    private getMode(): "pill" | "microStacked" {
        const cfg = String(this.formattingSettings.barStyle.displayMode.value || "pill");
        if (cfg === "microStacked") return "microStacked";
        return this.seriesLegend.length > 1 ? "microStacked" : "pill";
    }

    private formatMeasureVal(val: number, compact: boolean): string {
        const fmt = this.measureFormatSpec;
        if (fmt.isPercent) {
            return formatMetricValue(val, { displayUnits: "percent", decimals: 1, numberLocale: fmt.numberLocale });
        }
        if (compact) {
            return formatMetricValue(val, {
                prefix: fmt.prefix,
                suffix: fmt.suffix,
                displayUnits: "auto",
                decimals: fmt.decimals,
                numberLocale: fmt.numberLocale,
            });
        }
        return formatFullCurrency(val, fmt.prefix, fmt.suffix, fmt.numberLocale);
    }

    private extractData(dataView?: powerbi.DataView): void {
        this.pillItems = [];
        this.microGroups = [];
        this.seriesLegend = [];
        this.hasData = false;

        const categorical = dataView?.categorical;
        const categories = categorical?.categories || [];
        const values = categorical?.values;

        if (!categories.length || !values || !values.length) {
            return;
        }

        const catCol = categories.find((c) => c.source?.roles?.["category"]) || categories[0];
        const subCol = categories.find((c) => c.source?.roles?.["subCategory"]);
        const grouped = values.grouped();
        const firstMeasureSource = grouped[0]?.values?.[0]?.source;
        this.measureName = firstMeasureSource?.displayName || "Valor";
        this.measureFormatSpec = resolveColumnFormatSpec(firstMeasureSource?.format, this.measureName, {
            currencyMode: String(this.formattingSettings.barStyle.currencyMode.value || BRAND_TOKENS.currency.mode),
            customPrefix: this.formattingSettings.barStyle.valuePrefix.value ?? "",
        });
        this.hasData = catCol.values.length > 0;

        const hasSeries = grouped.length > 1 || (grouped.length === 1 && grouped[0].name !== undefined && grouped[0].name !== null);
        if (hasSeries) {
            grouped.forEach((grp, idx) => {
                const name = String(grp.name ?? `Serie ${idx + 1}`);
                this.seriesLegend.push({ name, color: resolveHostSeriesColor(name, idx, this.host.colorPalette) });
            });
        }

        const topN = Math.max(0, Math.round(this.formattingSettings.barStyle.topN.value ?? 6));
        const sortOrder = String(this.formattingSettings.barStyle.sortOrder.value || "desc");

        const pillMap = new Map<string, { val: number; selectionId?: ISelectionId }>();
        const pillOrder: string[] = [];

        const microMap = new Map<
            string,
            {
                selectionId?: ISelectionId;
                subMap: Map<string, Map<string, { val: number; color: string; selectionId?: ISelectionId }>>;
                subOrder: string[];
            }
        >();
        const microOrder: string[] = [];

        const rowCount = catCol.values.length;
        for (let r = 0; r < rowCount; r++) {
            const catLabel = String(catCol.values[r] ?? "").trim();
            if (!catLabel) continue;
            const subLabel = subCol ? String(subCol.values[r] ?? "Total").trim() : "Total";

            if (!microMap.has(catLabel)) {
                microMap.set(catLabel, {
                    selectionId: this.host.createSelectionIdBuilder().withCategory(catCol, r).createSelectionId(),
                    subMap: new Map(),
                    subOrder: [],
                });
                microOrder.push(catLabel);
            }
            const catEntry = microMap.get(catLabel)!;
            if (!catEntry.subMap.has(subLabel)) {
                catEntry.subMap.set(subLabel, new Map());
                catEntry.subOrder.push(subLabel);
            }
            const segMap = catEntry.subMap.get(subLabel)!;

            let rowSum = 0;
            grouped.forEach((grp, sIdx) => {
                const col = grp.values?.[0];
                const v = col ? toNumericValue(col.values[r]) : 0;
                rowSum += v;

                const sName = grp.name !== undefined && grp.name !== null ? String(grp.name) : this.measureName;
                const sColor = resolveHostSeriesColor(sName, sIdx, this.host.colorPalette);
                const prevSeg = segMap.get(sName);
                if (!prevSeg) {
                    const builder = this.host.createSelectionIdBuilder().withCategory(catCol, r);
                    if (hasSeries) {
                        builder.withSeries(values, grp);
                    }
                    segMap.set(sName, { val: v, color: sColor, selectionId: builder.createSelectionId() });
                } else {
                    prevSeg.val += v;
                }
            });

            let pItem = pillMap.get(catLabel);
            if (!pItem) {
                pItem = {
                    val: 0,
                    selectionId: this.host.createSelectionIdBuilder().withCategory(catCol, r).createSelectionId(),
                };
                pillMap.set(catLabel, pItem);
                pillOrder.push(catLabel);
            }
            pItem.val += rowSum;
        }

        let pills: PillItem[] = pillOrder.map((c) => {
            const e = pillMap.get(c)!;
            return { category: c, value: e.val, selectionId: e.selectionId };
        });

        if (sortOrder === "desc") {
            pills.sort((a, b) => b.value - a.value);
        } else if (sortOrder === "asc") {
            pills.sort((a, b) => a.value - b.value);
        }

        if (topN > 0 && pills.length > topN && this.getMode() === "pill") {
            pills = pills.slice(0, topN);
        }
        this.pillItems = pills;

        let mGroups: MicroCategoryGroup[] = microOrder.map((c) => {
            const entry = microMap.get(c)!;
            entry.subOrder.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
            const subBars: SubBarGroup[] = entry.subOrder.map((sub) => {
                const sMap = entry.subMap.get(sub)!;
                const segments: SegmentValue[] = [];
                let subTotal = 0;
                const keys = Array.from(sMap.keys()).sort((a, b) => {
                    const diff = getSeriesStackRank(a) - getSeriesStackRank(b);
                    return diff !== 0 ? diff : a.localeCompare(b);
                });
                for (const k of keys) {
                    const seg = sMap.get(k)!;
                    if (seg.val > 0) {
                        segments.push({ seriesName: k, value: seg.val, color: seg.color, selectionId: seg.selectionId });
                        subTotal += seg.val;
                    }
                }
                return { subCategory: sub, total: subTotal, segments };
            });
            const catTotal = subBars.reduce((acc, s) => acc + s.total, 0);
            return { category: c, subBars, total: catTotal, selectionId: entry.selectionId };
        });

        if (sortOrder === "desc" && this.getMode() === "microStacked") {
            mGroups.sort((a, b) => b.total - a.total);
        } else if (sortOrder === "asc" && this.getMode() === "microStacked") {
            mGroups.sort((a, b) => a.total - b.total);
        }
        if (topN > 0 && mGroups.length > topN && this.getMode() === "microStacked") {
            mGroups = mGroups.slice(0, topN);
        }
        this.microGroups = mGroups;

        if (this.selectedCategory) {
            const activePool = this.getMode() === "microStacked"
                ? this.microGroups.some((g) => g.category === this.selectedCategory)
                : this.pillItems.some((p) => p.category === this.selectedCategory);
            if (!activePool) {
                this.selectedCategory = null;
            }
        }
    }

    private renderHeader(): void {
        const titleOverride = (this.formattingSettings.barStyle.titleOverride.value || "").trim();
        const accent = this.formattingSettings.barStyle.accentColor.value?.value || BRAND_TOKENS.visualDefaults.barDefaultAccent || SNOW_COLORS.primary;
        const mode = this.getMode();

        this.titleEl.textContent = titleOverride || this.measureName;
        this.titleEl.style.color = mode === "pill" ? accent : "var(--snow-ink, #111827)";

        clearElement(this.legendEl);
        if (mode === "microStacked" && this.seriesLegend.length > 0) {
            this.seriesLegend.forEach((s) => {
                const isDim = this.hiddenSeries.has(s.name);
                const btn = el("button", `snow-legend-item${isDim ? " is-dimmed" : ""}`) as HTMLButtonElement;
                btn.type = "button";
                const dot = el("span", "snow-legend-dot");
                dot.style.backgroundColor = s.color;
                const txt = el("span", undefined, s.name);
                btn.appendChild(dot);
                btn.appendChild(txt);
                btn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    if (this.hiddenSeries.has(s.name)) {
                        this.hiddenSeries.delete(s.name);
                    } else {
                        this.hiddenSeries.add(s.name);
                    }
                    this.renderHeader();
                    this.renderVisual(true);
                });
                this.legendEl.appendChild(btn);
            });
        }
    }

    private renderVisual(animate: boolean): void {
        this.clearHoverResetTimer();
        clearElement(this.svgRoot);
        this.svgRoot.onmouseleave = null;
        this.calloutEl.classList.remove("is-visible");

        const rawW = this.bodyEl.clientWidth;
        const rawH = this.bodyEl.clientHeight;
        const width = Math.max(80, rawW > 0 ? rawW : Math.max(80, this.lastViewportWidth - 32));
        const height = Math.max(48, rawH > 0 ? rawH : Math.max(48, this.lastViewportHeight - 56));
        this.svgRoot.setAttribute("viewBox", `0 0 ${width} ${height}`);

        if (!this.hasData) {
            this.renderCenteredMessage(width, height, "Sin datos disponibles");
            return;
        }

        if (this.getMode() === "microStacked") {
            this.renderMicroStacked(width, height, animate);
        } else {
            this.renderPillBars(width, height, animate);
        }
    }

    private renderCenteredMessage(width: number, height: number, text: string): void {
        const msg = svgEl("text", {
            x: width / 2,
            y: height / 2,
            "text-anchor": "middle",
            fill: "var(--snow-ink-muted, #9CA3AF)",
            "font-size": 12,
        });
        msg.textContent = text;
        this.svgRoot.appendChild(msg);
    }

    private drawYAxisAndGrid(
        yScale: d3.ScaleLinear<number, number>,
        marginLeft: number,
        marginRight: number,
        width: number,
        tickCount: number = 4,
    ): void {
        const gridG = svgEl("g");
        for (const t of yScale.ticks(tickCount)) {
            const ty = yScale(t);
            gridG.appendChild(
                svgEl("line", {
                    x1: marginLeft,
                    x2: width - marginRight,
                    y1: ty,
                    y2: ty,
                    stroke: "var(--snow-border, rgba(0, 0, 0, 0.05))",
                    "stroke-opacity": 0.65,
                    "stroke-width": 1,
                }),
            );
            const lbl = svgEl("text", {
                x: marginLeft - 8,
                y: ty + 3.5,
                "text-anchor": "end",
                fill: "var(--snow-ink-muted, #9CA3AF)",
                "font-size": 10.5,
            });
            lbl.textContent = this.formatMeasureVal(t, true);
            gridG.appendChild(lbl);
        }
        this.svgRoot.appendChild(gridG);
    }

    private createWrappedXAxisText(
        xCenter: number,
        height: number,
        hasMultiLine: boolean,
        lines: string[],
        isHighlighted: boolean,
        fontSize: number = 11,
    ): SVGTextElement {
        const yFirst = hasMultiLine
            ? (lines.length > 1 ? height - 21 : height - 13)
            : height - 7;
        const xLbl = svgEl("text", {
            x: xCenter,
            y: yFirst,
            "text-anchor": "middle",
            fill: isHighlighted ? "var(--snow-ink, #111827)" : "var(--snow-ink-muted, #9CA3AF)",
            "font-weight": isHighlighted ? 600 : 400,
            "font-size": fontSize,
        });
        lines.forEach((line, i) => {
            const tspan = svgEl("tspan", {
                x: xCenter,
                dy: i === 0 ? 0 : 12.5,
            });
            tspan.textContent = line;
            xLbl.appendChild(tspan);
        });
        return xLbl;
    }

    private positionCallout(
        text: string,
        xCenter: number,
        barTopY: number,
        canvasW: number,
        canvasH: number,
        marginLeft: number,
    ): void {
        this.calloutEl.textContent = text;
        const halfPill = (measureTextWidth(text, '600 11.5px "Segoe UI", sans-serif') + 24) / 2;
        const clampedX = clamp(xCenter, marginLeft + halfPill, canvasW - halfPill - 4);
        const clampedY = clamp(barTopY - 8, 24, canvasH - 18);
        this.calloutEl.style.left = `${clampedX}px`;
        this.calloutEl.style.top = `${clampedY}px`;
        this.calloutEl.classList.add("is-visible");
    }

    private renderPillBars(width: number, height: number, animate: boolean): void {
        const items = this.pillItems;
        if (!items.length) return;

        const accent = this.formattingSettings.barStyle.accentColor.value?.value || BRAND_TOKENS.visualDefaults.barDefaultAccent || SNOW_COLORS.primary;
        const showCallout = this.formattingSettings.barStyle.showFloatingCallout.value ?? true;
        const animMs = animate ? Math.max(0, Math.min(2000, this.formattingSettings.barStyle.animationMs.value ?? 620)) : 0;

        const totalAll = items.reduce((s, d) => s + Math.max(0, d.value), 0);
        const maxVal = d3.max(items, (d) => d.value) || 0;
        const yMax = maxVal > 0 ? maxVal * 1.15 : 100;

        const tickCount = height < 140 ? 3 : 4;
        const preYScale = d3.scaleLinear().domain([0, yMax]).nice(tickCount).range([100, 0]);
        const marginLeft = calcDynamicLeftMargin(
            preYScale.ticks(tickCount).map((t) => this.formatMeasureVal(t, true)),
            40,
            88,
            '10.5px "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif',
        );

        const xFontPx = width < 340 || height < 150 ? 9.5 : 11;
        const xAxisFont = `${xFontPx}px "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif`;
        const rightPad = width < 340 ? 8 : 12;
        const estStep = (width - marginLeft - rightPad) / Math.max(1, items.length);
        const maxLabelW = Math.max(26, estStep - 4);
        const wrappedPerItem = items.map((item) => wrapLabelLines(item.category, maxLabelW, xAxisFont, 2));
        const hasMultiLine = wrappedPerItem.some((lines) => lines.length > 1);

        const margin = {
            top: height < 160 ? 24 : 32,
            right: rightPad,
            bottom: hasMultiLine ? (xFontPx < 10 ? 34 : 38) : 25,
            left: marginLeft,
        };
        const plotW = Math.max(60, width - margin.left - margin.right);
        const plotH = Math.max(24, height - margin.top - margin.bottom);

        const yScale = d3.scaleLinear().domain([0, yMax]).nice(tickCount).range([margin.top + plotH, margin.top]);
        const xScale = d3
            .scaleBand<string>()
            .domain(items.map((d) => d.category))
            .range([margin.left, margin.left + plotW])
            .padding(width < 340 ? 0.22 : 0.28);

        const gradId = `snowPillGrad_${this.instanceId}`;
        const defs = svgEl("defs");
        const grad = svgEl("linearGradient", { id: gradId, x1: "0%", y1: "0%", x2: "0%", y2: "100%" });
        grad.appendChild(svgEl("stop", { offset: "0%", "stop-color": accent, "stop-opacity": "0.95" }));
        grad.appendChild(svgEl("stop", { offset: "100%", "stop-color": accent, "stop-opacity": "0.52" }));
        defs.appendChild(grad);
        this.svgRoot.appendChild(defs);

        this.drawYAxisAndGrid(yScale, margin.left, margin.right, width, tickCount);

        const topCat = items.reduce((best, cur) => (cur.value > best.value ? cur : best), items[0]).category;
        const featuredCat = this.hoveredCategory || this.selectedCategory || topCat;
        const barW = Math.min(46, Math.max(10, xScale.bandwidth()));
        const rx = Math.min(14, barW / 2.2);
        const baseY = yScale(0);

        const barsG = svgEl("g");
        const xAxisG = svgEl("g");
        const hitG = svgEl("g");
        this.svgRoot.appendChild(barsG);
        this.svgRoot.appendChild(xAxisG);
        this.svgRoot.appendChild(hitG);

        const rects: Array<{ rect: SVGRectElement; targetH: number; targetY: number; xCenter: number; item: PillItem }> = [];
        const xCenters = items.map((item) => {
            const bandX = (xScale(item.category) ?? margin.left) + (xScale.bandwidth() - barW) / 2;
            return bandX + barW / 2;
        });

        items.forEach((item, idx) => {
            const bandX = (xScale(item.category) ?? margin.left) + (xScale.bandwidth() - barW) / 2;
            const xCenter = xCenters[idx];
            const targetY = yScale(Math.max(0, item.value));
            const targetH = Math.max(4, baseY - targetY);
            const isFeatured = item.category === featuredCat;
            const isDimmed = Boolean(this.selectedCategory && this.selectedCategory !== item.category);

            const rect = svgEl("rect", {
                class: "snow-bar-capsule",
                x: bandX,
                y: animMs > 0 ? baseY : targetY,
                width: barW,
                height: animMs > 0 ? 0 : targetH,
                rx,
                ry: rx,
                fill: isFeatured ? `url(#${gradId})` : "rgba(0, 0, 0, 0.055)",
                opacity: isDimmed ? 0.42 : 1,
            });
            rect.setAttribute("data-cat", item.category);
            barsG.appendChild(rect);
            rects.push({ rect, targetH, targetY, xCenter, item });

            const xLbl = this.createWrappedXAxisText(xCenter, height, hasMultiLine, wrappedPerItem[idx], isFeatured, xFontPx);
            xLbl.setAttribute("data-cat", item.category);
            xAxisG.appendChild(xLbl);

            const colLeft = idx === 0 ? margin.left : (xCenters[idx - 1] + xCenter) / 2;
            const colRight = idx === items.length - 1 ? width - margin.right : (xCenter + xCenters[idx + 1]) / 2;
            const hitRect = svgEl("rect", {
                class: "snow-bar-hit",
                x: colLeft,
                y: margin.top,
                width: Math.max(4, colRight - colLeft),
                height: plotH + margin.bottom - 2,
                fill: "transparent",
            });

            hitRect.addEventListener("mouseenter", (evt: MouseEvent) => {
                this.clearHoverResetTimer();
                const changed = this.hoveredCategory !== item.category;
                this.hoveredCategory = item.category;
                this.updateBarHighlight(barsG, xAxisG, xCenter, targetY, item, showCallout, gradId, width, height, margin.left);
                if (changed) {
                    this.showPillTooltip(item, totalAll, evt);
                } else {
                    this.movePillTooltip(item, totalAll, evt);
                }
            });
            hitRect.addEventListener("mousemove", (evt: MouseEvent) => {
                this.clearHoverResetTimer();
                this.movePillTooltip(item, totalAll, evt);
            });
            hitRect.addEventListener("click", (evt: MouseEvent) => {
                this.clearHoverResetTimer();
                this.selectedCategory = this.selectedCategory === item.category ? null : item.category;
                handleSelectionClick(evt, this.selectionManager, this.selectedCategory ? item.selectionId : undefined);
                this.renderVisual(false);
            });

            hitG.appendChild(hitRect);
        });

        this.svgRoot.onmouseleave = () => {
            this.scheduleHoverReset(70, () => {
                this.hoveredCategory = null;
                this.tooltipService.hide({ immediately: true, isTouchEvent: false });
                const fallbackItem = items.find((i) => i.category === (this.selectedCategory || topCat)) || items[0];
                const fbIdx = items.indexOf(fallbackItem);
                const fbCenter = fbIdx >= 0 ? xCenters[fbIdx] : xCenters[0];
                const fbY = yScale(Math.max(0, fallbackItem.value));
                this.updateBarHighlight(barsG, xAxisG, fbCenter, fbY, fallbackItem, showCallout, gradId, width, height, margin.left);
            });
        };

        const placeDefaultCallout = () => {
            if (!showCallout) return;
            const target = rects.find((r) => r.item.category === featuredCat) || rects[0];
            if (target) {
                this.positionCallout(this.formatMeasureVal(target.item.value, true), target.xCenter, target.targetY, width, height, margin.left);
            }
        };

        if (animMs <= 0) {
            placeDefaultCallout();
            return;
        }

        this.animator.run(
            animMs,
            (rawP) => {
                rects.forEach((r, idx) => {
                    const localP = easeOutCubic(Math.min(1, rawP * (1 + idx * 0.08)));
                    const h = Math.max(0, r.targetH * localP);
                    r.rect.setAttribute("height", h.toFixed(2));
                    r.rect.setAttribute("y", (baseY - h).toFixed(2));
                });
            },
            () => {
                rects.forEach((r) => {
                    r.rect.setAttribute("height", r.targetH.toFixed(2));
                    r.rect.setAttribute("y", r.targetY.toFixed(2));
                });
                placeDefaultCallout();
            },
        );
    }

    private updateBarHighlight(
        barsG: SVGGElement,
        xAxisG: SVGGElement,
        xCenter: number,
        barTopY: number,
        item: PillItem,
        showCallout: boolean,
        gradId: string,
        canvasW: number,
        canvasH: number,
        marginLeft: number,
    ): void {
        const children = Array.from(barsG.children) as SVGRectElement[];
        for (const r of children) {
            const cat = r.getAttribute("data-cat");
            r.setAttribute("fill", cat === item.category ? `url(#${gradId})` : "rgba(0, 0, 0, 0.055)");
        }
        const xLabels = Array.from(xAxisG.children) as SVGTextElement[];
        for (const lbl of xLabels) {
            const isActive = lbl.getAttribute("data-cat") === item.category;
            lbl.setAttribute("fill", isActive ? "var(--snow-ink, #111827)" : "var(--snow-ink-muted, #9CA3AF)");
            lbl.setAttribute("font-weight", isActive ? "600" : "400");
        }
        if (showCallout) {
            this.positionCallout(this.formatMeasureVal(item.value, true), xCenter, barTopY, canvasW, canvasH, marginLeft);
        }
    }

    private showPillTooltip(item: PillItem, totalAll: number, evt: MouseEvent): void {
        const pct = totalAll > 0 ? ((item.value / totalAll) * 100).toFixed(1) : "0.0";
        const dataItems: VisualTooltipDataItem[] = [
            { displayName: "Categoría", value: item.category },
            { displayName: this.measureName, value: this.formatMeasureVal(item.value, false) },
            { displayName: "% del Total", value: `${pct}%` },
        ];
        this.tooltipService.show({
            coordinates: [evt.clientX, evt.clientY],
            isTouchEvent: false,
            dataItems,
            identities: item.selectionId ? [item.selectionId] : [],
        });
    }

    private movePillTooltip(item: PillItem, totalAll: number, evt: MouseEvent): void {
        const pct = totalAll > 0 ? ((item.value / totalAll) * 100).toFixed(1) : "0.0";
        this.tooltipService.move({
            coordinates: [evt.clientX, evt.clientY],
            isTouchEvent: false,
            dataItems: [
                { displayName: "Categoría", value: item.category },
                { displayName: this.measureName, value: this.formatMeasureVal(item.value, false) },
                { displayName: "% del Total", value: `${pct}%` },
            ],
            identities: item.selectionId ? [item.selectionId] : [],
        });
    }

    private renderMicroStacked(width: number, height: number, animate: boolean): void {
        const groups = this.microGroups;
        if (!groups.length) return;

        if (this.seriesLegend.length > 0 && this.hiddenSeries.size >= this.seriesLegend.length) {
            this.renderCenteredMessage(width, height, "Todas las series están ocultas · haz clic en la leyenda para mostrarlas");
            return;
        }

        const animMs = animate ? Math.max(0, Math.min(2000, this.formattingSettings.barStyle.animationMs.value ?? 620)) : 0;

        let maxSubTotal = 0;
        for (const g of groups) {
            for (const sub of g.subBars) {
                const visibleSum = sub.segments
                    .filter((s) => !this.hiddenSeries.has(s.seriesName))
                    .reduce((acc, s) => acc + s.value, 0);
                if (visibleSum > maxSubTotal) maxSubTotal = visibleSum;
            }
        }
        const yMax = maxSubTotal > 0 ? maxSubTotal * 1.15 : 100;

        const tickCount = height < 140 ? 3 : 4;
        const preYScale = d3.scaleLinear().domain([0, yMax]).nice(tickCount).range([100, 0]);
        const marginLeft = calcDynamicLeftMargin(
            preYScale.ticks(tickCount).map((t) => this.formatMeasureVal(t, true)),
            42,
            88,
            '10.5px "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif',
        );

        const xFontPx = width < 480 || height < 150 ? 10 : 11.5;
        const xAxisFont = `${xFontPx}px "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif`;
        const estStep = (width - marginLeft - 12) / Math.max(1, groups.length);
        const maxLabelW = Math.max(28, estStep - 4);
        const wrappedGroups = groups.map((g) => wrapLabelLines(g.category, maxLabelW, xAxisFont, 2));
        const hasMultiLine = wrappedGroups.some((lines) => lines.length > 1);

        const margin = { top: height < 160 ? 20 : 24, right: 12, bottom: hasMultiLine ? 36 : 25, left: marginLeft };
        const plotW = Math.max(60, width - margin.left - margin.right);
        const plotH = Math.max(24, height - margin.top - margin.bottom);

        const yScale = d3.scaleLinear().domain([0, yMax]).nice(tickCount).range([margin.top + plotH, margin.top]);
        const xGroupScale = d3.scaleBand<string>().domain(groups.map((g) => g.category)).range([margin.left, margin.left + plotW]).padding(width < 520 ? 0.16 : 0.24);

        this.drawYAxisAndGrid(yScale, margin.left, margin.right, width, tickCount);

        const barsG = svgEl("g");
        const xAxisG = svgEl("g");
        this.svgRoot.appendChild(barsG);
        this.svgRoot.appendChild(xAxisG);

        const baseY = yScale(0);
        const gapPx = 2;
        const animatedSegs: Array<{ rect: SVGRectElement; targetY: number; targetH: number; groupIdx: number }> = [];

        groups.forEach((grp, gIdx) => {
            const gx = xGroupScale(grp.category) ?? margin.left;
            const gw = xGroupScale.bandwidth();
            const subCount = Math.max(1, grp.subBars.length);
            const colGap = subCount > 1 ? (gw < 26 ? 1.5 : 3) : 0;
            const subW = Math.min(18, Math.max(2.5, (gw - colGap * (subCount - 1)) / subCount));
            const totalGroupWidth = subCount * subW + (subCount - 1) * colGap;
            const startX = gx + (gw - totalGroupWidth) / 2;
            const pillRx = Math.min(3.5, subW / 2);

            grp.subBars.forEach((sub, subIdx) => {
                const sx = startX + subIdx * (subW + colGap);
                const visibleSegs = sub.segments.filter((s) => !this.hiddenSeries.has(s.seriesName) && s.value > 0);
                let cumVal = 0;

                visibleSegs.forEach((seg, segIdx) => {
                    const bottomVal = cumVal;
                    const topVal = cumVal + seg.value;
                    cumVal = topVal;

                    const rawBottomY = yScale(bottomVal);
                    const rawTopY = yScale(topVal);
                    const rawH = Math.max(2, rawBottomY - rawTopY - (segIdx > 0 ? gapPx : 0));
                    const finalY = rawTopY;
                    const isDimmed = Boolean(this.selectedCategory && this.selectedCategory !== grp.category);

                    const rect = svgEl("rect", {
                        class: "snow-bar-micro",
                        x: sx,
                        y: animMs > 0 ? baseY : finalY,
                        width: subW,
                        height: animMs > 0 ? 0 : rawH,
                        rx: pillRx,
                        ry: pillRx,
                        fill: seg.color,
                        opacity: isDimmed ? 0.35 : 1,
                    });

                    const tooltipItems = (): VisualTooltipDataItem[] => {
                        const list: VisualTooltipDataItem[] = [
                            { displayName: `${grp.category}${sub.subCategory !== "Total" ? ` (${sub.subCategory})` : ""}`, value: seg.seriesName },
                            { displayName: seg.seriesName, value: this.formatMeasureVal(seg.value, false) },
                        ];
                        visibleSegs.forEach((other) => {
                            if (other.seriesName !== seg.seriesName) {
                                list.push({ displayName: other.seriesName, value: this.formatMeasureVal(other.value, false) });
                            }
                        });
                        const subSum = visibleSegs.reduce((a, b) => a + b.value, 0);
                        list.push({ displayName: "Total", value: this.formatMeasureVal(subSum, false) });
                        return list;
                    };

                    rect.addEventListener("mouseenter", (evt: MouseEvent) => {
                        this.clearHoverResetTimer();
                        const calloutTxt = `${grp.category}${sub.subCategory !== "Total" ? ` '${sub.subCategory.slice(-2)}` : ""} · ${this.formatMeasureVal(seg.value, true)}`;
                        this.positionCallout(calloutTxt, sx + subW / 2, finalY, width, height, margin.left);
                        this.tooltipService.show({
                            coordinates: [evt.clientX, evt.clientY],
                            isTouchEvent: false,
                            dataItems: tooltipItems(),
                            identities: seg.selectionId ? [seg.selectionId] : [],
                        });
                    });
                    rect.addEventListener("mousemove", (evt: MouseEvent) => {
                        this.clearHoverResetTimer();
                        this.tooltipService.move({
                            coordinates: [evt.clientX, evt.clientY],
                            isTouchEvent: false,
                            dataItems: tooltipItems(),
                            identities: seg.selectionId ? [seg.selectionId] : [],
                        });
                    });
                    rect.addEventListener("mouseleave", () => {
                        this.scheduleHoverReset(70, () => {
                            this.calloutEl.classList.remove("is-visible");
                            this.tooltipService.hide({ immediately: true, isTouchEvent: false });
                        });
                    });
                    rect.addEventListener("click", (evt: MouseEvent) => {
                        this.clearHoverResetTimer();
                        this.selectedCategory = this.selectedCategory === grp.category ? null : grp.category;
                        handleSelectionClick(evt, this.selectionManager, this.selectedCategory ? seg.selectionId || grp.selectionId : undefined);
                        this.renderVisual(false);
                    });

                    barsG.appendChild(rect);
                    animatedSegs.push({ rect, targetY: finalY, targetH: rawH, groupIdx: gIdx });
                });
            });

            const isSel = this.selectedCategory === grp.category;
            const xLbl = this.createWrappedXAxisText(gx + gw / 2, height, hasMultiLine, wrappedGroups[gIdx], isSel, xFontPx);
            xAxisG.appendChild(xLbl);
        });

        this.svgRoot.onmouseleave = () => {
            this.scheduleHoverReset(70, () => {
                this.calloutEl.classList.remove("is-visible");
                this.tooltipService.hide({ immediately: true, isTouchEvent: false });
            });
        };

        if (animMs <= 0) return;

        this.animator.run(
            animMs,
            (rawP) => {
                animatedSegs.forEach((s) => {
                    const lp = easeOutCubic(Math.min(1, rawP * (1 + s.groupIdx * 0.04)));
                    const curH = s.targetH * lp;
                    const curY = baseY - (baseY - s.targetY) * lp;
                    s.rect.setAttribute("height", Math.max(0, curH).toFixed(2));
                    s.rect.setAttribute("y", curY.toFixed(2));
                });
            },
            () => {
                animatedSegs.forEach((s) => {
                    s.rect.setAttribute("height", s.targetH.toFixed(2));
                    s.rect.setAttribute("y", s.targetY.toFixed(2));
                });
            },
        );
    }
}
