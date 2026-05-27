# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
import streamlit.components.v1 as components
import folium
from streamlit_folium import st_folium

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.figure import Figure

import requests
import json
import os
import io
import threading
import logging
import warnings
from datetime import datetime, timezone, timedelta

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

warnings.filterwarnings("ignore")
logging.getLogger("apscheduler").setLevel(logging.WARNING)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Yamada Engenharia | Agrometeorologia MS",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# IDENTIDADE VISUAL
# ─────────────────────────────────────────────────────────────────────────────
VERDE_ESCURO  = "#1B4D2E"
VERDE_MEDIO   = "#3DA63A"
PRETO         = "#1A1A1A"
CINZA_CLARO   = "#F4F7F4"
AMARELO_ALERT = "#F5A623"
VERMELHO_ALRT = "#D0021B"

CSS = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;900&family=Source+Sans+3:wght@300;400;600&display=swap');
  html, body, [class*="css"] {{
    font-family: 'Source Sans 3', sans-serif;
    background-color: {CINZA_CLARO}; color: {PRETO};
  }}
  .yamada-header {{
    background: linear-gradient(135deg, {VERDE_ESCURO} 0%, {VERDE_MEDIO} 100%);
    border-radius: 12px; padding: 24px 32px; margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(27,77,46,0.3);
  }}
  .yamada-header h1 {{
    font-family:'Montserrat',sans-serif; font-weight:900; font-size:1.8rem;
    color:white; margin:0; letter-spacing:-0.5px;
  }}
  .yamada-header p {{ color:rgba(255,255,255,0.82); margin:4px 0 0 0; font-size:0.9rem; }}
  .info-card {{
    background:white; border-left:4px solid {VERDE_MEDIO}; border-radius:8px;
    padding:14px 18px; margin-bottom:10px; box-shadow:0 2px 8px rgba(0,0,0,0.06);
  }}
  .info-card h4 {{
    font-family:'Montserrat',sans-serif; font-weight:700; color:{VERDE_ESCURO};
    margin:0 0 4px 0; font-size:0.88rem;
  }}
  .info-card p {{ margin:0; font-size:0.82rem; color:#333; line-height:1.4; }}
  .alert-verde    {{ background:#e8f5e9; border-left:4px solid #43a047; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .alert-amarelo  {{ background:#fff8e1; border-left:4px solid #fbc02d; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .alert-vermelho {{ background:#ffebee; border-left:4px solid #e53935; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .alert-laranja  {{ background:#fff3e0; border-left:4px solid #fb8c00; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .alert-azul     {{ background:#e3f2fd; border-left:4px solid #1565c0; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .secao-titulo {{
    font-family:'Montserrat',sans-serif; font-weight:800; font-size:1.1rem;
    color:{VERDE_ESCURO}; border-bottom:2px solid {VERDE_MEDIO};
    padding-bottom:6px; margin:24px 0 14px 0;
  }}
  .coord-box {{
    background: #1a2e1c; border: 1px solid #3DA63A; border-radius:10px;
    padding: 12px 16px; margin: 8px 0;
  }}
  .coord-box span {{ color: #a5d6a7; font-size: 0.82rem; font-family: 'Montserrat', sans-serif; }}
  .coord-val {{ color: #ffffff !important; font-weight: 700 !important; font-size: 0.95rem !important; }}
  .stButton > button {{
    background:linear-gradient(135deg,{VERDE_ESCURO},{VERDE_MEDIO}) !important;
    color:white !important; font-family:'Montserrat',sans-serif !important;
    font-weight:700 !important; border:none !important; border-radius:10px !important;
    padding:12px 32px !important; width:100% !important;
    box-shadow:0 4px 15px rgba(27,77,46,0.35) !important;
    transition: all 0.2s ease !important;
  }}
  .stButton > button:hover {{
    transform: translateY(-1px) !important;
    box-shadow:0 6px 20px rgba(27,77,46,0.5) !important;
  }}
  section[data-testid="stSidebar"] {{
    background-color:#1a2e1c !important; border-right:1px solid #2d5a30;
  }}
  section[data-testid="stSidebar"] * {{ color:#e8f5e9 !important; }}
  section[data-testid="stSidebar"] label {{
    font-family:'Montserrat',sans-serif !important; font-weight:600 !important;
    font-size:0.83rem !important; color:#a5d6a7 !important;
  }}
  section[data-testid="stSidebar"] .stSelectbox > div > div {{
    background-color:#2d5a30 !important; color:white !important; border-color:#3DA63A !important;
  }}
  section[data-testid="stSidebar"] hr {{ border-color:#2d5a30 !important; }}
  section[data-testid="stSidebar"] .stNumberInput input {{
    background-color:#2d5a30 !important; color:white !important;
    border-color:#3DA63A !important; border-radius:6px !important;
  }}
  div[data-testid="metric-container"] {{
    background:white; border-radius:10px; padding:14px;
    box-shadow:0 2px 10px rgba(0,0,0,0.07); border-top:3px solid {VERDE_MEDIO};
  }}
  hr {{ border-color:#ddeedd; margin:18px 0; }}
  .status-ponto {{
    background: linear-gradient(135deg, #1a2e1c, #2d5a30);
    border: 1px solid {VERDE_MEDIO}; border-radius: 10px;
    padding: 10px 16px; margin: 10px 0;
    font-family: 'Montserrat', sans-serif;
  }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DE E-MAIL
# ─────────────────────────────────────────────────────────────────────────────
try:
    EMAIL_REMETENTE     = st.secrets["email"]["remetente"]
    EMAIL_SENHA_APP     = st.secrets["email"]["senha_app"]
    _dest_raw           = st.secrets["email"]["destinatario"]
    EMAIL_DESTINATARIOS = ([e.strip() for e in _dest_raw.split(",") if e.strip()]
                           if isinstance(_dest_raw, str) else list(_dest_raw))
    _email_ok = True
except Exception:
    EMAIL_REMETENTE = ""; EMAIL_DESTINATARIOS = []; _email_ok = False

# ─────────────────────────────────────────────────────────────────────────────
# DADOS DE REFERÊNCIA GEOGRÁFICA (apenas para marcadores no mapa)
# ─────────────────────────────────────────────────────────────────────────────
CIDADES_MAPA = {
    "Campo Grande":    (-20.4428, -54.6460),
    "Dourados":        (-22.2212, -54.8056),
    "Três Lagoas":     (-20.7519, -51.6783),
    "Corumbá":         (-19.0078, -57.6500),
    "Ponta Porã":      (-22.5361, -55.7253),
    "Naviraí":         (-23.0622, -54.1914),
    "Aquidauana":      (-20.4700, -55.7869),
    "Maracaju":        (-21.6108, -55.1681),
    "Coxim":           (-18.5069, -54.7600),
    "Chapadão do Sul": (-18.7919, -52.6267),
    "Sonora":          (-17.5583, -54.7611),
    "Costa Rica":      (-18.5447, -53.1278),
    "Rio Brilhante":   (-21.8028, -54.5447),
    "Nova Andradina":  (-22.2333, -53.3444),
    "Sidrolândia":     (-20.9319, -54.9600),
}

# ─────────────────────────────────────────────────────────────────────────────
# MODELOS METEOROLÓGICOS
# ─────────────────────────────────────────────────────────────────────────────
MODELOS_OPENMETEO = {
    "best_match":    "Best Match (Ensemble automático)",
    "gfs_seamless":  "GFS (NOAA — EUA)",
    "icon_seamless": "ICON (DWD — Alemanha)",
    "era5_seamless": "ERA5 (ECMWF — Reanálise)",
}

VARIAVEIS_HORARIAS = [
    "temperature_2m", "precipitation", "relativehumidity_2m",
    "windspeed_10m", "windgusts_10m", "shortwave_radiation",
    "dewpoint_2m", "apparent_temperature", "weathercode",
    "surface_pressure", "cape", "cloudcover",
]

LABELS_PT = {
    "temperature_2m":       "Temperatura (°C)",
    "precipitation":        "Precipitação (mm)",
    "relativehumidity_2m":  "Umidade Relativa (%)",
    "windspeed_10m":        "Vento (km/h)",
    "windgusts_10m":        "Rajada de Vento (km/h)",
    "shortwave_radiation":  "Radiação Solar (W/m²)",
    "dewpoint_2m":          "Ponto de Orvalho (°C)",
    "apparent_temperature": "Temperatura Aparente (°C)",
    "weathercode":          "Código de Tempo (WMO)",
    "surface_pressure":     "Pressão Superficial (hPa)",
    "cape":                 "CAPE (J/kg)",
    "cloudcover":           "Cobertura de Nuvens (%)",
}

CORES_VAR = {
    "temperature_2m":       "#f97316",
    "precipitation":        "#3b82f6",
    "relativehumidity_2m":  "#06b6d4",
    "windspeed_10m":        "#a78bfa",
    "windgusts_10m":        "#c084fc",
    "shortwave_radiation":  "#fbbf24",
    "dewpoint_2m":          "#34d399",
    "apparent_temperature": "#fb7185",
    "weathercode":          "#94a3b8",
    "surface_pressure":     "#a3e635",
    "cape":                 "#f43f5e",
    "cloudcover":           "#cbd5e1",
}

WCODE_MAP = {
    0:"☀️ Céu limpo", 1:"🌤 Poucas nuvens", 2:"⛅ Parcialmente nublado",
    3:"☁️ Nublado", 45:"🌫 Névoa", 48:"🌫 Névoa c/ geada",
    51:"🌦 Chuvisco fraco", 53:"🌦 Chuvisco", 55:"🌦 Chuvisco forte",
    61:"🌧 Chuva fraca", 63:"🌧 Chuva moderada", 65:"🌧 Chuva forte",
    71:"🌨 Neve fraca", 73:"🌨 Neve", 75:"🌨 Neve forte",
    80:"🌦 Pancadas fracas", 81:"⛈ Pancadas", 82:"⛈ Pancadas fortes",
    85:"🌨 Chuva de neve", 86:"🌨 Chuva de neve forte",
    95:"⛈ Tempestade", 96:"⛈ Tempestade c/ granizo leve",
    99:"⛈ Tempestade c/ granizo",
}

# CAD padrão fixo (solo médio/franco — referência EMBRAPA para MS)
CAD_PADRAO_MM = 65.0

# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULER — KEEP ALIVE
# ─────────────────────────────────────────────────────────────────────────────
def _keep_alive():
    try:
        requests.get("https://yamada-agro-ms.streamlit.app/", timeout=20)
    except Exception:
        pass

if "scheduler_started" not in st.session_state:
    try:
        _sched = BackgroundScheduler(timezone="America/Campo_Grande")
        _sched.add_job(_keep_alive, trigger=IntervalTrigger(minutes=5),
                       id="keepalive", replace_existing=True, max_instances=1)
        _sched.start()
        st.session_state["scheduler_started"] = True
        st.session_state["scheduler_obj"] = _sched
    except Exception:
        st.session_state["scheduler_started"] = True

# ─────────────────────────────────────────────────────────────────────────────
# INICIALIZAÇÃO DO SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULTS = {
    "lat_sel":    -20.4428,
    "lon_sel":    -54.6460,
    "analisado":  False,
    "dados_raw":  None,
    "df_main":    None,
    "ensemble_raw": {},
    "df_ic_cache":  {},
    "dados_nasa": None,
    "df_focos":   None,
    "janelas_df": None,
    "riscos":     None,
    "alertas":    None,
    "bh":         None,
    "modelo_used": "best_match",
    "dias_used":   7,
    "lat_used":    None,
    "lon_used":    None,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE COLETA DE DADOS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def buscar_openmeteo(lat: float, lon: float, modelo: str, dias: int = 7) -> dict:
    vars_h = ",".join(VARIAVEIS_HORARIAS)
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly={vars_h}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"weathercode,windspeed_10m_max,et0_fao_evapotranspiration,"
        f"precipitation_probability_max,uv_index_max"
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
def buscar_ensemble_openmeteo(lat: float, lon: float, dias: int = 7) -> dict:
    resultados = {}
    vars_h = "temperature_2m,precipitation,relativehumidity_2m,windspeed_10m"
    for mod in ["gfs_seamless", "icon_seamless", "best_match"]:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly={vars_h}"
            f"&timezone=America%2FCampo_Grande"
            f"&forecast_days={dias}&models={mod}"
        )
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            resultados[mod] = r.json()
        except Exception:
            pass
    return resultados


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_nasa_power(lat: float, lon: float) -> dict:
    fim    = datetime.now()
    inicio = fim - timedelta(days=30)
    url = (
        f"https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=T2M,RH2M,ALLSKY_SFC_SW_DWN,WS10M,PRECTOTCORR,GWETTOP,GWETROOT"
        f"&community=AG&longitude={lon}&latitude={lat}"
        f"&start={inicio.strftime('%Y%m%d')}&end={fim.strftime('%Y%m%d')}&format=JSON"
    )
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


@st.cache_data(ttl=1800, show_spinner=False)
def buscar_focos_inpe() -> pd.DataFrame:
    try:
        url = "https://queimadas.dgi.inpe.br/api/focos/"
        params = {"pais_id": 33, "estado_id": 50, "satelite": "AQUA_M-T"}
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    except Exception:
        # Dados simulados para demonstração quando API indisponível
        np.random.seed(42)
        n = 8
        return pd.DataFrame({
            "latitude":  np.random.uniform(-23.0, -17.5, n),
            "longitude": np.random.uniform(-57.0, -51.5, n),
            "frp":       np.random.uniform(5, 80, n),
            "_simulado": [True]*n,
        })


# ─────────────────────────────────────────────────────────────────────────────
# PROCESSAMENTO DOS DADOS BRUTOS
# ─────────────────────────────────────────────────────────────────────────────
def openmeteo_para_df(dados: dict) -> pd.DataFrame:
    if not dados or "hourly" not in dados or "_erro" in dados:
        return pd.DataFrame()
    h = dados["hourly"]
    times = pd.to_datetime(h["time"])
    df = pd.DataFrame({"datetime": times})
    for var in VARIAVEIS_HORARIAS:
        if var in h:
            df[var] = pd.to_numeric(h[var], errors="coerce")
    df = df.set_index("datetime")
    return df


def calcular_intervalo_confianca(ensemble: dict, var: str) -> pd.DataFrame:
    """
    Calcula spread entre modelos como proxy de incerteza da previsão.
    IC 68% ≈ ±1σ | IC 95% ≈ ±2σ
    Metodologia: Goswami et al. (2010); Buizza et al. (2005).
    """
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
    df_ens = pd.concat(series, axis=1)
    media  = df_ens.mean(axis=1)
    std    = df_ens.std(axis=1)
    result = pd.DataFrame({
        "media":     media,
        "std":       std,
        "min":       df_ens.min(axis=1),
        "max":       df_ens.max(axis=1),
        "ic68_low":  media - std,
        "ic68_high": media + std,
        "ic95_low":  media - 2*std,
        "ic95_high": media + 2*std,
    })
    result["cv_pct"] = (std / (media.abs() + 1e-6) * 100).round(1)
    return result


def calcular_janelas_defensivos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Janela de aplicação de defensivos — Critérios MAPA/Embrapa (Portaria 371/2020):
      Vento < 10 km/h | Temperatura < 30°C | UR > 55% | Precipitação = 0
    """
    if df.empty:
        return pd.DataFrame()
    df2 = df.copy().head(24)
    rest = pd.DataFrame(index=df2.index)
    rest["vento_ok"] = (df2.get("windspeed_10m",  pd.Series(5,  index=df2.index)) < 10).astype(int)
    rest["temp_ok"]  = (df2.get("temperature_2m", pd.Series(25, index=df2.index)) < 30).astype(int)
    rest["ur_ok"]    = (df2.get("relativehumidity_2m", pd.Series(65, index=df2.index)) > 55).astype(int)
    rest["chuva_ok"] = (df2.get("precipitation",  pd.Series(0,  index=df2.index)) == 0).astype(int)
    rest["n_ok"]     = rest[["vento_ok","temp_ok","ur_ok","chuva_ok"]].sum(axis=1)
    rest["status"]   = rest["n_ok"].apply(
        lambda x: "aberta" if x == 4 else ("parcial" if x >= 3 else "bloqueada"))
    rest["n_restricoes"] = 4 - rest["n_ok"]

    def motivo(row):
        m = []
        idx = row.name
        if not row["vento_ok"]:
            v = df2.get("windspeed_10m", pd.Series()).reindex([idx])
            m.append(f"Vento {v.iloc[0]:.0f}km/h" if not v.empty and pd.notna(v.iloc[0]) else "Vento alto")
        if not row["temp_ok"]:
            v = df2.get("temperature_2m", pd.Series()).reindex([idx])
            m.append(f"Temp {v.iloc[0]:.0f}°C" if not v.empty and pd.notna(v.iloc[0]) else "Temp alta")
        if not row["ur_ok"]:
            v = df2.get("relativehumidity_2m", pd.Series()).reindex([idx])
            m.append(f"UR {v.iloc[0]:.0f}%" if not v.empty and pd.notna(v.iloc[0]) else "UR baixa")
        if not row["chuva_ok"]:
            v = df2.get("precipitation", pd.Series()).reindex([idx])
            m.append(f"Chuva {v.iloc[0]:.1f}mm" if not v.empty and pd.notna(v.iloc[0]) else "Chuva")
        return " | ".join(m) if m else "✅ Todos OK"

    rest["motivo"] = rest.apply(motivo, axis=1)
    return rest


def calcular_risco_fitossanitario(df: pd.DataFrame) -> dict:
    """
    Risco de doenças foliares com base em horas consecutivas de condições favoráveis (48h).

    Ferrugem Asiática (Phakopsora pachyrhizi):
      T 15–30°C + UR >80% por ≥12h consecutivas
      (Del Ponte et al. 2006; Yorinori et al. 2005)

    Brusone (Magnaporthe oryzae):
      T 20–28°C + UR >90% por ≥10h consecutivas
      (Filippi & Prabhu 2001)
    """
    if df.empty:
        return {
            "ferrugem": {"doenca": "Ferrugem Asiática (Soja)", "horas_consecutivas": 0,
                         "horas_total": 0, "nivel": "Baixo", "limiar": 12,
                         "condicao": pd.Series(dtype=bool), "cor": "verde",
                         "emoji": "🍂", "referencia": "Del Ponte et al. (2006)"},
            "brusone":  {"doenca": "Brusone (Arroz/Trigo)", "horas_consecutivas": 0,
                         "horas_total": 0, "nivel": "Baixo", "limiar": 10,
                         "condicao": pd.Series(dtype=bool), "cor": "verde",
                         "emoji": "🌾", "referencia": "Filippi & Prabhu (2001)"},
        }
    df48 = df.head(48).copy()
    temp = df48.get("temperature_2m",      pd.Series(25, index=df48.index))
    umid = df48.get("relativehumidity_2m", pd.Series(70, index=df48.index))
    riscos = {}

    # ── Ferrugem Asiática ──
    cond_fer = (temp >= 15) & (temp <= 30) & (umid > 80)
    max_seq_fer = cur_fer = 0
    for v in cond_fer:
        if v: cur_fer += 1; max_seq_fer = max(max_seq_fer, cur_fer)
        else: cur_fer = 0
    nivel_fer = ("Crítico" if max_seq_fer >= 20 else
                 "Alto"    if max_seq_fer >= 16 else
                 "Médio"   if max_seq_fer >= 12 else "Baixo")
    riscos["ferrugem"] = {
        "doenca": "Ferrugem Asiática (Soja)",
        "horas_consecutivas": max_seq_fer,
        "horas_total": int(cond_fer.sum()),
        "nivel": nivel_fer, "limiar": 12, "condicao": cond_fer,
        "cor": "vermelho" if nivel_fer in ["Crítico","Alto"] else
               ("amarelo" if nivel_fer == "Médio" else "verde"),
        "emoji": "🍂", "referencia": "Del Ponte et al. (2006); Yorinori et al. (2005)",
    }

    # ── Brusone ──
    cond_bru = (temp >= 20) & (temp <= 28) & (umid > 90)
    max_seq_bru = cur_bru = 0
    for v in cond_bru:
        if v: cur_bru += 1; max_seq_bru = max(max_seq_bru, cur_bru)
        else: cur_bru = 0
    nivel_bru = ("Crítico" if max_seq_bru >= 18 else
                 "Alto"    if max_seq_bru >= 14 else
                 "Médio"   if max_seq_bru >= 10 else "Baixo")
    riscos["brusone"] = {
        "doenca": "Brusone (Arroz/Trigo)",
        "horas_consecutivas": max_seq_bru,
        "horas_total": int(cond_bru.sum()),
        "nivel": nivel_bru, "limiar": 10, "condicao": cond_bru,
        "cor": "vermelho" if nivel_bru in ["Crítico","Alto"] else
               ("amarelo" if nivel_bru == "Médio" else "verde"),
        "emoji": "🌾", "referencia": "Filippi & Prabhu (2001)",
    }
    return riscos


def calcular_alertas_meteo(df: pd.DataFrame, lat: float) -> list:
    """Gera alertas meteorológicos automáticos para os próximos 7 dias."""
    alertas = []
    if df.empty:
        return [{"nivel":"verde","icone":"✅",
                 "titulo":"🟢 Sem alertas ativos",
                 "msg":"Dados insuficientes para gerar alertas."}]
    try:
        df_daily = df.resample("D").agg({
            "temperature_2m":      ["max","min"],
            "precipitation":       "sum",
            "windgusts_10m":       "max",
            "cape":                "max",
            "relativehumidity_2m": "mean",
        }).head(7)

        for dia, row in df_daily.iterrows():
            try:
                tmin = row[("temperature_2m","min")]
                tmax = row[("temperature_2m","max")]
                pp   = row[("precipitation","sum")]
                raj  = row.get(("windgusts_10m","max"), None)
                cape = row.get(("cape","max"), None)
                data_str = dia.strftime("%d/%m")

                if pd.notna(tmin) and tmin < 5:
                    nivel = "vermelho" if tmin < 2 else "amarelo"
                    alertas.append({"nivel": nivel, "icone": "❄️",
                        "titulo": f"{'🔴 EMERGÊNCIA' if tmin<2 else '🟡 ALERTA'} — Risco de Geada ({data_str})",
                        "msg": f"Temperatura mínima prevista: {tmin:.1f}°C. Proteja culturas sensíveis imediatamente."})
                if pd.notna(pp) and pp > 40:
                    nivel = "vermelho" if pp > 80 else "amarelo"
                    alertas.append({"nivel": nivel, "icone": "⛈️",
                        "titulo": f"{'🔴' if pp>80 else '🟡'} Chuva Intensa ({data_str})",
                        "msg": f"{pp:.0f} mm acumulados. Risco de enxurrada, erosão e encharcamento."})
                if raj is not None and pd.notna(raj) and raj > 60:
                    alertas.append({"nivel":"vermelho","icone":"💨",
                        "titulo": f"🔴 Rajada de Vento Forte ({data_str})",
                        "msg": f"Rajada prevista: {raj:.0f} km/h. Risco de danos a culturas e estruturas."})
                if cape is not None and pd.notna(cape) and cape > 1500:
                    alertas.append({"nivel":"vermelho","icone":"⚡",
                        "titulo": f"🔴 Risco de Tempestade Severa ({data_str})",
                        "msg": f"CAPE: {cape:.0f} J/kg. Alta energia convectiva disponível. Risco de granizo e raios."})
            except Exception:
                continue

        dias_secos = int((df_daily[("precipitation","sum")] < 1).sum())
        if dias_secos >= 5:
            alertas.append({"nivel":"amarelo","icone":"🌵",
                "titulo": f"🟡 Veranico — {dias_secos} dias consecutivos sem chuva significativa",
                "msg": "Déficit hídrico crescente. Monitore umidade do solo e intensifique a irrigação."})
    except Exception:
        pass

    if not alertas:
        alertas.append({"nivel":"verde","icone":"✅",
            "titulo": "🟢 Condições meteorológicas favoráveis",
            "msg": "Nenhum alerta ativo para as próximas 72 horas. Condições adequadas para operações de campo."})
    return alertas


def calcular_balanco_hidrico(df: pd.DataFrame, cad_mm: float = CAD_PADRAO_MM) -> dict:
    """
    Balanço hídrico Thornthwaite-Mather simplificado.
    ETo estimada pelo método de Hargreaves-Samani (1985).
    CAD padrão = 65mm (solo médio/franco — referência EMBRAPA para o MS).
    """
    if df.empty:
        return {}
    try:
        df_d = df.resample("D").agg({"precipitation": "sum"}).head(7)
        eto_lista = []
        for dia in df_d.index:
            try:
                sub  = df[df.index.date == dia.date()]
                tmax = sub["temperature_2m"].max()
                tmin = sub["temperature_2m"].min()
                ra   = sub.get("shortwave_radiation", pd.Series(dtype=float)).mean()
                if pd.isna(ra) or ra == 0: ra = 200
                eto = 0.0023 * max(0, tmax - tmin)**0.5 * ((tmax + tmin) / 2 + 17.8) * (ra / 2450)
                eto_lista.append(max(0, float(eto)))
            except Exception:
                eto_lista.append(3.5)

        arm = cad_mm * 0.5
        resultados = []
        for eto, pp in zip(eto_lista, df_d["precipitation"].fillna(0)):
            bal = float(pp) - eto
            if bal >= 0:
                arm_n = min(arm + bal, cad_mm)
                exc, def_, etr = arm + bal - arm_n, 0.0, eto
            else:
                arm_n = max(0.0, arm * np.exp(bal / max(cad_mm, 1)))
                exc = 0.0
                etr = float(pp) + (arm - arm_n)
                def_ = eto - etr
            resultados.append({"arm": round(arm_n,2), "def": round(def_,2),
                                "exc": round(exc,2),  "etr": round(etr,2),
                                "eto": round(eto,2),  "pp":  round(float(pp),2)})
            arm = arm_n

        if not resultados:
            return {}
        hoje    = resultados[0]
        arm_pct = round(hoje["arm"] / cad_mm * 100, 1) if cad_mm > 0 else 0
        if arm_pct >= 70:
            rec, nivel = "✅ Solo bem suprido. Irrigação dispensável.", "verde"
        elif arm_pct >= 40:
            rec, nivel = f"💧 Aplicar {hoje['def']*1.1:.1f} mm para repor o déficit hídrico.", "amarelo"
        else:
            rec, nivel = f"🚿 Déficit crítico: {hoje['def']:.1f} mm. Irrigação urgente.", "vermelho"

        return {"arm_mm": hoje["arm"], "arm_pct": arm_pct, "def_mm": hoje["def"],
                "etr_mm": hoje["etr"], "eto_mm": hoje["eto"], "pp_mm": hoje["pp"],
                "cad_mm": cad_mm, "recomendacao": rec, "nivel": nivel, "serie": resultados}
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE VISUALIZAÇÃO
# ─────────────────────────────────────────────────────────────────────────────
def _ax_base(ax):
    """Aplica estilo escuro padrão a um eixo matplotlib."""
    ax.set_facecolor("#111827")
    ax.tick_params(colors="#9ca3af", labelsize=8)
    for sp in ax.spines.values():
        sp.set_edgecolor("#374151")
    ax.grid(True, color="#1f2937", linewidth=0.6, alpha=0.7)


def fig_variavel_com_ic(df_main: pd.DataFrame, var: str,
                         df_ic: pd.DataFrame = None) -> Figure:
    fig, ax = plt.subplots(figsize=(12, 4), facecolor="#0d1117")
    _ax_base(ax)
    cor   = CORES_VAR.get(var, "#60a5fa")
    label = LABELS_PT.get(var, var)

    if var not in df_main.columns or df_main.empty:
        ax.text(0.5, 0.5, "Dados não disponíveis", transform=ax.transAxes,
                ha="center", va="center", color="white", fontsize=12)
        return fig

    serie = df_main[var].dropna()
    x     = serie.index

    # Faixas de intervalo de confiança
    if df_ic is not None and not df_ic.empty:
        ic_re = df_ic.reindex(x, method="nearest")
        ax.fill_between(x, ic_re["ic95_low"], ic_re["ic95_high"],
                        alpha=0.10, color=cor, label="IC 95%")
        ax.fill_between(x, ic_re["ic68_low"], ic_re["ic68_high"],
                        alpha=0.20, color=cor, label="IC 68%")

    if var == "precipitation":
        ax.bar(x, serie.values, width=1/24, color=cor, alpha=0.8,
               align="center", label=label)
    else:
        ax.plot(x, serie.values, color=cor, linewidth=2.0, label=label, zorder=5)
        ax.fill_between(x, serie.values, alpha=0.10, color=cor)

    # Limiares agronômicos relevantes
    limiares = {
        "temperature_2m":      [(5,  "#60a5fa", "Risco geada (5°C)"),
                                 (30, "#f97316", "Lim. defensivos (30°C)"),
                                 (38, "#ef4444", "Estresse calor (38°C)")],
        "windspeed_10m":       [(10, "#fbbf24", "Lim. defensivos (10 km/h)"),
                                 (40, "#ef4444", "Dano potencial (40 km/h)")],
        "relativehumidity_2m": [(55, "#f43f5e", "Lim. defensivos (55%)"),
                                 (80, "#fb923c", "Risco ferrugem (80%)")],
        "cape":                [(500,  "#fbbf24","CAPE fraco (500 J/kg)"),
                                 (1500, "#f97316","CAPE moderado (1500 J/kg)"),
                                 (2500, "#ef4444","CAPE alto (2500 J/kg)")],
    }
    for lim_val, lim_cor, lim_label in limiares.get(var, []):
        ax.axhline(lim_val, color=lim_cor, linewidth=0.9,
                   linestyle="--", alpha=0.7, label=lim_label)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%Hh"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    ax.set_ylabel(label, color="#9ca3af", fontsize=9)
    ax.set_title(label, color="white", fontsize=10, fontweight="bold", pad=8)

    handles, labels_leg = ax.get_legend_handles_labels()
    ax.legend(handles, labels_leg, fontsize=7, facecolor="#111827",
              labelcolor="white", edgecolor="#374151", loc="upper right")
    plt.tight_layout(pad=0.5)
    return fig


def fig_multiplas_variaveis(df: pd.DataFrame, vars_list: list) -> Figure:
    n = len(vars_list)
    if n == 0:
        return None
    fig, axes = plt.subplots(n, 1, figsize=(12, 3.2*n), facecolor="#0d1117", sharex=True)
    if n == 1:
        axes = [axes]
    for ax, var in zip(axes, vars_list):
        _ax_base(ax)
        cor = CORES_VAR.get(var, "#60a5fa")
        lbl = LABELS_PT.get(var, var)
        if var not in df.columns:
            ax.text(0.5, 0.5, f"{lbl} — sem dados", transform=ax.transAxes,
                    ha="center", va="center", color="#9ca3af", fontsize=9)
            continue
        serie = df[var].dropna()
        if var == "precipitation":
            ax.bar(serie.index, serie.values, width=1/24, color=cor, alpha=0.85)
        else:
            ax.plot(serie.index, serie.values, color=cor, linewidth=1.8)
            ax.fill_between(serie.index, serie.values, alpha=0.10, color=cor)
        ax.set_ylabel(lbl, color="#9ca3af", fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%Hh"))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
    plt.tight_layout(pad=0.5)
    return fig


def fig_matriz_alertas(df_main: pd.DataFrame) -> Figure:
    """
    Matriz hora × variável para as próximas 24h.
    Verde = OK | Amarelo = Atenção | Vermelho = Risco/Bloqueado
    """
    if df_main.empty:
        return None
    df24  = df_main.head(24).copy()
    n_h   = min(24, len(df24))
    horas = [df24.index[i].strftime("%Hh") for i in range(n_h)]

    temp_h = df24.get("temperature_2m",      pd.Series(25, index=df24.index))
    ur_h   = df24.get("relativehumidity_2m", pd.Series(70, index=df24.index))
    vt_h   = df24.get("windspeed_10m",       pd.Series(5,  index=df24.index))
    pp_h   = df24.get("precipitation",       pd.Series(0,  index=df24.index))

    colunas = ["Temp (°C)", "UR (%)", "Vento\n(km/h)", "Chuva\n(mm)",
               "Ferrugem", "Brusone", "Janela\nDefens."]
    matriz  = np.zeros((n_h, len(colunas)))

    for i in range(n_h):
        t  = float(temp_h.iloc[i]) if i < len(temp_h) and pd.notna(temp_h.iloc[i]) else 25
        ur = float(ur_h.iloc[i])   if i < len(ur_h)   and pd.notna(ur_h.iloc[i])   else 70
        vt = float(vt_h.iloc[i])   if i < len(vt_h)   and pd.notna(vt_h.iloc[i])   else 5
        pp = float(pp_h.iloc[i])   if i < len(pp_h)   and pd.notna(pp_h.iloc[i])   else 0

        matriz[i, 0] = 0 if t < 30 else 2
        matriz[i, 1] = 0 if ur > 55 else 2
        matriz[i, 2] = 0 if vt < 10 else (1 if vt < 15 else 2)
        matriz[i, 3] = 0 if pp == 0 else (1 if pp < 2 else 2)
        matriz[i, 4] = 2 if (15 <= t <= 30 and ur > 80) else 0    # Ferrugem
        matriz[i, 5] = 2 if (20 <= t <= 28 and ur > 90) else 0    # Brusone
        ok_cnt = (t < 30) + (ur > 55) + (vt < 10) + (pp == 0)
        matriz[i, 6] = 0 if ok_cnt == 4 else (1 if ok_cnt == 3 else 2)

    cmap = mcolors.ListedColormap(["#22c55e", "#fbbf24", "#ef4444"])
    norm = mcolors.BoundaryNorm([0, 0.5, 1.5, 2.5], cmap.N)

    fig, ax = plt.subplots(figsize=(12, max(6, n_h * 0.30)), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")
    ax.imshow(matriz, cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(range(len(colunas)))
    ax.set_xticklabels(colunas, fontsize=8.5, color="white", fontweight="bold")
    ax.set_yticks(range(n_h))
    ax.set_yticklabels(horas, fontsize=7, color="#9ca3af")
    ax.set_title("Matriz de Risco Hora × Variável — Próximas 24h",
                 color="white", fontsize=11, fontweight="bold", pad=10)

    for i in range(n_h):
        for j in range(len(colunas)):
            val = matriz[i, j]
            txt = "✓" if val == 0 else ("!" if val == 1 else "✗")
            ax.text(j, i, txt, ha="center", va="center",
                    fontsize=7.5, color="#000", fontweight="bold")

    p_verde  = mpatches.Patch(facecolor="#22c55e", label="✓ Favorável / OK")
    p_amar   = mpatches.Patch(facecolor="#fbbf24", label="! Atenção")
    p_verm   = mpatches.Patch(facecolor="#ef4444", label="✗ Risco / Bloqueado")
    ax.legend(handles=[p_verde, p_amar, p_verm],
              loc="lower right", fontsize=8, facecolor="#111827",
              labelcolor="white", edgecolor="#374151",
              bbox_to_anchor=(1.0, -0.08))
    for sp in ax.spines.values():
        sp.set_visible(False)
    plt.tight_layout(pad=0.8)
    return fig


def fig_confianca_modelos(ensemble: dict, var: str) -> Figure:
    """Spread entre modelos com painel de coeficiente de variação (incerteza)."""
    series = {}
    for mod, dados in ensemble.items():
        if "hourly" in dados and var in dados["hourly"]:
            s = pd.Series(
                pd.to_numeric(dados["hourly"][var], errors="coerce"),
                index=pd.to_datetime(dados["hourly"]["time"]),
                name=MODELOS_OPENMETEO.get(mod, mod),
            )
            series[MODELOS_OPENMETEO.get(mod, mod)] = s
    if len(series) < 2:
        return None

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), facecolor="#0d1117",
                                    gridspec_kw={"height_ratios": [3, 1]})
    for ax in [ax1, ax2]:
        _ax_base(ax)

    colors_mod = ["#60a5fa", "#f97316", "#34d399", "#a78bfa"]
    df_all = pd.concat(series.values(), axis=1)
    media  = df_all.mean(axis=1)
    std    = df_all.std(axis=1)
    cv     = (std / (media.abs() + 1e-6) * 100)

    ax1.fill_between(media.index, media - 2*std, media + 2*std,
                     alpha=0.10, color="#60a5fa", label="IC 95%")
    ax1.fill_between(media.index, media - std, media + std,
                     alpha=0.20, color="#60a5fa", label="IC 68%")
    for (nome, s), cor in zip(series.items(), colors_mod):
        ax1.plot(s.index, s.values, color=cor, linewidth=1.2,
                 alpha=0.8, label=nome, linestyle="--")
    ax1.plot(media.index, media.values, color="white", linewidth=2.2,
             label="Média dos modelos", zorder=5)
    ax1.set_ylabel(LABELS_PT.get(var, var), color="#9ca3af", fontsize=9)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%Hh"))
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=12))
    ax1.legend(fontsize=7, facecolor="#111827", labelcolor="white",
               edgecolor="#374151", loc="upper right", ncol=2)
    ax1.set_title(f"Spread entre modelos — {LABELS_PT.get(var, var)}",
                  color="white", fontsize=10, fontweight="bold")

    cv_colors = ["#22c55e" if v < 10 else ("#fbbf24" if v < 25 else "#ef4444")
                 for v in cv.values]
    ax2.bar(cv.index, cv.values, width=1/24, color=cv_colors, alpha=0.85)
    ax2.axhline(10, color="#22c55e", linestyle="--", linewidth=0.8, alpha=0.6, label="Alta (<10%)")
    ax2.axhline(25, color="#ef4444", linestyle="--", linewidth=0.8, alpha=0.6, label="Baixa (>25%)")
    ax2.set_ylabel("CV % (incerteza)", color="#9ca3af", fontsize=8)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax2.xaxis.set_major_locator(mdates.DayLocator())
    ax2.legend(fontsize=7, facecolor="#111827", labelcolor="white",
               edgecolor="#374151", loc="upper right")
    plt.tight_layout(pad=0.5)
    return fig


def df_previsao_display(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cols_show = {k: v for k, v in LABELS_PT.items() if k in df.columns}
    df_disp   = df[list(cols_show.keys())].copy()
    df_disp.columns = [cols_show[c] for c in df_disp.columns]
    df_disp.index   = df_disp.index.strftime("%d/%m %Hh")
    df_disp.index.name = "Data/Hora"
    if "Código de Tempo (WMO)" in df_disp.columns:
        df_disp["Condição"] = df_disp["Código de Tempo (WMO)"].apply(
            lambda x: WCODE_MAP.get(int(x), f"Cód {int(x)}") if pd.notna(x) else "—")
        df_disp.drop(columns=["Código de Tempo (WMO)"], inplace=True)
    return df_disp.round(1)


# ─────────────────────────────────────────────────────────────────────────────
# MAPA FOLIUM
# ─────────────────────────────────────────────────────────────────────────────
def criar_mapa(lat_sel: float, lon_sel: float) -> folium.Map:
    m = folium.Map(
        location=[-20.5, -54.5],
        zoom_start=7,
        tiles="OpenStreetMap",
        control_scale=True,
    )
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="🛰️ Satélite",
        overlay=False,
        control=True,
    ).add_to(m)

    # Marcadores de cidades (referência visual apenas)
    for nome, (lat, lon) in CIDADES_MAPA.items():
        folium.CircleMarker(
            location=[lat, lon], radius=5,
            color=VERDE_MEDIO, fill=True,
            fill_color=VERDE_MEDIO, fill_opacity=0.6,
            tooltip=f"🏙️ {nome} ({lat:.4f}, {lon:.4f})",
            popup=folium.Popup(
                f"<b>{nome}</b><br><small>Clique em qualquer ponto para selecionar</small>",
                max_width=180,
            ),
        ).add_to(m)

    # Ponto de análise atual
    folium.Marker(
        location=[lat_sel, lon_sel],
        popup=f"<b>📌 Ponto de Análise</b><br>Lat: {lat_sel:.4f}<br>Lon: {lon_sel:.4f}",
        tooltip=f"📌 Análise: ({lat_sel:.4f}, {lon_sel:.4f})",
        icon=folium.Icon(color="red", icon="star", prefix="fa"),
    ).add_to(m)

    folium.Rectangle(
        bounds=[[-23.67, -57.65], [-17.16, -50.92]],
        color=VERDE_MEDIO, fill=False, weight=1.5,
        dash_array="6", tooltip="Mato Grosso do Sul",
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return m


# ─────────────────────────────────────────────────────────────────────────────
# E-MAIL
# ─────────────────────────────────────────────────────────────────────────────
def gerar_html_relatorio(lat, lon, df, alertas, riscos, bh, janelas_list, nome_local="") -> str:
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    loc   = nome_local or f"{abs(lat):.4f}°S, {abs(lon):.4f}°W"

    def card(titulo, valor, cor="#1B4D2E"):
        return (f"<div style='flex:1;min-width:110px;background:#fff;border-radius:10px;"
                f"border-top:4px solid {cor};padding:12px 10px;box-shadow:0 2px 8px rgba(0,0,0,0.08);text-align:center;'>"
                f"<div style='font-size:11px;color:#777;'>{titulo}</div>"
                f"<div style='font-size:20px;font-weight:bold;color:#222;'>{valor}</div></div>")

    cards = ""
    if not df.empty:
        try:
            cards += card("🌡 Temp Atual",   f"{df['temperature_2m'].iloc[0]:.1f}°C", "#e65100")
            cards += card("🌧 Chuva 24h",    f"{df['precipitation'].iloc[:24].sum():.1f}mm", "#1565c0")
            cards += card("💧 UR Atual",     f"{df['relativehumidity_2m'].iloc[0]:.0f}%", "#0277bd")
            cards += card("💨 Vento",        f"{df['windspeed_10m'].iloc[0]:.0f}km/h", "#6a1b9a")
        except Exception:
            pass

    _cor_al = {"verde":"#e8f5e9","amarelo":"#fff8e1","vermelho":"#ffebee"}
    _brd_al = {"verde":"#43a047","amarelo":"#fbc02d","vermelho":"#e53935"}
    html_alertas = ""
    for al in alertas:
        bg  = _cor_al.get(al["nivel"], "#f5f5f5")
        brd = _brd_al.get(al["nivel"], "#9e9e9e")
        html_alertas += (f"<div style='background:{bg};border-left:5px solid {brd};"
                         f"border-radius:6px;padding:10px 14px;margin:5px 0;'>"
                         f"<b>{al['icone']} {al['titulo']}</b><br>"
                         f"<span style='font-size:12px;'>{al['msg']}</span></div>")

    html_riscos = ""
    for r in riscos.values():
        bg  = _cor_al.get(r["cor"], "#f5f5f5")
        brd = _brd_al.get(r["cor"], "#9e9e9e")
        html_riscos += (f"<div style='background:{bg};border-left:5px solid {brd};"
                        f"border-radius:6px;padding:10px 14px;margin:5px 0;'>"
                        f"<b>{r['emoji']} {r['doenca']} — Risco {r['nivel']}</b><br>"
                        f"<span style='font-size:12px;'>{r['horas_consecutivas']}h consecutivas favoráveis "
                        f"(limiar: {r['limiar']}h) | Ref.: {r['referencia']}</span></div>")

    bh_html = ""
    if bh:
        bh_html = (f"<p style='font-size:13px;'>ARM: {bh.get('arm_mm',0):.1f}mm "
                   f"({bh.get('arm_pct',0):.0f}% CAD) | Déficit: {bh.get('def_mm',0):.1f}mm<br>"
                   f"<b>Recomendação:</b> {bh.get('recomendacao','—')}</p>")

    n_ab = sum(1 for j in janelas_list if j.get("status") == "aberta")
    n_bl = sum(1 for j in janelas_list if j.get("status") == "bloqueada")

    return f"""<html><body style='font-family:Arial,sans-serif;background:#f0f2f5;padding:20px;margin:0;'>
  <div style='max-width:720px;margin:auto;background:#fff;border-radius:14px;box-shadow:0 4px 18px rgba(0,0,0,.12);overflow:hidden;'>
    <div style='background:linear-gradient(135deg,#1B4D2E,#3DA63A);padding:28px 32px;text-align:center;'>
      <h1 style='color:white;margin:0;font-size:22px;'>🌿 Yamada Engenharia</h1>
      <p style='color:rgba(255,255,255,0.85);margin:6px 0 0;font-size:14px;'>Relatório Agroclimático — {loc}</p>
    </div>
    <div style='padding:28px 32px;'>
      <p style='color:#777;font-size:12px;'>Gerado em {agora}</p>
      <h3 style='color:#1B4D2E;border-bottom:2px solid #3DA63A;padding-bottom:6px;'>📊 Condições Atuais</h3>
      <div style='display:flex;flex-wrap:wrap;gap:10px;margin-bottom:22px;'>{cards}</div>
      <h3 style='color:#1B4D2E;border-bottom:2px solid #3DA63A;padding-bottom:6px;'>⚠️ Alertas</h3>
      {html_alertas}
      <h3 style='color:#1B4D2E;border-bottom:2px solid #3DA63A;padding-bottom:6px;margin-top:20px;'>🍂 Risco Fitossanitário</h3>
      {html_riscos}
      <h3 style='color:#1B4D2E;border-bottom:2px solid #3DA63A;padding-bottom:6px;margin-top:20px;'>🧪 Janela de Defensivos (24h)</h3>
      <p style='font-size:13px;'>✅ Horas ideais: <b>{n_ab}</b> | ❌ Horas bloqueadas: <b>{n_bl}</b></p>
      <h3 style='color:#1B4D2E;border-bottom:2px solid #3DA63A;padding-bottom:6px;margin-top:20px;'>💧 Balanço Hídrico</h3>
      {bh_html}
      <p style='color:#bbb;font-size:10px;margin-top:28px;border-top:1px solid #eee;padding-top:12px;text-align:center;'>
        Dados: Open-Meteo (GFS/ICON/ERA5) · NASA POWER · INPE<br>
        CAD padrão 65mm (solo médio/franco, EMBRAPA) · MVP v4.1 · {agora}
      </p>
    </div>
  </div>
</body></html>"""


def enviar_email(html: str, assunto: str, extras: list = None) -> tuple:
    if not _email_ok:
        return False, "E-mail não configurado nos secrets.toml"
    try:
        dests = list(EMAIL_DESTINATARIOS)
        if extras:
            dests += [e for e in extras if "@" in e and e not in dests]
        msg = MIMEMultipart("mixed")
        msg["Subject"] = assunto
        msg["From"]    = EMAIL_REMETENTE
        msg["To"]      = ", ".join(dests)
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(html, "html"))
        msg.attach(alt)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
            srv.login(EMAIL_REMETENTE, st.secrets["email"]["senha_app"])
            srv.sendmail(EMAIL_REMETENTE, dests, msg.as_string())
        return True, f"Enviado para {', '.join(dests)}"
    except Exception as e:
        return False, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# INTERFACE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
def main():

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="yamada-header">
      <h1>🌿 Yamada Engenharia</h1>
      <p>Plataforma de Monitoramento Agroclimático — Mato Grosso do Sul</p>
      <p style="font-size:0.75rem;color:rgba(255,255,255,0.5);">
        Open-Meteo (GFS · ICON · ERA5) · NASA POWER · INPE · v4.1
      </p>
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # SIDEBAR
    # ─────────────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:8px 0 18px;">
          <div style="font-family:'Montserrat',sans-serif;font-weight:900;
                      font-size:1.15rem;color:#a5d6a7;">YAMADA</div>
          <div style="font-size:0.7rem;color:#81c784;letter-spacing:2px;">ENGENHARIA</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("---")

        # ── Coordenadas manuais ──────────────────────────────────────────────
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;'
                    'font-size:0.88rem;">📍 COORDENADAS DO PONTO</p>',
                    unsafe_allow_html=True)
        st.caption("Digite manualmente ou clique no mapa abaixo.")

        lat_input = st.number_input(
            "Latitude", value=float(st.session_state["lat_sel"]),
            min_value=-23.8, max_value=-17.0, step=0.0001, format="%.4f",
            key="lat_input_num",
            help="Latitudes válidas para o MS: -23.8 a -17.0")

        lon_input = st.number_input(
            "Longitude", value=float(st.session_state["lon_sel"]),
            min_value=-57.8, max_value=-50.8, step=0.0001, format="%.4f",
            key="lon_input_num",
            help="Longitudes válidas para o MS: -57.8 a -50.8")

        # Detecta alteração manual e invalida análise anterior
        coords_changed = (
            abs(lat_input - st.session_state["lat_sel"]) > 0.0001 or
            abs(lon_input - st.session_state["lon_sel"]) > 0.0001
        )
        if coords_changed:
            st.session_state["lat_sel"]   = round(lat_input, 4)
            st.session_state["lon_sel"]   = round(lon_input, 4)
            st.session_state["analisado"] = False

        # Indicador do ponto atual
        st.markdown(
            f'<div class="status-ponto">'
            f'<span style="color:#a5d6a7;font-size:0.78rem;">Ponto selecionado</span><br>'
            f'<span style="color:#ffffff;font-weight:700;font-size:0.9rem;">'
            f'{abs(st.session_state["lat_sel"]):.4f}°S &nbsp;|&nbsp; '
            f'{abs(st.session_state["lon_sel"]):.4f}°W</span>'
            f'</div>',
            unsafe_allow_html=True)

        st.markdown("---")

        # ── Configurações da análise ─────────────────────────────────────────
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;'
                    'font-size:0.88rem;">⚙️ CONFIGURAÇÕES</p>',
                    unsafe_allow_html=True)

        modelo_sel = st.selectbox(
            "Modelo meteorológico",
            list(MODELOS_OPENMETEO.keys()),
            format_func=lambda k: MODELOS_OPENMETEO[k],
            index=0, label_visibility="collapsed",
            help="Best Match usa ensemble ponderado. GFS e ICON têm boa performance no Centro-Oeste.")

        dias_prev = st.slider(
            "Horizonte de previsão (dias)", 3, 7, 7,
            help="Confiabilidade decresce significativamente após D+4.")

        calcular_ic = st.checkbox(
            "Calcular IC multi-modelo (+30s)",
            value=True,
            help="Faixa de incerteza via spread GFS/ICON/Best Match (Buizza et al. 2005)")

        st.markdown("---")

        # ── E-mail ───────────────────────────────────────────────────────────
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;'
                    'font-size:0.88rem;">📧 E-MAIL</p>',
                    unsafe_allow_html=True)
        if _email_ok:
            st.caption(f"✅ {', '.join(EMAIL_DESTINATARIOS)}")
        else:
            st.caption("⚠️ Configure [email] no secrets.toml")
        st.markdown("---")

        # ── Botão principal ──────────────────────────────────────────────────
        botao_analise = st.button("🚀  GERAR ANÁLISE", use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # MAPA INTERATIVO (renderizado antes do gatilho de análise)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="secao-titulo">🗺️ Selecione o Ponto de Análise no Mapa</div>',
                unsafe_allow_html=True)
    st.caption(
        "**Clique em qualquer ponto** do Mato Grosso do Sul para definir as coordenadas. "
        "Os marcadores verdes indicam cidades de referência. "
        "Após selecionar, clique em **GERAR ANÁLISE** na barra lateral.")

    mapa    = criar_mapa(st.session_state["lat_sel"], st.session_state["lon_sel"])
    map_out = st_folium(mapa, width="100%", height=430,
                         returned_objects=["last_clicked"],
                         key="mapa_principal")

    # Atualiza coordenadas a partir do clique no mapa
    if map_out and map_out.get("last_clicked"):
        clk = map_out["last_clicked"]
        lat_c = round(clk["lat"], 4)
        lon_c = round(clk["lng"], 4)
        # Bounding box MS com margem
        if -24.2 <= lat_c <= -16.8 and -58.2 <= lon_c <= -50.5:
            if (abs(lat_c - st.session_state["lat_sel"]) > 0.001 or
                    abs(lon_c - st.session_state["lon_sel"]) > 0.001):
                st.session_state["lat_sel"]   = lat_c
                st.session_state["lon_sel"]   = lon_c
                st.session_state["analisado"] = False
                st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # GATILHO DE ANÁLISE
    # ─────────────────────────────────────────────────────────────────────────
    if botao_analise:
        st.session_state["analisado"] = True
        # Salva parâmetros usados para possível re-execução
        st.session_state["lat_used"]    = st.session_state["lat_sel"]
        st.session_state["lon_used"]    = st.session_state["lon_sel"]
        st.session_state["modelo_used"] = modelo_sel
        st.session_state["dias_used"]   = dias_prev

    if not st.session_state["analisado"]:
        st.markdown("""
        <div class="alert-azul" style="margin-top:16px;">
          <b>👆 Como usar esta plataforma:</b><br>
          <span style="font-size:0.88rem;">
            1. Clique em um ponto no mapa ou informe as coordenadas manualmente na barra lateral.<br>
            2. Escolha o modelo meteorológico e o horizonte de previsão.<br>
            3. Clique em <b>🚀 GERAR ANÁLISE</b> para obter o relatório completo.
          </span>
        </div>""", unsafe_allow_html=True)
        st.stop()

    # Recupera parâmetros fixados no momento do clique em GERAR ANÁLISE
    lat        = st.session_state.get("lat_used", st.session_state["lat_sel"])
    lon        = st.session_state.get("lon_used", st.session_state["lon_sel"])
    modelo_sel = st.session_state.get("modelo_used", modelo_sel)
    dias_prev  = st.session_state.get("dias_used",   dias_prev)

    # ─────────────────────────────────────────────────────────────────────────
    # COLETA E PROCESSAMENTO DE DADOS
    # ─────────────────────────────────────────────────────────────────────────
    progresso = st.progress(0, text="Inicializando coleta de dados...")

    with st.spinner(""):
        progresso.progress(10, text=f"🌤 Coletando Open-Meteo ({MODELOS_OPENMETEO[modelo_sel]})...")
        dados_raw = buscar_openmeteo(lat, lon, modelo_sel, dias_prev)

        if "_erro" in dados_raw:
            st.error(f"❌ Erro ao acessar Open-Meteo: {dados_raw['_erro']}")
            st.session_state["analisado"] = False
            st.stop()

        df_main = openmeteo_para_df(dados_raw)
        if df_main.empty:
            st.error("❌ Nenhum dado retornado pela API. Verifique as coordenadas e tente novamente.")
            st.session_state["analisado"] = False
            st.stop()

        progresso.progress(25, text="📊 Calculando ensemble multi-modelo...")
        ensemble_raw = {}
        df_ic_cache  = {}
        if calcular_ic:
            ensemble_raw = buscar_ensemble_openmeteo(lat, lon, dias_prev)
            for v in ["temperature_2m","precipitation","relativehumidity_2m","windspeed_10m"]:
                df_ic_cache[v] = calcular_intervalo_confianca(ensemble_raw, v)

        progresso.progress(50, text="☀️ Consultando NASA POWER (solo/radiação)...")
        dados_nasa = buscar_nasa_power(lat, lon)

        progresso.progress(65, text="🔥 Consultando INPE Queimadas...")
        df_focos = buscar_focos_inpe()

        progresso.progress(78, text="📐 Processando análises agronômicas...")
        janelas_df = calcular_janelas_defensivos(df_main)
        riscos     = calcular_risco_fitossanitario(df_main)
        alertas    = calcular_alertas_meteo(df_main, lat)
        bh         = calcular_balanco_hidrico(df_main, CAD_PADRAO_MM)

        progresso.progress(95, text="🎨 Renderizando painéis...")

    progresso.progress(100, text="✅ Análise concluída!")

    # ─────────────────────────────────────────────────────────────────────────
    # BANNER DO PONTO ANALISADO
    # ─────────────────────────────────────────────────────────────────────────
    wc_atual = ""
    if "weathercode" in df_main.columns and not df_main.empty:
        wc = df_main["weathercode"].dropna()
        if not wc.empty:
            wc_atual = WCODE_MAP.get(int(wc.iloc[0]), "")

    st.markdown(f"""
    <div style="background:linear-gradient(90deg,{VERDE_ESCURO},{VERDE_MEDIO});
                border-radius:10px;padding:14px 22px;margin:16px 0 20px 0;">
      <span style="color:white;font-family:Montserrat;font-weight:700;font-size:1.1rem;">
        📍 {abs(lat):.4f}°S, {abs(lon):.4f}°W
      </span>
      <span style="color:rgba(255,255,255,0.7);font-size:0.82rem;margin-left:14px;">
        Modelo: {MODELOS_OPENMETEO[modelo_sel]} · {dias_prev} dias ·
        {datetime.now().strftime('%d/%m/%Y %H:%M')} · {wc_atual}
      </span>
    </div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTRICAS RÁPIDAS
    # ─────────────────────────────────────────────────────────────────────────
    try:
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        with c1: st.metric("🌡 Temperatura",
                            f"{df_main['temperature_2m'].iloc[0]:.1f}°C")
        with c2: st.metric("🌧 Chuva 24h",
                            f"{df_main['precipitation'].iloc[:24].sum():.1f} mm")
        with c3: st.metric("💧 Umidade",
                            f"{df_main['relativehumidity_2m'].iloc[0]:.0f}%")
        with c4: st.metric("💨 Vento",
                            f"{df_main['windspeed_10m'].iloc[0]:.0f} km/h")
        with c5:
            rad_val = df_main.get("shortwave_radiation", pd.Series([0]))
            st.metric("☀️ Radiação",
                      f"{rad_val.iloc[0]:.0f} W/m²")
        with c6:
            cape_val = df_main.get("cape", pd.Series([0]))
            st.metric("⚡ CAPE",
                      f"{cape_val.iloc[0]:.0f} J/kg")
    except Exception:
        pass

    # ═════════════════════════════════════════════════════════════════════════
    # ABAS PRINCIPAIS
    # ═════════════════════════════════════════════════════════════════════════
    aba1, aba2, aba3, aba4, aba5 = st.tabs([
        "📈 Previsão Meteorológica",
        "🌡️ Climatologia & Solo",
        "🌾 Síntese Agrícola",
        "⚠️ Alertas & Risco",
        "📧 Relatório & E-mail",
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 1 — PREVISÃO METEOROLÓGICA HORÁRIA
    # ─────────────────────────────────────────────────────────────────────────
    with aba1:
        st.markdown('<div class="secao-titulo">📈 Previsão Horária — Variáveis Meteorológicas</div>',
                    unsafe_allow_html=True)
        st.caption(
            f"Modelo: **{MODELOS_OPENMETEO[modelo_sel]}** · Horizonte: {dias_prev} dias · "
            "GFS validado para o Centro-Oeste (Souza et al. 2021); "
            "ICON superior para convecção subtropical (Zängl et al. 2015)")

        # Gráfico com IC
        vars_disponiveis = [v for v in VARIAVEIS_HORARIAS if v in df_main.columns]
        var_escolhida = st.selectbox(
            "Variável para gráfico detalhado (com intervalo de confiança):",
            vars_disponiveis,
            format_func=lambda v: LABELS_PT.get(v, v),
            index=0,
        )
        df_ic_var = df_ic_cache.get(var_escolhida, pd.DataFrame()) if calcular_ic else pd.DataFrame()
        fig_ic = fig_variavel_com_ic(df_main, var_escolhida, df_ic_var)
        st.pyplot(fig_ic, use_container_width=True)
        plt.close(fig_ic)

        # Nota de confiança
        if calcular_ic and not df_ic_var.empty:
            cv_med = df_ic_var["cv_pct"].mean()
            conf   = "Alta" if cv_med < 10 else ("Moderada" if cv_med < 25 else "Baixa")
            cor_c  = "#22c55e" if conf=="Alta" else ("#fbbf24" if conf=="Moderada" else "#ef4444")
            n_mod  = len([k for k,v in ensemble_raw.items() if "hourly" in v])
            st.markdown(
                f'<div class="alert-azul">'
                f'<b>📊 Confiança da previsão — {LABELS_PT.get(var_escolhida,"")}:</b> '
                f'<span style="color:{cor_c};font-weight:bold;">{conf}</span> '
                f'(CV médio = {cv_med:.1f}%) — Spread entre {n_mod} modelos '
                f'(GFS, ICON, Best Match). IC 68% = ±1σ; IC 95% = ±2σ '
                f'(Buizza et al. 2005).</div>',
                unsafe_allow_html=True)

        # Painel multi-variável
        st.markdown('<div class="secao-titulo">📊 Painel Geral — Múltiplas Variáveis</div>',
                    unsafe_allow_html=True)
        vars_painel = st.multiselect(
            "Selecione variáveis para o painel comparativo:",
            vars_disponiveis,
            default=[v for v in ["temperature_2m","precipitation",
                                  "relativehumidity_2m","windspeed_10m"]
                     if v in vars_disponiveis],
            format_func=lambda v: LABELS_PT.get(v, v),
        )
        if vars_painel:
            fig_multi = fig_multiplas_variaveis(df_main, vars_painel)
            if fig_multi:
                st.pyplot(fig_multi, use_container_width=True)
                plt.close(fig_multi)

        # Análise de spread entre modelos
        if calcular_ic and ensemble_raw:
            st.markdown(
                '<div class="secao-titulo">🔬 Spread entre Modelos — Análise de Incerteza</div>',
                unsafe_allow_html=True)
            var_conf = st.selectbox(
                "Variável para análise de spread entre modelos:",
                [v for v in ["temperature_2m","precipitation",
                              "relativehumidity_2m","windspeed_10m"]
                 if v in df_main.columns],
                format_func=lambda v: LABELS_PT.get(v, v),
                index=0, key="sel_spread",
            )
            fig_conf = fig_confianca_modelos(ensemble_raw, var_conf)
            if fig_conf:
                st.pyplot(fig_conf, use_container_width=True)
                plt.close(fig_conf)
            st.caption(
                "**CV < 10%** = Alta confiança  |  **10–25%** = Confiança moderada  |  "
                "**> 25%** = Baixa confiança (elevada incerteza). "
                "Metodologia: Goswami et al. (2010); Buizza et al. (2005).")

        # Tabela horária completa
        st.markdown('<div class="secao-titulo">🗃️ Dados Horários Completos</div>',
                    unsafe_allow_html=True)
        df_disp = df_previsao_display(df_main)
        if not df_disp.empty:
            st.dataframe(df_disp, use_container_width=True, height=320)
            csv = df_disp.to_csv().encode("utf-8")
            st.download_button(
                "⬇️ Baixar CSV completo",
                csv,
                f"previsao_{abs(lat):.3f}S_{abs(lon):.3f}W_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
            )

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 2 — CLIMATOLOGIA & SOLO
    # ─────────────────────────────────────────────────────────────────────────
    with aba2:
        st.markdown('<div class="secao-titulo">📊 Estatísticas Descritivas do Período</div>',
                    unsafe_allow_html=True)

        if not df_main.empty:
            vars_stat = [v for v in ["temperature_2m","relativehumidity_2m",
                                      "windspeed_10m","precipitation",
                                      "shortwave_radiation","cape"]
                         if v in df_main.columns]
            df_stat = df_main[vars_stat].describe().T
            df_stat.index = [LABELS_PT.get(i, i) for i in df_stat.index]
            df_stat = df_stat[["mean","std","min","max"]].round(2)
            df_stat.columns = ["Média","Desvio Padrão","Mínimo","Máximo"]
            st.dataframe(df_stat, use_container_width=True)

            # Distribuição de temperatura
            st.markdown('<div class="secao-titulo">🌡️ Distribuição de Temperatura no Período</div>',
                        unsafe_allow_html=True)
            temp_s = df_main["temperature_2m"].dropna()
            if not temp_s.empty:
                fig_t, ax_t = plt.subplots(figsize=(10, 3), facecolor="#0d1117")
                _ax_base(ax_t)
                ax_t.hist(temp_s.values, bins=32, color=CORES_VAR["temperature_2m"],
                          alpha=0.8, edgecolor="none")
                for p, cor, lbl in [(10,"#60a5fa","P10"),(50,"#fbbf24","P50"),(90,"#f43f5e","P90")]:
                    v = float(np.percentile(temp_s, p))
                    ax_t.axvline(v, color=cor, linewidth=1.5,
                                 linestyle="--", label=f"{lbl}: {v:.1f}°C")
                ax_t.set_xlabel("Temperatura (°C)", color="#9ca3af", fontsize=9)
                ax_t.set_ylabel("Frequência (h)", color="#9ca3af", fontsize=9)
                ax_t.legend(fontsize=8, facecolor="#111827", labelcolor="white", edgecolor="#374151")
                ax_t.set_title("Distribuição de Temperatura — Período de Previsão",
                               color="white", fontsize=10, fontweight="bold")
                plt.tight_layout()
                st.pyplot(fig_t, use_container_width=True)
                plt.close(fig_t)

            # Precipitação acumulada diária
            st.markdown('<div class="secao-titulo">🌧️ Precipitação Acumulada por Dia</div>',
                        unsafe_allow_html=True)
            pp_diario = df_main["precipitation"].resample("D").sum()
            fig_pp, ax_pp = plt.subplots(figsize=(10, 3), facecolor="#0d1117")
            _ax_base(ax_pp)
            bar_cores = [VERDE_MEDIO if v < 20 else (AMARELO_ALERT if v < 50 else VERMELHO_ALRT)
                         for v in pp_diario.values]
            ax_pp.bar(range(len(pp_diario)), pp_diario.values,
                      color=bar_cores, alpha=0.85, edgecolor="none")
            ax_pp.set_xticks(range(len(pp_diario)))
            ax_pp.set_xticklabels([d.strftime("%d/%m") for d in pp_diario.index],
                                   color="#9ca3af", fontsize=8)
            ax_pp.set_ylabel("Precipitação (mm)", color="#9ca3af", fontsize=9)
            ax_pp.axhline(20, color=AMARELO_ALERT, linewidth=0.8, linestyle="--",
                          alpha=0.7, label="20 mm (atenção)")
            ax_pp.axhline(50, color=VERMELHO_ALRT, linewidth=0.8, linestyle="--",
                          alpha=0.7, label="50 mm (alerta)")
            ax_pp.legend(fontsize=8, facecolor="#111827", labelcolor="white", edgecolor="#374151")
            ax_pp.set_title("Precipitação Acumulada Diária",
                            color="white", fontsize=10, fontweight="bold")
            plt.tight_layout()
            st.pyplot(fig_pp, use_container_width=True)
            plt.close(fig_pp)

        # Umidade do solo — NASA POWER
        st.markdown(
            '<div class="secao-titulo">🌱 Umidade do Solo — NASA POWER (últimos 30 dias)</div>',
            unsafe_allow_html=True)
        if dados_nasa and "properties" in dados_nasa:
            try:
                params   = dados_nasa["properties"]["parameter"]
                gwettop  = params.get("GWETTOP",  {})
                gwetroot = params.get("GWETROOT", {})
                if gwettop:
                    datas_n = sorted(gwettop.keys())[-30:]
                    vt = [float(gwettop.get(d,  0)) for d in datas_n]
                    vr = [float(gwetroot.get(d, 0)) for d in datas_n]

                    fig_s, ax_s = plt.subplots(figsize=(11, 3.5), facecolor="#0d1117")
                    _ax_base(ax_s)
                    ax_s.plot(range(len(vt)), vt, color="#66BB6A", linewidth=2.0,
                              label="GWETTOP (0–5 cm — superfície)")
                    ax_s.fill_between(range(len(vt)), vt, alpha=0.15, color="#66BB6A")
                    ax_s.plot(range(len(vr)), vr, color="#42A5F5", linewidth=2.0,
                              linestyle="--", label="GWETROOT (zona radicular)")
                    ax_s.fill_between(range(len(vr)), vr, alpha=0.10, color="#42A5F5")
                    ax_s.axhline(0.5, color="#FFB74D", linewidth=0.8, linestyle=":",
                                 alpha=0.8, label="Capacidade de campo (0.5)")
                    ax_s.axhline(0.2, color="#ef4444", linewidth=0.8, linestyle=":",
                                 alpha=0.8, label="Ponto de murcha permanente (0.2)")
                    ax_s.set_ylim(0, 1.05)
                    ax_s.set_ylabel("Umidade relativa (fração 0–1)",
                                    color="#9ca3af", fontsize=9)
                    step = max(1, len(datas_n) // 10)
                    ax_s.set_xticks(range(0, len(datas_n), step))
                    ax_s.set_xticklabels(
                        [f"{datas_n[i][6:8]}/{datas_n[i][4:6]}"
                         for i in range(0, len(datas_n), step)],
                        color="#9ca3af", fontsize=8, rotation=30)
                    ax_s.legend(fontsize=8, facecolor="#111827", labelcolor="white",
                                edgecolor="#374151")
                    ax_s.set_title("Umidade do Solo — NASA POWER",
                                   color="white", fontsize=10, fontweight="bold")
                    plt.tight_layout()
                    st.pyplot(fig_s, use_container_width=True)
                    plt.close(fig_s)

                    # Tabela resumo
                    df_solo = pd.DataFrame({
                        "Data":             [f"{datas_n[i][6:8]}/{datas_n[i][4:6]}/{datas_n[i][:4]}"
                                             for i in range(len(datas_n))],
                        "GWETTOP (0–5cm)":  [round(v, 3) for v in vt],
                        "GWETROOT (radicular)": [round(v, 3) for v in vr],
                        "Status": ["✅ Adequado" if v > 0.5 else
                                   ("⚠️ Atenção"   if v > 0.2 else "❌ Crítico") for v in vr],
                    })
                    st.dataframe(df_solo.tail(14), use_container_width=True, hide_index=True)
            except Exception as e:
                st.info(f"ℹ️ Dados NASA POWER indisponíveis nesta consulta: {e}")
        else:
            st.info("ℹ️ NASA POWER não respondeu. Verifique a conexão e tente novamente.")

        # Balanço hídrico
        st.markdown(
            f'<div class="secao-titulo">💧 Balanço Hídrico — Thornthwaite-Mather</div>',
            unsafe_allow_html=True)
        st.caption(f"CAD = {CAD_PADRAO_MM:.0f} mm (solo médio/franco — padrão EMBRAPA para o MS). "
                   "ETo estimada pelo método Hargreaves-Samani (1985).")

        if bh:
            c1,c2,c3,c4 = st.columns(4)
            with c1: st.metric("ARM atual",    f"{bh['arm_mm']:.1f} mm",
                               delta=f"{bh['arm_pct']:.0f}% da CAD")
            with c2: st.metric("CAD",          f"{bh['cad_mm']:.0f} mm")
            with c3: st.metric("Déficit hoje", f"{bh['def_mm']:.1f} mm",
                               delta_color="inverse",
                               delta="❌ déficit" if bh["def_mm"] > 0 else "✅ OK")
            with c4: st.metric("ETo estimada", f"{bh['eto_mm']:.1f} mm/dia")

            if "serie" in bh and bh["serie"]:
                serie = bh["serie"][:7]
                dias  = [f"D+{i}" for i in range(len(serie))]
                fig_bh, (ax1, ax2) = plt.subplots(
                    2, 1, figsize=(10, 5), facecolor="#0d1117",
                    gridspec_kw={"height_ratios": [2, 1]})
                for ax in [ax1, ax2]:
                    _ax_base(ax)
                arm_vals = [s["arm"] for s in serie]
                def_vals = [s["def"] for s in serie]
                exc_vals = [s["exc"] for s in serie]

                ax1.fill_between(range(len(arm_vals)), arm_vals,
                                 alpha=0.25, color="#42A5F5")
                ax1.plot(range(len(arm_vals)), arm_vals,
                         color="#42A5F5", linewidth=2, label="ARM (mm)")
                ax1.axhline(bh["cad_mm"], color="#FFB74D", linewidth=1.2,
                            linestyle="--", label=f"CAD = {bh['cad_mm']:.0f} mm")
                ax1.axhline(bh["cad_mm"]*0.4, color="#ef4444", linewidth=0.9,
                            linestyle=":", label="Limite crítico (40% CAD)")
                ax1.set_ylabel("Armazenamento (mm)", color="#9ca3af", fontsize=9)
                ax1.set_ylim(0, bh["cad_mm"] * 1.15)
                ax1.set_xticks([])
                ax1.legend(fontsize=8, facecolor="#111827", labelcolor="white",
                           edgecolor="#374151")
                ax1.set_title("Balanço Hídrico Thornthwaite-Mather",
                              color="white", fontsize=10, fontweight="bold")

                ax2.bar(range(len(def_vals)), def_vals,
                        color="#ef4444", alpha=0.8, label="Déficit", width=0.42)
                ax2.bar([i+0.44 for i in range(len(exc_vals))], exc_vals,
                        color="#29B6F6", alpha=0.8, label="Excedente", width=0.42)
                ax2.set_ylabel("mm", color="#9ca3af", fontsize=9)
                ax2.set_xticks(range(len(dias)))
                ax2.set_xticklabels(dias, color="#9ca3af", fontsize=8)
                ax2.legend(fontsize=8, facecolor="#111827", labelcolor="white",
                           edgecolor="#374151")
                plt.tight_layout()
                st.pyplot(fig_bh, use_container_width=True)
                plt.close(fig_bh)

            st.markdown(
                f'<div class="alert-{bh["nivel"]}">'
                f'<b>💧 Recomendação de Irrigação:</b> {bh["recomendacao"]}'
                f'</div>',
                unsafe_allow_html=True)
        else:
            st.warning("Balanço hídrico não pôde ser calculado com os dados disponíveis.")

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 3 — SÍNTESE AGRÍCOLA
    # ─────────────────────────────────────────────────────────────────────────
    with aba3:
        st.markdown(
            '<div class="secao-titulo">🌾 Síntese Agrícola — Resumo Executivo</div>',
            unsafe_allow_html=True)
        st.caption(
            f"Análise consolidada para **{abs(lat):.4f}°S, {abs(lon):.4f}°W** · "
            f"Gerada em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        # Cards de síntese
        col_s1, col_s2, col_s3 = st.columns(3)

        with col_s1:
            n_crit = sum(1 for a in alertas if a["nivel"] == "vermelho")
            n_amar = sum(1 for a in alertas if a["nivel"] == "amarelo")
            if n_crit > 0:
                cond_geral, bg_cond = "🔴 Crítica",   "#ffebee"
            elif n_amar > 0:
                cond_geral, bg_cond = "🟡 Atenção",   "#fff8e1"
            else:
                cond_geral, bg_cond = "🟢 Favorável", "#e8f5e9"
            st.markdown(
                f'<div class="info-card" style="background:{bg_cond};">'
                f'<h4>Condição Geral</h4>'
                f'<p style="font-size:1.2rem;font-weight:700;">{cond_geral}</p>'
                f'<p>{n_crit} alerta(s) crítico(s) · {n_amar} atenção(ões)</p>'
                f'</div>', unsafe_allow_html=True)

        with col_s2:
            if not janelas_df.empty:
                n_ab  = int((janelas_df["status"] == "aberta").sum())
                n_tot = len(janelas_df)
                bloco = cur = 0
                for v in (janelas_df["status"] == "aberta").values:
                    if v: cur += 1; bloco = max(bloco, cur)
                    else: cur = 0
                cor_j = "#e8f5e9" if n_ab >= 8 else ("#fff8e1" if n_ab >= 4 else "#ffebee")
                st.markdown(
                    f'<div class="info-card" style="background:{cor_j};">'
                    f'<h4>🧪 Janela de Defensivos (24h)</h4>'
                    f'<p style="font-size:1.1rem;font-weight:700;">{n_ab}/{n_tot}h disponíveis</p>'
                    f'<p>Bloco contínuo máximo: {bloco}h</p>'
                    f'</div>', unsafe_allow_html=True)

        with col_s3:
            nivel_max = "Baixo"
            for r in riscos.values():
                if r["nivel"] == "Crítico": nivel_max = "Crítico"; break
                if r["nivel"] == "Alto":    nivel_max = "Alto"
                elif r["nivel"] == "Médio" and nivel_max == "Baixo":
                    nivel_max = "Médio"
            bg_fito = {"Crítico":"#ffebee","Alto":"#ffebee",
                       "Médio":"#fff8e1","Baixo":"#e8f5e9"}.get(nivel_max,"#e8f5e9")
            st.markdown(
                f'<div class="info-card" style="background:{bg_fito};">'
                f'<h4>🍂 Risco Fitossanitário</h4>'
                f'<p style="font-size:1.1rem;font-weight:700;">Nível {nivel_max}</p>'
                f'<p>Ferrugem: {riscos["ferrugem"]["nivel"]} · '
                f'Brusone: {riscos["brusone"]["nivel"]}</p>'
                f'</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📋 Relatório Narrativo Técnico")

        # Temperatura
        if "temperature_2m" in df_main.columns:
            tmax_v = df_main["temperature_2m"].resample("D").max().max()
            tmin_v = df_main["temperature_2m"].resample("D").min().min()
            tmed   = df_main["temperature_2m"].mean()
            geada_txt = ("⚠️ **Risco de geada detectado** (Tmín < 5°C). "
                         "Proteja culturas sensíveis imediatamente."
                         if tmin_v < 5 else "Sem risco de geada no período.")
            calor_txt = ("⚠️ **Calor extremo previsto** (>38°C). "
                         "Estresse hídrico e fisiológico elevados."
                         if tmax_v > 38 else "Sem ocorrência de calor extremo.")
            st.markdown(
                f'<div class="info-card"><h4>🌡️ Temperatura</h4>'
                f'<p>Média do período: <b>{tmed:.1f}°C</b> · '
                f'Máxima esperada: <b>{tmax_v:.1f}°C</b> · '
                f'Mínima esperada: <b>{tmin_v:.1f}°C</b><br>'
                f'{geada_txt} · {calor_txt}</p></div>',
                unsafe_allow_html=True)

        # Precipitação
        if "precipitation" in df_main.columns:
            pp_total = df_main["precipitation"].sum()
            pp_max   = df_main["precipitation"].resample("D").sum().max()
            dias_ch  = int((df_main["precipitation"].resample("D").sum() > 1).sum())
            if pp_max > 50:
                pp_rec = "⚠️ Chuva intensa prevista (>50 mm/dia). Suspenda operações de campo."
            elif pp_max > 20:
                pp_rec = "⚠️ Volumes moderados previstos. Monitore possível encharcamento."
            else:
                pp_rec = "Precipitação dentro dos limites normais para operações agrícolas."
            veranico = ("<br>🌵 <b>Atenção ao veranico:</b> poucos dias com chuva no período."
                        if dias_ch < 2 and dias_prev >= 5 else "")
            st.markdown(
                f'<div class="info-card"><h4>🌧️ Precipitação</h4>'
                f'<p>Total do período: <b>{pp_total:.1f} mm</b> · '
                f'Máximo diário: <b>{pp_max:.1f} mm</b> · '
                f'Dias com chuva: <b>{dias_ch}/{dias_prev}</b><br>'
                f'{pp_rec}{veranico}</p></div>',
                unsafe_allow_html=True)

        # Vento
        if "windspeed_10m" in df_main.columns:
            vt_med  = df_main["windspeed_10m"].mean()
            gust_c  = df_main.get("windgusts_10m", df_main["windspeed_10m"])
            vt_max  = gust_c.max()
            h_vt_ok = int((df_main["windspeed_10m"].iloc[:24] < 10).sum())
            raj_txt = ("⚠️ Rajadas fortes previstas. Risco de acamamento e danos a estruturas."
                       if vt_max > 60 else "Condições de vento sem risco estrutural.")
            st.markdown(
                f'<div class="info-card"><h4>💨 Vento</h4>'
                f'<p>Velocidade média: <b>{vt_med:.1f} km/h</b> · '
                f'Rajada máxima: <b>{vt_max:.1f} km/h</b><br>'
                f'Horas com vento adequado para defensivos (próximas 24h): '
                f'<b>{h_vt_ok}h</b><br>{raj_txt}</p></div>',
                unsafe_allow_html=True)

        # Irrigação
        if bh:
            st.markdown(
                f'<div class="info-card"><h4>💧 Manejo de Irrigação</h4>'
                f'<p>Armazenamento atual: <b>{bh["arm_mm"]:.1f} mm ({bh["arm_pct"]:.0f}% da CAD)</b><br>'
                f'Déficit hoje: <b>{bh["def_mm"]:.1f} mm</b> · '
                f'ETo estimada: <b>{bh["eto_mm"]:.2f} mm/dia</b><br>'
                f'<b>Recomendação:</b> {bh["recomendacao"]}</p></div>',
                unsafe_allow_html=True)

        # Janela de defensivos
        if not janelas_df.empty:
            abertas = janelas_df[janelas_df["status"] == "aberta"]
            if not abertas.empty:
                h_ini = abertas.index[0].strftime("%Hh")
                h_fim = abertas.index[-1].strftime("%Hh")
                st.markdown(
                    f'<div class="info-card" style="background:#e8f5e9;">'
                    f'<h4>🧪 Recomendação — Aplicação de Defensivos</h4>'
                    f'<p>Janelas favoráveis identificadas entre <b>{h_ini}</b> e <b>{h_fim}</b> '
                    f'(com possíveis intervalos).<br>'
                    f'Critérios atendidos: vento &lt;10 km/h, temperatura &lt;30°C, '
                    f'UR &gt;55%, sem precipitação.<br>'
                    f'<i>Verifique sempre a bula do produto e condições locais no ato da aplicação.</i>'
                    f'</p></div>',
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="info-card" style="background:#ffebee;">'
                    '<h4>🧪 Aplicação de Defensivos</h4>'
                    '<p><b>Nenhuma janela ideal nas próximas 24h.</b> '
                    'Adie as aplicações para o próximo período favorável.</p></div>',
                    unsafe_allow_html=True)

        # Riscos fitossanitários
        for r in riscos.values():
            if r["nivel"] != "Baixo":
                st.markdown(
                    f'<div class="alert-{r["cor"]}">'
                    f'<b>{r["emoji"]} {r["doenca"]} — Risco {r["nivel"]}</b><br>'
                    f'{r["horas_consecutivas"]}h consecutivas com condições favoráveis '
                    f'(limiar: {r["limiar"]}h). Referência: {r["referencia"]}.'
                    f'</div>',
                    unsafe_allow_html=True)

        # Tabela resumo diário 7 dias
        st.markdown('<div class="secao-titulo">📅 Resumo Diário — Próximos 7 Dias</div>',
                    unsafe_allow_html=True)
        try:
            agg_dict = {k: v for k, v in {
                "temperature_2m":      ["max","min","mean"],
                "precipitation":       "sum",
                "relativehumidity_2m": "mean",
                "windspeed_10m":       "max",
                "shortwave_radiation": "mean",
            }.items() if k in df_main.columns}
            df_res = df_main.resample("D").agg(agg_dict).head(7)

            cols_rename = {}
            if "temperature_2m" in df_main.columns:
                cols_rename.update({
                    ("temperature_2m","max"):  "T.Máx (°C)",
                    ("temperature_2m","min"):  "T.Mín (°C)",
                    ("temperature_2m","mean"): "T.Méd (°C)",
                })
            if "precipitation" in df_main.columns:
                cols_rename[("precipitation","sum")] = "Precip (mm)"
            if "relativehumidity_2m" in df_main.columns:
                cols_rename[("relativehumidity_2m","mean")] = "UR méd (%)"
            if "windspeed_10m" in df_main.columns:
                cols_rename[("windspeed_10m","max")] = "Vento máx (km/h)"
            if "shortwave_radiation" in df_main.columns:
                cols_rename[("shortwave_radiation","mean")] = "Rad. méd (W/m²)"

            df_res.columns = [cols_rename.get(c, str(c)) for c in df_res.columns]
            df_res.index   = [d.strftime("%a %d/%m") for d in df_res.index]
            df_res = df_res.round(1)

            if "weathercode" in df_main.columns:
                wc_d = df_main["weathercode"].resample("D").max()
                df_res["Condição"] = [
                    WCODE_MAP.get(int(v), "—") if pd.notna(v) else "—"
                    for v in wc_d.values[:7]
                ]
            st.dataframe(df_res, use_container_width=True)
        except Exception as e:
            st.warning(f"Erro ao gerar tabela resumo: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 4 — ALERTAS & RISCO
    # ─────────────────────────────────────────────────────────────────────────
    with aba4:
        st.markdown('<div class="secao-titulo">⚠️ Alertas Meteorológicos</div>',
                    unsafe_allow_html=True)
        for al in alertas:
            st.markdown(
                f'<div class="alert-{al["nivel"]}">'
                f'<b>{al["icone"]} {al["titulo"]}</b><br>'
                f'<span style="font-size:0.9rem;">{al["msg"]}</span>'
                f'</div>',
                unsafe_allow_html=True)

        # Matriz de risco
        st.markdown(
            '<div class="secao-titulo">🔲 Matriz de Risco Hora × Variável (24h)</div>',
            unsafe_allow_html=True)
        st.caption("Verde ✓ = condição favorável | Amarelo ! = atenção | Vermelho ✗ = risco/bloqueado")
        fig_mat = fig_matriz_alertas(df_main)
        if fig_mat:
            st.pyplot(fig_mat, use_container_width=True)
            plt.close(fig_mat)

        # Risco fitossanitário detalhado
        st.markdown(
            '<div class="secao-titulo">🍂 Risco Fitossanitário Detalhado (48h)</div>',
            unsafe_allow_html=True)
        for r in riscos.values():
            st.markdown(
                f'<div class="alert-{r["cor"]}">'
                f'<b>{r["emoji"]} {r["doenca"]} — Risco: {r["nivel"]}</b><br>'
                f'<span style="font-size:0.88rem;">'
                f'Horas consecutivas favoráveis: <b>{r["horas_consecutivas"]}h</b> '
                f'(limiar de risco: {r["limiar"]}h) · '
                f'Total de horas favoráveis nas 48h: {r["horas_total"]}h<br>'
                f'Referência: <i>{r["referencia"]}</i>'
                f'</span></div>',
                unsafe_allow_html=True)

        # Evolução temporal do risco
        st.markdown(
            '<div class="secao-titulo">📊 Evolução Temporal das Janelas de Risco (48h)</div>',
            unsafe_allow_html=True)
        fig_r, (ax_f, ax_b) = plt.subplots(2, 1, figsize=(12, 5),
                                             facecolor="#0d1117", sharex=True)
        for ax in [ax_f, ax_b]:
            _ax_base(ax)
        idx48 = df_main.index[:48]
        fer_c = riscos["ferrugem"]["condicao"].reindex(idx48, fill_value=False)
        bru_c = riscos["brusone"]["condicao"].reindex(idx48, fill_value=False)

        ax_f.fill_between(idx48, fer_c.values.astype(float), color="#f97316",
                          alpha=0.75, step="mid", label="Condição favorável — Ferrugem Asiática")
        ax_f.set_ylabel("Ferrugem (0/1)", color="#9ca3af", fontsize=8)
        ax_f.set_ylim(-0.05, 1.5)
        ax_f.legend(fontsize=7, facecolor="#111827", labelcolor="white", edgecolor="#374151")
        ax_f.set_title("Janelas de Risco Fitossanitário — 48h",
                       color="white", fontsize=10, fontweight="bold")

        ax_b.fill_between(idx48, bru_c.values.astype(float), color="#a78bfa",
                          alpha=0.75, step="mid", label="Condição favorável — Brusone")
        ax_b.set_ylabel("Brusone (0/1)", color="#9ca3af", fontsize=8)
        ax_b.set_ylim(-0.05, 1.5)
        ax_b.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%Hh"))
        ax_b.xaxis.set_major_locator(mdates.HourLocator(interval=6))
        ax_b.legend(fontsize=7, facecolor="#111827", labelcolor="white", edgecolor="#374151")
        plt.tight_layout()
        st.pyplot(fig_r, use_container_width=True)
        plt.close(fig_r)

        # Janela de defensivos — detalhe
        st.markdown(
            '<div class="secao-titulo">🧪 Janela de Aplicação de Defensivos — 24h</div>',
            unsafe_allow_html=True)
        st.caption("**Critérios MAPA/Embrapa (Portaria 371/2020):** "
                   "Vento < 10 km/h  ·  Temperatura < 30°C  ·  UR > 55%  ·  Sem precipitação")

        if not janelas_df.empty:
            # Timeline visual
            n_cols_j = min(24, len(janelas_df))
            cols_j   = st.columns(n_cols_j)
            for i, (idx_j, row_j) in enumerate(janelas_df.head(n_cols_j).iterrows()):
                with cols_j[i]:
                    emoji_j = {"aberta":"🟢","parcial":"🟡","bloqueada":"🔴"}[row_j["status"]]
                    st.markdown(
                        f"<div style='text-align:center;font-size:0.62rem;color:#555;'>"
                        f"<b>{idx_j.strftime('%Hh')}</b><br>{emoji_j}</div>",
                        unsafe_allow_html=True)

            n_ab = int((janelas_df["status"]=="aberta").sum())
            n_pa = int((janelas_df["status"]=="parcial").sum())
            n_bl = int((janelas_df["status"]=="bloqueada").sum())
            c1,c2,c3 = st.columns(3)
            with c1: st.metric("✅ Horas ideais",    n_ab)
            with c2: st.metric("⚠️ Horas parciais",  n_pa)
            with c3: st.metric("❌ Horas bloqueadas", n_bl)

            df_jan_disp = janelas_df[["status","motivo","n_restricoes"]].copy()
            df_jan_disp.index   = [t.strftime("%Hh") for t in df_jan_disp.index]
            df_jan_disp.columns = ["Status","Restrições","N° Restrições"]
            df_jan_disp["Status"] = df_jan_disp["Status"].map(
                {"aberta":"✅ Aberta","parcial":"⚠️ Parcial","bloqueada":"❌ Bloqueada"})
            st.dataframe(df_jan_disp, use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 5 — RELATÓRIO & E-MAIL
    # ─────────────────────────────────────────────────────────────────────────
    with aba5:
        st.markdown('<div class="secao-titulo">📧 Relatório por E-mail</div>',
                    unsafe_allow_html=True)

        if _email_ok:
            st.markdown(
                f'<div class="alert-verde">'
                f'<b>✅ E-mail configurado</b><br>'
                f'Remetente: {EMAIL_REMETENTE}<br>'
                f'Destinatários: {", ".join(EMAIL_DESTINATARIOS)}'
                f'</div>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="alert-amarelo">'
                '<b>⚠️ E-mail não configurado</b><br>'
                'Adicione ao <code>.streamlit/secrets.toml</code>:<br>'
                '<code>[email]<br>remetente = "seu@gmail.com"<br>'
                'senha_app = "sua_senha_app_gmail"<br>'
                'destinatario = "destino@email.com"</code>'
                '</div>',
                unsafe_allow_html=True)

        st.markdown("---")
        dest_extra = st.text_input(
            "Destinatários adicionais (separar por vírgula):",
            placeholder="eng@fazenda.com, gestor@empresa.com")
        extras = [e.strip() for e in dest_extra.split(",") if "@" in e] if dest_extra else []

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if st.button("📤 Enviar Relatório Agora", use_container_width=True):
                with st.spinner("Gerando e enviando relatório..."):
                    html_rel = gerar_html_relatorio(
                        lat, lon, df_main, alertas, riscos, bh,
                        janelas_df.to_dict("records") if not janelas_df.empty else [],
                        f"{abs(lat):.4f}°S, {abs(lon):.4f}°W"
                    )
                    tem_crit = any(a["nivel"] == "vermelho" for a in alertas)
                    assunto  = (
                        f"{'🚨 ALERTA — ' if tem_crit else '📋 '}"
                        f"Relatório Agroclimático — {abs(lat):.4f}°S, {abs(lon):.4f}°W | "
                        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"
                    )
                    ok, msg = enviar_email(html_rel, assunto, extras)
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

        with col_e2:
            if st.button("👁 Pré-visualizar HTML", use_container_width=True):
                html_prev = gerar_html_relatorio(
                    lat, lon, df_main, alertas, riscos, bh,
                    janelas_df.to_dict("records") if not janelas_df.empty else [],
                    f"{abs(lat):.4f}°S, {abs(lon):.4f}°W"
                )
                components.html(html_prev, height=680, scrolling=True)

        st.markdown("---")
        st.markdown("**📋 Conteúdo do relatório:**")
        st.markdown(
            "- 📊 Condições atuais (temperatura, chuva, umidade, vento, CAPE)\n"
            "- ⚠️ Alertas meteorológicos com nível de severidade\n"
            "- 🍂 Risco fitossanitário (Ferrugem Asiática e Brusone)\n"
            "- 🧪 Janela de aplicação de defensivos — horas disponíveis nas 24h\n"
            "- 💧 Balanço hídrico Thornthwaite-Mather e recomendação de irrigação\n"
            "- 📅 Tabela de previsão detalhada para 7 dias"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # RODAPÉ
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align:center;padding:14px;color:#888;font-size:0.78rem;">
      <b style="color:{VERDE_ESCURO};">Yamada Engenharia</b> — Meteorologia Aplicada ao Agronegócio · MS<br>
      Open-Meteo (GFS · ICON · ERA5) · NASA POWER · INPE BDQueimadas · v4.1<br>
      <i>Souza et al. (2021) · Zängl et al. (2015) · Hersbach et al. (2020) ·
      Buizza et al. (2005) · Del Ponte et al. (2006) · Hargreaves & Samani (1985)</i><br>
      {datetime.now().strftime('%d/%m/%Y %H:%M')}
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
