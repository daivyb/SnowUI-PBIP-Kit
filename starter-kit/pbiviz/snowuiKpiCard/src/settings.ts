"use strict";

import { formattingSettings } from "powerbi-visuals-utils-formattingmodel";
import { BRAND_TOKENS } from "./snowuiTokens";

import FormattingSettingsCard = formattingSettings.SimpleCard;
import FormattingSettingsSlice = formattingSettings.Slice;
import FormattingSettingsModel = formattingSettings.Model;

export class CardStyleSettings extends FormattingSettingsCard {
    themeVariant = new formattingSettings.AutoDropdown({
        name: "themeVariant",
        displayName: "Variante de Color",
        value: "blue",
    });

    surfaceMode = new formattingSettings.AutoDropdown({
        name: "surfaceMode",
        displayName: "Acabado de superficie",
        value: "auto",
    });

    titleOverride = new formattingSettings.TextInput({
        name: "titleOverride",
        displayName: "Título personalizado",
        placeholder: "Automático desde medida",
        value: "",
    });

    subtitleText = new formattingSettings.TextInput({
        name: "subtitleText",
        displayName: "Subtítulo delta",
        placeholder: "Ej: vs año ant.",
        value: "",
    });

    cornerRadius = new formattingSettings.NumUpDown({
        name: "cornerRadius",
        displayName: "Radio de borde (px)",
        value: BRAND_TOKENS.style.cornerRadius,
    });

    animationMs = new formattingSettings.NumUpDown({
        name: "animationMs",
        displayName: "Duración transición (ms)",
        value: 650,
    });

    name: string = "cardStyle";
    displayName: string = "Estilo de Tarjeta";
    slices: Array<FormattingSettingsSlice> = [
        this.themeVariant,
        this.surfaceMode,
        this.titleOverride,
        this.subtitleText,
        this.cornerRadius,
        this.animationMs,
    ];
}

export class NumberFormatSettings extends FormattingSettingsCard {
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

    valueSuffix = new formattingSettings.TextInput({
        name: "valueSuffix",
        displayName: "Sufijo",
        placeholder: "",
        value: "",
    });

    displayUnits = new formattingSettings.AutoDropdown({
        name: "displayUnits",
        displayName: "Unidades",
        value: "auto",
    });

    decimals = new formattingSettings.NumUpDown({
        name: "decimals",
        displayName: "Decimales",
        value: BRAND_TOKENS.currency.defaultDecimals,
    });

    deltaIsRatio = new formattingSettings.ToggleSwitch({
        name: "deltaIsRatio",
        displayName: "Delta como ratio",
        value: true,
    });

    deltaSuffix = new formattingSettings.TextInput({
        name: "deltaSuffix",
        displayName: "Sufijo de delta",
        placeholder: "",
        value: "",
    });

    name: string = "numberFormat";
    displayName: string = "Formato Numérico";
    slices: Array<FormattingSettingsSlice> = [
        this.currencyMode,
        this.valuePrefix,
        this.valueSuffix,
        this.displayUnits,
        this.decimals,
        this.deltaIsRatio,
        this.deltaSuffix,
    ];
}

export class VisualFormattingSettingsModel extends FormattingSettingsModel {
    cardStyle = new CardStyleSettings();
    numberFormat = new NumberFormatSettings();
    cards = [this.cardStyle, this.numberFormat];
}
