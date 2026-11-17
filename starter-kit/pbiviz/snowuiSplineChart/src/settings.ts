"use strict";

import { formattingSettings } from "powerbi-visuals-utils-formattingmodel";
import { BRAND_TOKENS } from "./snowuiTokens";

import FormattingSettingsCard = formattingSettings.SimpleCard;
import FormattingSettingsSlice = formattingSettings.Slice;
import FormattingSettingsModel = formattingSettings.Model;

export class ChartStyleSettings extends FormattingSettingsCard {
    lineColor = new formattingSettings.ColorPicker({
        name: "lineColor",
        displayName: "Color de curva",
        value: { value: BRAND_TOKENS.visualDefaults.splineLineColor },
    });

    defaultChartMode = new formattingSettings.AutoDropdown({
        name: "defaultChartMode",
        displayName: "Modo inicial",
        value: "area",
    });

    defaultGranularity = new formattingSettings.AutoDropdown({
        name: "defaultGranularity",
        displayName: "Eje inicial",
        value: "primary",
    });

    primaryAxisLabel = new formattingSettings.TextInput({
        name: "primaryAxisLabel",
        displayName: "Etiqueta eje principal",
        placeholder: "Mensual",
        value: "Mensual",
    });

    secondaryAxisLabel = new formattingSettings.TextInput({
        name: "secondaryAxisLabel",
        displayName: "Etiqueta eje alterno",
        placeholder: "Anual",
        value: "Anual",
    });

    currencyMode = new formattingSettings.AutoDropdown({
        name: "currencyMode",
        displayName: "Modo de moneda",
        value: BRAND_TOKENS.currency.mode,
    });

    valuePrefix = new formattingSettings.TextInput({
        name: "valuePrefix",
        displayName: "Prefijo personalizado",
        placeholder: BRAND_TOKENS.currency.symbol,
        value: "",
    });

    animationMs = new formattingSettings.NumUpDown({
        name: "animationMs",
        displayName: "Duración morphing (ms)",
        value: 620,
    });

    name: string = "chartStyle";
    displayName: string = "Estilo Spline";
    slices: Array<FormattingSettingsSlice> = [
        this.lineColor,
        this.defaultChartMode,
        this.defaultGranularity,
        this.primaryAxisLabel,
        this.secondaryAxisLabel,
        this.currencyMode,
        this.valuePrefix,
        this.animationMs,
    ];
}

export class VisualFormattingSettingsModel extends FormattingSettingsModel {
    chartStyle = new ChartStyleSettings();
    cards = [this.chartStyle];
}
