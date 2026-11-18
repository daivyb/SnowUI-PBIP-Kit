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
    el,
    formatFullCurrency,
    formatMetricValue,
    handleSelectionClick,
    measureTextWidth,
    resolveColumnFormatSpec,
    svgEl,
    toNumericValue,
} from "./snowuiUtils";
import { BRAND_TOKENS } from "./snowuiTokens";
import { VisualFormattingSettingsModel } from "./settings";

interface SplineExtra {
    name: string;
    value: number;
    formatSpec: ResolvedFormatSpec;
}

interface SplinePoint {
    label: string;
    value: number;
    extras: SplineExtra[];
    selectionId?: ISelectionId;
}

interface MeasureSeries {
    displayName: string;
    formatSpec: ResolvedFormatSpec;
    pointsByPrimary: SplinePoint[];
    pointsBySecondary: SplinePoint[];
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
    private tabsEl: HTMLDivElement;
    private granularityBtn: HTMLButtonElement;
    private modeBtn: HTMLButtonElement;
    private canvasWrapEl: HTMLDivElement;
    private svgRoot: SVGSVGElement;
    private calloutEl: HTMLDivElement;

    private activePrimaryIndex: number = 0;
    private activeSecondaryIndex: number = 0;
    private chartMode: "area" | "line" = "area";
    private granularity: "primary" | "secondary" = "primary";
    private initializedControls: boolean = false;
    private hasAltCategory: boolean = false;
    private primarySeriesList: MeasureSeries[] = [];
    private secondarySeriesList: MeasureSeries[] = [];
    private currentYValues: number[] = [];
    private currentHoverIndex: number = -1;
    private selectedLabel: string | null = null;
    private lastViewportWidth: number = 600;
    private lastViewportHeight: number = 300;

