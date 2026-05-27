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
from apscheduler.triggers.cron import CronTrigger
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
  .stButton > button {{
    background:linear-gradient(135deg,{VERDE_ESCURO},{VERDE_MEDIO}) !important;
    color:white !important; font-family:'Montserrat',sans-serif !important;
    font-weight:700 !important; border:none !important; border-radius:10px !important;
    padding:12px 32px !important; width:100% !important;
    box-shadow:0 4px 15px rgba(27,77,46,0.35) !important;
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
  div[data-testid="metric-container"] {{
    background:white; border-radius:10px; padding:14px;
    box-shadow:0 2px 10px rgba(0,0,0,0.07); border-top:3px solid {VERDE_MEDIO};
  }}
  hr {{ border-color:#ddeedd; margin:18px 0; }}
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

_scheduler_log: list = []
_log_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────────────────
# DADOS ESTÁTICOS — MUNICÍPIOS DE REFERÊNCIA (para o mapa)
# ─────────────────────────────────────────────────────────────────────────────
MUNICIPIOS_REF = {
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
# MODELOS OPEN-METEO SELECIONADOS PARA MATO GROSSO DO SUL
#
# Justificativa bibliográfica:
#   • GFS (NCEP/NOAA) — cobertura global, bom desempenho nos trópicos úmidos,
#     amplamente validado para precipitação no Centro-Oeste (Souza et al. 2021)
#   • ICON (DWD) — melhor representação de convecção profunda em regiões
#     subtropicais úmidas (Zängl et al. 2015, Bauer et al. 2020)
#   • ERA5 (ECMWF reanálise) — padrão-ouro de reanálise, usado como referência
#     para validação no MS (Hersbach et al. 2020)
#   • BEST_MATCH — ensemble automático do Open-Meteo (média ponderada dos
#     melhores modelos por variável)
# ─────────────────────────────────────────────────────────────────────────────
MODELOS_OPENMETEO = {
    "best_match": "Best Match (Ensemble automático)",
    "gfs_seamless": "GFS (NOAA — EUA)",
    "icon_seamless": "ICON (DWD — Alemanha)",
    "era5_seamless": "ERA5 (ECMWF — Reanálise)",
}

VARIAVEIS_HORARIAS = [
    "temperature_2m",
    "precipitation",
    "relativehumidity_2m",
    "windspeed_10m",
    "windgusts_10m",
    "shortwave_radiation",
    "dewpoint_2m",
    "apparent_temperature",
    "weathercode",
    "surface_pressure",
    "cape",
    "cloudcover",
]

LABELS_PT = {
    "temperature_2m":      "Temperatura (°C)",
    "precipitation":       "Precipitação (mm)",
    "relativehumidity_2m": "Umidade Relativa (%)",
    "windspeed_10m":       "Vento (km/h)",
    "windgusts_10m":       "Rajada de Vento (km/h)",
    "shortwave_radiation":  "Radiação Solar (W/m²)",
    "dewpoint_2m":         "Ponto de Orvalho (°C)",
    "apparent_temperature":"Temperatura Aparente (°C)",
    "weathercode":         "Código de Tempo (WMO)",
    "surface_pressure":    "Pressão Superficial (hPa)",
    "cape":                "CAPE (J/kg)",
    "cloudcover":          "Cobertura de Nuvens (%)",
}

CORES_VAR = {
    "temperature_2m":      "#f97316",
    "precipitation":       "#3b82f6",
    "relativehumidity_2m": "#06b6d4",
    "windspeed_10m":       "#a78bfa",
    "windgusts_10m":       "#c084fc",
    "shortwave_radiation":  "#fbbf24",
    "dewpoint_2m":         "#34d399",
    "apparent_temperature":"#fb7185",
    "weathercode":         "#94a3b8",
    "surface_pressure":    "#a3e635",
    "cape":                "#f43f5e",
    "cloudcover":          "#cbd5e1",
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

# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULER
# ─────────────────────────────────────────────────────────────────────────────
def keep_alive():
    try:
        requests.get("https://yamada-agro-ms.streamlit.app/", timeout=20)
    except Exception:
        pass

if "scheduler_started" not in st.session_state:
    _sched = BackgroundScheduler(timezone="America/Campo_Grande")
    _sched.add_job(keep_alive, trigger=IntervalTrigger(minutes=5),
                   id="keepalive", replace_existing=True, max_instances=1)
    _sched.start()
    st.session_state["scheduler_started"] = True
    st.session_state["scheduler_obj"] = _sched

# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE COLETA DE DADOS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def buscar_openmeteo(lat: float, lon: float, modelo: str, dias: int = 7) -> dict:
    """
    Coleta previsão horária e diária via Open-Meteo.
    Retorna dict com hourly, daily e metadados do modelo.
    """
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
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_erro": str(e)}


@st.cache_data(ttl=1800, show_spinner=False)
def buscar_ensemble_openmeteo(lat: float, lon: float, dias: int = 7) -> dict:
    """
    Busca previsão ensemble (membros individuais) para cálculo de
    intervalo de confiança/spread entre modelos.
    Retorna dict com média e desvio-padrão entre modelos para cada variável.
    """
    resultados = {}
    modelos_ensemble = ["gfs_seamless", "icon_seamless", "best_match"]
    vars_h = "temperature_2m,precipitation,relativehumidity_2m,windspeed_10m"
    for mod in modelos_ensemble:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly={vars_h}"
            f"&timezone=America%2FCampo_Grande"
            f"&forecast_days={dias}&models={mod}"
        )
        try:
            r = requests.get(url, timeout=15)
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
        r = requests.get(url, timeout=25)
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
        np.random.seed(42)
        n = 8
        return pd.DataFrame({
            "latitude":  np.random.uniform(-23.0, -17.5, n),
            "longitude": np.random.uniform(-57.0, -51.5, n),
            "frp":       np.random.uniform(5, 80, n),
            "_simulado": [True]*n,
        })

# ─────────────────────────────────────────────────────────────────────────────
# PROCESSAMENTO DOS DADOS BRUTOS → DATAFRAMES
# ─────────────────────────────────────────────────────────────────────────────

def openmeteo_para_df(dados: dict) -> pd.DataFrame:
    """
    Converte o JSON do Open-Meteo em DataFrame horário limpo.
    Índice: datetime localizado em America/Campo_Grande.
    """
    if not dados or "hourly" not in dados:
        return pd.DataFrame()
    h = dados["hourly"]
    times = pd.to_datetime(h["time"])
    df = pd.DataFrame({"datetime": times})
    for var in VARIAVEIS_HORARIAS:
        if var in h:
            df[var] = h[var]
    df = df.set_index("datetime")
    # Converte NaN em float para todas as colunas numéricas
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def calcular_intervalo_confianca(ensemble: dict, var: str) -> pd.DataFrame:
    """
    Calcula média, desvio-padrão e intervalo de confiança (±1σ e ±2σ)
    entre os modelos do ensemble para uma variável.

    O spread entre modelos funciona como proxy de incerteza da previsão:
    spread grande = baixa confiança | spread pequeno = alta confiança.
    Metodologia: Goswami et al. (2010), Buizza et al. (2005).
    """
    series = []
    for mod, dados in ensemble.items():
        if "hourly" in dados and var in dados["hourly"]:
            s = pd.Series(
                dados["hourly"][var],
                index=pd.to_datetime(dados["hourly"]["time"]),
                name=mod,
            )
            s = pd.to_numeric(s, errors="coerce")
            series.append(s)
    if len(series) < 2:
        return pd.DataFrame()
    df_ens = pd.concat(series, axis=1)
    result = pd.DataFrame({
        "media":    df_ens.mean(axis=1),
        "std":      df_ens.std(axis=1),
        "min":      df_ens.min(axis=1),
        "max":      df_ens.max(axis=1),
        "ic68_low": df_ens.mean(axis=1) - df_ens.std(axis=1),       # ~68%
        "ic68_high":df_ens.mean(axis=1) + df_ens.std(axis=1),
        "ic95_low": df_ens.mean(axis=1) - 2*df_ens.std(axis=1),     # ~95%
        "ic95_high":df_ens.mean(axis=1) + 2*df_ens.std(axis=1),
    })
    result["cv_pct"] = (result["std"] / (result["media"].abs() + 1e-6) * 100).round(1)
    return result


def calcular_janelas_defensivos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula status de janela de aplicação de defensivos para cada hora.
    Critérios MAPA/Embrapa (Portaria 371/2020):
      Vento < 10 km/h | Temperatura < 30°C | UR > 55% | Precipitação = 0

    Retorna DataFrame com coluna 'status' (0=bloqueada, 1=parcial, 2=aberta)
    e 'n_restricoes'.
    """
    df2 = df.copy().head(24)
    rest = pd.DataFrame(index=df2.index)

    rest["vento_ok"]  = (df2.get("windspeed_10m",  pd.Series(5,  index=df2.index)) < 10).astype(int)
    rest["temp_ok"]   = (df2.get("temperature_2m", pd.Series(25, index=df2.index)) < 30).astype(int)
    rest["ur_ok"]     = (df2.get("relativehumidity_2m", pd.Series(65, index=df2.index)) > 55).astype(int)
    rest["chuva_ok"]  = (df2.get("precipitation",  pd.Series(0,  index=df2.index)) == 0).astype(int)

    rest["n_ok"]      = rest[["vento_ok","temp_ok","ur_ok","chuva_ok"]].sum(axis=1)
    rest["status"]    = rest["n_ok"].apply(lambda x: "aberta" if x==4 else ("parcial" if x>=3 else "bloqueada"))
    rest["n_restricoes"] = 4 - rest["n_ok"]

    # Motivos de bloqueio
    def motivo(row, df_src):
        m = []
        if not row["vento_ok"]:
            v = df_src.get("windspeed_10m", pd.Series()).reindex([row.name])
            m.append(f"Vento {v.iloc[0]:.0f}km/h" if not v.empty else "Vento alto")
        if not row["temp_ok"]:
            v = df_src.get("temperature_2m", pd.Series()).reindex([row.name])
            m.append(f"Temp {v.iloc[0]:.0f}°C" if not v.empty else "Temp alta")
        if not row["ur_ok"]:
            v = df_src.get("relativehumidity_2m", pd.Series()).reindex([row.name])
            m.append(f"UR {v.iloc[0]:.0f}%" if not v.empty else "UR baixa")
        if not row["chuva_ok"]:
            v = df_src.get("precipitation", pd.Series()).reindex([row.name])
            m.append(f"Chuva {v.iloc[0]:.1f}mm" if not v.empty else "Chuva")
        return " | ".join(m) if m else "✅ Todos OK"

    rest["motivo"] = rest.apply(lambda r: motivo(r, df2), axis=1)
    return rest


def calcular_risco_fitossanitario(df: pd.DataFrame) -> dict:
    """
    Calcula risco de doenças foliares com base em horas consecutivas
    de condições favoráveis nas próximas 48h.

    Ferrugem Asiática (Phakopsora pachyrhizi):
      T 15–30°C + UR >80% por ≥12h consecutivas
      (Del Ponte et al. 2006; Yorinori et al. 2005)

    Brusone (Magnaporthe oryzae):
      T 20–28°C + UR >90% por ≥10h consecutivas
      (Filippi & Prabhu 2001)

    Retorna dict com detalhes de risco para cada doença.
    """
    df48 = df.head(48).copy()
    temp = df48.get("temperature_2m",       pd.Series(25, index=df48.index))
    umid = df48.get("relativehumidity_2m",  pd.Series(70, index=df48.index))
    riscos = {}

    # ── Ferrugem Asiática ──
    cond_fer = ((temp >= 15) & (temp <= 30) & (umid > 80))
    # Conta sequências consecutivas
    max_seq_fer = cur_fer = 0
    for v in cond_fer:
        if v: cur_fer += 1; max_seq_fer = max(max_seq_fer, cur_fer)
        else: cur_fer = 0
    total_horas_fer = int(cond_fer.sum())
    if max_seq_fer >= 20: nivel_fer = "Crítico"
    elif max_seq_fer >= 16: nivel_fer = "Alto"
    elif max_seq_fer >= 12: nivel_fer = "Médio"
    else: nivel_fer = "Baixo"
    riscos["ferrugem"] = {
        "doenca": "Ferrugem Asiática (Soja)",
        "horas_consecutivas": max_seq_fer,
        "horas_total": total_horas_fer,
        "nivel": nivel_fer,
        "limiar": 12,
        "condicao": cond_fer,
        "cor": "vermelho" if nivel_fer in ["Crítico","Alto"] else ("amarelo" if nivel_fer=="Médio" else "verde"),
        "emoji": "🍂",
        "referencia": "Del Ponte et al. (2006); Yorinori et al. (2005)",
    }

    # ── Brusone ──
    cond_bru = ((temp >= 20) & (temp <= 28) & (umid > 90))
    max_seq_bru = cur_bru = 0
    for v in cond_bru:
        if v: cur_bru += 1; max_seq_bru = max(max_seq_bru, cur_bru)
        else: cur_bru = 0
    total_horas_bru = int(cond_bru.sum())
    if max_seq_bru >= 18: nivel_bru = "Crítico"
    elif max_seq_bru >= 14: nivel_bru = "Alto"
    elif max_seq_bru >= 10: nivel_bru = "Médio"
    else: nivel_bru = "Baixo"
    riscos["brusone"] = {
        "doenca": "Brusone (Arroz/Trigo)",
        "horas_consecutivas": max_seq_bru,
        "horas_total": total_horas_bru,
        "nivel": nivel_bru,
        "limiar": 10,
        "condicao": cond_bru,
        "cor": "vermelho" if nivel_bru in ["Crítico","Alto"] else ("amarelo" if nivel_bru=="Médio" else "verde"),
        "emoji": "🌾",
        "referencia": "Filippi & Prabhu (2001)",
    }
    return riscos


def calcular_alertas_meteo(df: pd.DataFrame, lat: float) -> list:
    """Gera lista de alertas meteorológicos baseados nos próximos 7 dias."""
    alertas = []
    if df.empty:
        return alertas
    # Agrupa por dia
    df_daily = df.resample("D").agg({
        "temperature_2m":      ["max","min"],
        "precipitation":       "sum",
        "windgusts_10m":       "max",
        "cape":                "max",
        "relativehumidity_2m": "mean",
    }).head(7)

    for i, (dia, row) in enumerate(df_daily.iterrows()):
        try:
            tmin = row[("temperature_2m","min")]
            tmax = row[("temperature_2m","max")]
            pp   = row[("precipitation","sum")]
            raj  = row[("windgusts_10m","max")]
            cape = row[("cape","max")]
            data_str = dia.strftime("%d/%m")

            if tmin < 5:
                nivel = "vermelho" if tmin < 2 else "amarelo"
                alertas.append({"nivel":nivel,"icone":"❄️",
                    "titulo":f"{'🔴 EMERGÊNCIA' if tmin<2 else '🟡 ALERTA'} — Risco de Geada ({data_str})",
                    "msg":f"T mínima prevista: {tmin:.1f}°C. Proteja culturas sensíveis."})
            if pp > 40:
                nivel = "vermelho" if pp > 80 else "amarelo"
                alertas.append({"nivel":nivel,"icone":"⛈️",
                    "titulo":f"{'🔴' if pp>80 else '🟡'} Chuva Intensa ({data_str})",
                    "msg":f"{pp:.0f} mm acumulados. Risco de enxurrada e encharcamento."})
            if raj is not None and raj > 60:
                alertas.append({"nivel":"vermelho","icone":"💨",
                    "titulo":f"🔴 Rajada de Vento Forte ({data_str})",
                    "msg":f"Rajada prevista: {raj:.0f} km/h. Risco de danos a culturas e estruturas."})
            if cape is not None and cape > 1500:
                alertas.append({"nivel":"vermelho","icone":"⚡",
                    "titulo":f"🔴 Risco de Tempestade Severa ({data_str})",
                    "msg":f"CAPE: {cape:.0f} J/kg. Alta energia convectiva. Risco de granizo e raios."})
        except Exception:
            continue

    dias_secos = int((df_daily[("precipitation","sum")] < 1).sum())
    if dias_secos >= 5:
        alertas.append({"nivel":"amarelo","icone":"🌵",
            "titulo":f"🟡 Veranico — {dias_secos} dias sem chuva",
            "msg":"Déficit hídrico crescente. Monitore umidade do solo e intensifique irrigação."})

    if not alertas:
        alertas.append({"nivel":"verde","icone":"✅",
            "titulo":"🟢 Sem alertas ativos",
            "msg":"Condições meteorológicas favoráveis para as próximas 72 horas."})
    return alertas


def calcular_balanco_hidrico(df: pd.DataFrame, cad_mm: float = 65.0) -> dict:
    """Balanço hídrico Thornthwaite-Mather simplificado com dados horários agregados."""
    if df.empty:
        return {}
    df_d = df.resample("D").agg({"precipitation":"sum"}).head(7)
    # ETo estimada pelo método de Hargreaves (apenas Tmax, Tmin, Ra)
    # Aqui usamos proxy simples via radiação solar se disponível
    eto_lista = []
    for dia in df_d.index:
        try:
            sub = df[df.index.date == dia.date()]
            tmax = sub["temperature_2m"].max()
            tmin = sub["temperature_2m"].min()
            ra   = sub.get("shortwave_radiation", pd.Series(dtype=float)).mean()
            if pd.isna(ra) or ra == 0:
                ra = 200
            # Penman-Monteith simplificado (Hargreaves & Samani 1985)
            eto = 0.0023 * (tmax - tmin)**0.5 * ((tmax+tmin)/2 + 17.8) * (ra/2450)
            eto_lista.append(max(0, eto))
        except Exception:
            eto_lista.append(3.5)

    arm = cad_mm * 0.5
    resultados = []
    for i, (eto, pp) in enumerate(zip(eto_lista, df_d["precipitation"].fillna(0))):
        bal = pp - eto
        if bal >= 0:
            arm_n = min(arm + bal, cad_mm)
            exc, def_, etr = arm + bal - arm_n, 0.0, eto
        else:
            arm_n = max(0.0, arm * np.exp(bal / max(cad_mm, 1)))
            exc, etr = 0.0, pp + (arm - arm_n)
            def_ = eto - etr
        resultados.append({"arm":round(arm_n,2),"def":round(def_,2),
                           "exc":round(exc,2),"etr":round(etr,2),
                           "eto":round(eto,2),"pp":round(float(pp),2)})
        arm = arm_n

    if not resultados:
        return {}
    hoje   = resultados[0]
    arm_pct= round(hoje["arm"]/cad_mm*100, 1) if cad_mm > 0 else 0
    if arm_pct >= 70:
        rec, nivel = "✅ Solo bem suprido. Irrigação dispensável.", "verde"
    elif arm_pct >= 40:
        rec, nivel = f"💧 Irrigar {hoje['def']*1.1:.1f} mm para repor déficit.", "amarelo"
    else:
        rec, nivel = f"🚿 Déficit crítico {hoje['def']:.1f} mm. Irrigação urgente.", "vermelho"
    return {"arm_mm":hoje["arm"],"arm_pct":arm_pct,"def_mm":hoje["def"],
            "etr_mm":hoje["etr"],"eto_mm":hoje["eto"],"pp_mm":hoje["pp"],
            "cad_mm":cad_mm,"recomendacao":rec,"nivel":nivel,"serie":resultados}


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE VISUALIZAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def fig_variavel_com_ic(df_main: pd.DataFrame, var: str,
                         df_ic: pd.DataFrame = None,
                         titulo_extra: str = "") -> Figure:
    """
    Gráfico interativo Matplotlib de uma variável climática vs hora,
    com faixa de intervalo de confiança (±1σ e ±2σ) quando disponível.
    """
    fig, ax = plt.subplots(figsize=(12, 4), facecolor="#0d1117")
    ax.set_facecolor("#111827")

    cor = CORES_VAR.get(var, "#60a5fa")
    label = LABELS_PT.get(var, var)

    if var not in df_main.columns or df_main.empty:
        ax.text(0.5, 0.5, "Dados não disponíveis", transform=ax.transAxes,
                ha="center", va="center", color="white", fontsize=12)
        return fig

    serie = df_main[var].dropna()
    x     = serie.index

    # Faixas de IC (quando ensemble disponível)
    if df_ic is not None and not df_ic.empty:
        ic_re = df_ic.reindex(x, method="nearest")
        ax.fill_between(x, ic_re["ic95_low"], ic_re["ic95_high"],
                        alpha=0.12, color=cor, label="IC 95%")
        ax.fill_between(x, ic_re["ic68_low"], ic_re["ic68_high"],
                        alpha=0.22, color=cor, label="IC 68%")

    # Linha principal
    if var == "precipitation":
        ax.bar(x, serie.values, width=1/24, color=cor, alpha=0.8,
               align="center", label=label)
    else:
        ax.plot(x, serie.values, color=cor, linewidth=2.0,
                label=label, zorder=5)
        ax.fill_between(x, serie.values, alpha=0.12, color=cor)

    # Linhas de referência para variáveis com limiares
    limiares = {
        "temperature_2m":      [(5, "#60a5fa", "Risco geada (5°C)"),
                                 (30,"#f97316","Lim. defensivos (30°C)")],
        "windspeed_10m":       [(10,"#fbbf24","Lim. defensivos (10km/h)")],
        "relativehumidity_2m": [(55,"#f43f5e","Lim. defensivos (55%)"),
                                 (80,"#fb923c","Risco ferrugem (80%)")],
        "cape":                [(1000,"#fbbf24","CAPE moderado"),
                                 (2500,"#f43f5e","CAPE alto")],
    }
    for lim_val, lim_cor, lim_label in limiares.get(var, []):
        ax.axhline(lim_val, color=lim_cor, linewidth=0.9,
                   linestyle="--", alpha=0.7, label=lim_label)

    # Formatação dos eixos
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%Hh"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    ax.tick_params(colors="#9ca3af", labelsize=8)
    for sp in ax.spines.values():
        sp.set_edgecolor("#374151")
    ax.set_ylabel(label, color="#9ca3af", fontsize=9)
    ax.grid(True, color="#1f2937", linewidth=0.6, alpha=0.7)
    ax.set_title(f"{label}{titulo_extra}",
                 color="white", fontsize=10, fontweight="bold", pad=8)

    # IC legenda
    if df_ic is not None and not df_ic.empty:
        legenda_ic = mpatches.Patch(color=cor, alpha=0.22, label="IC 68% (1σ)")
        legenda_ic2= mpatches.Patch(color=cor, alpha=0.12, label="IC 95% (2σ)")
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles + [legenda_ic, legenda_ic2],
                  labels + ["IC 68% (1σ)", "IC 95% (2σ)"],
                  fontsize=7, facecolor="#111827", labelcolor="white",
                  edgecolor="#374151", loc="upper right")
    else:
        ax.legend(fontsize=7, facecolor="#111827", labelcolor="white",
                  edgecolor="#374151", loc="upper right")

    plt.tight_layout(pad=0.5)
    return fig


def fig_multiplas_variaveis(df: pd.DataFrame, vars_list: list) -> Figure:
    """Painel com múltiplos subplots, um por variável selecionada."""
    n = len(vars_list)
    if n == 0:
        return None
    fig, axes = plt.subplots(n, 1, figsize=(12, 3.2*n), facecolor="#0d1117",
                              sharex=True)
    if n == 1:
        axes = [axes]
    for ax, var in zip(axes, vars_list):
        ax.set_facecolor("#111827")
        cor = CORES_VAR.get(var, "#60a5fa")
        lbl = LABELS_PT.get(var, var)
        if var not in df.columns:
            continue
        serie = df[var].dropna()
        if var == "precipitation":
            ax.bar(serie.index, serie.values, width=1/24, color=cor, alpha=0.85)
        else:
            ax.plot(serie.index, serie.values, color=cor, linewidth=1.8)
            ax.fill_between(serie.index, serie.values, alpha=0.12, color=cor)
        ax.set_ylabel(lbl, color="#9ca3af", fontsize=8)
        ax.tick_params(colors="#9ca3af", labelsize=7)
        for sp in ax.spines.values():
            sp.set_edgecolor("#374151")
        ax.grid(True, color="#1f2937", linewidth=0.5, alpha=0.6)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%Hh"))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))

    plt.tight_layout(pad=0.5)
    return fig


def fig_matriz_alertas(df_main: pd.DataFrame, df_janelas: pd.DataFrame,
                        riscos: dict) -> Figure:
    """
    Matriz hora × variável — exibe visualmente quais horas e quais variáveis
    estão dentro/fora dos limiares de risco ou defensivos.

    Linhas = horas (0–23h do primeiro dia)
    Colunas = variáveis monitoradas
    Cor = verde (OK) / amarelo (atenção) / vermelho (bloqueado)
    """
    vars_matriz = {
        "Temp (°C)":   ("temperature_2m",      lambda v: 0 if v<30 else 2),
        "UR (%)":      ("relativehumidity_2m",  lambda v: 0 if v>55 else 2),
        "Vento (km/h)":("windspeed_10m",        lambda v: 0 if v<10 else (1 if v<15 else 2)),
        "Precip (mm)": ("precipitation",        lambda v: 0 if v==0 else (1 if v<2 else 2)),
        "Ferrugem":    ("relativehumidity_2m",  None),  # tratamento especial
        "Brusone":     ("relativehumidity_2m",  None),
        "Jan.Defens.": ("_janela",              None),
    }

    df24 = df_main.head(24).copy()
    temp_h = df24.get("temperature_2m",      pd.Series(25, index=df24.index))
    ur_h   = df24.get("relativehumidity_2m", pd.Series(70, index=df24.index))
    vt_h   = df24.get("windspeed_10m",       pd.Series(5,  index=df24.index))
    pp_h   = df24.get("precipitation",       pd.Series(0,  index=df24.index))

    n_horas = min(24, len(df24))
    horas   = [df24.index[i].strftime("%Hh") for i in range(n_horas)]

    colunas = ["Temp", "UR", "Vento", "Chuva", "Ferrugem", "Brusone", "Janela Def."]
    matriz  = np.zeros((n_horas, len(colunas)))

    for i in range(n_horas):
        t  = temp_h.iloc[i] if i < len(temp_h) else 25
        ur = ur_h.iloc[i]   if i < len(ur_h)   else 70
        vt = vt_h.iloc[i]   if i < len(vt_h)   else 5
        pp = pp_h.iloc[i]   if i < len(pp_h)    else 0

        # 0=verde, 1=amarelo, 2=vermelho
        matriz[i, 0] = 0 if t < 30 else 2        # Temp
        matriz[i, 1] = 0 if ur > 55 else 2        # UR
        matriz[i, 2] = 0 if vt < 10 else (1 if vt < 15 else 2)   # Vento
        matriz[i, 3] = 0 if pp == 0 else (1 if pp < 2 else 2)     # Chuva

        # Ferrugem: T 15-30 + UR > 80
        fer = 1 if (15 <= t <= 30 and ur > 80) else 0
        matriz[i, 4] = fer * 2

        # Brusone: T 20-28 + UR > 90
        bru = 1 if (20 <= t <= 28 and ur > 90) else 0
        matriz[i, 5] = bru * 2

        # Janela defensivos
        ok_count = (t < 30) + (ur > 55) + (vt < 10) + (pp == 0)
        matriz[i, 6] = 0 if ok_count == 4 else (1 if ok_count == 3 else 2)

    # Cria colormap tricolor
    cmap = mcolors.ListedColormap(["#22c55e", "#fbbf24", "#ef4444"])
    norm = mcolors.BoundaryNorm([0, 0.5, 1.5, 2.5], cmap.N)

    fig, ax = plt.subplots(figsize=(12, max(6, n_horas * 0.28)), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")

    im = ax.imshow(matriz, cmap=cmap, norm=norm, aspect="auto")

    ax.set_xticks(range(len(colunas)))
    ax.set_xticklabels(colunas, fontsize=9, color="white", fontweight="bold")
    ax.set_yticks(range(n_horas))
    ax.set_yticklabels(horas, fontsize=7, color="#9ca3af")
    ax.set_title("Matriz de Risco Hora × Variável (próximas 24h)",
                 color="white", fontsize=11, fontweight="bold", pad=10)

    # Anotações nos cells
    for i in range(n_horas):
        for j in range(len(colunas)):
            val = matriz[i, j]
            txt = "✓" if val == 0 else ("!" if val == 1 else "✗")
            cor_txt = "#000" if val == 0 else "#000"
            ax.text(j, i, txt, ha="center", va="center",
                    fontsize=7, color=cor_txt, fontweight="bold")

    # Legenda
    p_verde  = mpatches.Patch(facecolor="#22c55e", label="✓ Favorável / OK")
    p_amarelo= mpatches.Patch(facecolor="#fbbf24", label="! Atenção")
    p_verm   = mpatches.Patch(facecolor="#ef4444", label="✗ Risco / Bloqueado")
    ax.legend(handles=[p_verde, p_amarelo, p_verm],
              loc="lower right", fontsize=8,
              facecolor="#111827", labelcolor="white", edgecolor="#374151",
              bbox_to_anchor=(1.0, -0.08))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#374151")
    ax.spines["left"].set_color("#374151")
    plt.tight_layout(pad=0.8)
    return fig


def fig_confianca_modelos(ensemble: dict, var: str) -> Figure:
    """
    Visualização do spread entre modelos como indicador de confiança.
    Apresenta série de cada modelo + média + IC, com texto explicativo
    do nível de confiança para o agricultor.
    """
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

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6),
                                     facecolor="#0d1117",
                                     gridspec_kw={"height_ratios": [3,1]})
    for ax in [ax1, ax2]:
        ax.set_facecolor("#111827")
        ax.tick_params(colors="#9ca3af", labelsize=8)
        for sp in ax.spines.values():
            sp.set_edgecolor("#374151")
        ax.grid(True, color="#1f2937", linewidth=0.5, alpha=0.6)

    colors_mod = ["#60a5fa","#f97316","#34d399","#a78bfa"]
    df_all = pd.concat(series.values(), axis=1)
    media  = df_all.mean(axis=1)
    std    = df_all.std(axis=1)
    cv     = (std / (media.abs() + 1e-6) * 100)

    # Faixas de confiança
    ax1.fill_between(media.index, media-2*std, media+2*std,
                     alpha=0.10, color="#60a5fa", label="IC 95%")
    ax1.fill_between(media.index, media-std, media+std,
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

    # Painel de coeficiente de variação (proxy de incerteza)
    cv_colors = ["#22c55e" if v < 10 else ("#fbbf24" if v < 25 else "#ef4444")
                 for v in cv.values]
    ax2.bar(cv.index, cv.values, width=1/24, color=cv_colors, alpha=0.85)
    ax2.set_ylabel("CV (%) = Incerteza", color="#9ca3af", fontsize=8)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax2.xaxis.set_major_locator(mdates.DayLocator())

    # Faixas de referência no painel de CV
    ax2.axhline(10, color="#22c55e", linestyle="--", linewidth=0.8,
                alpha=0.6, label="Alta confiança (<10%)")
    ax2.axhline(25, color="#ef4444", linestyle="--", linewidth=0.8,
                alpha=0.6, label="Baixa confiança (>25%)")
    ax2.legend(fontsize=7, facecolor="#111827", labelcolor="white",
               edgecolor="#374151", loc="upper right")

    plt.tight_layout(pad=0.5)
    return fig


def df_previsao_display(df: pd.DataFrame) -> pd.DataFrame:
    """Formata o DataFrame horário para exibição ao usuário."""
    if df.empty:
        return pd.DataFrame()
    cols_show = {k: v for k, v in LABELS_PT.items() if k in df.columns}
    df_disp = df[list(cols_show.keys())].copy()
    df_disp.columns = [cols_show[c] for c in df_disp.columns]
    df_disp.index = df_disp.index.strftime("%d/%m %Hh")
    df_disp.index.name = "Data/Hora"
    # Substitui código de tempo por texto
    if "Código de Tempo (WMO)" in df_disp.columns:
        df_disp["Condição"] = df_disp["Código de Tempo (WMO)"].apply(
            lambda x: WCODE_MAP.get(int(x), f"Cód {int(x)}") if pd.notna(x) else "—"
        )
        df_disp.drop(columns=["Código de Tempo (WMO)"], inplace=True)
    return df_disp.round(1)


# ─────────────────────────────────────────────────────────────────────────────
# MAPA INTERATIVO (FOLIUM)
# ─────────────────────────────────────────────────────────────────────────────

def criar_mapa(lat_sel: float = -20.4428, lon_sel: float = -54.6460) -> folium.Map:
    """
    Cria mapa Folium centrado no MS com:
    - Camada OpenStreetMap + camada satélite (Esri)
    - Marcadores de municípios de referência (clicáveis)
    - Marcador do ponto selecionado atual
    - Caixa de instrução
    """
    m = folium.Map(
        location=[-20.5, -54.5],
        zoom_start=7,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    # Camada satélite
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="🛰️ Satélite",
        overlay=False,
        control=True,
    ).add_to(m)

    # Municípios de referência
    for nome, (lat, lon) in MUNICIPIOS_REF.items():
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color=VERDE_MEDIO,
            fill=True,
            fill_color=VERDE_MEDIO,
            fill_opacity=0.7,
            tooltip=f"📍 {nome}",
            popup=folium.Popup(
                f"<b>{nome}</b><br>Lat: {lat:.4f}<br>Lon: {lon:.4f}<br>"
                f"<small>Clique em qualquer ponto do mapa para selecionar</small>",
                max_width=200,
            ),
        ).add_to(m)

    # Marcador do ponto atual
    folium.Marker(
        location=[lat_sel, lon_sel],
        popup=f"Ponto selecionado<br>Lat: {lat_sel:.4f}<br>Lon: {lon_sel:.4f}",
        tooltip="📌 Ponto de análise atual",
        icon=folium.Icon(color="red", icon="star", prefix="fa"),
    ).add_to(m)

    # Retângulo do MS (bounding box)
    folium.Rectangle(
        bounds=[[-23.67, -57.65], [-17.16, -50.92]],
        color=VERDE_MEDIO,
        fill=False,
        weight=1.5,
        dash_array="6",
        tooltip="Mato Grosso do Sul",
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return m


# ─────────────────────────────────────────────────────────────────────────────
# E-MAIL — HTML RICO
# ─────────────────────────────────────────────────────────────────────────────

def gerar_html_relatorio(lat, lon, df, alertas, riscos, bh, janelas, municipio_nome="") -> str:
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    loc   = municipio_nome or f"{lat:.4f}°S, {lon:.4f}°W"

    def card(titulo, valor, cor="#1B4D2E"):
        return (f"<div style='flex:1;min-width:110px;background:#fff;border-radius:10px;"
                f"border-top:4px solid {cor};padding:12px 10px;box-shadow:0 2px 8px rgba(0,0,0,0.08);text-align:center;'>"
                f"<div style='font-size:11px;color:#777;'>{titulo}</div>"
                f"<div style='font-size:20px;font-weight:bold;color:#222;'>{valor}</div></div>")

    cards = ""
    if not df.empty:
        try:
            cards += card("🌡 Temp Atual", f"{df['temperature_2m'].iloc[0]:.1f}°C", "#e65100")
            cards += card("🌧 Chuva 24h",  f"{df['precipitation'].sum():.1f}mm", "#1565c0")
            cards += card("💧 UR Atual",   f"{df['relativehumidity_2m'].iloc[0]:.0f}%", "#0277bd")
            cards += card("💨 Vento",      f"{df['windspeed_10m'].iloc[0]:.0f}km/h", "#6a1b9a")
        except Exception:
            pass

    html_alertas = ""
    _cor_al = {"verde":"#e8f5e9","amarelo":"#fff8e1","vermelho":"#ffebee"}
    _brd_al = {"verde":"#43a047","amarelo":"#fbc02d","vermelho":"#e53935"}
    for al in alertas:
        bg = _cor_al.get(al["nivel"],"#f5f5f5")
        brd= _brd_al.get(al["nivel"],"#9e9e9e")
        html_alertas += (f"<div style='background:{bg};border-left:5px solid {brd};"
                         f"border-radius:6px;padding:10px 14px;margin:5px 0;'>"
                         f"<b>{al['icone']} {al['titulo']}</b><br>"
                         f"<span style='font-size:12px;'>{al['msg']}</span></div>")

    html_riscos = ""
    for r in riscos.values():
        bg = _cor_al.get(r["cor"],"#f5f5f5")
        brd= _brd_al.get(r["cor"],"#9e9e9e")
        html_riscos += (f"<div style='background:{bg};border-left:5px solid {brd};"
                        f"border-radius:6px;padding:10px 14px;margin:5px 0;'>"
                        f"<b>{r['emoji']} {r['doenca']} — Risco {r['nivel']}</b><br>"
                        f"<span style='font-size:12px;'>{r['horas_consecutivas']}h consecutivas favoráveis "
                        f"(limiar: {r['limiar']}h) | Ref.: {r['referencia']}</span></div>")

    bh_html = ""
    if bh:
        bh_html = (f"<p style='font-size:13px;'>"
                   f"ARM: {bh.get('arm_mm',0):.1f}mm ({bh.get('arm_pct',0):.0f}% CAD) | "
                   f"Déficit: {bh.get('def_mm',0):.1f}mm<br>"
                   f"<b>Recomendação:</b> {bh.get('recomendacao','—')}</p>")

    n_ab = sum(1 for j in janelas if j["status"]=="aberta")
    n_bl = sum(1 for j in janelas if j["status"]=="bloqueada")

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
        Dados: Open-Meteo (GFS/ICON/ERA5) · NASA POWER · INPE<br>MVP v4.0 · {agora}
      </p>
    </div>
  </div>
</body></html>"""


def enviar_email(html: str, assunto: str, extras: list = None) -> tuple:
    if not _email_ok:
        return False, "E-mail não configurado"
    try:
        dests = list(EMAIL_DESTINATARIOS)
        if extras:
            dests += [e for e in extras if "@" in e and e not in dests]
        msg = MIMEMultipart("mixed")
        msg["Subject"] = assunto
        msg["From"]    = EMAIL_REMETENTE
        msg["To"]      = ", ".join(dests)
        msg.attach(MIMEMultipart("alternative"))
        msg.get_payload(0).attach(MIMEText(html, "html"))
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
        Open-Meteo (GFS · ICON · ERA5) · NASA POWER · INPE · v4.0
      </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Estado da sessão ─────────────────────────────────────────────────────
    if "lat_sel" not in st.session_state:
        st.session_state["lat_sel"] = -20.4428
    if "lon_sel" not in st.session_state:
        st.session_state["lon_sel"] = -54.6460
    if "mun_nome" not in st.session_state:
        st.session_state["mun_nome"] = "Campo Grande"
    if "analisado" not in st.session_state:
        st.session_state["analisado"] = False

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

        # Ponto selecionado (atualizado pelo mapa)
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.88rem;">📍 PONTO SELECIONADO</p>', unsafe_allow_html=True)

        lat_input = st.number_input("Latitude",  value=st.session_state["lat_sel"],
                                    min_value=-23.8, max_value=-17.0, step=0.0001,
                                    format="%.4f", key="lat_input")
        lon_input = st.number_input("Longitude", value=st.session_state["lon_sel"],
                                    min_value=-57.8, max_value=-50.8, step=0.0001,
                                    format="%.4f", key="lon_input")

        if lat_input != st.session_state["lat_sel"] or lon_input != st.session_state["lon_sel"]:
            st.session_state["lat_sel"]  = lat_input
            st.session_state["lon_sel"]  = lon_input
            st.session_state["mun_nome"] = f"Ponto ({lat_input:.3f}, {lon_input:.3f})"
            st.session_state["analisado"]= False

        # Município rápido
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.88rem;">🏙️ OU SELECIONE MUNICÍPIO</p>', unsafe_allow_html=True)
        mun_escolha = st.selectbox("Município de referência",
            ["— selecionar —"] + list(MUNICIPIOS_REF.keys()),
            index=0, label_visibility="collapsed")
        if mun_escolha != "— selecionar —":
            lat_m, lon_m = MUNICIPIOS_REF[mun_escolha]
            st.session_state["lat_sel"]  = lat_m
            st.session_state["lon_sel"]  = lon_m
            st.session_state["mun_nome"] = mun_escolha

        st.caption(f"📌 {st.session_state['mun_nome']}")
        st.caption(f"🌐 {st.session_state['lat_sel']:.4f}°S, {st.session_state['lon_sel']:.4f}°W")
        st.markdown("---")

        # Configurações da análise
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.88rem;">⚙️ CONFIGURAÇÕES</p>', unsafe_allow_html=True)

        modelo_sel = st.selectbox("Modelo meteorológico",
            list(MODELOS_OPENMETEO.keys()),
            format_func=lambda k: MODELOS_OPENMETEO[k],
            index=0, label_visibility="collapsed")
        dias_prev = st.slider("Dias de previsão", 3, 7, 7)
        cad_opcao = st.selectbox("Textura do solo (Balanço Hídrico)",
            ["Argiloso (CAD=100mm)","Médio/Franco (CAD=65mm)","Arenoso (CAD=35mm)"],
            index=1, label_visibility="collapsed")
        cad_mm = {"Argiloso (CAD=100mm)":100.0,
                  "Médio/Franco (CAD=65mm)":65.0,
                  "Arenoso (CAD=35mm)":35.0}[cad_opcao]

        calcular_ic = st.checkbox("Calcular intervalo de confiança\n(multi-modelo — +30s)", value=True)
        st.markdown("---")

        # E-mail
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.88rem;">📧 E-MAIL</p>', unsafe_allow_html=True)
        if _email_ok:
            st.caption(f"✅ {', '.join(EMAIL_DESTINATARIOS)}")
        else:
            st.caption("⚠️ Configure [email] no secrets.toml")
        st.markdown("---")

        botao = st.button("🚀  GERAR ANÁLISE", use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # MAPA INTERATIVO
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown('<div class="secao-titulo">🗺️ Selecione o ponto de análise no mapa</div>',
                unsafe_allow_html=True)
    st.caption("Clique em qualquer ponto do MS para definir as coordenadas. "
               "Use os marcadores verdes para municípios de referência.")

    mapa = criar_mapa(st.session_state["lat_sel"], st.session_state["lon_sel"])
    mapa_output = st_folium(mapa, width="100%", height=420,
                             returned_objects=["last_clicked"])

    # Atualiza coordenadas se clicou no mapa
    if mapa_output and mapa_output.get("last_clicked"):
        clk = mapa_output["last_clicked"]
        lat_c, lon_c = clk["lat"], clk["lng"]
        # Verifica se está dentro do bounding box do MS (com margem)
        if -24.0 <= lat_c <= -16.8 and -58.0 <= lon_c <= -50.5:
            if (abs(lat_c - st.session_state["lat_sel"]) > 0.001 or
                    abs(lon_c - st.session_state["lon_sel"]) > 0.001):
                st.session_state["lat_sel"]  = round(lat_c, 4)
                st.session_state["lon_sel"]  = round(lon_c, 4)
                # Verifica se é um município de referência
                nome_prox = None
                for nm, (lm, lom) in MUNICIPIOS_REF.items():
                    if abs(lm - lat_c) < 0.1 and abs(lom - lon_c) < 0.1:
                        nome_prox = nm
                        break
                st.session_state["mun_nome"] = (nome_prox or
                    f"Ponto ({lat_c:.3f}, {lon_c:.3f})")
                st.session_state["analisado"] = False
                st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # GATILHO DE ANÁLISE
    # ─────────────────────────────────────────────────────────────────────────
    if not botao and not st.session_state["analisado"]:
        st.info("👆 Clique em um ponto no mapa ou selecione um município, depois clique em **GERAR ANÁLISE**.")
        return

    if botao:
        st.session_state["analisado"] = True

    lat = st.session_state["lat_sel"]
    lon = st.session_state["lon_sel"]
    nome_local = st.session_state["mun_nome"]

    # ─────────────────────────────────────────────────────────────────────────
    # COLETA DE DADOS
    # ─────────────────────────────────────────────────────────────────────────
    progress = st.progress(0, text="Coletando dados...")

    progress.progress(10, text=f"🌤 Open-Meteo ({MODELOS_OPENMETEO[modelo_sel]})...")
    dados_raw = buscar_openmeteo(lat, lon, modelo_sel, dias_prev)

    df_main = openmeteo_para_df(dados_raw)

    ensemble_raw = {}
    df_ic_cache  = {}
    if calcular_ic:
        progress.progress(30, text="📊 Calculando ensemble multi-modelo...")
        ensemble_raw = buscar_ensemble_openmeteo(lat, lon, dias_prev)
        for v in ["temperature_2m","precipitation","relativehumidity_2m","windspeed_10m"]:
            df_ic_cache[v] = calcular_intervalo_confianca(ensemble_raw, v)

    progress.progress(50, text="☀️ NASA POWER (umidade do solo)...")
    dados_nasa = buscar_nasa_power(lat, lon)

    progress.progress(60, text="🔥 INPE Queimadas...")
    df_focos = buscar_focos_inpe()

    progress.progress(70, text="📐 Calculando análises agronômicas...")
    janelas_df  = calcular_janelas_defensivos(df_main)
    riscos      = calcular_risco_fitossanitario(df_main)
    alertas     = calcular_alertas_meteo(df_main, lat)
    bh          = calcular_balanco_hidrico(df_main, cad_mm)

    progress.progress(90, text="🎨 Renderizando...")

    # ── Banner ───────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,{VERDE_ESCURO},{VERDE_MEDIO});
                border-radius:10px;padding:14px 22px;margin:16px 0 20px 0;">
      <span style="color:white;font-family:Montserrat;font-weight:700;font-size:1.05rem;">
        📍 {nome_local}
      </span>
      <span style="color:rgba(255,255,255,0.7);font-size:0.82rem;margin-left:14px;">
        {lat:.4f}°S, {lon:.4f}°W · Modelo: {MODELOS_OPENMETEO[modelo_sel]} · {datetime.now().strftime('%d/%m/%Y %H:%M')}
      </span>
    </div>""", unsafe_allow_html=True)

    # ── Métricas rápidas ─────────────────────────────────────────────────────
    if not df_main.empty:
        try:
            c1,c2,c3,c4,c5,c6 = st.columns(6)
            with c1: st.metric("🌡 Temperatura",  f"{df_main['temperature_2m'].iloc[0]:.1f}°C")
            with c2: st.metric("🌧 Chuva 24h",    f"{df_main['precipitation'].iloc[:24].sum():.1f} mm")
            with c3: st.metric("💧 Umidade",       f"{df_main['relativehumidity_2m'].iloc[0]:.0f}%")
            with c4: st.metric("💨 Vento",         f"{df_main['windspeed_10m'].iloc[0]:.0f} km/h")
            with c5: st.metric("☀️ Radiação",      f"{df_main.get('shortwave_radiation', pd.Series([0])).iloc[0]:.0f} W/m²")
            with c6: st.metric("⚡ CAPE",           f"{df_main.get('cape', pd.Series([0])).iloc[0]:.0f} J/kg")
        except Exception:
            pass

    # ═════════════════════════════════════════════════════════════════════════
    # ABAS
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
        st.caption(f"Modelo: **{MODELOS_OPENMETEO[modelo_sel]}** · Horizonte: {dias_prev} dias · "
                   f"Fonte: Open-Meteo · Justificativa: GFS validado para Centro-Oeste (Souza et al. 2021); "
                   f"ICON superior para convecção subtropical (Zängl et al. 2015)")

        # Seletor de variável para o gráfico individual com IC
        var_escolhida = st.selectbox(
            "Variável para gráfico detalhado com intervalo de confiança:",
            [v for v in VARIAVEIS_HORARIAS if v in df_main.columns],
            format_func=lambda v: LABELS_PT.get(v, v),
            index=0,
        )

        df_ic_var = df_ic_cache.get(var_escolhida, pd.DataFrame()) if calcular_ic else pd.DataFrame()
        fig_ic = fig_variavel_com_ic(df_main, var_escolhida, df_ic_var)
        st.pyplot(fig_ic, use_container_width=True)
        plt.close(fig_ic)

        # Nota sobre o IC
        if calcular_ic and not df_ic_var.empty:
            cv_med = df_ic_var["cv_pct"].mean()
            conf   = "Alta" if cv_med < 10 else ("Moderada" if cv_med < 25 else "Baixa")
            cor_c  = "#22c55e" if conf=="Alta" else ("#fbbf24" if conf=="Moderada" else "#ef4444")
            st.markdown(f"""<div class="alert-azul">
              <b>📊 Confiança da previsão para {LABELS_PT.get(var_escolhida, var_escolhida)}:</b>
              <span style="color:{cor_c};font-weight:bold;"> {conf} </span>
              (CV médio = {cv_med:.1f}%) — Baseado no spread entre {len(ensemble_raw)} modelos
              (GFS, ICON, Best Match). IC 68% = ±1σ; IC 95% = ±2σ (Buizza et al. 2005).
            </div>""", unsafe_allow_html=True)

        # Painel multi-variável
        st.markdown('<div class="secao-titulo">📊 Painel Geral — Todas as Variáveis</div>',
                    unsafe_allow_html=True)
        vars_painel = st.multiselect(
            "Selecione variáveis para o painel:",
            [v for v in VARIAVEIS_HORARIAS if v in df_main.columns],
            default=["temperature_2m","precipitation","relativehumidity_2m","windspeed_10m"],
            format_func=lambda v: LABELS_PT.get(v, v),
        )
        if vars_painel:
            fig_multi = fig_multiplas_variaveis(df_main, vars_painel)
            if fig_multi:
                st.pyplot(fig_multi, use_container_width=True)
                plt.close(fig_multi)

        # Confiança entre modelos
        if calcular_ic and ensemble_raw:
            st.markdown('<div class="secao-titulo">🔬 Spread entre Modelos — Análise de Confiança</div>',
                        unsafe_allow_html=True)
            var_conf = st.selectbox(
                "Variável para análise de spread:",
                ["temperature_2m","precipitation","relativehumidity_2m","windspeed_10m"],
                format_func=lambda v: LABELS_PT.get(v, v),
                index=0, key="sel_conf",
            )
            fig_conf = fig_confianca_modelos(ensemble_raw, var_conf)
            if fig_conf:
                st.pyplot(fig_conf, use_container_width=True)
                plt.close(fig_conf)
            st.caption("CV (Coeficiente de Variação) < 10% = Alta confiança | 10–25% = Moderada | > 25% = Baixa. "
                       "Metodologia: Goswami et al. (2010); Buizza et al. (2005).")

        # DataFrame horário completo
        st.markdown('<div class="secao-titulo">🗃️ Dados Horários Completos</div>',
                    unsafe_allow_html=True)
        df_disp = df_previsao_display(df_main)
        if not df_disp.empty:
            st.dataframe(df_disp, use_container_width=True, height=320)
            csv = df_disp.to_csv().encode("utf-8")
            st.download_button("⬇️ Baixar CSV", csv,
                               f"previsao_{nome_local.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                               "text/csv")

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 2 — CLIMATOLOGIA & SOLO
    # ─────────────────────────────────────────────────────────────────────────
    with aba2:
        st.markdown('<div class="secao-titulo">🌍 Climatologia — Resumo Estatístico do Período</div>',
                    unsafe_allow_html=True)

        if not df_main.empty:
            # Estatísticas descritivas das variáveis principais
            vars_stat = ["temperature_2m","relativehumidity_2m","windspeed_10m",
                         "precipitation","shortwave_radiation","cape"]
            vars_stat = [v for v in vars_stat if v in df_main.columns]
            df_stat = df_main[vars_stat].describe().T
            df_stat.index = [LABELS_PT.get(i,i) for i in df_stat.index]
            df_stat = df_stat[["mean","std","min","max"]].round(2)
            df_stat.columns = ["Média","Desvio Padrão","Mínimo","Máximo"]
            st.dataframe(df_stat, use_container_width=True)

            # Percentis de temperatura
            st.markdown('<div class="secao-titulo">🌡️ Distribuição de Temperatura (percentis)</div>',
                        unsafe_allow_html=True)
            temp_s = df_main["temperature_2m"].dropna()
            fig_t, ax_t = plt.subplots(figsize=(10,3), facecolor="#0d1117")
            ax_t.set_facecolor("#111827")
            ax_t.hist(temp_s.values, bins=30, color=CORES_VAR["temperature_2m"],
                      alpha=0.8, edgecolor="none")
            for p, cor, lbl in [(10,"#60a5fa","P10"),(50,"#fbbf24","P50"),(90,"#f43f5e","P90")]:
                v = float(np.percentile(temp_s.dropna(), p))
                ax_t.axvline(v, color=cor, linewidth=1.5, linestyle="--",
                             label=f"{lbl}: {v:.1f}°C")
            ax_t.set_xlabel("Temperatura (°C)", color="#9ca3af", fontsize=9)
            ax_t.set_ylabel("Frequência", color="#9ca3af", fontsize=9)
            ax_t.tick_params(colors="#9ca3af", labelsize=8)
            for sp in ax_t.spines.values(): sp.set_edgecolor("#374151")
            ax_t.legend(fontsize=8, facecolor="#111827", labelcolor="white", edgecolor="#374151")
            ax_t.set_title("Distribuição de Temperatura — Período de Previsão",
                           color="white", fontsize=10, fontweight="bold")
            plt.tight_layout()
            st.pyplot(fig_t, use_container_width=True)
            plt.close(fig_t)

            # Acumulado de precipitação diária
            st.markdown('<div class="secao-titulo">🌧️ Precipitação Acumulada Diária</div>',
                        unsafe_allow_html=True)
            pp_diario = df_main["precipitation"].resample("D").sum()
            fig_pp, ax_pp = plt.subplots(figsize=(10,3), facecolor="#0d1117")
            ax_pp.set_facecolor("#111827")
            bars = ax_pp.bar(range(len(pp_diario)), pp_diario.values,
                             color=[VERDE_MEDIO if v < 20 else (AMARELO_ALERT if v < 50 else VERMELHO_ALRT)
                                    for v in pp_diario.values],
                             alpha=0.85, edgecolor="none")
            ax_pp.set_xticks(range(len(pp_diario)))
            ax_pp.set_xticklabels([d.strftime("%d/%m") for d in pp_diario.index],
                                   color="#9ca3af", fontsize=8)
            ax_pp.set_ylabel("Precipitação (mm)", color="#9ca3af", fontsize=9)
            ax_pp.axhline(20, color=AMARELO_ALERT, linewidth=0.8, linestyle="--",
                          alpha=0.7, label="20mm (atenção)")
            ax_pp.axhline(50, color=VERMELHO_ALRT, linewidth=0.8, linestyle="--",
                          alpha=0.7, label="50mm (alerta)")
            ax_pp.tick_params(colors="#9ca3af", labelsize=8)
            for sp in ax_pp.spines.values(): sp.set_edgecolor("#374151")
            ax_pp.legend(fontsize=8, facecolor="#111827", labelcolor="white", edgecolor="#374151")
            ax_pp.set_title("Precipitação Acumulada por Dia",
                            color="white", fontsize=10, fontweight="bold")
            plt.tight_layout()
            st.pyplot(fig_pp, use_container_width=True)
            plt.close(fig_pp)

        # Umidade do solo — NASA POWER
        st.markdown('<div class="secao-titulo">🌱 Umidade do Solo — NASA POWER (últimos 30 dias)</div>',
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
                    ax_s.set_facecolor("#111827")
                    ax_s.plot(range(len(vt)), vt, color="#66BB6A", linewidth=2,
                              label="GWETTOP (0–5cm)")
                    ax_s.fill_between(range(len(vt)), vt, alpha=0.18, color="#66BB6A")
                    ax_s.plot(range(len(vr)), vr, color="#42A5F5", linewidth=2,
                              linestyle="--", label="GWETROOT (zona radicular)")
                    ax_s.fill_between(range(len(vr)), vr, alpha=0.12, color="#42A5F5")
                    ax_s.axhline(0.5, color="#FFB74D", linewidth=0.8, linestyle=":",
                                 alpha=0.7, label="Capacidade de campo (0.5)")
                    ax_s.axhline(0.2, color="#ef4444", linewidth=0.8, linestyle=":",
                                 alpha=0.7, label="Ponto de murcha permanente (0.2)")
                    ax_s.set_ylim(0, 1)
                    ax_s.set_ylabel("Umidade relativa (0–1)", color="#9ca3af", fontsize=9)
                    step = max(1, len(datas_n)//10)
                    ax_s.set_xticks(range(0, len(datas_n), step))
                    ax_s.set_xticklabels(
                        [datas_n[i][6:8]+"/"+datas_n[i][4:6] for i in range(0,len(datas_n),step)],
                        color="#9ca3af", fontsize=8, rotation=30)
                    ax_s.tick_params(colors="#9ca3af", labelsize=8)
                    for sp in ax_s.spines.values(): sp.set_edgecolor("#374151")
                    ax_s.grid(True, color="#1f2937", linewidth=0.5, alpha=0.6)
                    ax_s.legend(fontsize=8, facecolor="#111827", labelcolor="white",
                                edgecolor="#374151")
                    ax_s.set_title("Umidade do Solo — NASA POWER (GWETTOP & GWETROOT)",
                                   color="white", fontsize=10)
                    plt.tight_layout()
                    st.pyplot(fig_s, use_container_width=True)
                    plt.close(fig_s)

                    # DataFrame de umidade
                    df_solo = pd.DataFrame({
                        "Data": [datas_n[i][6:8]+"/"+datas_n[i][4:6]+"/"+datas_n[i][:4]
                                 for i in range(len(datas_n))],
                        "GWETTOP (0–5cm)":   [round(v, 3) for v in vt],
                        "GWETROOT (radicular)":[round(v, 3) for v in vr],
                        "Status": ["✅ OK" if v > 0.5 else ("⚠️ Atenção" if v > 0.2 else "❌ Crítico")
                                   for v in vr],
                    })
                    st.dataframe(df_solo.tail(14), use_container_width=True, hide_index=True)
            except Exception as e:
                st.info(f"ℹ️ Dados NASA POWER não disponíveis: {e}")
        else:
            st.info("ℹ️ NASA POWER não respondeu. Verifique conexão.")

        # Balanço hídrico
        st.markdown(f'<div class="secao-titulo">💧 Balanço Hídrico (Thornthwaite-Mather) — {cad_opcao}</div>',
                    unsafe_allow_html=True)
        if bh:
            c1,c2,c3,c4 = st.columns(4)
            with c1: st.metric("ARM atual", f"{bh['arm_mm']:.1f} mm",
                               delta=f"{bh['arm_pct']:.0f}% da CAD")
            with c2: st.metric("CAD", f"{bh['cad_mm']:.0f} mm")
            with c3: st.metric("Déficit hoje", f"{bh['def_mm']:.1f} mm",
                               delta_color="inverse",
                               delta="❌" if bh["def_mm"]>0 else "✅")
            with c4: st.metric("ETR estimada", f"{bh['etr_mm']:.1f} mm/dia")

            if "serie" in bh:
                serie = bh["serie"][:7]
                dias  = [f"D+{i}" for i in range(len(serie))]
                fig_bh, (ax1,ax2) = plt.subplots(2,1,figsize=(10,5),facecolor="#0d1117",
                                                   gridspec_kw={"height_ratios":[2,1]})
                for ax in [ax1,ax2]:
                    ax.set_facecolor("#111827"); ax.tick_params(colors="#9ca3af",labelsize=8)
                    for sp in ax.spines.values(): sp.set_edgecolor("#374151")
                    ax.grid(True,color="#1f2937",linewidth=0.5,alpha=0.7)
                arm_vals = [s["arm"] for s in serie]
                def_vals = [s["def"] for s in serie]
                exc_vals = [s["exc"] for s in serie]
                ax1.fill_between(range(len(arm_vals)),arm_vals,alpha=0.3,color="#42A5F5")
                ax1.plot(range(len(arm_vals)),arm_vals,color="#42A5F5",linewidth=2,label="ARM (mm)")
                ax1.axhline(bh["cad_mm"],color="#FFB74D",linewidth=1,linestyle="--",
                            label=f"CAD={bh['cad_mm']:.0f}mm")
                ax1.axhline(bh["cad_mm"]*0.4,color="#ef4444",linewidth=0.8,linestyle=":",
                            label="Limite crítico (40% CAD)")
                ax1.set_ylabel("Armazenamento (mm)",color="#9ca3af",fontsize=9)
                ax1.set_ylim(0,bh["cad_mm"]*1.15); ax1.set_xticks([])
                ax1.legend(fontsize=8,facecolor="#111827",labelcolor="white",edgecolor="#374151")
                ax1.set_title("Balanço Hídrico Thornthwaite-Mather",color="white",fontsize=10,fontweight="bold")
                ax2.bar(range(len(def_vals)),def_vals,color="#ef4444",alpha=0.8,label="Déficit",width=0.4)
                ax2.bar([i+0.42 for i in range(len(exc_vals))],exc_vals,
                        color="#29B6F6",alpha=0.8,label="Excedente",width=0.4)
                ax2.set_ylabel("mm",color="#9ca3af",fontsize=9)
                ax2.set_xticks(range(len(dias))); ax2.set_xticklabels(dias,color="#9ca3af",fontsize=8)
                ax2.legend(fontsize=8,facecolor="#111827",labelcolor="white",edgecolor="#374151")
                plt.tight_layout()
                st.pyplot(fig_bh, use_container_width=True)
                plt.close(fig_bh)

            st.markdown(f"""<div class="alert-{bh['nivel']}">
              <b>💧 Recomendação de Irrigação:</b> {bh['recomendacao']}
            </div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 3 — SÍNTESE AGRÍCOLA
    # ─────────────────────────────────────────────────────────────────────────
    with aba3:
        st.markdown('<div class="secao-titulo">🌾 Síntese Agrícola — Resumo Executivo para o Produtor</div>',
                    unsafe_allow_html=True)
        st.caption(f"Análise consolidada para **{nome_local}** · Gerada em {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        # Resumo em cards visuais
        col_s1, col_s2, col_s3 = st.columns(3)

        # Card 1: Condição geral
        with col_s1:
            n_alertas_crit = sum(1 for a in alertas if a["nivel"] == "vermelho")
            n_alertas_amar = sum(1 for a in alertas if a["nivel"] == "amarelo")
            if n_alertas_crit > 0:
                cond_geral = "🔴 Crítica"
                bg_cond = "#ffebee"
            elif n_alertas_amar > 0:
                cond_geral = "🟡 Atenção"
                bg_cond = "#fff8e1"
            else:
                cond_geral = "🟢 Favorável"
                bg_cond = "#e8f5e9"
            st.markdown(f"""<div class="info-card" style="background:{bg_cond};">
              <h4>Condição Geral</h4>
              <p style="font-size:1.2rem;font-weight:700;">{cond_geral}</p>
              <p>{n_alertas_crit} alerta(s) crítico(s) · {n_alertas_amar} atenção(ões)</p>
            </div>""", unsafe_allow_html=True)

        # Card 2: Janela de defensivos
        with col_s2:
            if not janelas_df.empty:
                n_ab  = int((janelas_df["status"]=="aberta").sum())
                n_tot = len(janelas_df)
                # Melhor bloco
                max_b = cur_b = max_s = 0
                for v in (janelas_df["status"]=="aberta").values:
                    if v: cur_b+=1; max_b=max(max_b,cur_b)
                    else: cur_b=0
                cor_jan = "#e8f5e9" if n_ab >= 8 else ("#fff8e1" if n_ab >= 4 else "#ffebee")
                st.markdown(f"""<div class="info-card" style="background:{cor_jan};">
                  <h4>🧪 Janela de Defensivos (24h)</h4>
                  <p style="font-size:1.1rem;font-weight:700;">{n_ab}/{n_tot}h disponíveis</p>
                  <p>Bloco contínuo máximo: {max_b}h</p>
                </div>""", unsafe_allow_html=True)

        # Card 3: Risco fitossanitário
        with col_s3:
            nivel_max_fito = "Baixo"
            for r in riscos.values():
                if r["nivel"] == "Crítico": nivel_max_fito = "Crítico"; break
                if r["nivel"] == "Alto":    nivel_max_fito = "Alto"
                elif r["nivel"] == "Médio" and nivel_max_fito == "Baixo":
                    nivel_max_fito = "Médio"
            bg_fito = {"Crítico":"#ffebee","Alto":"#ffebee",
                       "Médio":"#fff8e1","Baixo":"#e8f5e9"}.get(nivel_max_fito,"#e8f5e9")
            st.markdown(f"""<div class="info-card" style="background:{bg_fito};">
              <h4>🍂 Risco Fitossanitário</h4>
              <p style="font-size:1.1rem;font-weight:700;">Nível {nivel_max_fito}</p>
              <p>Ferrugem: {riscos['ferrugem']['nivel']} · Brusone: {riscos['brusone']['nivel']}</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # Síntese textual completa
        st.markdown("### 📋 Relatório Narrativo")

        # Temperatura
        if not df_main.empty and "temperature_2m" in df_main.columns:
            tmax7 = df_main["temperature_2m"].resample("D").max()
            tmin7 = df_main["temperature_2m"].resample("D").min()
            tmax_v = tmax7.max()
            tmin_v = tmin7.min()
            tmed   = df_main["temperature_2m"].mean()
            st.markdown(f"""<div class="info-card">
              <h4>🌡️ Temperatura</h4>
              <p>Média do período: <b>{tmed:.1f}°C</b> · Máxima esperada: <b>{tmax_v:.1f}°C</b> · Mínima esperada: <b>{tmin_v:.1f}°C</b><br>
              {"⚠️ Risco de geada detectado (Tmin < 5°C). Proteja culturas." if tmin_v < 5 else "Sem risco de geada no período."} · 
              {"⚠️ Calor extremo previsto (>38°C). Estresse hídrico elevado." if tmax_v > 38 else "Sem ocorrência de calor extremo."}</p>
            </div>""", unsafe_allow_html=True)

        # Precipitação
        if "precipitation" in df_main.columns:
            pp_total = df_main["precipitation"].sum()
            pp_max   = df_main["precipitation"].resample("D").sum().max()
            dias_ch  = int((df_main["precipitation"].resample("D").sum() > 1).sum())
            st.markdown(f"""<div class="info-card">
              <h4>🌧️ Precipitação</h4>
              <p>Total do período: <b>{pp_total:.1f} mm</b> · Máximo diário: <b>{pp_max:.1f} mm</b> · Dias com chuva: <b>{dias_ch}/{dias_prev}</b><br>
              {"⚠️ Chuva intensa prevista (>50mm/dia). Evite operações de campo." if pp_max > 50 else
               ("⚠️ Volumes moderados previstos. Monitore encharcamento." if pp_max > 20 else
                "Precipitação dentro dos limites normais para as operações agrícolas.")}
              {"<br>🌵 Possível veranico: poucos dias com chuva." if dias_ch < 2 and dias_prev >= 5 else ""}
              </p>
            </div>""", unsafe_allow_html=True)

        # Vento
        if "windspeed_10m" in df_main.columns:
            vt_med = df_main["windspeed_10m"].mean()
            vt_max = df_main.get("windgusts_10m", df_main["windspeed_10m"]).max()
            horas_vt_ok = int((df_main["windspeed_10m"].iloc[:24] < 10).sum())
            st.markdown(f"""<div class="info-card">
              <h4>💨 Vento</h4>
              <p>Velocidade média: <b>{vt_med:.1f} km/h</b> · Rajada máxima: <b>{vt_max:.1f} km/h</b><br>
              Horas com vento adequado para defensivos (24h): <b>{horas_vt_ok}h</b><br>
              {"⚠️ Rajadas fortes previstas. Risco de danos a estruturas e culturas." if vt_max > 60 else "Condições de vento sem risco estrutural."}</p>
            </div>""", unsafe_allow_html=True)

        # Irrigação
        if bh:
            st.markdown(f"""<div class="info-card">
              <h4>💧 Manejo de Irrigação</h4>
              <p>Armazenamento atual: <b>{bh['arm_mm']:.1f} mm ({bh['arm_pct']:.0f}% da CAD)</b><br>
              Déficit hoje: <b>{bh['def_mm']:.1f} mm</b> · ETo estimada: <b>{bh['eto_mm']:.2f} mm/dia</b><br>
              <b>Recomendação:</b> {bh['recomendacao']}</p>
            </div>""", unsafe_allow_html=True)

        # Defensivos — melhor janela
        if not janelas_df.empty:
            abertas = janelas_df[janelas_df["status"] == "aberta"]
            if not abertas.empty:
                h_ini = abertas.index[0].strftime("%Hh")
                h_fim = abertas.index[-1].strftime("%Hh")
                st.markdown(f"""<div class="info-card" style="background:#e8f5e9;">
                  <h4>🧪 Recomendação — Aplicação de Defensivos</h4>
                  <p>Janelas favoráveis identificadas entre <b>{h_ini}</b> e <b>{h_fim}</b> (com possíveis intervalos).<br>
                  Critérios atendidos: vento &lt;10km/h, temperatura &lt;30°C, UR &gt;55%, sem chuva.<br>
                  <i>Verifique sempre a bula do produto e condições locais antes da aplicação.</i></p>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""<div class="info-card" style="background:#ffebee;">
                  <h4>🧪 Aplicação de Defensivos</h4>
                  <p><b>Nenhuma janela ideal disponível nas próximas 24h.</b> Adie as aplicações.</p>
                </div>""", unsafe_allow_html=True)

        # Risco fitossanitário resumido
        for r in riscos.values():
            if r["nivel"] != "Baixo":
                st.markdown(f"""<div class="alert-{r['cor']}">
                  <b>{r['emoji']} {r['doenca']} — Risco {r['nivel']}</b><br>
                  {r['horas_consecutivas']}h consecutivas com condições favoráveis (limiar: {r['limiar']}h).
                  Referência: {r['referencia']}.
                </div>""", unsafe_allow_html=True)

        # Tabela resumo 7 dias
        st.markdown('<div class="secao-titulo">📅 Resumo Diário — 7 Dias</div>', unsafe_allow_html=True)
        if not df_main.empty:
            try:
                df_res = df_main.resample("D").agg({
                    "temperature_2m":      ["max","min","mean"],
                    "precipitation":       "sum",
                    "relativehumidity_2m": "mean",
                    "windspeed_10m":       "max",
                    "shortwave_radiation": "mean",
                }).head(7)
                df_res.columns = ["T.Máx (°C)","T.Mín (°C)","T.Méd (°C)",
                                   "Precip (mm)","UR méd (%)","Vento máx (km/h)",
                                   "Rad.méd (W/m²)"]
                df_res.index = [d.strftime("%a %d/%m") for d in df_res.index]
                df_res = df_res.round(1)
                # Adiciona condição de tempo
                if "weathercode" in df_main.columns:
                    wc_d = df_main["weathercode"].resample("D").max()
                    df_res["Condição"] = [WCODE_MAP.get(int(v), "—")
                                          if pd.notna(v) else "—" for v in wc_d.values[:7]]
                st.dataframe(df_res, use_container_width=True)
            except Exception as e:
                st.warning(f"Erro ao gerar resumo: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 4 — ALERTAS & RISCO
    # ─────────────────────────────────────────────────────────────────────────
    with aba4:
        st.markdown('<div class="secao-titulo">⚠️ Alertas Meteorológicos</div>',
                    unsafe_allow_html=True)
        for al in alertas:
            st.markdown(f"""<div class="alert-{al['nivel']}">
              <b>{al['icone']} {al['titulo']}</b><br>
              <span style="font-size:0.9rem;">{al['msg']}</span>
            </div>""", unsafe_allow_html=True)

        # Matriz de risco
        st.markdown('<div class="secao-titulo">🔲 Matriz de Risco — Hora × Variável (24h)</div>',
                    unsafe_allow_html=True)
        st.caption("Cada célula indica se a condição está favorável (✓ verde), em atenção (! amarelo) "
                   "ou em risco/bloqueada (✗ vermelho) para cada hora.")
        fig_mat = fig_matriz_alertas(df_main, janelas_df, riscos)
        st.pyplot(fig_mat, use_container_width=True)
        plt.close(fig_mat)

        # Risco fitossanitário detalhado
        st.markdown('<div class="secao-titulo">🍂 Risco Fitossanitário Detalhado (48h)</div>',
                    unsafe_allow_html=True)
        for nome_r, r in riscos.items():
            st.markdown(f"""<div class="alert-{r['cor']}">
              <b>{r['emoji']} {r['doenca']} — Risco: {r['nivel']}</b><br>
              <span style="font-size:0.88rem;">
                Horas consecutivas favoráveis: <b>{r['horas_consecutivas']}h</b>
                (limiar de risco: {r['limiar']}h) · Total de horas favoráveis: {r['horas_total']}h<br>
                Referência bibliográfica: <i>{r['referencia']}</i>
              </span>
            </div>""", unsafe_allow_html=True)

        # Gráfico de condições favoráveis ao longo do tempo
        st.markdown('<div class="secao-titulo">📊 Evolução Temporal das Condições de Risco</div>',
                    unsafe_allow_html=True)

        fig_r, (ax_f, ax_b) = plt.subplots(2, 1, figsize=(12, 5), facecolor="#0d1117",
                                             sharex=True)
        for ax in [ax_f, ax_b]:
            ax.set_facecolor("#111827")
            ax.tick_params(colors="#9ca3af", labelsize=8)
            for sp in ax.spines.values(): sp.set_edgecolor("#374151")
            ax.grid(True, color="#1f2937", linewidth=0.5, alpha=0.6)

        idx48 = df_main.index[:48]
        fer_cond = riscos["ferrugem"]["condicao"].reindex(idx48, fill_value=False)
        bru_cond = riscos["brusone"]["condicao"].reindex(idx48, fill_value=False)

        ax_f.fill_between(idx48, fer_cond.values.astype(float),
                          color="#f97316", alpha=0.7, step="mid",
                          label="Condição favorável Ferrugem")
        ax_f.set_ylabel("Ferrugem (0/1)", color="#9ca3af", fontsize=8)
        ax_f.set_ylim(-0.05, 1.5)
        ax_f.legend(fontsize=7, facecolor="#111827", labelcolor="white", edgecolor="#374151")
        ax_f.set_title("Janelas de Risco Fitossanitário — 48h",
                       color="white", fontsize=10, fontweight="bold")

        ax_b.fill_between(idx48, bru_cond.values.astype(float),
                          color="#a78bfa", alpha=0.7, step="mid",
                          label="Condição favorável Brusone")
        ax_b.set_ylabel("Brusone (0/1)", color="#9ca3af", fontsize=8)
        ax_b.set_ylim(-0.05, 1.5)
        ax_b.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%Hh"))
        ax_b.xaxis.set_major_locator(mdates.HourLocator(interval=6))
        ax_b.legend(fontsize=7, facecolor="#111827", labelcolor="white", edgecolor="#374151")

        plt.tight_layout()
        st.pyplot(fig_r, use_container_width=True)
        plt.close(fig_r)

        # Janela de defensivos — tabela detalhada
        st.markdown('<div class="secao-titulo">🧪 Janela de Aplicação de Defensivos — 24h</div>',
                    unsafe_allow_html=True)
        st.caption("Critérios MAPA/Embrapa (Portaria 371/2020): Vento <10km/h | Temp <30°C | UR >55% | Sem chuva")

        if not janelas_df.empty:
            # Timeline colorida
            n_cols_jan = min(24, len(janelas_df))
            cols_jan   = st.columns(n_cols_jan)
            for i, (idx_j, row_j) in enumerate(janelas_df.head(n_cols_jan).iterrows()):
                with cols_jan[i]:
                    cor_e = {"aberta":"🟢","parcial":"🟡","bloqueada":"🔴"}[row_j["status"]]
                    st.markdown(
                        f"<div style='text-align:center;font-size:0.65rem;color:#555;'>"
                        f"<b>{idx_j.strftime('%Hh')}</b><br>{cor_e}</div>",
                        unsafe_allow_html=True)

            n_ab = int((janelas_df["status"]=="aberta").sum())
            n_pa = int((janelas_df["status"]=="parcial").sum())
            n_bl = int((janelas_df["status"]=="bloqueada").sum())
            c1,c2,c3 = st.columns(3)
            with c1: st.metric("✅ Horas ideais", n_ab)
            with c2: st.metric("⚠️ Horas parciais", n_pa)
            with c3: st.metric("❌ Horas bloqueadas", n_bl)

            # Tabela detalhada com motivos
            df_jan_disp = janelas_df[["status","motivo","n_restricoes"]].copy()
            df_jan_disp.index = [t.strftime("%Hh") for t in df_jan_disp.index]
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
            st.markdown(f"""<div class="alert-verde">
              <b>✅ E-mail configurado</b><br>
              Remetente: {EMAIL_REMETENTE}<br>
              Destinatários: {', '.join(EMAIL_DESTINATARIOS)}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="alert-amarelo">
              <b>⚠️ E-mail não configurado</b><br>
              Adicione ao <code>.streamlit/secrets.toml</code>:<br>
              <code>[email]<br>remetente = "seu@gmail.com"<br>senha_app = "senha_app_gmail"<br>destinatario = "destino@email.com"</code><br>
              Senha de app: Conta Google → Segurança → Verificação 2 etapas → Senhas de app.
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        dest_extra = st.text_input("Destinatários adicionais (separar por vírgula):",
                                    placeholder="eng@fazenda.com, gestor@empresa.com")
        extras = [e.strip() for e in dest_extra.split(",") if "@" in e] if dest_extra else []

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if st.button("📤 Enviar Relatório", use_container_width=True):
                with st.spinner("Gerando e enviando..."):
                    html_rel = gerar_html_relatorio(
                        lat, lon, df_main, alertas, riscos, bh,
                        janelas_df.to_dict("records") if not janelas_df.empty else [],
                        nome_local
                    )
                    tem_crit = any(a["nivel"]=="vermelho" for a in alertas)
                    assunto  = (f"{'🚨 ALERTA — ' if tem_crit else '📋 '}Relatório Agroclimático — "
                                f"{nome_local} | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
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
                    nome_local
                )
                components.html(html_prev, height=650, scrolling=True)

        st.markdown("---")
        st.markdown("**📋 Conteúdo do relatório:**")
        st.markdown("""
- 📊 Condições atuais (temperatura, chuva, umidade, vento)
- ⚠️ Alertas meteorológicos com severidade
- 🍂 Risco fitossanitário (Ferrugem Asiática, Brusone)
- 🧪 Janela de aplicação de defensivos (horas disponíveis)
- 💧 Balanço hídrico e recomendação de irrigação
- 📅 Tabela de previsão para 7 dias
""")

    # ─────────────────────────────────────────────────────────────────────────
    # RODAPÉ
    # ─────────────────────────────────────────────────────────────────────────
    progress.progress(100, text="✅ Análise concluída!")
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align:center;padding:14px;color:#888;font-size:0.78rem;">
      <b style="color:{VERDE_ESCURO};">Yamada Engenharia</b> — Meteorologia Aplicada ao Agronegócio<br>
      Open-Meteo (GFS · ICON · ERA5) · NASA POWER · INPE BDQueimadas · MVP v4.0<br>
      <i>Souza et al. (2021) · Zängl et al. (2015) · Hersbach et al. (2020) · Buizza et al. (2005)</i><br>
      {datetime.now().strftime('%d/%m/%Y %H:%M')}
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
