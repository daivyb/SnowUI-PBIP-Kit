"use strict";

import { formattingSettings } from "powerbi-visuals-utils-formattingmodel";
import { BRAND_TOKENS } from "./snowuiTokens";

import FormattingSettingsCard = formattingSettings.SimpleCard;
import FormattingSettingsSlice = formattingSettings.Slice;
import FormattingSettingsModel = formattingSettings.Model;

export class BarStyleSettings extends FormattingSettingsCard {
    displayMode = new formattingSettings.AutoDropdown({
        name: "displayMode",
        displayName: "Modo Visual",
        value: "pill",
    });

    titleOverride = new formattingSettings.TextInput({
        name: "titleOverride",
        displayName: "Título de tarjeta",
        placeholder: "Automático desde campos",
        value: "",
    });

    accentColor = new formattingSettings.ColorPicker({
        name: "accentColor",
        displayName: "Color acento / título",
        value: { value: BRAND_TOKENS.visualDefaults.barDefaultAccent },
    });

    topN = new formattingSettings.NumUpDown({
        name: "topN",
        displayName: "Top N categorías (0 = todas)",
        value: 6,
    });

    sortOrder = new formattingSettings.AutoDropdown({
        name: "sortOrder",
        displayName: "Orden",
        value: "desc",
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

    showFloatingCallout = new formattingSettings.ToggleSwitch({
        name: "showFloatingCallout",
        displayName: "Callout flotante oscuro",
        value: true,
    });

    animationMs = new formattingSettings.NumUpDown({
        name: "animationMs",
        displayName: "Duración transición (ms)",
        value: 620,
    });

    name: string = "barStyle";
    displayName: string = "Estilo de Barras";
    slices: Array<FormattingSettingsSlice> = [
        this.displayMode,
        this.titleOverride,
        this.accentColor,
        this.topN,
        this.sortOrder,
        this.currencyMode,
        this.valuePrefix,
        this.showFloatingCallout,
        this.animationMs,
    ];
}

export class VisualFormattingSettingsModel extends FormattingSettingsModel {
    barStyle = new BarStyleSettings();
    cards = [this.barStyle];
}
