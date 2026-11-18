"use strict";

import powerbi from "powerbi-visuals-api";
import { FormattingSettingsService } from "powerbi-visuals-utils-formattingmodel";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;
import IVisualHost = powerbi.extensibility.visual.IVisualHost;
import IVisualEventService = powerbi.extensibility.IVisualEventService;
import ITooltipService = powerbi.extensibility.ITooltipService;
import VisualTooltipDataItem = powerbi.extensibility.VisualTooltipDataItem;
import DataViewValueColumn = powerbi.DataViewValueColumn;

import {
    DisplayUnitsMode,
    RafAnimator,
    ResolvedFormatSpec,
    applyHostColorTokens,
    bindPowerBiTooltip,
    clamp,
    clearElement,
    el,
    formatFullCurrency,
    formatMetricValue,
    formatPercentDelta,
    measureTextWidth,
    resolveColumnFormatSpec,
    svgEl,
    toNumericValue,
} from "./snowuiUtils";
import { BRAND_TOKENS } from "./snowuiTokens";
import { VisualFormattingSettingsModel } from "./settings";

interface KpiDataState {
    hasData: boolean;
    title: string;
    value: number;
    hasDelta: boolean;
    delta: number;
    formatSpec: ResolvedFormatSpec;
    tooltipExtras: Array<{ displayName: string; formatted: string }>;
}

export class Visual implements IVisual {
    private host: IVisualHost;
    private events: IVisualEventService;
    private tooltipService: ITooltipService;
    private target: HTMLElement;
    private formattingSettings: VisualFormattingSettingsModel;
    private formattingSettingsService: FormattingSettingsService;
    private animator: RafAnimator;

    private cardEl: HTMLDivElement;
    private titleEl: HTMLSpanElement;
    private iconBadgeEl: HTMLSpanElement;
    private valueEl: HTMLSpanElement;
    private deltaWrapEl: HTMLDivElement;
    private deltaPillEl: HTMLSpanElement;
    private deltaTextEl: HTMLSpanElement;
    private subtitleEl: HTMLSpanElement;

    private currentDisplayedValue: number = 0;
    private currentDisplayedDelta: number = 0;
    private hasRenderedOnce: boolean = false;
    private latestState: KpiDataState | null = null;
    private lastViewportHeight: number = 156;

    constructor(options: VisualConstructorOptions) {
        this.host = options.host;
        this.events = options.host.eventService;
        this.tooltipService = options.host.tooltipService;
        this.formattingSettingsService = new FormattingSettingsService();
        this.formattingSettings = new VisualFormattingSettingsModel();
        this.animator = new RafAnimator();

        this.target = options.element;
        this.target.classList.add("snow-kpi-host");
        applyHostColorTokens(this.target, this.host.colorPalette);

        this.cardEl = el("div", "snow-kpi-card variant-blue");
        const headerEl = el("div", "snow-kpi-header");
        this.titleEl = el("span", "snow-kpi-title", "KPI");
        this.iconBadgeEl = el("span", "snow-kpi-icon-badge");
        headerEl.appendChild(this.titleEl);
        headerEl.appendChild(this.iconBadgeEl);

        const bodyEl = el("div", "snow-kpi-body");
        this.valueEl = el("span", "snow-kpi-value", "—");
        this.deltaWrapEl = el("div", "snow-kpi-delta-wrap");
        this.deltaPillEl = el("span", "snow-kpi-delta-pill");
        this.deltaTextEl = el("span");
        this.subtitleEl = el("span", "snow-kpi-subtitle");
        this.deltaWrapEl.appendChild(this.deltaPillEl);
        this.deltaWrapEl.appendChild(this.subtitleEl);
        bodyEl.appendChild(this.valueEl);
        bodyEl.appendChild(this.deltaWrapEl);

        this.cardEl.appendChild(headerEl);
        this.cardEl.appendChild(bodyEl);
        this.target.appendChild(this.cardEl);
        this.renderTrendBadgeIcon(true);

        bindPowerBiTooltip(this.cardEl, this.tooltipService, () => this.buildTooltipItems());
    }

