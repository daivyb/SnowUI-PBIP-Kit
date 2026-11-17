import powerbi from "powerbi-visuals-api";
import VisualTooltipDataItem = powerbi.extensibility.VisualTooltipDataItem;
import ITooltipService = powerbi.extensibility.ITooltipService;
import ISelectionId = powerbi.visuals.ISelectionId;
import ISelectionManager = powerbi.extensibility.ISelectionManager;
import ISandboxExtendedColorPalette = powerbi.extensibility.ISandboxExtendedColorPalette;

import { BRAND_TOKENS, StatusRuleConfig } from "./snowuiTokens";

export function hexToRgba(hex: string, alpha: number): string {
    const cleaned = (hex || "").trim().replace(/^#/, "");
    if (!/^[0-9A-Fa-f]{6}$/.test(cleaned)) {
        return `rgba(0, 122, 255, ${alpha})`;
    }
    const r = parseInt(cleaned.slice(0, 2), 16);
    const g = parseInt(cleaned.slice(2, 4), 16);
    const b = parseInt(cleaned.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function darkenHex(hex: string, factor: number = 0.2): string {
    const cleaned = (hex || "").trim().replace(/^#/, "");
    if (!/^[0-9A-Fa-f]{6}$/.test(cleaned)) return "#111827";
    const clamp = (v: number) => Math.max(0, Math.min(255, Math.round(v)));
    const r = clamp(parseInt(cleaned.slice(0, 2), 16) * (1 - factor));
    const g = clamp(parseInt(cleaned.slice(2, 4), 16) * (1 - factor));
    const b = clamp(parseInt(cleaned.slice(4, 6), 16) * (1 - factor));
    return `#${[r, g, b].map((c) => c.toString(16).padStart(2, "0")).join("")}`.toUpperCase();
}

export const SNOW_COLORS = {
    blue: BRAND_TOKENS.colors.brand.primary,
    primary: BRAND_TOKENS.colors.brand.primary,
    blueLight: BRAND_TOKENS.colors.dataColors[6] || "#5AC8FA",
    purple: BRAND_TOKENS.colors.brand.secondary,
    secondary: BRAND_TOKENS.colors.brand.secondary,
    green: BRAND_TOKENS.colors.semantic.positive,
    positive: BRAND_TOKENS.colors.semantic.positive,
    red: BRAND_TOKENS.colors.semantic.negative,
    negative: BRAND_TOKENS.colors.semantic.negative,
    teal: BRAND_TOKENS.colors.brand.tertiary,
    tertiary: BRAND_TOKENS.colors.brand.tertiary,
    orange: BRAND_TOKENS.colors.semantic.warning,
    warning: BRAND_TOKENS.colors.semantic.warning,
    charcoal: BRAND_TOKENS.colors.brand.darkSurface,
    slate: "#3A3A3C",
    ink: BRAND_TOKENS.colors.text.primary,
    inkSecondary: BRAND_TOKENS.colors.text.secondary,
    inkMuted: BRAND_TOKENS.colors.text.muted,
    pillSurface: "rgba(0, 0, 0, 0.045)",
    rowSurface: "rgba(0, 0, 0, 0.024)",
    rowSurfaceHover: hexToRgba(BRAND_TOKENS.colors.brand.primary, 0.06),
    hairline: "rgba(0, 0, 0, 0.06)",
    white: BRAND_TOKENS.colors.surfaces.card,
} as const;

export const AVATAR_PALETTE: ReadonlyArray<{ bg: string; fg: string }> = [
    { bg: hexToRgba(BRAND_TOKENS.colors.brand.primary, 0.14), fg: darkenHex(BRAND_TOKENS.colors.brand.primary, 0.22) },
    { bg: hexToRgba(BRAND_TOKENS.colors.brand.secondary, 0.14), fg: darkenHex(BRAND_TOKENS.colors.brand.secondary, 0.22) },
    { bg: hexToRgba(BRAND_TOKENS.colors.semantic.positive, 0.16), fg: darkenHex(BRAND_TOKENS.colors.semantic.positive, 0.28) },
    { bg: hexToRgba(BRAND_TOKENS.colors.semantic.warning, 0.16), fg: darkenHex(BRAND_TOKENS.colors.semantic.warning, 0.24) },
    { bg: hexToRgba(BRAND_TOKENS.colors.brand.tertiary, 0.16), fg: darkenHex(BRAND_TOKENS.colors.brand.tertiary, 0.28) },
    { bg: hexToRgba(BRAND_TOKENS.colors.semantic.negative, 0.14), fg: darkenHex(BRAND_TOKENS.colors.semantic.negative, 0.22) },
];

export type DisplayUnitsMode = "auto" | "none" | "thousands" | "millions" | "percent";
export type CurrencyMode = "auto" | "brand" | "custom";

export interface FormatValueOptions {
    prefix?: string;
    suffix?: string;
    displayUnits?: DisplayUnitsMode;
    decimals?: number;
    numberLocale?: string;
}

export interface ResolvedFormatSpec {
    kind: "currency" | "percent" | "number";
    isPercent: boolean;
    prefix: string;
    suffix: string;
    numberLocale: string;
    decimals: number;
}

export function applyHostColorTokens(
    targetEl: HTMLElement,
    colorPalette?: ISandboxExtendedColorPalette,
): void {
    const s = targetEl.style;
    s.setProperty("--snow-radius", `${BRAND_TOKENS.style.cornerRadius}px`);
    if (colorPalette?.isHighContrast) {
        const bg = colorPalette.background?.value || "#000000";
        const fg = colorPalette.foreground?.value || "#FFFFFF";
        const hl = colorPalette.hyperlink?.value || fg;
        s.setProperty("--snow-card-bg", bg);
        s.setProperty("--snow-ink", fg);
        s.setProperty("--snow-ink-secondary", fg);
        s.setProperty("--snow-ink-muted", fg);
        s.setProperty("--snow-border", fg);
        s.setProperty("--snow-primary", hl);
        s.setProperty("--snow-secondary", hl);
        s.setProperty("--snow-hover-bg", hexToRgba(hl, 0.18));
        s.setProperty("--snow-selected-bg", hexToRgba(hl, 0.28));
        return;
    }

    const primary = BRAND_TOKENS.colors.brand.primary;
    s.setProperty("--snow-primary", primary);
    s.setProperty("--snow-secondary", BRAND_TOKENS.colors.brand.secondary);
    s.setProperty("--snow-tertiary", BRAND_TOKENS.colors.brand.tertiary);
    s.setProperty("--snow-positive", colorPalette?.positive?.value || BRAND_TOKENS.colors.semantic.positive);
    s.setProperty("--snow-negative", colorPalette?.negative?.value || BRAND_TOKENS.colors.semantic.negative);
    s.setProperty("--snow-warning", colorPalette?.neutral?.value || BRAND_TOKENS.colors.semantic.warning);
    s.setProperty("--snow-dark", BRAND_TOKENS.colors.brand.darkSurface);
    s.setProperty("--snow-ink", colorPalette?.foreground?.value || BRAND_TOKENS.colors.text.primary);
    s.setProperty("--snow-ink-secondary", colorPalette?.foregroundNeutralSecondary?.value || BRAND_TOKENS.colors.text.secondary);
    s.setProperty("--snow-ink-muted", colorPalette?.foregroundNeutralTertiary?.value || BRAND_TOKENS.colors.text.muted);
    s.setProperty("--snow-card-bg", BRAND_TOKENS.colors.surfaces.card);
    s.setProperty("--snow-border", BRAND_TOKENS.colors.surfaces.border);
    s.setProperty("--snow-hover-bg", hexToRgba(primary, 0.055));
    s.setProperty("--snow-hover-border", hexToRgba(primary, 0.14));
    s.setProperty("--snow-selected-bg", hexToRgba(primary, 0.09));
    s.setProperty("--snow-selected-border", hexToRgba(primary, 0.35));
}

export function resolveHostSeriesColor(
    seriesName: string,
    index: number,
    colorPalette?: ISandboxExtendedColorPalette,
): string {
    const low = (seriesName || "").trim().toLowerCase();
    for (const rule of BRAND_TOKENS.visualDefaults.seriesColorRules) {
        if (rule.match.some((kw) => low.includes(kw.toLowerCase()))) {
            return rule.color;
        }
    }
    const palettePool = BRAND_TOKENS.colors.dataColors;
    if (palettePool.length > 0 && index < palettePool.length) {
        return palettePool[index];
    }
    const hostColor = colorPalette?.getColor(seriesName || `series-${index}`)?.value;
    if (hostColor) return hostColor;
    return palettePool.length ? palettePool[index % palettePool.length] : SNOW_COLORS.primary;
}

export function getSeriesStackRank(seriesName: string): number {
    const low = (seriesName || "").trim().toLowerCase();
    for (let i = 0; i < BRAND_TOKENS.visualDefaults.seriesColorRules.length; i++) {
        const rule = BRAND_TOKENS.visualDefaults.seriesColorRules[i];
        if (rule.match.some((kw) => low.includes(kw.toLowerCase()))) {
            return rule.stackOrder ?? i;
        }
    }
    return 100;
}

function normalizeCurrencySymbol(raw: string): string {
    if (!raw) return "";
    // Conservar espacio final si la cadena explícita ya lo trae (p. ej. "S/ ")
    const hasTrailingSpace = /\s$/.test(raw);
    const trimmed = raw.trim();
    if (!trimmed) return "";
    // Símbolos cortos de 1 carácter como $, €, £, ¥ van pegados; prefijos alfabéticos como "S/" o "US$" quedan más limpios con espacio si no lo tenían
    if (hasTrailingSpace) return `${trimmed} `;
    if (/^[A-Za-z]{2,}\.?\/?$|^[A-Za-z]+\/$/.test(trimmed)) {
        return `${trimmed} `;
    }
    return trimmed;
}

function extractCurrencyFromFormatString(colFormat: string): { hasCurrency: boolean; prefix: string; suffix: string } {
    const firstSection = (colFormat.split(";")[0] || "").trim();
    if (!firstSection) {
        return { hasCurrency: false, prefix: "", suffix: "" };
    }

    // Caso Excel/Power BI con LCID: [$S/-280A]#,##0.00 o [$$-409]#,##0.00
    const lcidMatch = firstSection.match(/\[\$([^-\]]+)(?:-[^\]]+)?\]/);
    if (lcidMatch && lcidMatch[1]) {
        return { hasCurrency: true, prefix: normalizeCurrencySymbol(lcidMatch[1]), suffix: "" };
    }

    // Limpiar etiquetas de color/condición [Red], escapes \x y comillas "..."
    const cleaned = firstSection
        .replace(/\[[^\]]+\]/g, "")
        .replace(/\\(.)/g, "$1")
        .replace(/"([^"]*)"/g, "$1");

    const firstNumIdx = cleaned.search(/[#0]/);
    if (firstNumIdx < 0) {
        return { hasCurrency: false, prefix: "", suffix: "" };
    }
    let lastNumIdx = firstNumIdx;
    for (let i = cleaned.length - 1; i >= 0; i--) {
        if (cleaned[i] === "#" || cleaned[i] === "0") {
            lastNumIdx = i;
            break;
        }
    }

    const beforeNum = cleaned.slice(0, firstNumIdx).replace(/^[+\-(\s]+/, "");
    const afterNum = cleaned.slice(lastNumIdx + 1).replace(/[)\s]+$/, "");

    const currencyCharRe = /[$€£¥₹₩]|S\/\.?|US\$|MX\$|CLP\$|COP\$|R\$|CHF|PEN|USD|EUR|BRL|ARS|MXN|COP|CLP/;
    if (currencyCharRe.test(beforeNum)) {
        return { hasCurrency: true, prefix: normalizeCurrencySymbol(beforeNum), suffix: "" };
    }
    if (currencyCharRe.test(afterNum)) {
        return { hasCurrency: true, prefix: "", suffix: ` ${afterNum.trim()}` };
    }

    return { hasCurrency: false, prefix: "", suffix: "" };
}

export function resolveColumnFormatSpec(
    colFormat?: string,
    displayName?: string,
    opts: {
        currencyMode?: string;
        customPrefix?: string;
        customSuffix?: string;
        displayUnits?: DisplayUnitsMode;
        decimals?: number;
        numberLocale?: string;
    } = {},
): ResolvedFormatSpec {
    const mode = (opts.currencyMode || BRAND_TOKENS.currency.mode || "auto") as CurrencyMode;
    const decimals = opts.decimals ?? BRAND_TOKENS.currency.defaultDecimals ?? 1;
    const numberLocale = opts.numberLocale || BRAND_TOKENS.currency.numberLocale || "en-US";
    const fmt = (colFormat || "").trim();
    const customPrefix = opts.customPrefix ?? "";
    const customSuffix = opts.customSuffix ?? "";

    if (opts.displayUnits === "percent") {
        return { kind: "percent", isPercent: true, prefix: "", suffix: "%", numberLocale, decimals };
    }

    if (fmt.includes("%") || (!fmt && (displayName || "").includes("%"))) {
        return { kind: "percent", isPercent: true, prefix: "", suffix: "%", numberLocale, decimals };
    }

    if (mode === "custom") {
        return {
            kind: "currency",
            isPercent: false,
            prefix: customPrefix || BRAND_TOKENS.currency.symbol,
            suffix: customSuffix,
            numberLocale,
            decimals,
        };
    }

    if (fmt) {
        const parsed = extractCurrencyFromFormatString(fmt);
        if (parsed.hasCurrency) {
            return {
                kind: "currency",
                isPercent: false,
                prefix: parsed.prefix,
                suffix: parsed.suffix || customSuffix,
                numberLocale,
                decimals,
            };
        }
        if (mode === "auto") {
            // Formato numérico explícito sin símbolo monetario (p. ej. "#,0" o "0")
            return {
                kind: "number",
                isPercent: false,
                prefix: "",
                suffix: customSuffix,
                numberLocale,
                decimals,
            };
        }
    }

    // Fallback cuando col.format viene vacío o mode === "brand"
    return {
        kind: "currency",
        isPercent: false,
        prefix: BRAND_TOKENS.currency.symbol,
        suffix: customSuffix,
        numberLocale,
        decimals,
    };
}

export function easeOutCubic(t: number): number {
    const clamped = Math.max(0, Math.min(1, t));
    return 1 - Math.pow(1 - clamped, 3);
}

export class RafAnimator {
    private frameId: number | null = null;

    public cancel(): void {
        if (this.frameId !== null) {
            cancelAnimationFrame(this.frameId);
            this.frameId = null;
        }
    }

    public run(durationMs: number, onTick: (easedProgress: number) => void, onDone?: () => void): void {
        this.cancel();
        if (durationMs <= 0) {
            onTick(1);
            if (onDone) onDone();
            return;
        }
        const start = performance.now();
        const step = (now: number) => {
            const raw = Math.min(1, (now - start) / durationMs);
            const eased = easeOutCubic(raw);
            onTick(eased);
            if (raw < 1) {
                this.frameId = requestAnimationFrame(step);
            } else {
                this.frameId = null;
                if (onDone) onDone();
            }
        };
        this.frameId = requestAnimationFrame(step);
    }
}

export function toNumericValue(val: unknown): number {
    if (typeof val === "number" && Number.isFinite(val)) {
        return val;
    }
    if (typeof val === "string") {
        const parsed = Number(val);
        return Number.isFinite(parsed) ? parsed : 0;
    }
    return 0;
}

export function formatMetricValue(value: number, opts: FormatValueOptions = {}): string {
    if (!Number.isFinite(value)) {
        return "—";
    }
    const prefix = opts.prefix ?? BRAND_TOKENS.currency.symbol;
    const suffix = opts.suffix ?? "";
    const units = opts.displayUnits ?? "auto";
    const decimals = Math.max(0, Math.min(4, opts.decimals ?? BRAND_TOKENS.currency.defaultDecimals ?? 1));
    const locale = opts.numberLocale || BRAND_TOKENS.currency.numberLocale || "en-US";

    if (units === "percent") {
        const pct = Math.abs(value) <= 2 ? value * 100 : value;
        return `${pct.toFixed(decimals)}%`;
    }

    const abs = Math.abs(value);
    const sign = value < 0 ? "-" : "";

    let scaled = abs;
    let unitSuffix = "";

    if (units === "millions" || (units === "auto" && abs >= 1_000_000)) {
        scaled = abs / 1_000_000;
        unitSuffix = "M";
    } else if (units === "thousands" || (units === "auto" && abs >= 1_000)) {
        scaled = abs / 1_000;
        unitSuffix = "K";
    } else {
        scaled = abs;
        unitSuffix = "";
    }

    const dec = unitSuffix === "" && Number.isInteger(Math.round(scaled * 10) / 10) && scaled >= 100
        ? 0
        : unitSuffix === "K" && scaled >= 100
            ? 0
            : decimals;

    const formattedNumber = scaled.toLocaleString(locale, {
        minimumFractionDigits: dec === 0 ? 0 : Math.min(dec, 2),
        maximumFractionDigits: dec,
    });

    return `${sign}${prefix}${formattedNumber}${unitSuffix}${suffix}`;
}

export function formatFullCurrency(
    value: number,
    prefix: string = BRAND_TOKENS.currency.symbol,
    suffix: string = "",
    locale: string = BRAND_TOKENS.currency.numberLocale || "en-US",
): string {
    if (!Number.isFinite(value)) {
        return "—";
    }
    const sign = value < 0 ? "-" : "";
    const abs = Math.abs(value);
    return `${sign}${prefix}${abs.toLocaleString(locale, { maximumFractionDigits: 2 })}${suffix}`;
}

export function formatPercentDelta(deltaRatio: number, isRatio: boolean = true): { text: string; isPositive: boolean; isNeutral: boolean } {
    if (!Number.isFinite(deltaRatio)) {
        return { text: "0.0%", isPositive: true, isNeutral: true };
    }
    const pct = isRatio && Math.abs(deltaRatio) <= 5 ? deltaRatio * 100 : deltaRatio;
    const sign = pct > 0.05 ? "+" : "";
    return {
        text: `${sign}${pct.toFixed(2).replace(/\.00$/, ".0")}%`,
        isPositive: pct >= 0,
        isNeutral: Math.abs(pct) < 0.05,
    };
}

export function clamp(value: number, min: number, max: number): number {
    if (max <= min) return (min + max) / 2;
    return Math.max(min, Math.min(max, value));
}

let cachedMeasureCtx: CanvasRenderingContext2D | null | undefined;

export function measureTextWidth(
    text: string,
    font: string = '11px "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif',
): number {
    if (!text) return 0;
    try {
        if (cachedMeasureCtx === undefined && typeof document !== "undefined") {
            const canvas = document.createElement("canvas");
            cachedMeasureCtx = canvas.getContext("2d");
        }
        if (cachedMeasureCtx) {
            cachedMeasureCtx.font = font;
            return cachedMeasureCtx.measureText(text).width;
        }
    } catch {
        // Fallback cuando no existe contexto 2D (p. ej. tests Node sin DOM)
    }
    return text.length * 6.4;
}

export function truncateToWidth(text: string, maxWidthPx: number, font?: string): string {
    const clean = (text || "").trim();
    if (!clean) return "";
    if (measureTextWidth(clean, font) <= maxWidthPx) return clean;
    const ellipsis = "…";
    let lo = 1;
    let hi = clean.length;
    let best = `${clean.slice(0, 1)}${ellipsis}`;
    while (lo <= hi) {
        const mid = Math.floor((lo + hi) / 2);
        const cand = `${clean.slice(0, mid).trimEnd()}${ellipsis}`;
        if (measureTextWidth(cand, font) <= maxWidthPx) {
            best = cand;
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    return best;
}

export function wrapLabelLines(
    label: string,
    maxWidthPx: number,
    font: string = '11px "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif',
    maxLines: number = 2,
): string[] {
    const clean = (label || "").trim();
    if (!clean) return [];
    if (measureTextWidth(clean, font) <= maxWidthPx || maxLines <= 1) {
        return [truncateToWidth(clean, maxWidthPx, font)];
    }

    const words = clean.split(/\s+/).filter(Boolean);
    if (words.length <= 1) {
        return [truncateToWidth(clean, maxWidthPx, font)];
    }

    const lines: string[] = [];
    let current = "";
    for (let i = 0; i < words.length; i++) {
        const word = words[i];
        const candidate = current ? `${current} ${word}` : word;
        if (measureTextWidth(candidate, font) <= maxWidthPx) {
            current = candidate;
            continue;
        }
        if (lines.length + 1 >= maxLines) {
            const rest = current ? `${current} ${words.slice(i).join(" ")}` : words.slice(i).join(" ");
            lines.push(truncateToWidth(rest, maxWidthPx, font));
            current = "";
            break;
        }
        if (current) {
            lines.push(current);
            current = word;
        } else {
            lines.push(truncateToWidth(word, maxWidthPx, font));
            current = "";
        }
    }
    if (current && lines.length < maxLines) {
        lines.push(truncateToWidth(current, maxWidthPx, font));
    }
    return lines;
}

export function calcDynamicLeftMargin(
    tickLabels: string[],
    minMargin: number = 46,
    maxMargin: number = 96,
    font: string = '11px "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif',
): number {
    let maxW = 0;
    for (const lbl of tickLabels) {
        const w = measureTextWidth(lbl, font);
        if (w > maxW) maxW = w;
    }
    return Math.round(clamp(maxW + 14, minMargin, maxMargin));
}

export function truncateLabel(label: string, maxChars: number): string {
    if (!label) return "";
    if (label.length <= maxChars) return label;
    return `${label.slice(0, Math.max(1, maxChars - 1))}…`;
}

export function getMonogram(text: string): string {
    const cleaned = (text || "RG").trim();
    const parts = cleaned.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
        return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return cleaned.slice(0, 2).toUpperCase();
}

export function getAvatarColors(key: string): { bg: string; fg: string } {
    let hash = 0;
    for (let i = 0; i < key.length; i++) {
        hash = ((hash << 5) - hash + key.charCodeAt(i)) | 0;
    }
    const idx = Math.abs(hash) % AVATAR_PALETTE.length;
    return AVATAR_PALETTE[idx];
}

export interface StatusStyle {
    label: string;
    bg: string;
    fg: string;
    dot: string;
}

function toneToStatusColors(tone: StatusRuleConfig["tone"]): { bg: string; fg: string; dot: string } {
    switch (tone) {
        case "positive": {
            const c = BRAND_TOKENS.colors.semantic.positive;
            return { bg: hexToRgba(c, 0.14), fg: darkenHex(c, 0.34), dot: c };
        }
        case "negative": {
            const c = BRAND_TOKENS.colors.semantic.negative;
            return { bg: hexToRgba(c, 0.13), fg: darkenHex(c, 0.22), dot: c };
        }
        case "primary": {
            const c = BRAND_TOKENS.colors.brand.primary;
            return { bg: hexToRgba(c, 0.13), fg: darkenHex(c, 0.22), dot: c };
        }
        case "secondary": {
            const c = BRAND_TOKENS.colors.brand.secondary;
            return { bg: hexToRgba(c, 0.14), fg: darkenHex(c, 0.22), dot: c };
        }
        case "muted":
            return {
                bg: "rgba(0, 0, 0, 0.06)",
                fg: BRAND_TOKENS.colors.text.secondary,
                dot: BRAND_TOKENS.colors.text.muted,
            };
        case "warning":
        default: {
            const c = BRAND_TOKENS.colors.semantic.warning;
            return { bg: hexToRgba(c, 0.14), fg: darkenHex(c, 0.28), dot: c };
        }
    }
}

export function resolveStatusStyle(rawStatus: string): StatusStyle {
    const raw = (rawStatus || "").trim();
    const normalized = raw.toLowerCase();
    if (!normalized) {
        return {
            label: "Pendiente",
            ...toneToStatusColors("muted"),
        };
    }

    for (const rule of BRAND_TOKENS.statusRules) {
        if (rule.match.some((kw) => normalized.includes(kw.toLowerCase()))) {
            const label = rule.label
                ? rule.label
                : rule.tone === "negative" && raw.length > 22
                    ? "Sin Ejecución"
                    : raw;
            return {
                label,
                ...toneToStatusColors(rule.tone),
            };
        }
    }

    return {
        label: raw,
        ...toneToStatusColors("warning"),
    };
}

export function clearElement(node: Element): void {
    while (node.firstChild) {
        node.removeChild(node.firstChild);
    }
}

export function el<K extends keyof HTMLElementTagNameMap>(
    tag: K,
    className?: string,
    text?: string,
): HTMLElementTagNameMap[K] {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

export function svgEl<K extends keyof SVGElementTagNameMap>(
    tag: K,
    attrs: Record<string, string | number> = {},
): SVGElementTagNameMap[K] {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) {
        node.setAttribute(k, String(v));
    }
    return node;
}

export function bindPowerBiTooltip(
    target: Element,
    tooltipService: ITooltipService,
    getItems: () => VisualTooltipDataItem[],
    getIdentity?: () => ISelectionId | undefined,
): void {
    const show = (evt: MouseEvent) => {
        const items = getItems();
        if (!items.length) return;
        const identity = getIdentity ? getIdentity() : undefined;
        tooltipService.show({
            coordinates: [evt.clientX, evt.clientY],
            isTouchEvent: false,
            dataItems: items,
            identities: identity ? [identity] : [],
        });
    };
    const move = (evt: MouseEvent) => {
        const items = getItems();
        if (!items.length) return;
        const identity = getIdentity ? getIdentity() : undefined;
        tooltipService.move({
            coordinates: [evt.clientX, evt.clientY],
            isTouchEvent: false,
            dataItems: items,
            identities: identity ? [identity] : [],
        });
    };
    const hide = () => {
        tooltipService.hide({ immediately: true, isTouchEvent: false });
    };
    target.addEventListener("mouseenter", show as EventListener);
    target.addEventListener("mousemove", move as EventListener);
    target.addEventListener("mouseleave", hide as EventListener);
}

export function handleSelectionClick(
    evt: MouseEvent,
    selectionManager: ISelectionManager,
    selectionId: ISelectionId | undefined,
): void {
    evt.stopPropagation();
    if (!selectionId) {
        selectionManager.clear();
        return;
    }
    selectionManager.select(selectionId, evt.ctrlKey || evt.metaKey);
}