    constructor(options: VisualConstructorOptions) {
        this.host = options.host;
        this.events = options.host.eventService;
        this.selectionManager = options.host.createSelectionManager();
        this.tooltipService = options.host.tooltipService;
        this.formattingSettingsService = new FormattingSettingsService();
        this.formattingSettings = new VisualFormattingSettingsModel();
        this.animator = new RafAnimator();

        this.target = options.element;
        this.target.classList.add("snow-spline-host");
        applyHostColorTokens(this.target, this.host.colorPalette);

        this.cardEl = el("div", "snow-spline-card");
        const card = this.cardEl;
        const header = el("div", "snow-spline-header");
        this.tabsEl = el("div", "snow-spline-tabs");

        const controls = el("div", "snow-spline-controls");
        this.granularityBtn = this.createPillButton("Mensual");
        this.modeBtn = this.createPillButton("Área");

        this.granularityBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (!this.hasAltCategory) return;
            this.granularity = this.granularity === "primary" ? "secondary" : "primary";
            this.selectedLabel = null;
            this.currentHoverIndex = -1;
            this.selectionManager.clear();
            this.updateControlLabels();
            this.renderTabs();
            this.renderSpline(true);
        });

        this.modeBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            this.chartMode = this.chartMode === "area" ? "line" : "area";
            this.updateControlLabels();
            this.renderSpline(false);
        });

        controls.appendChild(this.granularityBtn);
        controls.appendChild(this.modeBtn);
        header.appendChild(this.tabsEl);
        header.appendChild(controls);

        this.canvasWrapEl = el("div", "snow-spline-canvas-wrap");
        this.svgRoot = svgEl("svg", { class: "snow-spline-svg" });
        this.calloutEl = el("div", "snow-spline-callout");
        this.canvasWrapEl.appendChild(this.svgRoot);
        this.canvasWrapEl.appendChild(this.calloutEl);

        card.addEventListener("click", () => {
            this.selectedLabel = null;
            this.selectionManager.clear();
            this.renderSpline(false);
        });

        card.appendChild(header);
        card.appendChild(this.canvasWrapEl);
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
            this.cardEl.classList.toggle("is-compact", this.lastViewportHeight < 260 || this.lastViewportWidth < 460);

            const dataView = options.dataViews?.[0];
            this.formattingSettings = this.formattingSettingsService.populateFormattingSettingsModel(
                VisualFormattingSettingsModel,
                dataView,
            );

            if (!this.initializedControls) {
                this.chartMode = this.formattingSettings.chartStyle.defaultChartMode.value === "line" ? "line" : "area";
                this.granularity = this.formattingSettings.chartStyle.defaultGranularity.value === "secondary" ? "secondary" : "primary";
                this.initializedControls = true;
            }

            const activeLineColor = this.resolveLineColor();
            this.cardEl.style.setProperty("--snow-spline-accent", activeLineColor);

            this.extractSeries(dataView);
            this.renderTabs();
            this.updateControlLabels();
            this.renderSpline(true);

            this.events.renderingFinished(options);
        } catch (err) {
            this.events.renderingFailed(options, String(err));
        }
    }

    public destroy(): void {
        this.animator.cancel();
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return this.formattingSettingsService.buildFormattingModel(this.formattingSettings);
    }

    private resolveLineColor(): string {
        return (
            this.formattingSettings.chartStyle.lineColor.value?.value
            || BRAND_TOKENS.visualDefaults.splineLineColor
            || SNOW_COLORS.secondary
        );
    }

    private buildFormatSpec(colFormat?: string, displayName?: string): ResolvedFormatSpec {
        return resolveColumnFormatSpec(colFormat, displayName, {
            currencyMode: String(this.formattingSettings.chartStyle.currencyMode.value || BRAND_TOKENS.currency.mode),
            customPrefix: this.formattingSettings.chartStyle.valuePrefix.value ?? "",
        });
    }

    private createPillButton(label: string): HTMLButtonElement {
        const btn = el("button", "snow-pill-btn") as HTMLButtonElement;
        btn.type = "button";
        const span = el("span", "snow-pill-text", label);
        const chev = svgEl("svg", { width: 10, height: 10, viewBox: "0 0 12 12", fill: "none" });
        chev.appendChild(
            svgEl("path", {
                d: "M3 4.5L6 7.5L9 4.5",
                stroke: "currentColor",
                "stroke-width": 1.5,
                "stroke-linecap": "round",
                "stroke-linejoin": "round",
            }),
        );
        btn.appendChild(span);
        btn.appendChild(chev);
        return btn;
    }

    private updateControlLabels(): void {
        const primaryTxt = this.formattingSettings.chartStyle.primaryAxisLabel.value || "Mensual";
        const secondaryTxt = this.formattingSettings.chartStyle.secondaryAxisLabel.value || "Anual";
        const granSpan = this.granularityBtn.querySelector(".snow-pill-text");
        if (granSpan) {
            granSpan.textContent = this.granularity === "primary" ? primaryTxt : secondaryTxt;
        }
        this.granularityBtn.style.display = this.hasAltCategory ? "inline-flex" : "none";

        const modeSpan = this.modeBtn.querySelector(".snow-pill-text");
        if (modeSpan) {
            modeSpan.textContent = this.chartMode === "area" ? "Área" : "Línea";
        }
    }

    private getActiveSeriesList(): MeasureSeries[] {
        return this.granularity === "secondary" && this.secondarySeriesList.length
            ? this.secondarySeriesList
            : this.primarySeriesList;
    }

    private getActiveMeasureIndex(): number {
        const list = this.getActiveSeriesList();
        if (!list.length) return 0;
        const raw = this.granularity === "secondary" && this.secondarySeriesList !== this.primarySeriesList
            ? this.activeSecondaryIndex
            : this.activePrimaryIndex;
        return clamp(raw, 0, list.length - 1);
    }

    private setActiveMeasureIndex(idx: number): void {
        if (this.granularity === "secondary" && this.secondarySeriesList !== this.primarySeriesList) {
            this.activeSecondaryIndex = idx;
        } else {
            this.activePrimaryIndex = idx;
        }
    }

    private collapseAltBucketValues(rawVals: number[], deduplicateAlt: boolean): number {
        if (!rawVals.length) return 0;
        if (deduplicateAlt && rawVals.length > 1) {
            const minV = Math.min(...rawVals);
            const maxV = Math.max(...rawVals);
            if (Math.abs(maxV - minV) <= 1e-4 * Math.max(1, Math.abs(maxV))) {
                return rawVals[0];
            }
        }
        return rawVals.reduce((acc, v) => acc + v, 0);
    }

    private buildMeasureSeriesGroup(
        measureCols: powerbi.DataViewValueColumn[],
        primaryCatCol: powerbi.DataViewCategoryColumn,
        altCatCol: powerbi.DataViewCategoryColumn | undefined,
        deduplicateAlt: boolean,
    ): MeasureSeries[] {
        if (!measureCols.length) return [];
        const rowCount = primaryCatCol.values.length;
        const measureFormats = measureCols.map((mc, idx) =>
            this.buildFormatSpec(mc.source?.format, mc.source?.displayName || `Métrica ${idx + 1}`),
        );
        const result: MeasureSeries[] = [];

        for (let mIdx = 0; mIdx < measureCols.length; mIdx++) {
            const col = measureCols[mIdx];
            const displayName = col.source?.displayName || `Métrica ${mIdx + 1}`;
            const formatSpec = measureFormats[mIdx];

            const primaryOrder: string[] = [];
            const primaryAgg = new Map<string, { sum: number; extras: Map<string, { value: number; formatSpec: ResolvedFormatSpec }>; selectionId?: ISelectionId }>();

            const secondaryOrder: string[] = [];
            const secondaryAgg = new Map<string, { vals: number[]; extras: Map<string, { vals: number[]; formatSpec: ResolvedFormatSpec }>; selectionId?: ISelectionId }>();

            for (let r = 0; r < rowCount; r++) {
                const pLabel = String(primaryCatCol.values[r] ?? "");
                if (!pLabel) continue;
                const rawMain = col.values[r];
                const val = toNumericValue(rawMain);

                let pEntry = primaryAgg.get(pLabel);
                if (!pEntry) {
                    pEntry = {
                        sum: 0,
                        extras: new Map(),
                        selectionId: this.host.createSelectionIdBuilder().withCategory(primaryCatCol, r).createSelectionId(),
                    };
                    primaryAgg.set(pLabel, pEntry);
                    primaryOrder.push(pLabel);
                }
                pEntry.sum += val;

                for (let eIdx = 0; eIdx < measureCols.length; eIdx++) {
                    if (eIdx === mIdx) continue;
                    const eName = measureCols[eIdx].source?.displayName || `Métrica ${eIdx + 1}`;
                    const prev = pEntry.extras.get(eName);
                    pEntry.extras.set(eName, {
                        value: (prev?.value || 0) + toNumericValue(measureCols[eIdx].values[r]),
                        formatSpec: measureFormats[eIdx],
                    });
                }

                if (altCatCol) {
                    const sLabel = String(altCatCol.values[r] ?? "");
                    if (sLabel) {
                        let sEntry = secondaryAgg.get(sLabel);
                        if (!sEntry) {
                            sEntry = {
                                vals: [],
                                extras: new Map(),
                                selectionId: this.host.createSelectionIdBuilder().withCategory(altCatCol, r).createSelectionId(),
                            };
                            secondaryAgg.set(sLabel, sEntry);
                            secondaryOrder.push(sLabel);
                        }
                        if (rawMain !== null && rawMain !== undefined) {
                            sEntry.vals.push(val);
                        }
                        for (let eIdx = 0; eIdx < measureCols.length; eIdx++) {
                            if (eIdx === mIdx) continue;
                            const eCol = measureCols[eIdx];
                            const eName = eCol.source?.displayName || `Métrica ${eIdx + 1}`;
                            const eRaw = eCol.values[r];
                            let ex = sEntry.extras.get(eName);
                            if (!ex) {
                                ex = { vals: [], formatSpec: measureFormats[eIdx] };
                                sEntry.extras.set(eName, ex);
                            }
                            if (eRaw !== null && eRaw !== undefined) {
                                ex.vals.push(toNumericValue(eRaw));
                            }
                        }
                    }
                }
            }

            secondaryOrder.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));

            const pointsByPrimary: SplinePoint[] = primaryOrder.map((lbl) => {
                const item = primaryAgg.get(lbl)!;
                return {
                    label: lbl,
                    value: item.sum,
                    extras: Array.from(item.extras.entries()).map(([name, info]) => ({
                        name,
                        value: info.value,
                        formatSpec: info.formatSpec,
                    })),
                    selectionId: item.selectionId,
                };
            });

            const pointsBySecondary: SplinePoint[] = secondaryOrder.map((lbl) => {
                const item = secondaryAgg.get(lbl)!;
                return {
                    label: lbl,
                    value: this.collapseAltBucketValues(item.vals, deduplicateAlt),
                    extras: Array.from(item.extras.entries()).map(([name, info]) => ({
                        name,
                        value: this.collapseAltBucketValues(info.vals, deduplicateAlt),
                        formatSpec: info.formatSpec,
                    })),
                    selectionId: item.selectionId,
                };
            });

            result.push({
                displayName,
                formatSpec,
                pointsByPrimary,
                pointsBySecondary,
            });
        }

        return result;
    }

    private extractSeries(dataView?: powerbi.DataView): void {
        this.primarySeriesList = [];
        this.secondarySeriesList = [];
        const categorical = dataView?.categorical;
        const categories = categorical?.categories || [];
        const values = categorical?.values || [];

        if (!categories.length || !values.length) {
            this.hasAltCategory = false;
            return;
        }

        const primaryCatCol = categories.find((c) => c.source?.roles?.["category"]) || categories[0];
        const altCatCol = categories.find((c) => c.source?.roles?.["altCategory"]);
        this.hasAltCategory = Boolean(altCatCol && altCatCol.values.length > 0);
        if (!this.hasAltCategory) {
            this.granularity = "primary";
        }

        const explicitPrimary = values.filter((v) => v.source?.roles?.["measures"]);
        const explicitAlt = values.filter((v) => v.source?.roles?.["altMeasures"]);
        const primaryCols = (explicitPrimary.length ? explicitPrimary : explicitAlt.length ? [] : values).slice(0, 3);
        const altCols = explicitAlt.slice(0, 3);

        this.primarySeriesList = this.buildMeasureSeriesGroup(primaryCols, primaryCatCol, altCatCol, false);
        this.secondarySeriesList = altCols.length
            ? this.buildMeasureSeriesGroup(altCols, primaryCatCol, altCatCol, true)
            : this.primarySeriesList;

        if (!this.primarySeriesList.length && this.secondarySeriesList.length) {
            this.primarySeriesList = this.secondarySeriesList;
        }
        if (this.activePrimaryIndex >= this.primarySeriesList.length) {
            this.activePrimaryIndex = 0;
        }
        if (this.activeSecondaryIndex >= this.secondarySeriesList.length) {
            this.activeSecondaryIndex = 0;
        }
    }

    private renderTabs(): void {
        clearElement(this.tabsEl);
        const activeList = this.getActiveSeriesList();
        const activeIdx = this.getActiveMeasureIndex();
        if (!activeList.length) {
            const emptyTab = el("span", "snow-spline-tab is-active", "Evolución");
            this.tabsEl.appendChild(emptyTab);
            return;
        }

        activeList.forEach((s, idx) => {
            const btn = el("button", `snow-spline-tab${idx === activeIdx ? " is-active" : ""}`, s.displayName) as HTMLButtonElement;
            btn.type = "button";
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                if (this.getActiveMeasureIndex() === idx) return;
                this.setActiveMeasureIndex(idx);
                this.renderTabs();
                this.renderSpline(true);
            });
            this.tabsEl.appendChild(btn);
        });
    }

    private formatSpecValue(val: number, spec: ResolvedFormatSpec, compact: boolean): string {
        if (spec.isPercent) {
            return formatMetricValue(val, { displayUnits: "percent", decimals: 1, numberLocale: spec.numberLocale });
        }
        if (compact) {
            return formatMetricValue(val, {
                prefix: spec.prefix,
                suffix: spec.suffix,
                displayUnits: "auto",
                decimals: spec.decimals,
                numberLocale: spec.numberLocale,
            });
        }
        return formatFullCurrency(val, spec.prefix, spec.suffix, spec.numberLocale);
    }

    private renderSpline(animate: boolean): void {
        clearElement(this.svgRoot);
        this.calloutEl.classList.remove("is-visible");
        this.currentHoverIndex = -1;

        const rawW = this.canvasWrapEl.clientWidth;
        const rawH = this.canvasWrapEl.clientHeight;
        const width = Math.max(80, rawW > 0 ? rawW : Math.max(80, this.lastViewportWidth - 40));
        const height = Math.max(56, rawH > 0 ? rawH : Math.max(56, this.lastViewportHeight - 62));
        this.svgRoot.setAttribute("viewBox", `0 0 ${width} ${height}`);

        const activeList = this.getActiveSeriesList();
        const activeIdx = this.getActiveMeasureIndex();
        const series = activeList[activeIdx];
        const points = series
            ? this.granularity === "secondary" && series.pointsBySecondary.length
                ? series.pointsBySecondary
                : series.pointsByPrimary
            : [];

        if (this.selectedLabel && !points.some((p) => p.label === this.selectedLabel)) {
            this.selectedLabel = null;
        }

        if (!points.length) {
            const txt = svgEl("text", {
                x: width / 2,
                y: height / 2,
                "text-anchor": "middle",
                fill: "var(--snow-ink-muted, #9CA3AF)",
                "font-size": 12,
            });
            txt.textContent = "Sin datos disponibles para los filtros actuales";
            this.svgRoot.appendChild(txt);
            return;
        }

        const lineColor = this.resolveLineColor();
        const fmt = series.formatSpec;
        const animMs = animate ? Math.max(0, Math.min(2000, this.formattingSettings.chartStyle.animationMs.value ?? 620)) : 0;

        const dataMin = d3.min(points, (d) => d.value) ?? 0;
        const dataMax = d3.max(points, (d) => d.value) ?? 0;
        const domainMin = dataMin < 0 ? dataMin * 1.12 : 0;
        const domainMax = dataMax > 0 ? dataMax * 1.15 : (dataMin < 0 ? 0 : 100);

        const tickCount = height < 140 ? 3 : 4;
        const preScale = d3.scaleLinear().domain([domainMin, domainMax]).nice(tickCount).range([100, 0]);
        const preTickStrings = preScale.ticks(tickCount).map((t) => this.formatSpecValue(t, fmt, true));
        const marginLeft = calcDynamicLeftMargin(
            preTickStrings,
            42,
            88,
            '11px "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif',
        );

        const margin = {
            top: height < 170 ? 22 : 28,
            right: width < 400 ? 12 : 20,
            bottom: height < 170 ? 22 : 28,
            left: marginLeft,
        };
        const plotW = Math.max(60, width - margin.left - margin.right);
        const plotH = Math.max(28, height - margin.top - margin.bottom);

        const yScale = d3.scaleLinear().domain([domainMin, domainMax]).nice(tickCount).range([margin.top + plotH, margin.top]);
        const yDom = yScale.domain();
        const baselineVal = clamp(0, yDom[0], yDom[1]);
        const baselineY = yScale(baselineVal);

        const xScale = d3
            .scalePoint<string>()
            .domain(points.map((d) => d.label))
            .range([margin.left + 8, margin.left + plotW - 8])
            .padding(0.2);

        const gradId = `snowSplineGrad_${this.instanceId}`;
        const defs = svgEl("defs");
        const grad = svgEl("linearGradient", { id: gradId, x1: "0%", y1: "0%", x2: "0%", y2: "100%" });
        grad.appendChild(svgEl("stop", { offset: "0%", "stop-color": lineColor, "stop-opacity": "0.18" }));
        grad.appendChild(svgEl("stop", { offset: "95%", "stop-color": lineColor, "stop-opacity": "0.0" }));
        defs.appendChild(grad);
        this.svgRoot.appendChild(defs);

        const ticks = yScale.ticks(tickCount);
        const gridG = svgEl("g");
        for (const t of ticks) {
            const ty = yScale(t);
            const isZero = Math.abs(t) < 1e-6 && yDom[0] < 0;
            gridG.appendChild(
                svgEl("line", {
                    x1: margin.left,
                    x2: width - margin.right,
                    y1: ty,
                    y2: ty,
                    stroke: isZero ? "var(--snow-ink-muted, #9CA3AF)" : "var(--snow-border, rgba(0, 0, 0, 0.06))",
                    "stroke-opacity": isZero ? 0.45 : 0.65,
                    "stroke-width": 1,
                    ...(isZero ? { "stroke-dasharray": "3,3" } : {}),
                }),
            );
            const lbl = svgEl("text", {
                x: margin.left - 10,
                y: ty + 4,
                "text-anchor": "end",
                fill: "var(--snow-ink-muted, #9CA3AF)",
                "font-size": 11,
            });
            lbl.textContent = this.formatSpecValue(t, fmt, true);
            gridG.appendChild(lbl);
        }
        this.svgRoot.appendChild(gridG);

        const dropLinesG = svgEl("g");
        const hoverGuideLine = svgEl("line", {
            x1: 0,
            x2: 0,
            y1: margin.top,
            y2: baselineY,
            stroke: lineColor,
            "stroke-width": 1.2,
            "stroke-dasharray": "3,3",
            opacity: 0,
        });
        this.svgRoot.appendChild(dropLinesG);
        this.svgRoot.appendChild(hoverGuideLine);

        const areaPathEl = svgEl("path", {
            class: "snow-spline-area",
            fill: `url(#${gradId})`,
            opacity: this.chartMode === "area" ? "1" : "0",
        });
        const linePathEl = svgEl("path", {
            class: "snow-spline-path",
            stroke: lineColor,
            "stroke-width": 2.4,
        });
        this.svgRoot.appendChild(areaPathEl);
        this.svgRoot.appendChild(linePathEl);

        const nodesG = svgEl("g");
        const xAxisG = svgEl("g");
        this.svgRoot.appendChild(nodesG);
        this.svgRoot.appendChild(xAxisG);

        const xs = points.map((d) => xScale(d.label) ?? margin.left);
        const targetVals = points.map((d) => d.value);
        const prevVals =
            this.currentYValues.length === targetVals.length
                ? this.currentYValues.slice()
                : targetVals.map(() => baselineVal);

        const lineGen = d3
            .line<{ x: number; y: number }>()
            .x((d) => d.x)
            .y((d) => d.y)
            .curve(d3.curveMonotoneX);

        const areaGen = d3
            .area<{ x: number; y: number }>()
            .x((d) => d.x)
            .y0(baselineY)
            .y1((d) => d.y)
            .curve(d3.curveMonotoneX);

        const maxLblW = points.reduce(
            (m, pt) => Math.max(m, measureTextWidth(pt.label, '11.5px "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif')),
            24,
        );
        const minSlotPx = Math.max(36, maxLblW + 14);
        const maxVisibleTicks = Math.max(2, Math.floor(plotW / minSlotPx));
        const tickStep = Math.max(1, Math.ceil(points.length / maxVisibleTicks));

        const nodeEls: SVGCircleElement[] = [];
        const verticalGuideEls: SVGLineElement[] = [];

        points.forEach((pt, idx) => {
            const x = xs[idx];
            const isSelected = this.selectedLabel === pt.label;
            const vLine = svgEl("line", {
                x1: x,
                x2: x,
                y1: baselineY,
                y2: baselineY,
                stroke: "var(--snow-border, rgba(0, 0, 0, 0.08))",
                "stroke-opacity": 0.75,
                "stroke-width": 1,
                "stroke-dasharray": "2,3",
            });
            dropLinesG.appendChild(vLine);
            verticalGuideEls.push(vLine);

            if (idx % tickStep === 0 || isSelected) {
                const xLbl = svgEl("text", {
                    x,
                    y: height - 6,
                    "text-anchor": "middle",
                    fill: isSelected ? "var(--snow-ink, #111827)" : "var(--snow-ink-muted, #9CA3AF)",
                    "font-weight": isSelected ? 600 : 400,
                    "font-size": 11.5,
                });
                xLbl.textContent = pt.label;
                xAxisG.appendChild(xLbl);
            }

            const circle = svgEl("circle", {
                class: "snow-spline-node",
                cx: x,
                cy: yScale(prevVals[idx]),
                r: isSelected ? 5.5 : 3.8,
                fill: "var(--snow-card-bg, #FFFFFF)",
                stroke: lineColor,
                "stroke-width": isSelected ? 2.5 : 2,
                opacity: this.selectedLabel && !isSelected ? 0.38 : 1,
            });
            circle.style.pointerEvents = "none";

            nodesG.appendChild(circle);
            nodeEls.push(circle);
        });

        const hitRect = svgEl("rect", {
            x: margin.left,
            y: margin.top,
            width: plotW,
            height: plotH,
            fill: "transparent",
            cursor: "pointer",
        });
        hitRect.addEventListener("mousemove", (evt: MouseEvent) => {
            const rect = this.svgRoot.getBoundingClientRect();
            const relX = ((evt.clientX - rect.left) / Math.max(1, rect.width)) * width;
            let bestIdx = 0;
            let bestDist = Infinity;
            for (let i = 0; i < xs.length; i++) {
                const dist = Math.abs(xs[i] - relX);
                if (dist < bestDist) {
                    bestDist = dist;
                    bestIdx = i;
                }
            }
            if (bestIdx !== this.currentHoverIndex) {
                this.currentHoverIndex = bestIdx;
                this.showHoverAt(bestIdx, xs, points, nodeEls, yScale, fmt, lineColor, hoverGuideLine, width, height, margin.left, evt);
            } else {
                this.moveTooltipAt(bestIdx, points, series.displayName, fmt, evt);
            }
        });
        hitRect.addEventListener("click", (evt: MouseEvent) => {
            if (this.currentHoverIndex >= 0 && this.currentHoverIndex < points.length) {
                const pt = points[this.currentHoverIndex];
                this.selectedLabel = this.selectedLabel === pt.label ? null : pt.label;
                handleSelectionClick(evt, this.selectionManager, this.selectedLabel ? pt.selectionId : undefined);
                this.renderSpline(false);
            }
        });
        hitRect.addEventListener("mouseleave", () => {
            this.currentHoverIndex = -1;
            this.hideHover(hoverGuideLine, nodeEls, points);
        });
        this.svgRoot.appendChild(hitRect);

        this.animator.run(
            animMs,
            (p) => {
                const coords: Array<{ x: number; y: number }> = [];
                const interpVals: number[] = [];
                for (let i = 0; i < points.length; i++) {
                    const v = prevVals[i] + (targetVals[i] - prevVals[i]) * p;
                    interpVals.push(v);
                    const py = yScale(v);
                    coords.push({ x: xs[i], y: py });
                    nodeEls[i].setAttribute("cy", py.toFixed(2));
                    verticalGuideEls[i].setAttribute("y1", py.toFixed(2));
                }
                this.currentYValues = interpVals;
                linePathEl.setAttribute("d", lineGen(coords) || "");
                areaPathEl.setAttribute("d", areaGen(coords) || "");
            },
            () => {
                this.currentYValues = targetVals.slice();
            },
        );
    }

    private showHoverAt(
        idx: number,
        xs: number[],
        points: SplinePoint[],
        nodeEls: SVGCircleElement[],
        yScale: d3.ScaleLinear<number, number>,
        fmt: ResolvedFormatSpec,
        lineColor: string,
        hoverGuideLine: SVGLineElement,
        canvasW: number,
        canvasH: number,
        marginLeft: number,
        evt: MouseEvent,
    ): void {
        const pt = points[idx];
        const x = xs[idx];
        const y = yScale(pt.value);
        hoverGuideLine.setAttribute("x1", String(x));
        hoverGuideLine.setAttribute("x2", String(x));
        hoverGuideLine.setAttribute("y1", String(y));
        hoverGuideLine.setAttribute("opacity", "0.75");

        points.forEach((p, i) => {
            const isSel = this.selectedLabel === p.label;
            const isHov = i === idx;
            nodeEls[i].setAttribute("r", isHov ? "6" : isSel ? "5.5" : "3.8");
            nodeEls[i].setAttribute("stroke-width", isHov || isSel ? "2.6" : "2");
            nodeEls[i].setAttribute("opacity", isHov || !this.selectedLabel || isSel ? "1" : "0.38");
        });

        const calloutTxt = `${pt.label} · ${this.formatSpecValue(pt.value, fmt, true)}`;
        this.calloutEl.textContent = calloutTxt;
        const halfPill = (measureTextWidth(calloutTxt, '600 11.5px "Segoe UI", sans-serif') + 24) / 2;
        const clampedX = clamp(x, marginLeft + halfPill, canvasW - halfPill - 6);
        const clampedY = clamp(y - 10, 28, canvasH - 18);
        this.calloutEl.style.left = `${clampedX}px`;
        this.calloutEl.style.top = `${clampedY}px`;
        this.calloutEl.style.borderBottom = `2px solid ${lineColor}`;
        this.calloutEl.classList.add("is-visible");

        const activeList = this.getActiveSeriesList();
        const seriesName = activeList[this.getActiveMeasureIndex()]?.displayName || "Valor";
        this.tooltipService.show({
            coordinates: [evt.clientX, evt.clientY],
            isTouchEvent: false,
            dataItems: this.buildTooltipItems(pt, seriesName, fmt),
            identities: pt.selectionId ? [pt.selectionId] : [],
        });
    }

    private moveTooltipAt(
        idx: number,
        points: SplinePoint[],
        seriesName: string,
        fmt: ResolvedFormatSpec,
        evt: MouseEvent,
    ): void {
        const pt = points[idx];
        this.tooltipService.move({
            coordinates: [evt.clientX, evt.clientY],
            isTouchEvent: false,
            dataItems: this.buildTooltipItems(pt, seriesName, fmt),
            identities: pt.selectionId ? [pt.selectionId] : [],
        });
    }

    private hideHover(hoverGuideLine: SVGLineElement, nodeEls: SVGCircleElement[], points: SplinePoint[]): void {
        hoverGuideLine.setAttribute("opacity", "0");
        points.forEach((p, i) => {
            const isSel = this.selectedLabel === p.label;
            nodeEls[i].setAttribute("r", isSel ? "5.5" : "3.8");
            nodeEls[i].setAttribute("stroke-width", isSel ? "2.5" : "2");
            nodeEls[i].setAttribute("opacity", this.selectedLabel && !isSel ? "0.38" : "1");
        });
        this.calloutEl.classList.remove("is-visible");
        this.tooltipService.hide({ immediately: true, isTouchEvent: false });
    }

    private buildTooltipItems(pt: SplinePoint, seriesName: string, fmt: ResolvedFormatSpec): VisualTooltipDataItem[] {
        const items: VisualTooltipDataItem[] = [
            { displayName: pt.label, value: "" },
            { displayName: seriesName, value: this.formatSpecValue(pt.value, fmt, false) },
        ];
        for (const extra of pt.extras) {
            items.push({ displayName: extra.name, value: this.formatSpecValue(extra.value, extra.formatSpec, false) });
        }
        return items;
    }
}
