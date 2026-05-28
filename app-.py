# ─── IMPORTS ──────────────────────────────────────────────────────────────────
import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Yamada Engenharia | Agrometeorologia MS",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── PALETA ───────────────────────────────────────────────────────────────────
VERDE_ESCURO  = "#1B4D2E"
VERDE_MEDIO   = "#3DA63A"
PRETO         = "#1A1A1A"
CINZA_CLARO   = "#F4F7F4"
BG_DARK       = "#0d1117"
BG_PANEL      = "#111827"

# ─── CSS ──────────────────────────────────────────────────────────────────────
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;900&family=Source+Sans+3:wght@300;400;600&display=swap');

html, body, [class*="css"] {{
  font-family:'Source Sans 3',sans-serif;
  background-color:{CINZA_CLARO}; color:{PRETO};
}}
.yamada-header {{
  background:linear-gradient(135deg,{VERDE_ESCURO} 0%,{VERDE_MEDIO} 100%);
  border-radius:12px; padding:22px 32px; margin-bottom:18px;
  box-shadow:0 4px 20px rgba(27,77,46,0.3);
}}
.yamada-header h1 {{
  font-family:'Montserrat',sans-serif; font-weight:900; font-size:1.75rem;
  color:white; margin:0; letter-spacing:-0.5px;
}}
.yamada-header p {{ color:rgba(255,255,255,0.82); margin:4px 0 0 0; font-size:0.88rem; }}
.info-card {{
  background:white; border-left:4px solid {VERDE_MEDIO}; border-radius:8px;
  padding:14px 18px; margin-bottom:10px; box-shadow:0 2px 8px rgba(0,0,0,0.06);
}}
.info-card h4 {{
  font-family:'Montserrat',sans-serif; font-weight:700; color:{VERDE_ESCURO};
  margin:0 0 4px 0; font-size:0.88rem;
}}
.info-card p {{ margin:0; font-size:0.82rem; color:#333; line-height:1.45; }}
.alert-verde    {{background:#e8f5e9;border-left:4px solid #43a047;border-radius:8px;padding:12px 16px;margin:6px 0;}}
.alert-amarelo  {{background:#fff8e1;border-left:4px solid #fbc02d;border-radius:8px;padding:12px 16px;margin:6px 0;}}
.alert-vermelho {{background:#ffebee;border-left:4px solid #e53935;border-radius:8px;padding:12px 16px;margin:6px 0;}}
.alert-azul     {{background:#e3f2fd;border-left:4px solid #1565c0;border-radius:8px;padding:12px 16px;margin:6px 0;}}
.secao-titulo {{
  font-family:'Montserrat',sans-serif; font-weight:800; font-size:1.05rem;
  color:{VERDE_ESCURO}; border-bottom:2px solid {VERDE_MEDIO};
  padding-bottom:5px; margin:22px 0 12px 0;
}}
.stButton>button {{
  background:linear-gradient(135deg,{VERDE_ESCURO},{VERDE_MEDIO}) !important;
  color:white !important; font-family:'Montserrat',sans-serif !important;
  font-weight:700 !important; border:none !important; border-radius:10px !important;
  padding:11px 28px !important; width:100% !important;
  box-shadow:0 4px 14px rgba(27,77,46,0.35) !important;
  transition:all 0.2s ease !important;
}}
.stButton>button:hover {{
  transform:translateY(-1px) !important;
  box-shadow:0 6px 20px rgba(27,77,46,0.5) !important;
}}
section[data-testid="stSidebar"] {{
  background-color:#1a2e1c !important; border-right:1px solid #2d5a30;
}}
section[data-testid="stSidebar"] * {{ color:#e8f5e9 !important; }}
section[data-testid="stSidebar"] label {{
  font-family:'Montserrat',sans-serif !important; font-weight:600 !important;
  font-size:0.82rem !important; color:#a5d6a7 !important;
}}
section[data-testid="stSidebar"] .stSelectbox>div>div {{
  background-color:#2d5a30 !important; color:white !important;
  border-color:#3DA63A !important;
}}
section[data-testid="stSidebar"] hr {{ border-color:#2d5a30 !important; }}
div[data-testid="metric-container"] {{
  background:white; border-radius:10px; padding:13px;
  box-shadow:0 2px 10px rgba(0,0,0,0.07); border-top:3px solid {VERDE_MEDIO};
}}
hr {{ border-color:#ddeedd; margin:16px 0; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ─── E-MAIL ───────────────────────────────────────────────────────────────────
try:
    _EMAIL_REM  = st.secrets["email"]["remetente"]
    _EMAIL_PASS = st.secrets["email"]["senha_app"]
    _dest_raw   = st.secrets["email"]["destinatario"]
    _EMAIL_DEST = ([e.strip() for e in _dest_raw.split(",") if e.strip()]
                   if isinstance(_dest_raw, str) else list(_dest_raw))
    _EMAIL_OK   = True
except Exception:
    _EMAIL_REM = _EMAIL_PASS = ""; _EMAIL_DEST = []; _EMAIL_OK = False

# ─── FAZENDAS ────────────────────────────────────────────────────────────────
FAZENDAS = {
    "Fazenda Santa Fé (Maracaju — Soja/Milho)":       {"lat": -21.614, "lon": -55.168, "area_ha": 3200, "cultura": "Soja/Milho"},
    "Fazenda Água Limpa (Chapadão do Sul — Soja)":    {"lat": -18.791, "lon": -52.627, "area_ha": 4800, "cultura": "Soja"},
    "Fazenda Planalto (Dourados — Soja/Trigo)":       {"lat": -22.221, "lon": -54.805, "area_ha": 2100, "cultura": "Soja/Trigo"},
    "Fazenda Campo Verde (Rio Brilhante — Cana/Soja)":{"lat": -21.802, "lon": -54.544, "area_ha": 5600, "cultura": "Cana/Soja"},
    "Fazenda Cerrado Vivo (Costa Rica — Soja)":       {"lat": -18.544, "lon": -53.127, "area_ha": 3900, "cultura": "Soja"},
    "Fazenda Pantanal (Aquidauana — Pecuária)":       {"lat": -20.470, "lon": -55.786, "area_ha": 8200, "cultura": "Pastagem/Pecuária"},
    "Fazenda Norte MS (Sonora — Soja/Milho)":         {"lat": -17.558, "lon": -54.761, "area_ha": 6100, "cultura": "Soja/Milho"},
    "Fazenda Fronteira (Ponta Porã — Soja)":          {"lat": -22.536, "lon": -55.725, "area_ha": 2800, "cultura": "Soja"},
    "Fazenda Leste (Nova Andradina — Eucalipto)":     {"lat": -22.233, "lon": -53.344, "area_ha": 1500, "cultura": "Eucalipto/Pastagem"},
    "Fazenda Três Lagoas (Celulose/Pastagem)":        {"lat": -20.752, "lon": -51.678, "area_ha": 7400, "cultura": "Celulose/Pastagem"},
}

MODELOS = {
    "best_match":    "Best Match (Ensemble GFS+ICON — recomendado)",
    "gfs_seamless":  "GFS (NOAA — precipitação Centro-Oeste)",
    "icon_seamless": "ICON (DWD — convecção subtropical)",
}

VARS_HORARIAS = [
    "temperature_2m", "precipitation", "relativehumidity_2m",
    "windspeed_10m", "windgusts_10m", "dewpoint_2m",
    "shortwave_radiation", "et0_fao_evapotranspiration",
    "weathercode", "cape", "surface_pressure", "cloudcover",
    "soil_moisture_0_to_1cm",
]

LABELS = {
    "temperature_2m":              "Temperatura (°C)",
    "precipitation":               "Precipitação (mm/h)",
    "relativehumidity_2m":         "Umidade Relativa (%)",
    "windspeed_10m":               "Velocidade do Vento (km/h)",
    "windgusts_10m":               "Rajada de Vento (km/h)",
    "dewpoint_2m":                 "Ponto de Orvalho (°C)",
    "shortwave_radiation":          "Radiação Solar (W/m²)",
    "et0_fao_evapotranspiration":   "ETo Penman-Monteith (mm/h)",
    "weathercode":                 "Código de Tempo WMO",
    "cape":                        "CAPE (J/kg)",
    "surface_pressure":            "Pressão (hPa)",
    "cloudcover":                  "Cobertura de Nuvens (%)",
    "soil_moisture_0_to_1cm":      "Umidade do Solo 0–1cm (m³/m³)",
}

HOVER_FMT = {
    "temperature_2m":             "%{x|%d/%m %Hh}<br><b>Temperatura:</b> %{y:.1f} °C<extra></extra>",
    "precipitation":              "%{x|%d/%m %Hh}<br><b>Precipitação:</b> %{y:.2f} mm/h<extra></extra>",
    "relativehumidity_2m":        "%{x|%d/%m %Hh}<br><b>Umidade Relativa:</b> %{y:.0f} %<extra></extra>",
    "windspeed_10m":              "%{x|%d/%m %Hh}<br><b>Vento:</b> %{y:.1f} km/h<extra></extra>",
    "windgusts_10m":              "%{x|%d/%m %Hh}<br><b>Rajada:</b> %{y:.1f} km/h<extra></extra>",
    "dewpoint_2m":                "%{x|%d/%m %Hh}<br><b>Orvalho:</b> %{y:.1f} °C<extra></extra>",
    "shortwave_radiation":         "%{x|%d/%m %Hh}<br><b>Radiação:</b> %{y:.1f} W/m²<extra></extra>",
    "et0_fao_evapotranspiration":  "%{x|%d/%m %Hh}<br><b>ETo:</b> %{y:.3f} mm/h<extra></extra>",
    "cape":                       "%{x|%d/%m %Hh}<br><b>CAPE:</b> %{y:.0f} J/kg<extra></extra>",
    "surface_pressure":           "%{x|%d/%m %Hh}<br><b>Pressão:</b> %{y:.1f} hPa<extra></extra>",
    "cloudcover":                 "%{x|%d/%m %Hh}<br><b>Nebulosidade:</b> %{y:.0f} %<extra></extra>",
    "soil_moisture_0_to_1cm":     "%{x|%d/%m %Hh}<br><b>Umidade Solo:</b> %{y:.4f} m³/m³<extra></extra>",
}

CORES = {
    "temperature_2m":             "#f97316",
    "precipitation":              "#3b82f6",
    "relativehumidity_2m":        "#06b6d4",
    "windspeed_10m":              "#a78bfa",
    "windgusts_10m":              "#c084fc",
    "dewpoint_2m":                "#34d399",
    "shortwave_radiation":         "#fbbf24",
    "et0_fao_evapotranspiration":  "#22c55e",
    "cape":                       "#f43f5e",
    "surface_pressure":           "#a3e635",
    "cloudcover":                 "#cbd5e1",
    "soil_moisture_0_to_1cm":     "#4ade80",
}

WCODE = {
    0:"☀️ Céu limpo", 1:"🌤 Poucas nuvens", 2:"⛅ Parcial",
    3:"☁️ Nublado", 45:"🌫 Névoa", 51:"🌦 Chuvisco leve",
    61:"🌧 Chuva fraca", 63:"🌧 Chuva moderada", 65:"🌧 Chuva forte",
    80:"🌦 Pancadas", 81:"⛈ Pancadas fortes", 82:"⛈ Pancadas severas",
    95:"⛈ Tempestade", 96:"⛈ Tempestade + granizo", 99:"⛈ Granizo severo",
}

# ─── PARÂMETROS EMBRAPA/MAPA ──────────────────────────────────────────────────
DEF_VENTO_MAX   = 10.0
DEF_TEMP_MAX    = 30.0
DEF_UR_MIN      = 55.0
DEF_PRECIP_MAX  = 0.0
IRR_UR_BAIXA    = 60.0
IRR_UR_CRITICA  = 40.0
IRR_TEMP_ALTA   = 32.0
IRR_ETO_ALTA    = 0.25


# ─── HELPER: HEX → RGB string ────────────────────────────────────────────────
def _rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"


def _plotly_layout(fig: go.Figure, title: str = "", height: int = 340) -> go.Figure:
    """Aplica tema escuro padrão Yamada a qualquer figura Plotly."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG_DARK,
        plot_bgcolor=BG_PANEL,
        title=dict(text=title, font=dict(color="white", size=11, family="Montserrat"), x=0.01),
        xaxis=dict(gridcolor="#1f2937", showgrid=True, zeroline=False,
                   tickfont=dict(size=8, color="#9ca3af")),
        yaxis=dict(gridcolor="#1f2937", showgrid=True, zeroline=False,
                   tickfont=dict(size=8, color="#9ca3af")),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01,
            xanchor="right", x=1,
            font=dict(size=8, color="white"),
            bgcolor="rgba(17,24,39,0.8)", bordercolor="#374151",
        ),
        height=height,
        margin=dict(l=55, r=20, t=55, b=40),
        hovermode="x unified",
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# COLETA DE DADOS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def buscar_previsao(lat: float, lon: float, modelo: str, dias: int = 7) -> dict:
    vars_str = ",".join(VARS_HORARIAS)
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat:.4f}&longitude={lon:.4f}"
        f"&hourly={vars_str}"
        f"&timezone=America%2FCampo_Grande"
        f"&forecast_days={dias}"
        f"&models={modelo}"
    )
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_erro": str(e)}


@st.cache_data(ttl=1800, show_spinner=False)
def buscar_ensemble(lat: float, lon: float, dias: int = 7) -> dict:
    out = {}
    vars_ic = "temperature_2m,precipitation,relativehumidity_2m,windspeed_10m"
    for mod in ["gfs_seamless", "icon_seamless", "best_match"]:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat:.4f}&longitude={lon:.4f}"
            f"&hourly={vars_ic}"
            f"&timezone=America%2FCampo_Grande"
            f"&forecast_days={dias}&models={mod}"
        )
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            out[mod] = r.json()
        except Exception:
            pass
    return out


# ─────────────────────────────────────────────────────────────────────────────
# CONVERSÃO PARA DATAFRAME
# ─────────────────────────────────────────────────────────────────────────────

def json_para_df(dados: dict) -> pd.DataFrame:
    if not dados or "hourly" not in dados or "_erro" in dados:
        return pd.DataFrame()
    h  = dados["hourly"]
    df = pd.DataFrame({"datetime": pd.to_datetime(h["time"])})
    for v in VARS_HORARIAS:
        if v in h:
            df[v] = pd.to_numeric(h[v], errors="coerce")
    return df.set_index("datetime")


def ic_entre_modelos(ensemble: dict, var: str) -> pd.DataFrame:
    series = []
    for mod, dados in ensemble.items():
        if "hourly" in dados and var in dados["hourly"]:
            s = pd.Series(
                pd.to_numeric(dados["hourly"][var], errors="coerce"),
                index=pd.to_datetime(dados["hourly"]["time"]),
                name=mod,
            )
            series.append(s)
    if len(series) < 2:
        return pd.DataFrame()
    df_e = pd.concat(series, axis=1)
    med  = df_e.mean(axis=1)
    std  = df_e.std(axis=1)
    return pd.DataFrame({
        "media": med, "std": std,
        "ic68_low": med - std, "ic68_high": med + std,
        "ic95_low": med - 2*std, "ic95_high": med + 2*std,
        "cv_pct": (std / (med.abs() + 1e-6) * 100).round(1),
    })


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISES EMBRAPA
# ─────────────────────────────────────────────────────────────────────────────

def calcular_janela_defensivos(df: pd.DataFrame) -> pd.DataFrame:
    df24 = df.head(24).copy()
    out  = pd.DataFrame(index=df24.index)
    out["vento_ok"] = (df24.get("windspeed_10m",        pd.Series(5,  index=df24.index)) < DEF_VENTO_MAX).astype(int)
    out["temp_ok"]  = (df24.get("temperature_2m",       pd.Series(25, index=df24.index)) < DEF_TEMP_MAX).astype(int)
    out["ur_ok"]    = (df24.get("relativehumidity_2m",  pd.Series(65, index=df24.index)) >= DEF_UR_MIN).astype(int)
    out["chuva_ok"] = (df24.get("precipitation",        pd.Series(0,  index=df24.index)) <= DEF_PRECIP_MAX).astype(int)
    out["n_ok"]     = out[["vento_ok","temp_ok","ur_ok","chuva_ok"]].sum(axis=1)
    out["status"]   = out["n_ok"].map(lambda x: "aberta" if x==4 else ("parcial" if x==3 else "bloqueada"))

    def _motivo(row):
        m = []
        idx = row.name
        if not row["vento_ok"]:
            v = df24["windspeed_10m"].get(idx, 0) if "windspeed_10m" in df24.columns else 0
            m.append(f"Vento {v:.0f} km/h ≥ {DEF_VENTO_MAX:.0f}")
        if not row["temp_ok"]:
            v = df24["temperature_2m"].get(idx, 0) if "temperature_2m" in df24.columns else 0
            m.append(f"Temp {v:.0f}°C ≥ {DEF_TEMP_MAX:.0f}")
        if not row["ur_ok"]:
            v = df24["relativehumidity_2m"].get(idx, 0) if "relativehumidity_2m" in df24.columns else 0
            m.append(f"UR {v:.0f}% < {DEF_UR_MIN:.0f}")
        if not row["chuva_ok"]:
            v = df24["precipitation"].get(idx, 0) if "precipitation" in df24.columns else 0
            m.append(f"Chuva {v:.1f} mm")
        return " · ".join(m) if m else "✅ Todos os critérios atendidos"

    out["motivo"] = out.apply(_motivo, axis=1)
    return out


def calcular_janela_irrigacao(df: pd.DataFrame) -> pd.DataFrame:
    df48 = df.head(48).copy()
    out  = pd.DataFrame(index=df48.index)
    ur   = df48.get("relativehumidity_2m",        pd.Series(65,   index=df48.index))
    tmp  = df48.get("temperature_2m",             pd.Series(27,   index=df48.index))
    eto  = df48.get("et0_fao_evapotranspiration", pd.Series(0.15, index=df48.index))
    out["ur_nivel"]  = ur.apply(lambda v:  0 if v >= IRR_UR_BAIXA else (1 if v >= IRR_UR_CRITICA else 2))
    out["tmp_nivel"] = tmp.apply(lambda v: 0 if v < IRR_TEMP_ALTA else (1 if v < 38 else 2))
    out["eto_nivel"] = eto.apply(lambda v: 0 if v < IRR_ETO_ALTA else (1 if v < 0.40 else 2))
    out["nivel_max"] = out[["ur_nivel","tmp_nivel","eto_nivel"]].max(axis=1)
    out["status_irr"] = out["nivel_max"].map({0:"sem_necessidade", 1:"atencao", 2:"irrigar"})

    def _motivo_irr(row):
        m = []
        if row["ur_nivel"]  == 2: m.append(f"UR crítica (<{IRR_UR_CRITICA:.0f}%)")
        elif row["ur_nivel"]== 1: m.append(f"UR baixa (<{IRR_UR_BAIXA:.0f}%)")
        if row["tmp_nivel"] >= 1: m.append(f"Calor (>{IRR_TEMP_ALTA:.0f}°C)")
        if row["eto_nivel"] >= 1: m.append(f"ETo elevada (>{IRR_ETO_ALTA:.2f} mm/h)")
        return " · ".join(m) if m else "Solo adequadamente abastecido"

    out["motivo_irr"] = out.apply(_motivo_irr, axis=1)
    return out


def resumo_janelas(df_def: pd.DataFrame, df_irr: pd.DataFrame) -> dict:
    n_ab = int((df_def["status"] == "aberta").sum())
    n_pa = int((df_def["status"] == "parcial").sum())
    n_bl = int((df_def["status"] == "bloqueada").sum())
    bloco = cur = 0
    bloco_inicio = bloco_fim = None
    cur_inicio = None
    for t, row in df_def.iterrows():
        if row["status"] == "aberta":
            if cur == 0: cur_inicio = t
            cur += 1
            if cur > bloco:
                bloco = cur; bloco_inicio = cur_inicio; bloco_fim = t
        else:
            cur = 0
    n_irr = int((df_irr["status_irr"] == "irrigar").sum())
    n_atn = int((df_irr["status_irr"] == "atencao").sum())
    return {
        "def_abertas": n_ab, "def_parciais": n_pa, "def_bloqueadas": n_bl,
        "def_bloco_h": bloco, "def_bloco_ini": bloco_inicio, "def_bloco_fim": bloco_fim,
        "irr_urgente": n_irr, "irr_atencao": n_atn,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GRÁFICOS PLOTLY — INTERATIVOS
# ─────────────────────────────────────────────────────────────────────────────

# Limiares por variável
LIMIARES = {
    "temperature_2m": [
        (5,             "#93c5fd", "Geada (5°C)"),
        (DEF_TEMP_MAX,  "#fbbf24", f"Lim. defensivos ({DEF_TEMP_MAX:.0f}°C)"),
        (IRR_TEMP_ALTA, "#f97316", f"Estresse hídrico ({IRR_TEMP_ALTA:.0f}°C)"),
        (38,            "#ef4444", "Calor extremo (38°C)"),
    ],
    "relativehumidity_2m": [
        (DEF_UR_MIN,     "#fbbf24", f"Lim. defensivos ({DEF_UR_MIN:.0f}%)"),
        (IRR_UR_BAIXA,   "#fb923c", f"Irrig. atenção ({IRR_UR_BAIXA:.0f}%)"),
        (IRR_UR_CRITICA, "#ef4444", f"Irrig. urgente ({IRR_UR_CRITICA:.0f}%)"),
        (80,             "#c084fc", "Risco ferrugem (80%)"),
    ],
    "windspeed_10m": [
        (DEF_VENTO_MAX, "#fbbf24", f"Lim. defensivos ({DEF_VENTO_MAX:.0f} km/h)"),
        (40,            "#ef4444", "Dano potencial (40 km/h)"),
    ],
    "precipitation": [
        (10, "#fbbf24", "Atenção (10 mm/h)"),
        (25, "#ef4444", "Intensidade forte (25 mm/h)"),
    ],
    "cape": [
        (500,  "#fbbf24", "CAPE moderado (500 J/kg)"),
        (1500, "#f97316", "CAPE alto (1500 J/kg)"),
        (2500, "#ef4444", "CAPE extremo (2500 J/kg)"),
    ],
    "et0_fao_evapotranspiration": [
        (IRR_ETO_ALTA, "#fb923c", f"ETo atenção ({IRR_ETO_ALTA:.2f} mm/h)"),
        (0.40,         "#ef4444", "ETo elevada (0.40 mm/h)"),
    ],
}


def grafico_variavel(df: pd.DataFrame, var: str,
                     df_ic: pd.DataFrame = None,
                     titulo_extra: str = "") -> go.Figure:
    cor   = CORES.get(var, "#60a5fa")
    label = LABELS.get(var, var)
    title = f"{label}{titulo_extra}"
    fig   = go.Figure()

    if var not in df.columns or df.empty:
        fig.add_annotation(text="Dados não disponíveis", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False,
                           font=dict(color="white", size=14))
        return _plotly_layout(fig, title)

    serie  = df[var].dropna()
    htmpl  = HOVER_FMT.get(var, "%{x|%d/%m %Hh}<br>%{y}<extra></extra>")

    # ── Faixas de incerteza (IC) ──
    if df_ic is not None and not df_ic.empty:
        ic_re = df_ic.reindex(serie.index, method="nearest")
        fig.add_trace(go.Scatter(
            x=ic_re.index, y=ic_re["ic95_high"],
            fill=None, mode="lines", line=dict(color=cor, width=0),
            showlegend=False, hoverinfo="skip", name="IC95 sup",
        ))
        fig.add_trace(go.Scatter(
            x=ic_re.index, y=ic_re["ic95_low"],
            fill="tonexty", mode="lines", line=dict(color=cor, width=0),
            fillcolor=f"rgba({_rgb(cor)},0.10)", name="IC 95%",
            hovertemplate="%{x|%d/%m %Hh}<br>IC 95%: %{y:.2f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=ic_re.index, y=ic_re["ic68_high"],
            fill=None, mode="lines", line=dict(color=cor, width=0),
            showlegend=False, hoverinfo="skip", name="IC68 sup",
        ))
        fig.add_trace(go.Scatter(
            x=ic_re.index, y=ic_re["ic68_low"],
            fill="tonexty", mode="lines", line=dict(color=cor, width=0),
            fillcolor=f"rgba({_rgb(cor)},0.20)", name="IC 68%",
            hovertemplate="%{x|%d/%m %Hh}<br>IC 68%: %{y:.2f}<extra></extra>",
        ))

    # ── Série principal ──
    if var == "precipitation":
        fig.add_trace(go.Bar(
            x=serie.index, y=serie.values, name=label,
            marker_color=cor, opacity=0.85,
            hovertemplate=htmpl,
        ))
    else:
        fig.add_trace(go.Scatter(
            x=serie.index, y=serie.values, mode="lines",
            name=label, line=dict(color=cor, width=2.2),
            fill="tozeroy", fillcolor=f"rgba({_rgb(cor)},0.08)",
            hovertemplate=htmpl,
        ))

    # ── Limiares ──
    for val, cor_l, lbl in LIMIARES.get(var, []):
        fig.add_hline(
            y=val, line_dash="dash", line_color=cor_l, line_width=1.1,
            annotation_text=lbl,
            annotation_position="top right",
            annotation_font=dict(color=cor_l, size=8),
        )

    fig.update_layout(
        yaxis_title=label,
        yaxis_titlefont=dict(color="#9ca3af", size=9),
    )
    fig.update_xaxes(tickformat="%d/%m\n%Hh", dtick=6 * 3600000)
    return _plotly_layout(fig, title, height=340)


def grafico_spread(ensemble: dict, var: str) -> go.Figure | None:
    series = {}
    nomes  = {"gfs_seamless": "GFS", "icon_seamless": "ICON", "best_match": "Best Match"}
    cores_mod = {"GFS": "#60a5fa", "ICON": "#f97316", "Best Match": "#34d399"}

    for mod, dados in ensemble.items():
        if "hourly" in dados and var in dados["hourly"]:
            nome = nomes.get(mod, mod)
            s = pd.Series(
                pd.to_numeric(dados["hourly"][var], errors="coerce"),
                index=pd.to_datetime(dados["hourly"]["time"]),
                name=nome,
            )
            series[nome] = s

    if len(series) < 2:
        return None

    df_e = pd.concat(series.values(), axis=1)
    med  = df_e.mean(axis=1)
    std  = df_e.std(axis=1)
    cv   = (std / (med.abs() + 1e-6) * 100)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.70, 0.30],
        vertical_spacing=0.06,
    )

    # IC 95 e 68
    fig.add_trace(go.Scatter(x=med.index, y=(med + 2*std).values, fill=None,
                             mode="lines", line=dict(color="#60a5fa", width=0),
                             showlegend=False, hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=med.index, y=(med - 2*std).values,
                             fill="tonexty", mode="lines", line=dict(color="#60a5fa", width=0),
                             fillcolor="rgba(96,165,250,0.09)", name="IC 95%",
                             hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=med.index, y=(med + std).values, fill=None,
                             mode="lines", line=dict(color="#60a5fa", width=0),
                             showlegend=False, hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=med.index, y=(med - std).values,
                             fill="tonexty", mode="lines", line=dict(color="#60a5fa", width=0),
                             fillcolor="rgba(96,165,250,0.18)", name="IC 68%",
                             hoverinfo="skip"), row=1, col=1)

    # Modelos individuais
    for nome, s in series.items():
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, mode="lines", name=nome,
            line=dict(color=cores_mod.get(nome, "#aaa"), width=1.4, dash="dot"),
            opacity=0.88,
            hovertemplate=f"%{{x|%d/%m %Hh}}<br>{nome}: %{{y:.2f}}<extra></extra>",
        ), row=1, col=1)

    # Média
    fig.add_trace(go.Scatter(
        x=med.index, y=med.values, mode="lines", name="Média modelos",
        line=dict(color="white", width=2.4),
        hovertemplate="%{x|%d/%m %Hh}<br>Média: %{y:.2f}<extra></extra>",
    ), row=1, col=1)

    # CV (incerteza)
    cv_colors = ["#22c55e" if v < 10 else ("#fbbf24" if v < 25 else "#ef4444") for v in cv.values]
    fig.add_trace(go.Bar(
        x=cv.index, y=cv.values, name="CV %",
        marker_color=cv_colors, opacity=0.88,
        hovertemplate="%{x|%d/%m %Hh}<br>Incerteza CV: %{y:.1f}%<extra></extra>",
    ), row=2, col=1)
    fig.add_hline(y=10, line_dash="dash", line_color="#22c55e", line_width=0.8,
                  annotation_text="Alta confiança (<10%)",
                  annotation_font=dict(color="#22c55e", size=7), row=2, col=1)
    fig.add_hline(y=25, line_dash="dash", line_color="#ef4444", line_width=0.8,
                  annotation_text="Baixa confiança (>25%)",
                  annotation_font=dict(color="#ef4444", size=7), row=2, col=1)

    label = LABELS.get(var, var)
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG_DARK, plot_bgcolor=BG_PANEL,
        title=dict(text=f"Spread entre modelos — {label}",
                   font=dict(color="white", size=11, family="Montserrat"), x=0.01),
        height=460,
        margin=dict(l=55, r=20, t=55, b=40),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1,
                    font=dict(size=8, color="white"),
                    bgcolor="rgba(17,24,39,0.8)", bordercolor="#374151"),
    )
    fig.update_xaxes(gridcolor="#1f2937", tickfont=dict(size=8, color="#9ca3af"))
    fig.update_yaxes(gridcolor="#1f2937", tickfont=dict(size=8, color="#9ca3af"))
    fig.update_yaxes(title_text=label, title_font=dict(color="#9ca3af", size=9), row=1, col=1)
    fig.update_yaxes(title_text="CV % (incerteza)", title_font=dict(color="#9ca3af", size=9), row=2, col=1)
    return fig


def grafico_matriz_defensivos(df_def: pd.DataFrame) -> go.Figure | None:
    n = min(24, len(df_def))
    if n == 0:
        return None

    col_labels = ["Vento<br><10km/h", "Temp<br><30°C", "UR<br>≥55%", "Sem<br>Chuva", "JANELA<br>GERAL"]
    horas = [df_def.index[i].strftime("%d/%m %Hh") for i in range(n)]
    M = np.zeros((n, len(col_labels)))
    text_m = [["" for _ in range(len(col_labels))] for _ in range(n)]
    hover_m = [["" for _ in range(len(col_labels))] for _ in range(n)]

    for i, (idx, row) in enumerate(df_def.head(n).iterrows()):
        M[i, 0] = row["vento_ok"]
        M[i, 1] = row["temp_ok"]
        M[i, 2] = row["ur_ok"]
        M[i, 3] = row["chuva_ok"]
        M[i, 4] = 1 if row["status"] == "aberta" else (0.5 if row["status"] == "parcial" else 0)
        for j in range(len(col_labels)):
            v = M[i, j]
            text_m[i][j] = "✓" if v == 1 else ("○" if v == 0.5 else "✗")
        status_label = {"aberta": "🟢 Aberta", "parcial": "🟡 Parcial", "bloqueada": "🔴 Bloqueada"}.get(row["status"], row["status"])
        hover_m[i][4] = f"{horas[i]}<br>Status: {status_label}<br>{row['motivo']}"
        for j in range(4):
            crit_nome = ["Vento", "Temperatura", "Umidade Relativa", "Precipitação"][j]
            estado = "✓ OK" if M[i, j] == 1 else "✗ Fora do limite"
            hover_m[i][j] = f"{horas[i]}<br>{crit_nome}: {estado}<br>{row['motivo']}"

    colorscale = [
        [0.0, "#ef4444"], [0.29, "#ef4444"],
        [0.30, "#fbbf24"], [0.69, "#fbbf24"],
        [0.70, "#22c55e"], [1.00, "#22c55e"],
    ]

    fig = go.Figure(go.Heatmap(
        z=M, x=col_labels, y=horas,
        text=text_m, texttemplate="%{text}",
        textfont=dict(size=11, color="black", family="Montserrat"),
        colorscale=colorscale, zmin=0, zmax=1, showscale=False,
        customdata=hover_m,
        hovertemplate="%{customdata}<extra></extra>",
        xgap=2, ygap=2,
    ))

    fig.update_layout(
        title=dict(text="Janela de Aplicação de Defensivos — Próximas 24h",
                   font=dict(color="white", size=11, family="Montserrat"), x=0.01),
        paper_bgcolor=BG_DARK, plot_bgcolor=BG_DARK,
        font=dict(color="white"),
        height=max(380, n * 22 + 120),
        xaxis=dict(side="top", tickfont=dict(size=9, color="white"), showgrid=False),
        yaxis=dict(tickfont=dict(size=8, color="#9ca3af"), autorange="reversed", showgrid=False),
        margin=dict(l=90, r=20, t=90, b=20),
    )
    return fig


def grafico_matriz_irrigacao(df_irr: pd.DataFrame) -> go.Figure | None:
    n = min(48, len(df_irr))
    if n == 0:
        return None

    col_labels = ["UR<br>(%)", "Temperatura<br>(°C)", "ETo<br>(mm/h)", "NECESSIDADE<br>IRRIGAÇÃO"]
    horas = [df_irr.index[i].strftime("%d/%m %Hh") for i in range(n)]
    M = np.zeros((n, 4))
    text_m = [["" for _ in range(4)] for _ in range(n)]
    hover_m = [["" for _ in range(4)] for _ in range(n)]
    TEXTOS = {2: "✓", 1: "!", 0: "✗"}
    STATUS_LABEL = {2: "🟢 Sem necessidade", 1: "🟡 Atenção", 0: "🔴 Irrigar urgente"}

    for i, (idx, row) in enumerate(df_irr.head(n).iterrows()):
        M[i, 0] = 2 - row["ur_nivel"]
        M[i, 1] = 2 - row["tmp_nivel"]
        M[i, 2] = 2 - row["eto_nivel"]
        M[i, 3] = 2 - row["nivel_max"]
        for j in range(4):
            v = int(round(M[i, j]))
            text_m[i][j] = TEXTOS.get(v, "?")
            crit_nome = ["Umidade Relativa", "Temperatura", "ETo", "Status Geral"][j]
            status_str = STATUS_LABEL.get(v, "—")
            hover_m[i][j] = f"{horas[i]}<br>{crit_nome}: {status_str}<br>{row['motivo_irr']}"

    colorscale = [
        [0.0, "#ef4444"], [0.29, "#ef4444"],
        [0.30, "#fbbf24"], [0.69, "#fbbf24"],
        [0.70, "#22c55e"], [1.00, "#22c55e"],
    ]

    fig = go.Figure(go.Heatmap(
        z=M, x=col_labels, y=horas,
        text=text_m, texttemplate="%{text}",
        textfont=dict(size=11, color="black", family="Montserrat"),
        colorscale=colorscale, zmin=0, zmax=2, showscale=False,
        customdata=hover_m,
        hovertemplate="%{customdata}<extra></extra>",
        xgap=2, ygap=2,
    ))

    fig.update_layout(
        title=dict(text="Necessidade de Irrigação — Próximas 48h (parâmetros EMBRAPA)",
                   font=dict(color="white", size=11, family="Montserrat"), x=0.01),
        paper_bgcolor=BG_DARK, plot_bgcolor=BG_DARK,
        font=dict(color="white"),
        height=max(420, n * 14 + 120),
        xaxis=dict(side="top", tickfont=dict(size=9, color="white"), showgrid=False),
        yaxis=dict(tickfont=dict(size=7, color="#9ca3af"), autorange="reversed", showgrid=False),
        margin=dict(l=100, r=20, t=90, b=20),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES DE DADOS / CSV
# ─────────────────────────────────────────────────────────────────────────────

def df_para_exibir(df: pd.DataFrame, max_rows: int = 168) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cols = {k: v for k, v in LABELS.items() if k in df.columns}
    out  = df[list(cols.keys())].head(max_rows).copy()
    out.columns = [cols[c] for c in out.columns]
    out.index   = out.index.strftime("%d/%m %Hh")
    out.index.name = "Data/Hora"
    wc_col = LABELS.get("weathercode")
    if wc_col in out.columns:
        out["Condição"] = out[wc_col].apply(
            lambda x: WCODE.get(int(x), f"Cód {x}") if pd.notna(x) else "—")
        out.drop(columns=[wc_col], inplace=True)
    return out.round(2)


def csv_btn(df: pd.DataFrame, label: str, filename: str, key: str):
    """Renderiza um botão de download CSV para o DataFrame fornecido."""
    if df.empty:
        return
    csv_bytes = df.to_csv().encode("utf-8")
    st.download_button(
        label=f"⬇️ Baixar CSV — {label}",
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        key=key,
    )


# ─────────────────────────────────────────────────────────────────────────────
# E-MAIL
# ─────────────────────────────────────────────────────────────────────────────

def enviar_email(assunto: str, corpo_html: str, destinatarios: list) -> tuple[bool, str]:
    if not _EMAIL_OK:
        return False, "Credenciais de e-mail não configuradas em st.secrets."
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"]    = _EMAIL_REM
        msg["To"]      = ", ".join(destinatarios)
        msg.attach(MIMEText(corpo_html, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(_EMAIL_REM, _EMAIL_PASS)
            s.sendmail(_EMAIL_REM, destinatarios, msg.as_string())
        return True, f"E-mail enviado para: {', '.join(destinatarios)}"
    except Exception as e:
        return False, str(e)


def gerar_relatorio_html(fazenda: str, info: dict, df: pd.DataFrame,
                          res: dict, agora: str) -> str:
    def _v(col, fmt="{:.1f}"):
        if df.empty or col not in df.columns: return "—"
        val = df[col].dropna()
        return fmt.format(val.iloc[0]) if not val.empty else "—"

    temp_atual   = _v("temperature_2m")
    ur_atual     = _v("relativehumidity_2m", "{:.0f}")
    vento_atual  = _v("windspeed_10m", "{:.0f}")
    precip_24h   = (f"{df['precipitation'].head(24).sum():.1f}"
                    if not df.empty and "precipitation" in df.columns else "—")
    wc_s = df["weathercode"].dropna() if "weathercode" in df.columns else pd.Series()
    wc   = int(wc_s.iloc[0]) if not wc_s.empty else 0
    condicao = WCODE.get(wc, "—")

    bloco_str = "—"
    if res.get("def_bloco_ini") and res.get("def_bloco_fim"):
        bloco_str = (f"{res['def_bloco_ini'].strftime('%Hh %d/%m')} → "
                     f"{res['def_bloco_fim'].strftime('%Hh %d/%m')} "
                     f"({res['def_bloco_h']}h consecutivas)")

    irr_status = ("🔴 Irrigação urgente" if res.get("irr_urgente", 0) > 0 else
                  ("🟡 Atenção à irrigação" if res.get("irr_atencao", 0) > 0 else "🟢 Sem necessidade"))

    return f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f7f4;padding:24px;">
    <div style="max-width:680px;margin:auto;background:white;border-radius:12px;overflow:hidden;
                box-shadow:0 4px 20px rgba(0,0,0,0.1);">
      <div style="background:linear-gradient(135deg,#1B4D2E,#3DA63A);padding:24px 32px;">
        <h1 style="color:white;margin:0;font-size:1.4rem;">🌿 Yamada Engenharia</h1>
        <p style="color:rgba(255,255,255,0.8);margin:4px 0 0 0;font-size:0.85rem;">
          Boletim Agrometeorólogico — {agora}</p>
      </div>
      <div style="padding:24px 32px;">
        <h2 style="color:#1B4D2E;font-size:1.1rem;border-bottom:2px solid #3DA63A;padding-bottom:6px;">
          📍 {fazenda}</h2>
        <p style="color:#555;font-size:0.85rem;">Cultura: {info['cultura']} | Área: {info['area_ha']:,} ha
          | Lat {info['lat']:.3f}° Lon {info['lon']:.3f}°</p>
        <h3 style="color:#1B4D2E;margin-top:20px;">🌡️ Condições Atuais</h3>
        <table style="width:100%;border-collapse:collapse;font-size:0.88rem;">
          <tr style="background:#f0f7f0;">
            <td style="padding:8px 12px;"><b>Temperatura</b></td><td>{temp_atual} °C</td>
            <td style="padding:8px 12px;"><b>Umidade Relativa</b></td><td>{ur_atual} %</td>
          </tr>
          <tr>
            <td style="padding:8px 12px;"><b>Vento</b></td><td>{vento_atual} km/h</td>
            <td style="padding:8px 12px;"><b>Precipitação 24h</b></td><td>{precip_24h} mm</td>
          </tr>
          <tr style="background:#f0f7f0;">
            <td style="padding:8px 12px;" colspan="4"><b>Condição:</b> {condicao}</td>
          </tr>
        </table>
        <h3 style="color:#1B4D2E;margin-top:20px;">🌿 Defensivos (24h) — MAPA/EMBRAPA</h3>
        <table style="width:100%;border-collapse:collapse;font-size:0.88rem;">
          <tr style="background:#f0f7f0;">
            <td style="padding:8px 12px;"><b>Horas abertas</b></td>
            <td style="color:#16a34a;font-weight:bold;">{res.get('def_abertas',0)}h</td>
            <td style="padding:8px 12px;"><b>Horas parciais</b></td>
            <td style="color:#d97706;font-weight:bold;">{res.get('def_parciais',0)}h</td>
          </tr>
          <tr>
            <td style="padding:8px 12px;" colspan="2"><b>Melhor janela contínua</b></td>
            <td style="padding:8px 12px;" colspan="2">{bloco_str}</td>
          </tr>
        </table>
        <h3 style="color:#1B4D2E;margin-top:20px;">💧 Irrigação (48h) — EMBRAPA</h3>
        <p style="font-size:0.9rem;">{irr_status} —
          {res.get('irr_urgente',0)} horas críticas · {res.get('irr_atencao',0)} horas de atenção</p>
        <hr style="border-color:#ddd;margin:20px 0;">
        <p style="font-size:0.75rem;color:#999;">
          Fonte: Open-Meteo (GFS+ICON) · Parâmetros EMBRAPA/MAPA Portaria 371/2020<br>
          Yamada Engenharia Agronômica — Mato Grosso do Sul</p>
      </div>
    </div></body></html>
    """


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:12px 0 8px 0;'>
      <span style='font-size:2rem;'>🌿</span><br>
      <span style='font-family:Montserrat,sans-serif;font-weight:900;font-size:1rem;
                   color:#a5d6a7;letter-spacing:1px;'>YAMADA</span><br>
      <span style='font-size:0.7rem;color:#81c784;'>ENGENHARIA AGRONÔMICA</span>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")

    nome_fazenda = st.selectbox("🏡 Fazenda", list(FAZENDAS.keys()), index=0)
    info_faz     = FAZENDAS[nome_fazenda]
    modelo_key   = st.selectbox("🔭 Modelo Meteorológico", list(MODELOS.keys()),
                                 format_func=lambda k: MODELOS[k], index=0)
    dias_prev    = st.slider("📅 Dias de previsão", 3, 7, 7)

    st.markdown("---")
    st.markdown("<div class='secao-titulo' style='color:#a5d6a7;border-color:#3DA63A;'>🔧 Variáveis extras</div>",
                unsafe_allow_html=True)
    VARS_EXTRAS = {
        "cape":                      "⚡ CAPE (tempestades)",
        "shortwave_radiation":        "☀️ Radiação Solar",
        "et0_fao_evapotranspiration": "💧 ETo Penman-Monteith",
        "soil_moisture_0_to_1cm":    "🌱 Umidade do Solo",
        "surface_pressure":          "🔵 Pressão Superficial",
        "cloudcover":                "☁️ Cobertura de Nuvens",
    }
    vars_selecionadas = []
    for v, lbl in VARS_EXTRAS.items():
        if st.checkbox(lbl, value=(v in ["cape", "et0_fao_evapotranspiration"]), key=f"chk_{v}"):
            vars_selecionadas.append(v)

    st.markdown("---")
    st.markdown(f"""
    <div class='info-card' style='background:#1a3d1c;border-color:#3DA63A;'>
      <h4 style='color:#a5d6a7;'>📍 Localização</h4>
      <p style='color:#e8f5e9;'>Lat: {info_faz['lat']:.3f}°<br>
      Lon: {info_faz['lon']:.3f}°<br>
      Área: {info_faz['area_ha']:,} ha<br>
      Cultura: {info_faz['cultura']}</p>
    </div>""", unsafe_allow_html=True)

    mostrar_spread = st.checkbox("📊 Comparar modelos (spread)", value=False)

    if st.button("🔄 Atualizar dados"):
        st.cache_data.clear()
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
faz_slug  = nome_fazenda[:30].replace(" ", "_")

st.markdown(f"""
<div class="yamada-header">
  <h1>🌿 Yamada Engenharia — Agrometeorologia MS</h1>
  <p>Previsão Open-Meteo (GFS + ICON) · Parâmetros EMBRAPA/MAPA · Atualizado {agora_str}
     · Gráficos interativos — use o mouse para zoom, pan e hover</p>
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CARREGAMENTO DE DADOS
# ─────────────────────────────────────────────────────────────────────────────

with st.spinner("⏳ Buscando previsão Open-Meteo…"):
    dados_raw = buscar_previsao(info_faz["lat"], info_faz["lon"], modelo_key, dias_prev)
    df_main   = json_para_df(dados_raw)

if "_erro" in dados_raw:
    st.error(f"❌ Erro na API Open-Meteo: {dados_raw['_erro']}")
    st.stop()
if df_main.empty:
    st.error("❌ Dados não disponíveis. Verifique a conexão e tente novamente.")
    st.stop()

ensemble_data: dict = {}
df_ic_temp = df_ic_precip = df_ic_ur = df_ic_vento = pd.DataFrame()

if mostrar_spread:
    with st.spinner("⏳ Buscando ensemble de modelos…"):
        ensemble_data = buscar_ensemble(info_faz["lat"], info_faz["lon"], dias_prev)
    df_ic_temp   = ic_entre_modelos(ensemble_data, "temperature_2m")
    df_ic_precip = ic_entre_modelos(ensemble_data, "precipitation")
    df_ic_ur     = ic_entre_modelos(ensemble_data, "relativehumidity_2m")
    df_ic_vento  = ic_entre_modelos(ensemble_data, "windspeed_10m")

df_def = calcular_janela_defensivos(df_main)
df_irr = calcular_janela_irrigacao(df_main)
res    = resumo_janelas(df_def, df_irr)

wc_s       = df_main["weathercode"].dropna() if "weathercode" in df_main.columns else pd.Series()
wc_atual   = int(wc_s.iloc[0]) if not wc_s.empty else 0
temp_agora = df_main["temperature_2m"].dropna().iloc[0]   if "temperature_2m"      in df_main.columns else float("nan")
ur_agora   = df_main["relativehumidity_2m"].dropna().iloc[0] if "relativehumidity_2m" in df_main.columns else float("nan")
vento_agora= df_main["windspeed_10m"].dropna().iloc[0]    if "windspeed_10m"        in df_main.columns else float("nan")
precip_24h = df_main["precipitation"].head(24).sum()      if "precipitation"        in df_main.columns else 0.0


# ─── MÉTRICAS ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🌡️ Temperatura",       f"{temp_agora:.1f} °C")
c2.metric("💧 Umidade Relativa",  f"{ur_agora:.0f} %")
c3.metric("🌬️ Vento",             f"{vento_agora:.0f} km/h")
c4.metric("🌧️ Precip. 24h",       f"{precip_24h:.1f} mm")
c5.metric("🌤️ Condição",          WCODE.get(wc_atual, f"Cód {wc_atual}"))
st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# ABAS
# ─────────────────────────────────────────────────────────────────────────────

tabs = st.tabs([
    "⭐ Síntese",
    "🌧️ Precipitação",
    "🌡️ Temperatura",
    "💧 Umidade",
    "🌬️ Vento",
    "📄 Relatório",
])


# ══════════════════════════════════════════════════════════════════════════════
# ABA 0 — SÍNTESE
# ══════════════════════════════════════════════════════════════════════════════

with tabs[0]:
    st.markdown("<div class='secao-titulo'>📋 Síntese Operacional</div>", unsafe_allow_html=True)

    col_a, col_b, col_c, col_d = st.columns(4)
    pct_ab = res["def_abertas"] / 24 * 100
    cls_d  = "alert-verde" if res["def_abertas"] >= 6 else ("alert-amarelo" if res["def_abertas"] >= 2 else "alert-vermelho")
    icn_d  = "🟢" if res["def_abertas"] >= 6 else ("🟡" if res["def_abertas"] >= 2 else "🔴")

    col_a.markdown(f"""
    <div class='{cls_d}'>
      <b>{icn_d} Defensivos — Abertas</b><br>
      <span style='font-size:1.6rem;font-weight:900;'>{res['def_abertas']}h</span>
      <span style='font-size:0.8rem;'> / 24h ({pct_ab:.0f}%)</span>
    </div>""", unsafe_allow_html=True)
    col_b.markdown(f"""
    <div class='alert-amarelo'>
      <b>🟡 Defensivos — Parciais</b><br>
      <span style='font-size:1.6rem;font-weight:900;'>{res['def_parciais']}h</span>
      <span style='font-size:0.8rem;'> / 24h</span>
    </div>""", unsafe_allow_html=True)

    bloco_txt = (f"{res['def_bloco_ini'].strftime('%Hh')} → {res['def_bloco_fim'].strftime('%Hh')} ({res['def_bloco_h']}h)"
                 if res["def_bloco_ini"] and res["def_bloco_h"] > 0 else "Sem janela contínua")
    col_c.markdown(f"""
    <div class='alert-azul'>
      <b>📅 Melhor janela contínua</b><br>
      <span style='font-size:0.95rem;font-weight:700;'>{bloco_txt}</span>
    </div>""", unsafe_allow_html=True)

    cls_i  = "alert-vermelho" if res["irr_urgente"] > 0 else ("alert-amarelo" if res["irr_atencao"] > 0 else "alert-verde")
    icn_i  = "🔴" if res["irr_urgente"] > 0 else ("🟡" if res["irr_atencao"] > 0 else "🟢")
    irr_txt= f"Irrigar urgente: {res['irr_urgente']}h" if res["irr_urgente"] > 0 else (
             f"Atenção: {res['irr_atencao']}h" if res["irr_atencao"] > 0 else "Sem necessidade hídrica")
    col_d.markdown(f"""
    <div class='{cls_i}'>
      <b>{icn_i} Irrigação (48h)</b><br>
      <span style='font-size:0.95rem;font-weight:700;'>{irr_txt}</span>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    col_m1, col_m2 = st.columns(2)

    with col_m1:
        st.markdown("<div class='secao-titulo'>🌿 Janela de Defensivos — 24h</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class='info-card'>
          <h4>Critérios MAPA Portaria 371/2020 + EMBRAPA Soja</h4>
          <p>Vento &lt; 10 km/h · Temp &lt; 30°C · UR ≥ 55% · Sem precipitação
             <br><small>💡 Passe o mouse sobre as células para ver detalhes de cada hora</small></p>
        </div>""", unsafe_allow_html=True)
        fig_def = grafico_matriz_defensivos(df_def)
        if fig_def:
            st.plotly_chart(fig_def, use_container_width=True)

        # CSV da janela de defensivos
        df_def_export = df_def.copy()
        df_def_export.index = df_def_export.index.strftime("%d/%m %Hh")
        df_def_export.index.name = "Data/Hora"
        csv_btn(df_def_export, "Janela Defensivos 24h",
                f"defensivos_{faz_slug}_{agora_str[:10]}.csv", "csv_def")

    with col_m2:
        st.markdown("<div class='secao-titulo'>💧 Necessidade de Irrigação — 48h</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class='info-card'>
          <h4>Critérios EMBRAPA Cerrados — Gomes (2014)</h4>
          <p>UR, Temperatura e ETo Penman-Monteith classificados em 3 níveis de demanda hídrica
             <br><small>💡 Passe o mouse sobre as células para ver o motivo de cada status</small></p>
        </div>""", unsafe_allow_html=True)
        fig_irr = grafico_matriz_irrigacao(df_irr)
        if fig_irr:
            st.plotly_chart(fig_irr, use_container_width=True)

        # CSV da irrigação
        df_irr_export = df_irr.copy()
        df_irr_export.index = df_irr_export.index.strftime("%d/%m %Hh")
        df_irr_export.index.name = "Data/Hora"
        csv_btn(df_irr_export, "Necessidade Irrigação 48h",
                f"irrigacao_{faz_slug}_{agora_str[:10]}.csv", "csv_irr")

    if vars_selecionadas:
        st.markdown("---")
        st.markdown("<div class='secao-titulo'>📊 Variáveis Complementares</div>", unsafe_allow_html=True)
        for var in vars_selecionadas:
            st.plotly_chart(grafico_variavel(df_main, var), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ABA 1 — PRECIPITAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

with tabs[1]:
    st.markdown("<div class='secao-titulo'>🌧️ Precipitação</div>", unsafe_allow_html=True)

    if "precipitation" in df_main.columns:
        precip_s = df_main["precipitation"].dropna()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total 24h",    f"{precip_s.head(24).sum():.1f} mm")
        c2.metric("Total 48h",    f"{precip_s.head(48).sum():.1f} mm")
        c3.metric("Total 7 dias", f"{precip_s.sum():.1f} mm")
        c4.metric("Máx horário",  f"{precip_s.max():.1f} mm/h")

    st.plotly_chart(grafico_variavel(df_main, "precipitation",
                    df_ic_precip if mostrar_spread else None),
                    use_container_width=True)

    if mostrar_spread and ensemble_data:
        fig_sp = grafico_spread(ensemble_data, "precipitation")
        if fig_sp:
            st.plotly_chart(fig_sp, use_container_width=True)

    if "precipitation" in df_main.columns:
        st.markdown("<div class='secao-titulo'>📅 Acumulado Diário</div>", unsafe_allow_html=True)
        diario = df_main["precipitation"].resample("D").sum().reset_index()
        diario.columns = ["Data", "Precipitação (mm)"]
        diario["Data"] = diario["Data"].dt.strftime("%d/%m/%Y")
        diario["Precipitação (mm)"] = diario["Precipitação (mm)"].round(1)
        st.dataframe(diario, use_container_width=True, hide_index=True)

    if "cape" in df_main.columns:
        st.markdown("<div class='secao-titulo'>⚡ CAPE — Energia Convectiva Disponível</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class='info-card'>
          <h4>Referência: CAPE como proxy de tempestades</h4>
          <p>CAPE &lt; 500 J/kg: baixo risco · 500–1500: moderado · 1500–2500: alto · &gt;2500: extremo</p>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(grafico_variavel(df_main, "cape"), use_container_width=True)

    # ── CSV da aba ──
    st.markdown("---")
    cols_precip = [c for c in ["precipitation", "cape", "weathercode"] if c in df_main.columns]
    if cols_precip:
        df_p_exp = df_main[cols_precip].copy()
        df_p_exp.index = df_p_exp.index.strftime("%d/%m %Hh")
        df_p_exp.columns = [LABELS.get(c, c) for c in cols_precip]
        csv_btn(df_p_exp, "Precipitação & CAPE",
                f"precipitacao_{faz_slug}_{agora_str[:10]}.csv", "csv_precip")


# ══════════════════════════════════════════════════════════════════════════════
# ABA 2 — TEMPERATURA
# ══════════════════════════════════════════════════════════════════════════════

with tabs[2]:
    st.markdown("<div class='secao-titulo'>🌡️ Temperatura</div>", unsafe_allow_html=True)

    if "temperature_2m" in df_main.columns:
        ts = df_main["temperature_2m"].dropna()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Atual",      f"{ts.iloc[0]:.1f} °C")
        c2.metric("Máxima 7d",  f"{ts.max():.1f} °C")
        c3.metric("Mínima 7d",  f"{ts.min():.1f} °C")
        c4.metric("Média 7d",   f"{ts.mean():.1f} °C")

    st.plotly_chart(grafico_variavel(df_main, "temperature_2m",
                    df_ic_temp if mostrar_spread else None),
                    use_container_width=True)

    if mostrar_spread and ensemble_data:
        fig_st = grafico_spread(ensemble_data, "temperature_2m")
        if fig_st:
            st.plotly_chart(fig_st, use_container_width=True)

    if "dewpoint_2m" in df_main.columns:
        st.markdown("<div class='secao-titulo'>🌫️ Ponto de Orvalho</div>", unsafe_allow_html=True)
        st.plotly_chart(grafico_variavel(df_main, "dewpoint_2m"), use_container_width=True)

    if "shortwave_radiation" in df_main.columns:
        st.markdown("<div class='secao-titulo'>☀️ Radiação Solar de Onda Curta</div>", unsafe_allow_html=True)
        st.plotly_chart(grafico_variavel(df_main, "shortwave_radiation"), use_container_width=True)

    # ── CSV da aba ──
    st.markdown("---")
    cols_temp = [c for c in ["temperature_2m", "dewpoint_2m", "shortwave_radiation"] if c in df_main.columns]
    if cols_temp:
        df_t_exp = df_main[cols_temp].copy()
        df_t_exp.index = df_t_exp.index.strftime("%d/%m %Hh")
        df_t_exp.columns = [LABELS.get(c, c) for c in cols_temp]
        csv_btn(df_t_exp, "Temperatura & Radiação",
                f"temperatura_{faz_slug}_{agora_str[:10]}.csv", "csv_temp")


# ══════════════════════════════════════════════════════════════════════════════
# ABA 3 — UMIDADE RELATIVA
# ══════════════════════════════════════════════════════════════════════════════

with tabs[3]:
    st.markdown("<div class='secao-titulo'>💧 Umidade Relativa</div>", unsafe_allow_html=True)

    if "relativehumidity_2m" in df_main.columns:
        ur_s = df_main["relativehumidity_2m"].dropna()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Atual",      f"{ur_s.iloc[0]:.0f} %")
        c2.metric("Mínima 7d",  f"{ur_s.min():.0f} %")
        c3.metric("Máxima 7d",  f"{ur_s.max():.0f} %")
        c4.metric(f"Horas < {IRR_UR_BAIXA:.0f}%", f"{int((ur_s < IRR_UR_BAIXA).sum())}h")

    st.plotly_chart(grafico_variavel(df_main, "relativehumidity_2m",
                    df_ic_ur if mostrar_spread else None),
                    use_container_width=True)

    if mostrar_spread and ensemble_data:
        fig_sur = grafico_spread(ensemble_data, "relativehumidity_2m")
        if fig_sur:
            st.plotly_chart(fig_sur, use_container_width=True)

    if "et0_fao_evapotranspiration" in df_main.columns:
        st.markdown("<div class='secao-titulo'>🌿 Evapotranspiração de Referência (ETo)</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class='info-card'>
          <h4>ETo Penman-Monteith — FAO-56</h4>
          <p>Demanda evapotranspirativa horária. ETo &gt; 0.25 mm/h: atenção à irrigação. ETo &gt; 0.40 mm/h: elevada — irrigar.</p>
        </div>""", unsafe_allow_html=True)
        st.plotly_chart(grafico_variavel(df_main, "et0_fao_evapotranspiration"), use_container_width=True)

    if "soil_moisture_0_to_1cm" in df_main.columns:
        st.markdown("<div class='secao-titulo'>🌱 Umidade do Solo (0–1 cm)</div>", unsafe_allow_html=True)
        st.plotly_chart(grafico_variavel(df_main, "soil_moisture_0_to_1cm"), use_container_width=True)

    # ── CSV da aba ──
    st.markdown("---")
    cols_ur = [c for c in ["relativehumidity_2m", "et0_fao_evapotranspiration", "soil_moisture_0_to_1cm"] if c in df_main.columns]
    if cols_ur:
        df_ur_exp = df_main[cols_ur].copy()
        df_ur_exp.index = df_ur_exp.index.strftime("%d/%m %Hh")
        df_ur_exp.columns = [LABELS.get(c, c) for c in cols_ur]
        csv_btn(df_ur_exp, "Umidade, ETo & Solo",
                f"umidade_{faz_slug}_{agora_str[:10]}.csv", "csv_ur")


# ══════════════════════════════════════════════════════════════════════════════
# ABA 4 — VENTO
# ══════════════════════════════════════════════════════════════════════════════

with tabs[4]:
    st.markdown("<div class='secao-titulo'>🌬️ Vento</div>", unsafe_allow_html=True)

    if "windspeed_10m" in df_main.columns:
        ws = df_main["windspeed_10m"].dropna()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Atual",      f"{ws.iloc[0]:.0f} km/h")
        c2.metric("Máximo 7d",  f"{ws.max():.0f} km/h")
        c3.metric("Média 7d",   f"{ws.mean():.1f} km/h")
        c4.metric(f"Horas < {DEF_VENTO_MAX:.0f} km/h", f"{int((ws < DEF_VENTO_MAX).sum())}h")

    st.plotly_chart(grafico_variavel(df_main, "windspeed_10m",
                    df_ic_vento if mostrar_spread else None),
                    use_container_width=True)

    if mostrar_spread and ensemble_data:
        fig_sw = grafico_spread(ensemble_data, "windspeed_10m")
        if fig_sw:
            st.plotly_chart(fig_sw, use_container_width=True)

    if "windgusts_10m" in df_main.columns:
        st.markdown("<div class='secao-titulo'>💨 Rajadas de Vento</div>", unsafe_allow_html=True)
        st.plotly_chart(grafico_variavel(df_main, "windgusts_10m"), use_container_width=True)

    col_p, col_c = st.columns(2)
    with col_p:
        if "surface_pressure" in df_main.columns:
            st.markdown("<div class='secao-titulo'>🔵 Pressão Superficial</div>", unsafe_allow_html=True)
            st.plotly_chart(grafico_variavel(df_main, "surface_pressure"), use_container_width=True)
    with col_c:
        if "cloudcover" in df_main.columns:
            st.markdown("<div class='secao-titulo'>☁️ Cobertura de Nuvens</div>", unsafe_allow_html=True)
            st.plotly_chart(grafico_variavel(df_main, "cloudcover"), use_container_width=True)

    # ── CSV da aba ──
    st.markdown("---")
    cols_vento = [c for c in ["windspeed_10m", "windgusts_10m", "surface_pressure", "cloudcover"] if c in df_main.columns]
    if cols_vento:
        df_v_exp = df_main[cols_vento].copy()
        df_v_exp.index = df_v_exp.index.strftime("%d/%m %Hh")
        df_v_exp.columns = [LABELS.get(c, c) for c in cols_vento]
        csv_btn(df_v_exp, "Vento, Pressão & Nuvens",
                f"vento_{faz_slug}_{agora_str[:10]}.csv", "csv_vento")


# ══════════════════════════════════════════════════════════════════════════════
# ABA 5 — RELATÓRIO & E-MAIL
# ══════════════════════════════════════════════════════════════════════════════

with tabs[5]:
    st.markdown("<div class='secao-titulo'>📄 Relatório & Exportação</div>", unsafe_allow_html=True)

    col_r1, col_r2 = st.columns([3, 2])

    with col_r1:
        st.markdown("""
        <div class='info-card'>
          <h4>📋 Boletim Agrometeorólogico</h4>
          <p>Gere o boletim completo da fazenda com todas as análises EMBRAPA/MAPA
             e envie por e-mail para a equipe de campo.</p>
        </div>""", unsafe_allow_html=True)
        html_report = gerar_relatorio_html(nome_fazenda, info_faz, df_main, res, agora_str)
        st.markdown("#### Pré-visualização")
        components.html(html_report, height=500, scrolling=True)

    with col_r2:
        st.markdown("#### 📧 Envio por E-mail")
        if not _EMAIL_OK:
            st.markdown("""
            <div class='alert-amarelo'>
              <b>⚠️ E-mail não configurado</b><br>
              Adicione as credenciais Gmail em <code>.streamlit/secrets.toml</code>:<br><br>
              <code>[email]<br>
              remetente = "seu@gmail.com"<br>
              senha_app = "xxxx xxxx xxxx xxxx"<br>
              destinatario = "dest1@ex.com"</code>
            </div>""", unsafe_allow_html=True)
        else:
            dest_input   = st.text_input("Destinatários (separados por vírgula)", value=", ".join(_EMAIL_DEST))
            assunto_input= st.text_input("Assunto", value=f"Boletim Agrometeorológico — {nome_fazenda[:40]} — {agora_str}")
            if st.button("📨 Enviar Boletim"):
                dests = [e.strip() for e in dest_input.split(",") if e.strip()]
                if not dests:
                    st.error("Informe ao menos um destinatário.")
                else:
                    with st.spinner("Enviando…"):
                        ok, msg_r = enviar_email(assunto_input, html_report, dests)
                    if ok: st.success(f"✅ {msg_r}")
                    else:  st.error(f"❌ Erro: {msg_r}")

        st.markdown("---")
        st.markdown("#### 📊 Tabela de Dados Brutos — Todos os Campos")
        df_exib = df_para_exibir(df_main)
        if not df_exib.empty:
            st.dataframe(df_exib, use_container_width=True, height=320)
            csv_btn(df_exib, "Todos os dados brutos",
                    f"yamada_completo_{faz_slug}_{agora_str[:10]}.csv", "csv_full")

    # Referências
    st.markdown("---")
    st.markdown("<div class='secao-titulo'>📚 Referências Técnicas</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='info-card'>
      <h4>Fontes e Normativos</h4>
      <p>
        • <b>Open-Meteo</b>: Zippenfenig, P. (2023). Open-Meteo.com Weather API. Zenodo. doi:10.5281/zenodo.7970649<br>
        • <b>GFS</b>: NOAA/NCEP Global Forecast System — 0.25° resolução<br>
        • <b>ICON</b>: Zängl, G. et al. (2015). The ICON modelling framework. Q. J. R. Meteorol. Soc., 141:563–579<br>
        • <b>Defensivos</b>: MAPA Portaria 371/2020 + EMBRAPA Soja (2022) — Tecnologia de Aplicação<br>
        • <b>Irrigação</b>: Gomes, H.P. (2014). EMBRAPA Cerrados — Manejo de Irrigação no Cerrado<br>
        • <b>ETo</b>: Allen, R.G. et al. (1998). FAO Irrigation and Drainage Paper 56 — Penman-Monteith<br>
        • <b>CAPE</b>: Doswell, C.A. & Rasmussen, E.N. (1994). Wea. Forecasting, 9:625–629
      </p>
    </div>""", unsafe_allow_html=True)
