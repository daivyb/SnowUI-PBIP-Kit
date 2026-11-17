"use strict";

import { formattingSettings } from "powerbi-visuals-utils-formattingmodel";
import { BRAND_TOKENS } from "./snowuiTokens";

import FormattingSettingsCard = formattingSettings.SimpleCard;
import FormattingSettingsSlice = formattingSettings.Slice;
import FormattingSettingsModel = formattingSettings.Model;

export class TableStyleSettings extends FormattingSettingsCard {
    titleOverride = new formattingSettings.TextInput({
        name: "titleOverride",
        displayName: "Título de tarjeta",
        placeholder: BRAND_TOKENS.visualDefaults.defaultTableTitle || "Registros",
        value: "",
    });

    maxRows = new formattingSettings.NumUpDown({
        name: "maxRows",
        displayName: "Máximo de filas visibles",
        value: 15,
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

    showAvatars = new formattingSettings.ToggleSwitch({
        name: "showAvatars",
        displayName: "Mostrar avatar circular",
        value: true,
    });

    staggerMs = new formattingSettings.NumUpDown({
        name: "staggerMs",
        displayName: "Escalonado transición (ms)",
        value: 28,
    });

    name: string = "tableStyle";
    displayName: string = "Estilo de Tabla";
    slices: Array<FormattingSettingsSlice> = [
        this.titleOverride,
        this.maxRows,
        this.currencyMode,
        this.valuePrefix,
        this.showAvatars,
        this.staggerMs,
    ];
}

export class VisualFormattingSettingsModel extends FormattingSettingsModel {
    tableStyle = new TableStyleSettings();
    cards = [this.tableStyle];
}
