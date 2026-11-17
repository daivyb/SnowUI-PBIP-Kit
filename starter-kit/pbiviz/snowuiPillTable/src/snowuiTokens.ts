// Archivo generado por apply_brand.py desde brand-config.json
export interface SeriesColorRule {
    match: string[];
    color: string;
    stackOrder?: number;
}

export interface StatusRuleConfig {
    match: string[];
    tone: "positive" | "negative" | "warning" | "primary" | "secondary" | "muted";
    label?: string;
}

export interface BrandTokensConfig {
    currency: { code: string; symbol: string; numberLocale: string; defaultDecimals: number; mode: "auto" | "brand" | "custom" };
    style: { cornerRadius: number; kpiSurfaceMode: "gradient" | "solid" | "light-bordered"; sidebarMode: "light" | "tinted" | "dark"; fontFamily: string; density: "comfortable" | "compact" };
    colors: {
        brand: { primary: string; secondary: string; tertiary: string; darkSurface: string };
        semantic: { positive: string; warning: string; negative: string; alertText: string };
        surfaces: { canvas: string; card: string; border: string; pillBg: string };
        text: { primary: string; secondary: string; muted: string; onDark: string };
        dataColors: string[];
    };
    visualDefaults: {
        splineLineColor: string;
        barDefaultAccent: string;
        defaultTableTitle: string;
        defaultEmptyMessage: string;
        seriesColorRules: SeriesColorRule[];
        columnFriendlyNames: Record<string, string>;
    };
    statusRules: StatusRuleConfig[];
}

export const BRAND_TOKENS: BrandTokensConfig = {
    "currency": {
        "code": "USD",
        "symbol": "$",
        "numberLocale": "en-US",
        "defaultDecimals": 1,
        "mode": "auto"
    },
    "style": {
        "cornerRadius": 18,
        "kpiSurfaceMode": "gradient",
        "sidebarMode": "light",
        "fontFamily": "Segoe UI",
        "density": "comfortable"
    },
    "colors": {
        "brand": {
            "primary": "#007AFF",
            "secondary": "#AF52DE",
            "tertiary": "#00C7BE",
            "darkSurface": "#1C1C1E"
        },
        "semantic": {
            "positive": "#34C759",
            "warning": "#FF9500",
            "negative": "#FF3B30",
            "alertText": "#DC2626"
        },
        "surfaces": {
            "canvas": "#F5F5F6",
            "card": "#FFFFFF",
            "border": "#E5E7EB",
            "pillBg": "#F4F5F7"
        },
        "text": {
            "primary": "#111827",
            "secondary": "#6B7280",
            "muted": "#9CA3AF",
            "onDark": "#FFFFFF"
        },
        "dataColors": [
            "#007AFF",
            "#AF52DE",
            "#34C759",
            "#FF3B30",
            "#00C7BE",
            "#FF9500",
            "#5AC8FA",
            "#5856D6"
        ]
    },
    "visualDefaults": {
        "splineLineColor": "#AF52DE",
        "barDefaultAccent": "#007AFF",
        "defaultTableTitle": "Proyectos",
        "defaultEmptyMessage": "Ajusta los filtros superiores para visualizar registros.",
        "seriesColorRules": [
            {
                "match": [
                    "técnico",
                    "tecnico"
                ],
                "color": "#FF3B30",
                "stackOrder": 2
            },
            {
                "match": [
                    "sin clasificar",
                    "no registrado"
                ],
                "color": "#C7C7CC",
                "stackOrder": 1
            },
            {
                "match": [
                    "administrativo"
                ],
                "color": "#1C1C1E",
                "stackOrder": 0
            }
        ],
        "columnFriendlyNames": {
            "AlertaSinMovimiento": "Alerta",
            "TipoIntervencion": "Tipo Intervención",
            "EstadoPlanOperativoAnual": "Estado POA",
            "UnidadEjecutora": "Unidad Ejecutora",
            "AreaTematica": "Área Temática"
        }
    },
    "statusRules": [
        {
            "match": [
                "no registrado",
                "sin clasificar"
            ],
            "tone": "muted"
        },
        {
            "match": [
                "sí, con ejecución",
                "si, con ejecucion",
                "al día",
                "complet"
            ],
            "tone": "positive",
            "label": "Activo · POA"
        },
        {
            "match": [
                "no, sin ejecución",
                "sin movimiento",
                "alerta",
                "sí"
            ],
            "tone": "negative"
        },
        {
            "match": [
                "técnico",
                "tecnico"
            ],
            "tone": "primary"
        },
        {
            "match": [
                "administrativo"
            ],
            "tone": "secondary"
        }
    ]
};
