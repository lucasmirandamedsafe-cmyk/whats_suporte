// Port literal de dashboard/colors.py - mesma paleta, mesma ordem fixa (nunca
// ciclar/reatribuir CATEGORICAL dinamicamente). Sem variante dark: o app
// Streamlit atual tambem e' light-only.

export const CATEGORICAL = [
  "#2a78d6",
  "#008300",
  "#e87ba4",
  "#eda100",
  "#1baf7a",
  "#eb6834",
  "#4a3aa7",
  "#e34948",
] as const;

export const STATUS = {
  positivo: "#0ca30c",
  neutro: "#898781",
  negativo: "#d03b3b",
} as const;

export const INK = {
  primary: "#0b0b0b",
  secondary: "#52514e",
  muted: "#898781",
  grid: "#e1e0d9",
} as const;

export const SURFACE = "#fcfcfb";

export const FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', sans-serif";