    public update(options: VisualUpdateOptions): void {
        this.events.renderingStarted(options);
        try {
            applyHostColorTokens(this.target, this.host.colorPalette);
            if (options.viewport?.width > 0) {
                this.target.style.width = `${Math.floor(options.viewport.width)}px`;
            }
            if (options.viewport?.height > 0) {
                const h = Math.floor(options.viewport.height);
                this.lastViewportHeight = h;
                this.target.style.height = `${h}px`;
                this.cardEl.style.height = `${h}px`;
            }

            const dataView = options.dataViews?.[0];
            this.formattingSettings = this.formattingSettingsService.populateFormattingSettingsModel(
                VisualFormattingSettingsModel,
                dataView,
            );

            const state = this.extractData(dataView);
            this.latestState = state;
            this.applyCardTheme();

            const subtitleText = (this.formattingSettings.cardStyle.subtitleText.value ?? "").trim();
            if (!state.hasData) {
                this.titleEl.textContent = state.title || "KPI";
                this.valueEl.textContent = "—";
                this.valueEl.style.fontSize = "27px";
                this.deltaPillEl.style.display = "none";
                this.subtitleEl.textContent = subtitleText;
                this.subtitleEl.style.display = subtitleText ? "inline" : "none";
                this.deltaWrapEl.style.display = subtitleText ? "inline-flex" : "none";
                this.events.renderingFinished(options);
                return;
            }

            this.titleEl.textContent = state.title;
            this.deltaPillEl.style.display = state.hasDelta ? "inline-flex" : "none";
            this.deltaWrapEl.style.display = state.hasDelta || Boolean(subtitleText) ? "inline-flex" : "none";

            const duration = Math.max(0, Math.min(2000, this.formattingSettings.cardStyle.animationMs.value ?? 650));
            const startValue = this.hasRenderedOnce ? this.currentDisplayedValue : 0;
            const startDelta = this.hasRenderedOnce ? this.currentDisplayedDelta : 0;
            const targetValue = state.value;
            const targetDelta = state.delta;

            const isPositive = targetDelta >= 0;
            this.renderTrendBadgeIcon(isPositive);
            this.deltaPillEl.classList.toggle("is-negative", !isPositive);

            const units = (this.formattingSettings.numberFormat.displayUnits.value as DisplayUnitsMode) || "auto";
            const decimals = this.formattingSettings.numberFormat.decimals.value ?? BRAND_TOKENS.currency.defaultDecimals;
            const deltaIsRatio = this.formattingSettings.numberFormat.deltaIsRatio.value ?? true;
            const deltaSuffix = this.formattingSettings.numberFormat.deltaSuffix.value ?? "";
            const subtitle = this.formattingSettings.cardStyle.subtitleText.value ?? "";

            this.subtitleEl.textContent = subtitle;
            this.subtitleEl.style.display = subtitle ? "inline" : "none";

            const fmt = state.formatSpec;
            const finalText = formatMetricValue(targetValue, {
                prefix: fmt.prefix,
                suffix: fmt.suffix,
                displayUnits: fmt.isPercent ? "percent" : units,
                decimals,
                numberLocale: fmt.numberLocale,
            });
            this.fitValueFontSize(finalText, state.hasDelta || Boolean(subtitleText));

            this.animator.run(
                duration,
                (p) => {
                    const interpVal = startValue + (targetValue - startValue) * p;
                    const interpDelta = startDelta + (targetDelta - startDelta) * p;
                    this.currentDisplayedValue = interpVal;
                    this.currentDisplayedDelta = interpDelta;

                    this.valueEl.textContent = formatMetricValue(interpVal, {
                        prefix: fmt.prefix,
                        suffix: fmt.suffix,
                        displayUnits: fmt.isPercent ? "percent" : units,
                        decimals,
                        numberLocale: fmt.numberLocale,
                    });

                    if (state.hasDelta) {
                        const fmtDelta = formatPercentDelta(interpDelta, deltaIsRatio);
                        this.deltaTextEl.textContent = `${fmtDelta.text}${deltaSuffix ? ` ${deltaSuffix}` : ""}`;
                    }
                },
                () => {
                    this.currentDisplayedValue = targetValue;
                    this.currentDisplayedDelta = targetDelta;
                    this.hasRenderedOnce = true;
                },
            );

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

    private fitValueFontSize(text: string, hasDeltaOrSub: boolean): void {
        const cardW = this.cardEl.clientWidth || parseFloat(this.target.style.width) || 260;
        const cardH = this.cardEl.clientHeight || this.lastViewportHeight || 156;
        const basePx = cardH < 76 ? 19 : cardH < 98 ? 22 : 27;
        const padH = cardH < 76 ? 24 : cardH < 98 ? 28 : 40;
        const availW = Math.max(80, cardW - padH);
        const deltaReserve = hasDeltaOrSub ? Math.min(availW * 0.44, cardH < 98 ? 82 : 92) : 0;
        const maxValW = Math.max(60, availW - deltaReserve - 8);
        const measuredW = measureTextWidth(text, `700 ${basePx}px "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif`);
        const nextSize = measuredW > maxValW ? clamp(Math.floor(basePx * (maxValW / measuredW)), 14, basePx) : basePx;
        this.valueEl.style.fontSize = `${nextSize}px`;
    }

    private applyCardTheme(): void {
        const variant = String(this.formattingSettings.cardStyle.themeVariant.value || "blue");
        const cfgSurface = String(this.formattingSettings.cardStyle.surfaceMode.value || "auto");
        const resolvedSurface = cfgSurface === "auto" ? BRAND_TOKENS.style.kpiSurfaceMode : cfgSurface;
        const radius = Math.max(0, Math.min(36, this.formattingSettings.cardStyle.cornerRadius.value ?? BRAND_TOKENS.style.cornerRadius));
        const h = this.cardEl.clientHeight || this.lastViewportHeight || 156;
        const compactCls = h < 76 ? " is-ultra-compact" : h < 98 ? " is-compact" : "";
        this.cardEl.className = `snow-kpi-card variant-${variant} surface-${resolvedSurface}${compactCls}`;
        this.cardEl.style.borderRadius = `${radius}px`;
    }

    private renderTrendBadgeIcon(positive: boolean): void {
        if (this.iconBadgeEl) {
            clearElement(this.iconBadgeEl);
            const svg = svgEl("svg", { width: 16, height: 16, viewBox: "0 0 16 16", fill: "none" });
            const d = positive
                ? "M2.5 11.2L6.2 7.5L8.7 9.9L13.5 4.8M13.5 4.8H10.1M13.5 4.8V8.2"
                : "M2.5 4.8L6.2 8.5L8.7 6.1L13.5 11.2M13.5 11.2H10.1M13.5 11.2V7.8";
            svg.appendChild(
                svgEl("path", {
                    d,
                    stroke: "currentColor",
                    "stroke-width": 1.7,
                    "stroke-linecap": "round",
                    "stroke-linejoin": "round",
                }),
            );
            this.iconBadgeEl.appendChild(svg);
        }

        if (this.deltaPillEl && this.deltaTextEl) {
            clearElement(this.deltaPillEl);
            const arrow = svgEl("svg", { width: 10, height: 10, viewBox: "0 0 12 12", fill: "none" });
            const arrowPath = positive
                ? "M2 8.5L5.2 5.3L7.2 7.3L10 3.5M10 3.5H7.6M10 3.5V5.9"
                : "M2 3.5L5.2 6.7L7.2 4.7L10 8.5M10 8.5H7.6M10 8.5V6.1";
            arrow.appendChild(
                svgEl("path", {
                    d: arrowPath,
                    stroke: "currentColor",
                    "stroke-width": 1.6,
                    "stroke-linecap": "round",
                    "stroke-linejoin": "round",
                }),
            );
            this.deltaPillEl.appendChild(this.deltaTextEl);
            this.deltaPillEl.appendChild(arrow);
        }
    }

    private formatExtraTooltip(
        name: string,
        raw: unknown,
        colFormat: string | undefined,
    ): { displayName: string; formatted: string } {
        const v = toNumericValue(raw);
        const spec = resolveColumnFormatSpec(colFormat, name, {
            currencyMode: String(this.formattingSettings.numberFormat.currencyMode.value || BRAND_TOKENS.currency.mode),
            customPrefix: this.formattingSettings.numberFormat.valuePrefix.value ?? "",
            customSuffix: this.formattingSettings.numberFormat.valueSuffix.value ?? "",
        });
        if (spec.isPercent) {
            const pct = Math.abs(v) <= 2 ? v * 100 : v;
            return { displayName: name, formatted: `${pct.toFixed(1)}%` };
        }
        return {
            displayName: name,
            formatted: formatFullCurrency(v, spec.prefix, spec.suffix, spec.numberLocale),
        };
    }

    private buildMainFormatSpec(colFormat?: string, displayName?: string): ResolvedFormatSpec {
        return resolveColumnFormatSpec(colFormat, displayName, {
            currencyMode: String(this.formattingSettings.numberFormat.currencyMode.value || BRAND_TOKENS.currency.mode),
            customPrefix: this.formattingSettings.numberFormat.valuePrefix.value ?? "",
            customSuffix: this.formattingSettings.numberFormat.valueSuffix.value ?? "",
            displayUnits: (this.formattingSettings.numberFormat.displayUnits.value as DisplayUnitsMode) || "auto",
            decimals: this.formattingSettings.numberFormat.decimals.value ?? BRAND_TOKENS.currency.defaultDecimals,
        });
    }

    private extractData(dataView?: powerbi.DataView): KpiDataState {
        const titleOverride = (this.formattingSettings.cardStyle.titleOverride.value || "").trim();

        const table = dataView?.table;
        if (table?.columns?.length && table.rows?.length) {
            const cols = table.columns;
            const row0 = table.rows[0];
            let mainIdx = -1;
            let deltaIdx = -1;
            const extraIndices: number[] = [];

            cols.forEach((col, idx) => {
                const roles = col.roles || {};
                if (roles["value"] && mainIdx < 0) {
                    mainIdx = idx;
                } else if (roles["delta"] && deltaIdx < 0) {
                    deltaIdx = idx;
                } else if (roles["tooltipFields"]) {
                    extraIndices.push(idx);
                }
            });
            if (mainIdx < 0) mainIdx = 0;

            const rawMain = row0[mainIdx];
            const hasMain = rawMain !== null && rawMain !== undefined;
            const mainVal = toNumericValue(rawMain);
            const rawDelta = deltaIdx >= 0 ? row0[deltaIdx] : undefined;
            const hasDelta = deltaIdx >= 0 && rawDelta !== null && rawDelta !== undefined;
            const deltaVal = toNumericValue(rawDelta);

            const extras = extraIndices
                .filter((idx) => row0[idx] !== null && row0[idx] !== undefined)
                .map((idx) =>
                    this.formatExtraTooltip(
                        cols[idx]?.displayName || "Métrica",
                        row0[idx],
                        cols[idx]?.format,
                    ),
                );

            const resolvedTitle = titleOverride || cols[mainIdx]?.displayName || "KPI";
            return {
                hasData: hasMain,
                title: resolvedTitle,
                value: mainVal,
                hasDelta,
                delta: deltaVal,
                formatSpec: this.buildMainFormatSpec(cols[mainIdx]?.format, cols[mainIdx]?.displayName || resolvedTitle),
                tooltipExtras: extras,
            };
        }

        const values = dataView?.categorical?.values;
        if (!values || values.length === 0) {
            return {
                hasData: false,
                title: titleOverride || "Asigna un Valor",
                value: 0,
                hasDelta: false,
                delta: 0,
                formatSpec: this.buildMainFormatSpec(undefined, titleOverride),
                tooltipExtras: [],
            };
        }

        let mainCol: DataViewValueColumn | undefined;
        let deltaCol: DataViewValueColumn | undefined;
        const extraCols: DataViewValueColumn[] = [];

        for (const col of values) {
            const roles = col.source?.roles || {};
            if (roles["value"] && !mainCol) {
                mainCol = col;
            } else if (roles["delta"] && !deltaCol) {
                deltaCol = col;
            } else if (roles["tooltipFields"]) {
                extraCols.push(col);
            }
        }

        if (!mainCol) {
            mainCol = values[0];
        }

        const rawMain = mainCol?.values?.[0];
        const hasMain = rawMain !== null && rawMain !== undefined;
        const mainVal = toNumericValue(rawMain);
        const rawDelta = deltaCol?.values?.[0];
        const hasDelta = Boolean(deltaCol) && rawDelta !== null && rawDelta !== undefined;
        const deltaVal = toNumericValue(rawDelta);

        const extras = extraCols
            .filter((c) => c.values?.[0] !== null && c.values?.[0] !== undefined)
            .map((c) =>
                this.formatExtraTooltip(
                    c.source?.displayName || "Métrica",
                    c.values[0],
                    c.source?.format,
                ),
            );

        const resolvedTitle = titleOverride || mainCol?.source?.displayName || "KPI";
        return {
            hasData: hasMain,
            title: resolvedTitle,
            value: mainVal,
            hasDelta,
            delta: deltaVal,
            formatSpec: this.buildMainFormatSpec(mainCol?.source?.format, mainCol?.source?.displayName || resolvedTitle),
            tooltipExtras: extras,
        };
    }

    private buildTooltipItems(): VisualTooltipDataItem[] {
        if (!this.latestState || !this.latestState.hasData) {
            return [];
        }
        const fmt = this.latestState.formatSpec;
        const deltaIsRatio = this.formattingSettings.numberFormat.deltaIsRatio.value ?? true;
        const items: VisualTooltipDataItem[] = [
            {
                displayName: this.latestState.title,
                value: fmt.isPercent
                    ? formatMetricValue(this.latestState.value, { displayUnits: "percent", decimals: 2 })
                    : formatFullCurrency(this.latestState.value, fmt.prefix, fmt.suffix, fmt.numberLocale),
            },
        ];
        if (this.latestState.hasDelta) {
            const dFmt = formatPercentDelta(this.latestState.delta, deltaIsRatio);
            items.push({
                displayName: "Variación / Indicador",
                value: dFmt.text,
            });
        }
        for (const extra of this.latestState.tooltipExtras) {
            items.push({
                displayName: extra.displayName,
                value: extra.formatted,
            });
        }
        return items;
    }
}
