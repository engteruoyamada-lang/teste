"""
=============================================================================
YAMADA ENGENHARIA — Agrometeorologia para Fazendas do MS  v5.0
=============================================================================
Estrutura:
  • Sidebar  : seleciona fazenda mock + modelo + variáveis
  • Aba 0 ★  : Síntese   — matrizes defensivos + irrigação (padrão EMBRAPA)
  • Aba 1    : Precipitação
  • Aba 2    : Temperatura
  • Aba 3    : Umidade Relativa
  • Aba 4    : Vento
  • Aba 5    : Relatório & E-mail
Fonte única: Open-Meteo (GFS + ICON — melhores para convecção subtropical MS)
=============================================================================
"""

# ─── IMPORTS ──────────────────────────────────────────────────────────────────
import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
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
AMARELO_ALERT = "#F5A623"
VERMELHO_ALRT = "#D0021B"
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

/* ── Header ── */
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

/* ── Cards ── */
.info-card {{
  background:white; border-left:4px solid {VERDE_MEDIO}; border-radius:8px;
  padding:14px 18px; margin-bottom:10px; box-shadow:0 2px 8px rgba(0,0,0,0.06);
}}
.info-card h4 {{
  font-family:'Montserrat',sans-serif; font-weight:700; color:{VERDE_ESCURO};
  margin:0 0 4px 0; font-size:0.88rem;
}}
.info-card p {{ margin:0; font-size:0.82rem; color:#333; line-height:1.45; }}

/* ── Alertas ── */
.alert-verde    {{background:#e8f5e9;border-left:4px solid #43a047;border-radius:8px;padding:12px 16px;margin:6px 0;}}
.alert-amarelo  {{background:#fff8e1;border-left:4px solid #fbc02d;border-radius:8px;padding:12px 16px;margin:6px 0;}}
.alert-vermelho {{background:#ffebee;border-left:4px solid #e53935;border-radius:8px;padding:12px 16px;margin:6px 0;}}
.alert-azul     {{background:#e3f2fd;border-left:4px solid #1565c0;border-radius:8px;padding:12px 16px;margin:6px 0;}}

/* ── Seção título ── */
.secao-titulo {{
  font-family:'Montserrat',sans-serif; font-weight:800; font-size:1.05rem;
  color:{VERDE_ESCURO}; border-bottom:2px solid {VERDE_MEDIO};
  padding-bottom:5px; margin:22px 0 12px 0;
}}

/* ── Botão ── */
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

/* ── Sidebar ── */
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

/* ── Métricas ── */
div[data-testid="metric-container"] {{
  background:white; border-radius:10px; padding:13px;
  box-shadow:0 2px 10px rgba(0,0,0,0.07); border-top:3px solid {VERDE_MEDIO};
}}
hr {{ border-color:#ddeedd; margin:16px 0; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ─── E-MAIL (secrets opcionais) ───────────────────────────────────────────────
try:
    _EMAIL_REM  = st.secrets["email"]["remetente"]
    _EMAIL_PASS = st.secrets["email"]["senha_app"]
    _dest_raw   = st.secrets["email"]["destinatario"]
    _EMAIL_DEST = ([e.strip() for e in _dest_raw.split(",") if e.strip()]
                   if isinstance(_dest_raw, str) else list(_dest_raw))
    _EMAIL_OK   = True
except Exception:
    _EMAIL_REM = _EMAIL_PASS = ""; _EMAIL_DEST = []; _EMAIL_OK = False

# ─── FAZENDAS MOCK ────────────────────────────────────────────────────────────
FAZENDAS = {
    "Fazenda Santa Fé (Maracaju — Soja/Milho)":      {"lat": -21.614, "lon": -55.168, "area_ha": 3200, "cultura": "Soja/Milho"},
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

# ─── MODELOS OPEN-METEO ───────────────────────────────────────────────────────
MODELOS = {
    "best_match":    "Best Match (Ensemble GFS+ICON — recomendado)",
    "gfs_seamless":  "GFS (NOAA — precipitação Centro-Oeste)",
    "icon_seamless": "ICON (DWD — convecção subtropical)",
}

# ─── VARIÁVEIS ────────────────────────────────────────────────────────────────
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

# ─── PARÂMETROS EMBRAPA / MAPA ────────────────────────────────────────────────
DEF_VENTO_MAX   = 10.0
DEF_TEMP_MAX    = 30.0
DEF_UR_MIN      = 55.0
DEF_PRECIP_MAX  = 0.0

IRR_UR_BAIXA    = 60.0
IRR_UR_CRITICA  = 40.0
IRR_TEMP_ALTA   = 32.0
IRR_ETO_ALTA    = 0.25


# ─────────────────────────────────────────────────────────────────────────────
# COLETA DE DADOS — OPEN-METEO
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
        "media":     med,
        "std":       std,
        "ic68_low":  med - std,
        "ic68_high": med + std,
        "ic95_low":  med - 2*std,
        "ic95_high": med + 2*std,
        "cv_pct":   (std / (med.abs() + 1e-6) * 100).round(1),
    })


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISES EMBRAPA
# ─────────────────────────────────────────────────────────────────────────────

def calcular_janela_defensivos(df: pd.DataFrame) -> pd.DataFrame:
    df24 = df.head(24).copy()
    out  = pd.DataFrame(index=df24.index)

    out["vento_ok"] = (df24.get("windspeed_10m",
                                pd.Series(5,  index=df24.index)) < DEF_VENTO_MAX).astype(int)
    out["temp_ok"]  = (df24.get("temperature_2m",
                                pd.Series(25, index=df24.index)) < DEF_TEMP_MAX).astype(int)
    out["ur_ok"]    = (df24.get("relativehumidity_2m",
                                pd.Series(65, index=df24.index)) >= DEF_UR_MIN).astype(int)
    out["chuva_ok"] = (df24.get("precipitation",
                                pd.Series(0,  index=df24.index)) <= DEF_PRECIP_MAX).astype(int)
    out["n_ok"]     = out[["vento_ok","temp_ok","ur_ok","chuva_ok"]].sum(axis=1)
    out["status"]   = out["n_ok"].map(lambda x: "aberta" if x==4 else
                                                ("parcial" if x==3 else "bloqueada"))

    def _motivo(row):
        src = df24
        m = []
        idx = row.name
        if not row["vento_ok"]:
            v = src["windspeed_10m"].get(idx, 0) if "windspeed_10m" in src.columns else 0
            m.append(f"Vento {v:.0f} km/h ≥ {DEF_VENTO_MAX:.0f}")
        if not row["temp_ok"]:
            v = src["temperature_2m"].get(idx, 0) if "temperature_2m" in src.columns else 0
            m.append(f"Temp {v:.0f}°C ≥ {DEF_TEMP_MAX:.0f}")
        if not row["ur_ok"]:
            v = src["relativehumidity_2m"].get(idx, 0) if "relativehumidity_2m" in src.columns else 0
            m.append(f"UR {v:.0f}% < {DEF_UR_MIN:.0f}")
        if not row["chuva_ok"]:
            v = src["precipitation"].get(idx, 0) if "precipitation" in src.columns else 0
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

    out["ur_nivel"]  = ur.apply(lambda v:  0 if v >= IRR_UR_BAIXA else
                                           (1 if v >= IRR_UR_CRITICA else 2))
    out["tmp_nivel"] = tmp.apply(lambda v: 0 if v < IRR_TEMP_ALTA else
                                           (1 if v < 38 else 2))
    out["eto_nivel"] = eto.apply(lambda v: 0 if v < IRR_ETO_ALTA else
                                           (1 if v < 0.40 else 2))

    out["nivel_max"]   = out[["ur_nivel","tmp_nivel","eto_nivel"]].max(axis=1)
    out["status_irr"]  = out["nivel_max"].map(
        {0:"sem_necessidade", 1:"atencao", 2:"irrigar"})

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
    n_ab  = int((df_def["status"] == "aberta").sum())
    n_pa  = int((df_def["status"] == "parcial").sum())
    n_bl  = int((df_def["status"] == "bloqueada").sum())

    bloco = cur = 0
    bloco_inicio = bloco_fim = None
    cur_inicio = None
    for t, row in df_def.iterrows():
        if row["status"] == "aberta":
            if cur == 0: cur_inicio = t
            cur += 1
            if cur > bloco:
                bloco = cur
                bloco_inicio = cur_inicio
                bloco_fim    = t
        else:
            cur = 0

    n_irr = int((df_irr["status_irr"] == "irrigar").sum())
    n_atn = int((df_irr["status_irr"] == "atencao").sum())

    return {
        "def_abertas":    n_ab,
        "def_parciais":   n_pa,
        "def_bloqueadas": n_bl,
        "def_bloco_h":    bloco,
        "def_bloco_ini":  bloco_inicio,
        "def_bloco_fim":  bloco_fim,
        "irr_urgente":    n_irr,
        "irr_atencao":    n_atn,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE GRÁFICO
# ─────────────────────────────────────────────────────────────────────────────

def _ax_dark(ax):
    ax.set_facecolor(BG_PANEL)
    ax.tick_params(colors="#9ca3af", labelsize=8)
    for sp in ax.spines.values():
        sp.set_edgecolor("#374151")
    ax.grid(True, color="#1f2937", linewidth=0.6, alpha=0.7)


def grafico_variavel(df: pd.DataFrame, var: str,
                     df_ic: pd.DataFrame = None,
                     titulo_extra: str = "") -> plt.Figure:
    fig, ax = plt.subplots(figsize=(13, 3.8), facecolor=BG_DARK)
    _ax_dark(ax)

    cor   = CORES.get(var, "#60a5fa")
    label = LABELS.get(var, var)

    if var not in df.columns or df.empty:
        ax.text(0.5, 0.5, "Dados não disponíveis",
                transform=ax.transAxes, ha="center", va="center",
                color="white", fontsize=12)
        return fig

    serie = df[var].dropna()

    if df_ic is not None and not df_ic.empty:
        ic_re = df_ic.reindex(serie.index, method="nearest")
        ax.fill_between(serie.index, ic_re["ic95_low"], ic_re["ic95_high"],
                        alpha=0.08, color=cor, label="IC 95%")
        ax.fill_between(serie.index, ic_re["ic68_low"], ic_re["ic68_high"],
                        alpha=0.18, color=cor, label="IC 68%")

    if var == "precipitation":
        ax.bar(serie.index, serie.values, width=1/24,
               color=cor, alpha=0.82, align="center", label=label, zorder=5)
    else:
        ax.plot(serie.index, serie.values, color=cor,
                linewidth=2.0, label=label, zorder=5)
        ax.fill_between(serie.index, serie.values, alpha=0.09, color=cor)

    LIMIARES = {
        "temperature_2m": [
            (5,           "#93c5fd", "Geada (5°C)"),
            (DEF_TEMP_MAX,"#fbbf24", f"Lim. defensivos ({DEF_TEMP_MAX:.0f}°C)"),
            (IRR_TEMP_ALTA,"#f97316",f"Estresse hídrico ({IRR_TEMP_ALTA:.0f}°C)"),
            (38,          "#ef4444", "Calor extremo (38°C)"),
        ],
        "relativehumidity_2m": [
            (DEF_UR_MIN,  "#fbbf24", f"Lim. defensivos ({DEF_UR_MIN:.0f}%)"),
            (IRR_UR_BAIXA,"#fb923c", f"Irrig. atenção ({IRR_UR_BAIXA:.0f}%)"),
            (IRR_UR_CRITICA,"#ef4444",f"Irrig. urgente ({IRR_UR_CRITICA:.0f}%)"),
            (80,          "#c084fc", "Risco ferrugem (80%)"),
        ],
        "windspeed_10m": [
            (DEF_VENTO_MAX,"#fbbf24",f"Lim. defensivos ({DEF_VENTO_MAX:.0f} km/h)"),
            (40,           "#ef4444","Dano potencial (40 km/h)"),
        ],
        "precipitation": [
            (10,  "#fbbf24","Atenção (10 mm/h)"),
            (25,  "#ef4444","Intensidade forte (25 mm/h)"),
        ],
        "cape": [
            (500,  "#fbbf24","CAPE moderado (500 J/kg)"),
            (1500, "#f97316","CAPE alto (1500 J/kg)"),
            (2500, "#ef4444","CAPE extremo (2500 J/kg)"),
        ],
        "et0_fao_evapotranspiration": [
            (IRR_ETO_ALTA, "#fb923c",f"ETo atenção ({IRR_ETO_ALTA:.2f} mm/h)"),
            (0.40,         "#ef4444","ETo elevada (0.40 mm/h)"),
        ],
    }
    for val, cor_l, lbl in LIMIARES.get(var, []):
        ax.axhline(val, color=cor_l, linewidth=0.9,
                   linestyle="--", alpha=0.75, label=lbl)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%Hh"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    ax.set_ylabel(label, color="#9ca3af", fontsize=9)
    titulo = f"{label}{titulo_extra}"
    ax.set_title(titulo, color="white", fontsize=10, fontweight="bold", pad=8)

    handles, labs = ax.get_legend_handles_labels()
    ax.legend(handles, labs, fontsize=7, facecolor=BG_PANEL,
              labelcolor="white", edgecolor="#374151",
              loc="upper right", ncol=2)
    plt.tight_layout(pad=0.5)
    return fig


def grafico_spread(ensemble: dict, var: str) -> plt.Figure:
    series = {}
    for mod, dados in ensemble.items():
        if "hourly" in dados and var in dados["hourly"]:
            s = pd.Series(
                pd.to_numeric(dados["hourly"][var], errors="coerce"),
                index=pd.to_datetime(dados["hourly"]["time"]),
                name={"gfs_seamless":"GFS","icon_seamless":"ICON",
                      "best_match":"Best Match"}.get(mod, mod),
            )
            series[s.name] = s
    if len(series) < 2:
        return None

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 5.5),
                                    facecolor=BG_DARK,
                                    gridspec_kw={"height_ratios":[3,1]})
    for ax in [ax1, ax2]:
        _ax_dark(ax)

    df_e  = pd.concat(series.values(), axis=1)
    med   = df_e.mean(axis=1)
    std   = df_e.std(axis=1)
    cv    = (std / (med.abs() + 1e-6) * 100)
    cores_mod = ["#60a5fa","#f97316","#34d399"]

    ax1.fill_between(med.index, med-2*std, med+2*std, alpha=0.09, color="#60a5fa", label="IC 95%")
    ax1.fill_between(med.index, med-std,   med+std,   alpha=0.18, color="#60a5fa", label="IC 68%")
    for (nome, s), c in zip(series.items(), cores_mod):
        ax1.plot(s.index, s.values, color=c, linewidth=1.3,
                 alpha=0.85, linestyle="--", label=nome)
    ax1.plot(med.index, med.values, color="white",
             linewidth=2.2, label="Média modelos", zorder=5)
    ax1.set_ylabel(LABELS.get(var, var), color="#9ca3af", fontsize=9)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%Hh"))
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=12))
    ax1.legend(fontsize=7, facecolor=BG_PANEL, labelcolor="white",
               edgecolor="#374151", loc="upper right", ncol=3)
    ax1.set_title(f"Spread entre modelos — {LABELS.get(var,var)}",
                  color="white", fontsize=10, fontweight="bold")

    cv_c = ["#22c55e" if v<10 else ("#fbbf24" if v<25 else "#ef4444") for v in cv.values]
    ax2.bar(cv.index, cv.values, width=1/24, color=cv_c, alpha=0.85)
    ax2.axhline(10, color="#22c55e", linestyle="--", linewidth=0.8, alpha=0.7, label="Alta (<10%)")
    ax2.axhline(25, color="#ef4444", linestyle="--", linewidth=0.8, alpha=0.7, label="Baixa (>25%)")
    ax2.set_ylabel("CV % (incerteza)", color="#9ca3af", fontsize=8)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax2.xaxis.set_major_locator(mdates.DayLocator())
    ax2.legend(fontsize=7, facecolor=BG_PANEL, labelcolor="white", edgecolor="#374151")

    plt.tight_layout(pad=0.5)
    return fig


def grafico_matriz_defensivos(df_def: pd.DataFrame) -> plt.Figure:
    n = min(24, len(df_def))
    if n == 0:
        return None

    colunas_crit = ["Vento\n<10km/h", "Temp\n<30°C", "UR\n≥55%", "Sem\nChuva", "JANELA\nGERAL"]
    horas = [df_def.index[i].strftime("%Hh") for i in range(n)]
    M = np.zeros((n, len(colunas_crit)))

    for i, (_, row) in enumerate(df_def.head(n).iterrows()):
        M[i,0] = row["vento_ok"]
        M[i,1] = row["temp_ok"]
        M[i,2] = row["ur_ok"]
        M[i,3] = row["chuva_ok"]
        M[i,4] = 1 if row["status"]=="aberta" else (0.5 if row["status"]=="parcial" else 0)

    cmap = mcolors.ListedColormap(["#ef4444","#fbbf24","#22c55e"])
    norm = mcolors.BoundaryNorm([-0.1, 0.3, 0.7, 1.1], cmap.N)

    fig, ax = plt.subplots(figsize=(10, max(5, n*0.30)), facecolor=BG_DARK)
    ax.set_facecolor(BG_DARK)
    ax.imshow(M, cmap=cmap, norm=norm, aspect="auto")

    ax.set_xticks(range(len(colunas_crit)))
    ax.set_xticklabels(colunas_crit, color="white", fontsize=8.5, fontweight="bold")
    ax.set_yticks(range(n))
    ax.set_yticklabels(horas, color="#9ca3af", fontsize=7)
    ax.set_title("Janela de Aplicação de Defensivos — Próximas 24h",
                 color="white", fontsize=11, fontweight="bold", pad=10)

    for i in range(n):
        for j in range(len(colunas_crit)):
            val = M[i, j]
            txt = "✓" if val == 1 else ("○" if val == 0.5 else "✗")
            ax.text(j, i, txt, ha="center", va="center",
                    fontsize=8, color="#000", fontweight="bold")

    p_v = mpatches.Patch(facecolor="#22c55e", label="✓ Critério atendido / Janela aberta")
    p_a = mpatches.Patch(facecolor="#fbbf24", label="○ Parcial (1 restrição)")
    p_r = mpatches.Patch(facecolor="#ef4444", label="✗ Critério bloqueado")
    ax.legend(handles=[p_v,p_a,p_r], loc="lower right", fontsize=7.5,
              facecolor=BG_PANEL, labelcolor="white", edgecolor="#374151",
              bbox_to_anchor=(1.0,-0.06))
    for sp in ax.spines.values(): sp.set_visible(False)
    plt.tight_layout(pad=0.8)
    return fig


def grafico_matriz_irrigacao(df_irr: pd.DataFrame) -> plt.Figure:
    n = min(48, len(df_irr))
    if n == 0:
        return None

    colunas = ["UR\n(%)", "Temperatura\n(°C)", "ETo\n(mm/h)", "NECESSIDADE\nIRRIGAÇÃO"]
    horas   = [df_irr.index[i].strftime("%d/%m\n%Hh") for i in range(n)]

    M = np.zeros((n, 4))
    for i, (_, row) in enumerate(df_irr.head(n).iterrows()):
        M[i,0] = 2 - row["ur_nivel"]
        M[i,1] = 2 - row["tmp_nivel"]
        M[i,2] = 2 - row["eto_nivel"]
        M[i,3] = 2 - row["nivel_max"]

    cmap = mcolors.ListedColormap(["#ef4444","#fbbf24","#22c55e"])
    norm = mcolors.BoundaryNorm([-0.1, 0.7, 1.3, 2.1], cmap.N)

    fig, ax = plt.subplots(figsize=(9, max(6, n*0.22)), facecolor=BG_DARK)
    ax.set_facecolor(BG_DARK)
    ax.imshow(M, cmap=cmap, norm=norm, aspect="auto")

    ax.set_xticks(range(4))
    ax.set_xticklabels(colunas, color="white", fontsize=8.5, fontweight="bold")
    ax.set_yticks(range(n))
    ax.set_yticklabels(horas, color="#9ca3af", fontsize=6.5)
    ax.set_title("Necessidade de Irrigação — Próximas 48h (parâmetros EMBRAPA)",
                 color="white", fontsize=11, fontweight="bold", pad=10)

    TEXTS = {2:"✓", 1:"!", 0:"✗"}
    for i in range(n):
        for j in range(4):
            txt = TEXTS.get(int(round(M[i,j])), "?")
            ax.text(j, i, txt, ha="center", va="center",
                    fontsize=7.5, color="#000", fontweight="bold")

    p_v = mpatches.Patch(facecolor="#22c55e", label="✓ Sem necessidade")
    p_a = mpatches.Patch(facecolor="#fbbf24", label="! Atenção — monitorar")
    p_r = mpatches.Patch(facecolor="#ef4444", label="✗ Irrigar urgente")
    ax.legend(handles=[p_v,p_a,p_r], loc="lower right", fontsize=7.5,
              facecolor=BG_PANEL, labelcolor="white", edgecolor="#374151",
              bbox_to_anchor=(1.0,-0.04))
    for sp in ax.spines.values(): sp.set_visible(False)
    plt.tight_layout(pad=0.8)
    return fig


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
    wc           = int(df["weathercode"].dropna().iloc[0]) if (not df.empty and "weathercode" in df.columns and len(df["weathercode"].dropna()) > 0) else 0
    condicao     = WCODE.get(wc, "—")

    bloco_str = "—"
    if res.get("def_bloco_ini") and res.get("def_bloco_fim"):
        bloco_str = (f"{res['def_bloco_ini'].strftime('%Hh %d/%m')} → "
                     f"{res['def_bloco_fim'].strftime('%Hh %d/%m')} "
                     f"({res['def_bloco_h']}h consecutivas)")

    irr_status = "🔴 Irrigação urgente" if res.get("irr_urgente",0) > 0 else (
                 "🟡 Atenção à irrigação" if res.get("irr_atencao",0) > 0 else "🟢 Sem necessidade")

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

    modelo_key   = st.selectbox(
        "🔭 Modelo Meteorológico",
        list(MODELOS.keys()),
        format_func=lambda k: MODELOS[k],
        index=0,
    )

    dias_prev    = st.slider("📅 Dias de previsão", 3, 7, 7)

    st.markdown("---")
    st.markdown("<div class='secao-titulo' style='color:#a5d6a7;border-color:#3DA63A;'>🔧 Variáveis extras</div>",
                unsafe_allow_html=True)

    VARS_EXTRAS = {
        "cape":                       "⚡ CAPE (tempestades)",
        "shortwave_radiation":         "☀️ Radiação Solar",
        "et0_fao_evapotranspiration":  "💧 ETo Penman-Monteith",
        "soil_moisture_0_to_1cm":     "🌱 Umidade do Solo",
        "surface_pressure":           "🔵 Pressão Superficial",
        "cloudcover":                 "☁️ Cobertura de Nuvens",
    }
    vars_selecionadas = []
    for v, lbl in VARS_EXTRAS.items():
        if st.checkbox(lbl, value=(v in ["cape","et0_fao_evapotranspiration"]), key=f"chk_{v}"):
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
# HEADER PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
st.markdown(f"""
<div class="yamada-header">
  <h1>🌿 Yamada Engenharia — Agrometeorologia MS</h1>
  <p>Previsão Open-Meteo (GFS + ICON) · Parâmetros EMBRAPA/MAPA · Atualizado {agora_str}</p>
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

# Ensemble para IC (lazy)
ensemble_data: dict = {}
df_ic_temp = df_ic_precip = df_ic_ur = df_ic_vento = pd.DataFrame()

if mostrar_spread:
    with st.spinner("⏳ Buscando ensemble de modelos…"):
        ensemble_data = buscar_ensemble(info_faz["lat"], info_faz["lon"], dias_prev)
    df_ic_temp   = ic_entre_modelos(ensemble_data, "temperature_2m")
    df_ic_precip = ic_entre_modelos(ensemble_data, "precipitation")
    df_ic_ur     = ic_entre_modelos(ensemble_data, "relativehumidity_2m")
    df_ic_vento  = ic_entre_modelos(ensemble_data, "windspeed_10m")

# Cálculos EMBRAPA
df_def = calcular_janela_defensivos(df_main)
df_irr = calcular_janela_irrigacao(df_main)
res    = resumo_janelas(df_def, df_irr)

# Condição atual
wc_atual   = int(df_main["weathercode"].dropna().iloc[0]) if "weathercode" in df_main.columns and len(df_main["weathercode"].dropna()) > 0 else 0
temp_agora = df_main["temperature_2m"].dropna().iloc[0] if "temperature_2m" in df_main.columns else float("nan")
ur_agora   = df_main["relativehumidity_2m"].dropna().iloc[0] if "relativehumidity_2m" in df_main.columns else float("nan")
vento_agora= df_main["windspeed_10m"].dropna().iloc[0] if "windspeed_10m" in df_main.columns else float("nan")
precip_24h = df_main["precipitation"].head(24).sum() if "precipitation" in df_main.columns else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# MÉTRICAS RÁPIDAS
# ─────────────────────────────────────────────────────────────────────────────

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🌡️ Temperatura", f"{temp_agora:.1f} °C")
c2.metric("💧 Umidade Relativa", f"{ur_agora:.0f} %")
c3.metric("🌬️ Vento", f"{vento_agora:.0f} km/h")
c4.metric("🌧️ Precip. 24h", f"{precip_24h:.1f} mm")
c5.metric("🌤️ Condição", WCODE.get(wc_atual, f"Cód {wc_atual}"))

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

    # Cards de resumo
    col_a, col_b, col_c, col_d = st.columns(4)

    # Defensivos
    pct_ab = res["def_abertas"] / 24 * 100
    if res["def_abertas"] >= 6:
        cls_d = "alert-verde"
        icn_d = "🟢"
    elif res["def_abertas"] >= 2:
        cls_d = "alert-amarelo"
        icn_d = "🟡"
    else:
        cls_d = "alert-vermelho"
        icn_d = "🔴"

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

    # Melhor bloco
    if res["def_bloco_ini"] and res["def_bloco_h"] > 0:
        bloco_txt = (f"{res['def_bloco_ini'].strftime('%Hh')} → "
                     f"{res['def_bloco_fim'].strftime('%Hh')} "
                     f"({res['def_bloco_h']}h)")
    else:
        bloco_txt = "Sem janela contínua"
    col_c.markdown(f"""
    <div class='alert-azul'>
      <b>📅 Melhor janela contínua</b><br>
      <span style='font-size:0.95rem;font-weight:700;'>{bloco_txt}</span>
    </div>""", unsafe_allow_html=True)

    # Irrigação
    if res["irr_urgente"] > 0:
        cls_i = "alert-vermelho"; icn_i = "🔴"
        irr_txt = f"Irrigar urgente: {res['irr_urgente']}h"
    elif res["irr_atencao"] > 0:
        cls_i = "alert-amarelo"; icn_i = "🟡"
        irr_txt = f"Atenção: {res['irr_atencao']}h"
    else:
        cls_i = "alert-verde"; icn_i = "🟢"
        irr_txt = "Sem necessidade hídrica"
    col_d.markdown(f"""
    <div class='{cls_i}'>
      <b>{icn_i} Irrigação (48h)</b><br>
      <span style='font-size:0.95rem;font-weight:700;'>{irr_txt}</span>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Matrizes
    col_m1, col_m2 = st.columns([1, 1])

    with col_m1:
        st.markdown("<div class='secao-titulo'>🌿 Janela de Defensivos — 24h</div>",
                    unsafe_allow_html=True)
        st.markdown("""
        <div class='info-card'>
          <h4>Critérios MAPA Portaria 371/2020 + EMBRAPA Soja</h4>
          <p>Vento &lt; 10 km/h · Temp &lt; 30°C · UR ≥ 55% · Sem precipitação</p>
        </div>""", unsafe_allow_html=True)
        fig_def = grafico_matriz_defensivos(df_def)
        if fig_def:
            st.pyplot(fig_def, use_container_width=True)
            plt.close(fig_def)

    with col_m2:
        st.markdown("<div class='secao-titulo'>💧 Necessidade de Irrigação — 48h</div>",
                    unsafe_allow_html=True)
        st.markdown("""
        <div class='info-card'>
          <h4>Critérios EMBRAPA Cerrados — Gomes (2014)</h4>
          <p>UR, Temperatura e ETo Penman-Monteith classificados em 3 níveis de demanda hídrica</p>
        </div>""", unsafe_allow_html=True)
        fig_irr = grafico_matriz_irrigacao(df_irr)
        if fig_irr:
            st.pyplot(fig_irr, use_container_width=True)
            plt.close(fig_irr)

    # Variáveis extras selecionadas
    if vars_selecionadas:
        st.markdown("---")
        st.markdown("<div class='secao-titulo'>📊 Variáveis Complementares</div>",
                    unsafe_allow_html=True)
        for var in vars_selecionadas:
            fig_e = grafico_variavel(df_main, var)
            st.pyplot(fig_e, use_container_width=True)
            plt.close(fig_e)


# ══════════════════════════════════════════════════════════════════════════════
# ABA 1 — PRECIPITAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

with tabs[1]:
    st.markdown("<div class='secao-titulo'>🌧️ Precipitação</div>", unsafe_allow_html=True)

    # Estatísticas rápidas
    if "precipitation" in df_main.columns:
        precip_s = df_main["precipitation"].dropna()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total 24h",  f"{precip_s.head(24).sum():.1f} mm")
        c2.metric("Total 48h",  f"{precip_s.head(48).sum():.1f} mm")
        c3.metric("Total 7 dias", f"{precip_s.sum():.1f} mm")
        c4.metric("Máx horário", f"{precip_s.max():.1f} mm/h")

    fig_p = grafico_variavel(df_main, "precipitation",
                             df_ic_precip if mostrar_spread else None)
    st.pyplot(fig_p, use_container_width=True)
    plt.close(fig_p)

    if mostrar_spread and ensemble_data:
        fig_sp = grafico_spread(ensemble_data, "precipitation")
        if fig_sp:
            st.pyplot(fig_sp, use_container_width=True)
            plt.close(fig_sp)

    # Tabela diária de chuva acumulada
    if "precipitation" in df_main.columns:
        st.markdown("<div class='secao-titulo'>📅 Acumulado Diário</div>", unsafe_allow_html=True)
        diario = df_main["precipitation"].resample("D").sum().reset_index()
        diario.columns = ["Data", "Precipitação (mm)"]
        diario["Data"] = diario["Data"].dt.strftime("%d/%m/%Y")
        diario["Precipitação (mm)"] = diario["Precipitação (mm)"].round(1)
        st.dataframe(diario, use_container_width=True, hide_index=True)

    # CAPE
    if "cape" in df_main.columns:
        st.markdown("<div class='secao-titulo'>⚡ CAPE — Energia Convectiva Disponível</div>",
                    unsafe_allow_html=True)
        st.markdown("""
        <div class='info-card'>
          <h4>Referência: CAPE como proxy de tempestades</h4>
          <p>CAPE &lt; 500 J/kg: baixo risco · 500–1500: moderado · 1500–2500: alto · &gt;2500: extremo</p>
        </div>""", unsafe_allow_html=True)
        fig_cape = grafico_variavel(df_main, "cape")
        st.pyplot(fig_cape, use_container_width=True)
        plt.close(fig_cape)


# ══════════════════════════════════════════════════════════════════════════════
# ABA 2 — TEMPERATURA
# ══════════════════════════════════════════════════════════════════════════════

with tabs[2]:
    st.markdown("<div class='secao-titulo'>🌡️ Temperatura</div>", unsafe_allow_html=True)

    if "temperature_2m" in df_main.columns:
        ts = df_main["temperature_2m"].dropna()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Atual",  f"{ts.iloc[0]:.1f} °C")
        c2.metric("Máxima 7d", f"{ts.max():.1f} °C")
        c3.metric("Mínima 7d", f"{ts.min():.1f} °C")
        c4.metric("Média 7d",  f"{ts.mean():.1f} °C")

    fig_t = grafico_variavel(df_main, "temperature_2m",
                             df_ic_temp if mostrar_spread else None)
    st.pyplot(fig_t, use_container_width=True)
    plt.close(fig_t)

    if mostrar_spread and ensemble_data:
        fig_st = grafico_spread(ensemble_data, "temperature_2m")
        if fig_st:
            st.pyplot(fig_st, use_container_width=True)
            plt.close(fig_st)

    # Ponto de orvalho
    if "dewpoint_2m" in df_main.columns:
        st.markdown("<div class='secao-titulo'>🌫️ Ponto de Orvalho</div>", unsafe_allow_html=True)
        fig_dew = grafico_variavel(df_main, "dewpoint_2m")
        st.pyplot(fig_dew, use_container_width=True)
        plt.close(fig_dew)

    # Radiação solar
    if "shortwave_radiation" in df_main.columns:
        st.markdown("<div class='secao-titulo'>☀️ Radiação Solar de Onda Curta</div>",
                    unsafe_allow_html=True)
        fig_rad = grafico_variavel(df_main, "shortwave_radiation")
        st.pyplot(fig_rad, use_container_width=True)
        plt.close(fig_rad)


# ══════════════════════════════════════════════════════════════════════════════
# ABA 3 — UMIDADE RELATIVA
# ══════════════════════════════════════════════════════════════════════════════

with tabs[3]:
    st.markdown("<div class='secao-titulo'>💧 Umidade Relativa</div>", unsafe_allow_html=True)

    if "relativehumidity_2m" in df_main.columns:
        ur_s = df_main["relativehumidity_2m"].dropna()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Atual",    f"{ur_s.iloc[0]:.0f} %")
        c2.metric("Mínima 7d", f"{ur_s.min():.0f} %")
        c3.metric("Máxima 7d", f"{ur_s.max():.0f} %")
        horas_baixa = int((ur_s < IRR_UR_BAIXA).sum())
        c4.metric(f"Horas < {IRR_UR_BAIXA:.0f}%", f"{horas_baixa}h")

    fig_ur = grafico_variavel(df_main, "relativehumidity_2m",
                              df_ic_ur if mostrar_spread else None)
    st.pyplot(fig_ur, use_container_width=True)
    plt.close(fig_ur)

    if mostrar_spread and ensemble_data:
        fig_sur = grafico_spread(ensemble_data, "relativehumidity_2m")
        if fig_sur:
            st.pyplot(fig_sur, use_container_width=True)
            plt.close(fig_sur)

    # ETo
    if "et0_fao_evapotranspiration" in df_main.columns:
        st.markdown("<div class='secao-titulo'>🌿 Evapotranspiração de Referência (ETo)</div>",
                    unsafe_allow_html=True)
        st.markdown("""
        <div class='info-card'>
          <h4>ETo Penman-Monteith — FAO-56</h4>
          <p>Demanda evapotranspirativa horária. ETo &gt; 0.25 mm/h: atenção à irrigação.
             ETo &gt; 0.40 mm/h: elevada — irrigar.</p>
        </div>""", unsafe_allow_html=True)
        fig_eto = grafico_variavel(df_main, "et0_fao_evapotranspiration")
        st.pyplot(fig_eto, use_container_width=True)
        plt.close(fig_eto)

    # Umidade do solo
    if "soil_moisture_0_to_1cm" in df_main.columns:
        st.markdown("<div class='secao-titulo'>🌱 Umidade do Solo (0–1 cm)</div>",
                    unsafe_allow_html=True)
        fig_sm = grafico_variavel(df_main, "soil_moisture_0_to_1cm")
        st.pyplot(fig_sm, use_container_width=True)
        plt.close(fig_sm)


# ══════════════════════════════════════════════════════════════════════════════
# ABA 4 — VENTO
# ══════════════════════════════════════════════════════════════════════════════

with tabs[4]:
    st.markdown("<div class='secao-titulo'>🌬️ Vento</div>", unsafe_allow_html=True)

    if "windspeed_10m" in df_main.columns:
        ws = df_main["windspeed_10m"].dropna()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Atual",    f"{ws.iloc[0]:.0f} km/h")
        c2.metric("Máximo 7d", f"{ws.max():.0f} km/h")
        c3.metric("Média 7d",  f"{ws.mean():.1f} km/h")
        horas_lim = int((ws < DEF_VENTO_MAX).sum())
        c4.metric(f"Horas < {DEF_VENTO_MAX:.0f} km/h", f"{horas_lim}h")

    # Velocidade
    fig_w = grafico_variavel(df_main, "windspeed_10m",
                             df_ic_vento if mostrar_spread else None)
    st.pyplot(fig_w, use_container_width=True)
    plt.close(fig_w)

    if mostrar_spread and ensemble_data:
        fig_sw = grafico_spread(ensemble_data, "windspeed_10m")
        if fig_sw:
            st.pyplot(fig_sw, use_container_width=True)
            plt.close(fig_sw)

    # Rajadas
    if "windgusts_10m" in df_main.columns:
        st.markdown("<div class='secao-titulo'>💨 Rajadas de Vento</div>", unsafe_allow_html=True)
        fig_wg = grafico_variavel(df_main, "windgusts_10m")
        st.pyplot(fig_wg, use_container_width=True)
        plt.close(fig_wg)

    # Pressão e nebulosidade
    col_p, col_c = st.columns(2)
    with col_p:
        if "surface_pressure" in df_main.columns:
            st.markdown("<div class='secao-titulo'>🔵 Pressão Superficial</div>",
                        unsafe_allow_html=True)
            fig_prs = grafico_variavel(df_main, "surface_pressure")
            st.pyplot(fig_prs, use_container_width=True)
            plt.close(fig_prs)
    with col_c:
        if "cloudcover" in df_main.columns:
            st.markdown("<div class='secao-titulo'>☁️ Cobertura de Nuvens</div>",
                        unsafe_allow_html=True)
            fig_cc = grafico_variavel(df_main, "cloudcover")
            st.pyplot(fig_cc, use_container_width=True)
            plt.close(fig_cc)


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

        html_report = gerar_relatorio_html(
            nome_fazenda, info_faz, df_main, res, agora_str)

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
              destinatario = "dest1@ex.com, dest2@ex.com"</code>
            </div>""", unsafe_allow_html=True)
        else:
            dest_input = st.text_input(
                "Destinatários (separados por vírgula)",
                value=", ".join(_EMAIL_DEST))
            assunto_input = st.text_input(
                "Assunto",
                value=f"Boletim Agrometeorológico — {nome_fazenda[:40]} — {agora_str}")

            if st.button("📨 Enviar Boletim"):
                dests = [e.strip() for e in dest_input.split(",") if e.strip()]
                if not dests:
                    st.error("Informe ao menos um destinatário.")
                else:
                    with st.spinner("Enviando…"):
                        ok, msg_r = enviar_email(assunto_input, html_report, dests)
                    if ok:
                        st.success(f"✅ {msg_r}")
                    else:
                        st.error(f"❌ Erro: {msg_r}")

        st.markdown("---")
        st.markdown("#### 📊 Tabela de Dados Brutos")
        df_exib = df_para_exibir(df_main)
        if not df_exib.empty:
            st.dataframe(df_exib, use_container_width=True, height=340)
            csv_bytes = df_exib.to_csv().encode("utf-8")
            st.download_button(
                label="⬇️ Baixar CSV",
                data=csv_bytes,
                file_name=f"yamada_previsao_{nome_fazenda[:30].replace(' ','_')}_{agora_str[:10]}.csv",
                mime="text/csv",
            )

    # Referências
    st.markdown("---")
    st.markdown("<div class='secao-titulo'>📚 Referências Técnicas</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='info-card'>
      <h4>Fontes e Normativos</h4>
      <p>
        • <b>Open-Meteo</b>: Zippenfenig, P. (2023). Open-Meteo.com Weather API. Zenodo. doi:10.5281/zenodo.7970649<br>
        • <b>GFS</b>: NOAA/NCEP Global Forecast System — 0.25° resolução<br>
        • <b>ICON</b>: Zängl, G. et al. (2015). The ICON (ICOsahedral Non-hydrostatic) modelling framework. Q. J. R. Meteorol. Soc., 141:563–579<br>
        • <b>Defensivos</b>: MAPA Portaria 371/2020 + EMBRAPA Soja (2022) — Tecnologia de Aplicação<br>
        • <b>Irrigação</b>: Gomes, H.P. (2014). EMBRAPA Cerrados — Manejo de Irrigação no Cerrado<br>
        • <b>ETo</b>: Allen, R.G. et al. (1998). FAO Irrigation and Drainage Paper 56 — Penman-Monteith<br>
        • <b>CAPE</b>: Doswell, C.A. & Rasmussen, E.N. (1994). The Effect of Neglecting the Virtual Temperature Correction on CAPE Calculations. Wea. Forecasting, 9:625–629
      </p>
    </div>""", unsafe_allow_html=True)
