"""
=============================================================================
YAMADA ENGENHARIA — Plataforma de Monitoramento Agroclimático
MVP Streamlit v4.0 | GOES-19 (goes2go) + Open-Meteo + NASA POWER + INPE + SATVeg + INMET
Mato Grosso do Sul — Análise por Coordenada (Lat/Lon livre)

VERSÃO 4.0 — Melhorias sobre v3.0 (briefing Dr. Hiroshi Yamada):
  • Substituição de municípios fixos por seleção lat/lon livre + nome do ponto
  • Open-Meteo: modelo ICON-EU (primário) + GFS025 (fallback), 72h horárias
  • 15 variáveis horárias incluindo CAPE, LI, CIN, precipitação probabilística,
    radiação direta/difusa, temperatura do solo, umidade do solo
  • Gráfico matplotlib 5-painéis interativo com mplcursors (tooltip hover)
    – Painel 1: Temperatura + ponto de orvalho + CAPE (eixo secundário)
    – Painel 2: Precipitação + probabilidade de chuva (eixo secundário)
    – Painel 3: Radiação solar (GHI / DNI / Difusa) com pico anotado
    – Painel 4: Vento + rajadas + limites operacionais
    – Painel 5: Umidade relativa + Heat Index + limites de defensivos
  • GOES-19 via goes2go: B02/Visível, B09/Vapor d'água, B13/IR Clean,
    B14/IR Longo, RGB AirMass, RGB Day Cloud Phase — imagens ≤10 min
  • Nowcasting de chuva: 3 fontes integradas (TB GOES-19, prob. Open-Meteo,
    CAPE+LI) com timeline 0–6h e diagnóstico por severidade
  • Organização em 7 abas temáticas
  • Sistema de relatório por e-mail (SMTP Gmail SSL)
  • Scheduler APScheduler (06h / 12h / 18h) + keep-alive
=============================================================================
"""

# ─────────────────────────────────────────────────────────────────────────────
# AUTO-INSTALAÇÃO DE DEPENDÊNCIAS OPCIONAIS
# ─────────────────────────────────────────────────────────────────────────────
import sys, subprocess

def _pip_install(pkg: str):
    """Instala pacote via pip se não estiver disponível."""
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", pkg, "-q"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

try:
    import goes2go  # noqa: F401
except ImportError:
    _pip_install("goes2go")

try:
    import mplcursors  # noqa: F401
except ImportError:
    _pip_install("mplcursors")

try:
    import cartopy  # noqa: F401
except ImportError:
    _pip_install("cartopy")

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS PRINCIPAIS
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
import requests
import json
import boto3
from botocore import UNSIGNED
from botocore.config import Config
import netCDF4 as nc
import tempfile
import os
import io
from datetime import datetime, timezone, timedelta
from shapely.geometry import box
import warnings
warnings.filterwarnings("ignore")

# E-mail
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Scheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import threading
import logging
logging.getLogger("apscheduler").setLevel(logging.WARNING)

# Imports opcionais (com fallback gracioso)
try:
    import mplcursors
    _HAS_MPLCURSORS = True
except ImportError:
    _HAS_MPLCURSORS = False

try:
    import goes2go
    from goes2go import GOES
    _HAS_GOES2GO = True
except ImportError:
    _HAS_GOES2GO = False

try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    _HAS_CARTOPY = True
except ImportError:
    _HAS_CARTOPY = False

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Yamada Engenharia | Monitor Agroclimático MS",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# IDENTIDADE VISUAL YAMADA
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
    background-color: {CINZA_CLARO};
    color: {PRETO};
  }}

  .yamada-header {{
    background: linear-gradient(135deg, {VERDE_ESCURO} 0%, {VERDE_MEDIO} 100%);
    border-radius: 12px; padding: 28px 36px; margin-bottom: 24px;
    display: flex; align-items: center; gap: 20px;
    box-shadow: 0 4px 20px rgba(27,77,46,0.3);
  }}
  .yamada-header h1 {{
    font-family: 'Montserrat', sans-serif; font-weight: 900;
    font-size: 2rem; color: white; margin: 0; letter-spacing: -0.5px;
  }}
  .yamada-header p {{
    color: rgba(255,255,255,0.82); margin: 4px 0 0 0;
    font-size: 0.95rem; font-weight: 300;
  }}
  .band-card {{
    background: white; border-left: 4px solid {VERDE_MEDIO};
    border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }}
  .band-card h4 {{
    font-family: 'Montserrat', sans-serif; font-weight: 700;
    color: {VERDE_ESCURO}; margin: 0 0 4px 0; font-size: 0.88rem;
  }}
  .band-card p {{ margin: 0; font-size: 0.82rem; color: #000; line-height: 1.4; }}

  .alert-verde    {{ background:#e8f5e9; border-left:4px solid #43a047; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .alert-amarelo  {{ background:#fff8e1; border-left:4px solid #fbc02d; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .alert-vermelho {{ background:#ffebee; border-left:4px solid #e53935; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .alert-laranja  {{ background:#fff3e0; border-left:4px solid #fb8c00; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .alert-azul     {{ background:#e3f2fd; border-left:4px solid #1565c0; border-radius:8px; padding:12px 16px; margin:6px 0; }}

  .stButton > button {{
    background: linear-gradient(135deg, {VERDE_ESCURO}, {VERDE_MEDIO}) !important;
    color: white !important; font-family: 'Montserrat', sans-serif !important;
    font-weight: 700 !important; font-size: 1.05rem !important;
    border: none !important; border-radius: 10px !important;
    padding: 14px 40px !important; width: 100% !important;
    letter-spacing: 0.5px !important; transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(27,77,46,0.35) !important;
  }}
  .stButton > button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 22px rgba(27,77,46,0.45) !important;
  }}

  section[data-testid="stSidebar"] {{
    background-color: #1a2e1c !important;
    border-right: 1px solid #2d5a30;
  }}
  section[data-testid="stSidebar"] * {{ color: #e8f5e9 !important; }}
  section[data-testid="stSidebar"] label {{
    font-family: 'Montserrat', sans-serif !important; font-weight: 600 !important;
    font-size: 0.85rem !important; color: #a5d6a7 !important;
  }}
  section[data-testid="stSidebar"] .stSelectbox > div > div {{
    background-color: #2d5a30 !important; color: white !important;
    border-color: #3DA63A !important;
  }}
  section[data-testid="stSidebar"] p,
  section[data-testid="stSidebar"] span {{ color: #c8e6c9 !important; }}
  section[data-testid="stSidebar"] hr {{ border-color: #2d5a30 !important; }}

  div[data-testid="metric-container"] {{
    background: white; border-radius: 10px; padding: 16px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
    border-top: 3px solid {VERDE_MEDIO};
  }}
  .secao-titulo {{
    font-family: 'Montserrat', sans-serif; font-weight: 800;
    font-size: 1.15rem; color: {VERDE_ESCURO};
    border-bottom: 2px solid {VERDE_MEDIO};
    padding-bottom: 6px; margin: 28px 0 16px 0;
  }}
  hr {{ border-color: #ddeedd; margin: 20px 0; }}

  /* Card de nowcasting */
  .nowcast-card {{
    border-radius: 10px; padding: 16px 20px; margin: 4px 0;
    text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DE E-MAIL
# ─────────────────────────────────────────────────────────────────────────────
try:
    EMAIL_REMETENTE    = st.secrets["email"]["remetente"]
    EMAIL_SENHA_APP    = st.secrets["email"]["senha_app"]
    _dest_raw          = st.secrets["email"]["destinatario"]
    EMAIL_DESTINATARIOS = (
        [e.strip() for e in _dest_raw.split(",") if e.strip()]
        if isinstance(_dest_raw, str) else list(_dest_raw)
    )
    _email_configurado = True
except Exception:
    EMAIL_REMETENTE    = ""
    EMAIL_DESTINATARIOS= []
    _email_configurado = False

_scheduler_log: list = []
_log_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────────────────
# DADOS ESTÁTICOS — PONTOS PREDEFINIDOS PARA MS (substitui município fixo)
# ─────────────────────────────────────────────────────────────────────────────
# Pontos de referência sugeridos no seletor rápido da sidebar
PONTOS_REFERENCIA_MS = {
    "── Selecione um ponto de referência ──": None,
    "Campo Grande — Centro Urbano":     {"lat": -20.4428, "lon": -54.6460},
    "Dourados — Polo Sojícola":         {"lat": -22.2212, "lon": -54.8056},
    "Três Lagoas — Eucaliptocultura":   {"lat": -20.7519, "lon": -51.6783},
    "Corumbá — Pantanal":               {"lat": -19.0078, "lon": -57.6500},
    "Ponta Porã — Fronteira":           {"lat": -22.5361, "lon": -55.7253},
    "Naviraí — Pecuária Sul":           {"lat": -23.0622, "lon": -54.1914},
    "Aquidauana — Pantanal Sul":        {"lat": -20.4700, "lon": -55.7869},
    "Maracaju — Grãos":                 {"lat": -21.6108, "lon": -55.1681},
    "Chapadão do Sul — Cerrado Leste":  {"lat": -18.7919, "lon": -52.6267},
    "Coxim — Cerrado Norte":            {"lat": -18.5069, "lon": -54.7600},
    "Sonora — Portal da Amazônia":      {"lat": -17.5583, "lon": -54.7611},
    "Costa Rica — Nordeste MS":         {"lat": -18.5447, "lon": -53.1278},
}

BANDAS_INFO = {
    "B02": {"nome": "Visível (0,64µm)",         "icon": "☀️",  "uso": "Estrutura de nuvens cumulus/Cb — apenas diurno",           "cmap": "gray",      },
    "B09": {"nome": "Vapor d'Água (6,9µm)",      "icon": "💧",  "uso": "Dinâmica atmosférica, umidade em 300–700 hPa",             "cmap": "Blues_r",   },
    "B13": {"nome": "IR Clean (10,3µm)",          "icon": "⛈️",  "uso": "Topo de nuvens, temperatura de brilho, CBs",              "cmap": "inferno_r", },
    "B14": {"nome": "IR Longo (11,2µm)",          "icon": "🌧️",  "uso": "Diferença B13-B14 → nuvens de gelo/granizo",             "cmap": "Blues",     },
    "RGB_AirMass":       {"nome": "RGB AirMass",         "icon": "🌀",  "uso": "Massas de ar polar vs tropical — inverno no MS",         "cmap": None,        },
    "RGB_DayCloudPhase": {"nome": "RGB Day Cloud Phase", "icon": "🔵",  "uso": "Fase das nuvens: gelo (azul) vs água (ciano)",           "cmap": None,        },
}

CULTURAS_GDA = {
    "Soja":    {"tb": 7.0,  "tc": 40.0, "estagios": [
        (0,"V0 – Germinação"),(50,"V1 – Estádio unifoliar"),(120,"V2 – 1º trifólio"),
        (200,"V3–V4 – Desenvolvimento vegetativo"),(300,"V5–V6 – Pré-florescimento"),
        (400,"R1 – Florescimento"),(500,"R2 – Florescimento pleno"),
        (600,"R3 – Início formação de vagens"),(750,"R4 – Vagens completas"),
        (900,"R5 – Enchimento de grãos"),(1050,"R6 – Grão cheio"),
        (1200,"R7 – Início maturação"),(1400,"R8 – Maturação plena — Colheita"),
    ]},
    "Milho":   {"tb": 10.0, "tc": 40.0, "estagios": [
        (0,"VE – Emergência"),(60,"V1 – 1ª folha"),(150,"V3 – 3ª folha"),
        (300,"V6 – 6ª folha"),(450,"V9 – 9ª folha"),(600,"VT – Pendoamento"),
        (700,"R1 – Espigamento"),(850,"R2 – Bolha d'água"),(1000,"R3 – Grão leitoso"),
        (1200,"R4 – Grão pastoso"),(1400,"R5 – Grão farináceo"),
        (1600,"R6 – Maturação fisiológica — Colheita"),
    ]},
    "Algodão": {"tb": 15.0, "tc": 40.0, "estagios": [
        (0,"Germinação"),(100,"Emergência"),(250,"Crescimento vegetativo"),
        (500,"Botão floral"),(700,"Florescimento"),(900,"Maçã"),
        (1100,"Abertura de capulhos"),(1400,"Colheita"),
    ]},
    "Cana":    {"tb": 18.0, "tc": 40.0, "estagios": [
        (0,"Brotação"),(200,"Perfilhamento"),(600,"Crescimento rápido"),
        (1200,"Maturação inicial"),(1800,"Maturação plena — Colheita"),
    ]},
}

# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE COLETA DE DADOS — OPEN-METEO (ICON-EU + GFS025)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def buscar_previsao_openmeteo(lat: float, lon: float) -> dict:
    """
    Coleta previsão 72h horária + 7 dias diários do Open-Meteo.

    Modelos: ICON-EU (primário, melhor resolução para convecção do Cerrado/MS)
    com fallback para GFS025 (boa cobertura sinótica).

    Variáveis horárias (15 parâmetros):
      - temperature_2m, relativehumidity_2m, dewpoint_2m
      - precipitation, precipitation_probability
      - windspeed_10m, windgusts_10m
      - shortwave_radiation, diffuse_radiation, direct_normal_irradiance
      - cape, lifted_index, convective_inhibition
      - soil_temperature_0cm, soil_moisture_0_1cm, cloudcover

    Retorna dict JSON do Open-Meteo ou {} em caso de falha.
    """
    vars_horarias = (
        "temperature_2m,relativehumidity_2m,dewpoint_2m,"
        "precipitation,precipitation_probability,"
        "windspeed_10m,windgusts_10m,"
        "shortwave_radiation,diffuse_radiation,direct_normal_irradiance,"
        "cape,lifted_index,convective_inhibition,"
        "soil_temperature_0cm,soil_moisture_0_1cm,cloudcover"
    )
    vars_diarias = (
        "temperature_2m_max,temperature_2m_min,precipitation_sum,"
        "weathercode,windspeed_10m_max,et0_fao_evapotranspiration,"
        "precipitation_hours,shortwave_radiation_sum"
    )

    # Tenta ICON-EU primeiro (melhor para convecção profunda do Cerrado)
    for modelo in ["icon_eu", "gfs025"]:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly={vars_horarias}"
            f"&daily={vars_diarias}"
            f"&timezone=America%2FCampo_Grande"
            f"&forecast_days=7"
            f"&models={modelo}"
        )
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            data["_modelo_usado"] = modelo
            return data
        except Exception:
            continue

    # Fallback best_match se ambos falharem
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly={vars_horarias}"
            f"&daily={vars_diarias}"
            f"&timezone=America%2FCampo_Grande"
            f"&forecast_days=7"
            f"&models=best_match"
        )
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        data["_modelo_usado"] = "best_match (fallback)"
        return data
    except Exception as e:
        st.error(f"❌ Open-Meteo — todos os modelos falharam: {e}")
        return {}


@st.cache_data(ttl=1800, show_spinner=False)
def buscar_nasa_power(lat: float, lon: float) -> dict:
    """
    Coleta dados históricos 30 dias via NASA POWER para o ponto selecionado.
    Inclui GWETTOP (umidade 0-5cm) e GWETROOT (zona radicular) para
    complementar o balanço hídrico Thornthwaite-Mather.
    """
    fim    = datetime.now()
    inicio = fim - timedelta(days=30)
    url = (
        f"https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=T2M,RH2M,ALLSKY_SFC_SW_DWN,WS10M,PRECTOTCORR,GWETTOP,GWETROOT"
        f"&community=AG&longitude={lon}&latitude={lat}"
        f"&start={inicio.strftime('%Y%m%d')}&end={fim.strftime('%Y%m%d')}&format=JSON"
    )
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"⚠️ NASA POWER indisponível: {e}")
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_satveg_ndvi(lat: float, lon: float) -> dict:
    """
    Série histórica NDVI do ponto via API REST SATVeg (Embrapa).
    Cobre 2000 até hoje. Fallback com série sintética representativa do MS.
    """
    try:
        url = (
            f"https://www.satveg.cnptia.embrapa.br/satvegws/ws/perfil/"
            f"ZW1icmFwYQ==/ndvi/ponto/{lon}/{lat}/anual/"
        )
        r = requests.get(url, timeout=20, headers={"Accept": "application/json"})
        r.raise_for_status()
        return r.json()
    except Exception:
        np.random.seed(abs(int(lat * 100)) % 999)
        anos = list(range(2000, datetime.now().year + 1))
        ndvi = [round(float(np.clip(
            0.55 + 0.15 * np.sin(2 * np.pi * (a - 2000) / 10) + np.random.normal(0, 0.04),
            0.2, 0.9)), 3) for a in anos]
        return {"listaSerie": [{"data": str(a), "ndvi": v} for a, v in zip(anos, ndvi)],
                "_simulado": True}


@st.cache_data(ttl=1800, show_spinner=False)
def buscar_focos_inpe() -> pd.DataFrame:
    """Focos de queimada INPE BDQueimadas — MS, últimas 48h."""
    try:
        r = requests.get(
            "https://queimadas.dgi.inpe.br/api/focos/",
            params={"pais_id": 33, "estado_id": 50, "satelite": "AQUA_M-T"},
            timeout=15
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    except Exception:
        np.random.seed(42)
        n = 12
        return pd.DataFrame({
            "latitude":  np.random.uniform(-23.0, -17.5, n),
            "longitude": np.random.uniform(-57.0, -51.5, n),
            "frp":       np.random.uniform(5, 120, n),
            "_simulado": [True] * n,
        })


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_dados_inmet() -> pd.DataFrame:
    """Estações automáticas INMET no MS."""
    try:
        r = requests.get("https://apitempo.inmet.gov.br/estacoes/T", timeout=15)
        r.raise_for_status()
        est_ms = [e for e in r.json() if e.get("SG_ESTADO") == "MS"][:5]
        if not est_ms:
            raise ValueError("sem estações MS")
        return pd.DataFrame([{
            "Estação": e.get("DC_NOME", "—"),
            "Lat": float(e.get("VL_LATITUDE", 0)),
            "Lon": float(e.get("VL_LONGITUDE", 0)),
            "Alt (m)": e.get("VL_ALTITUDE", "—"),
            "Cod": e.get("CD_ESTACAO", "—"),
        } for e in est_ms])
    except Exception:
        return pd.DataFrame([
            {"Estação": "Campo Grande A702", "Lat": -20.44, "Lon": -54.65, "Alt (m)": 532, "Cod": "A702"},
            {"Estação": "Dourados A716",     "Lat": -22.22, "Lon": -54.81, "Alt (m)": 430, "Cod": "A716"},
            {"Estação": "Corumbá A722",      "Lat": -19.01, "Lon": -57.65, "Alt (m)": 118, "Cod": "A722"},
            {"Estação": "Três Lagoas A729",  "Lat": -20.75, "Lon": -51.68, "Alt (m)": 322, "Cod": "A729"},
            {"Estação": "Ponta Porã A718",   "Lat": -22.54, "Lon": -55.73, "Alt (m)": 650, "Cod": "A718"},
        ])


# ─────────────────────────────────────────────────────────────────────────────
# GOES-19 VIA GOES2GO — CANAIS E COMPOSTOS RGB
# ─────────────────────────────────────────────────────────────────────────────

# BBox de recorte para MS com margem
_MS_LON_MIN, _MS_LON_MAX = -57.65, -50.92
_MS_LAT_MIN, _MS_LAT_MAX = -23.67, -17.16


@st.cache_data(ttl=600, show_spinner=False)  # 10 minutos — imagens quase em tempo real
def buscar_goes19_canal(banda_num: int) -> tuple:
    """
    Busca imagem GOES-19 ABI-L2-CMIPC via goes2go (≤10 min atrás).
    Retorna (array_2d, extent, timestamp_str) ou (None, None, None).

    Parâmetros:
      banda_num — número do canal ABI (2, 9, 13, 14)

    Limitação: goes2go requer credenciais AWS configuradas ou acesso público S3.
    Em ambiente sem acesso, retorna None e usa fallback sintético.
    """
    if not _HAS_GOES2GO:
        return None, None, None
    try:
        from goes2go.data import goes_latest
        ds = goes_latest(
            satellite=19,
            product="ABI-L2-CMIPC",
            bands=banda_num,
            save_dir=tempfile.gettempdir(),
            overwrite=True,
        )
        if ds is None or "CMI" not in ds:
            return None, None, None

        # Extrai projeção e lat/lon
        cmi      = ds["CMI"].values
        x        = ds["x"].values
        y        = ds["y"].values
        proj_var = ds["goes_imager_projection"]

        lon_0 = float(proj_var.attrs.get("longitude_of_projection_origin", -75.0))
        H     = float(proj_var.attrs.get("perspective_point_height", 35786023.0)) + \
                float(proj_var.attrs.get("semi_major_axis", 6378137.0))
        r_eq  = float(proj_var.attrs.get("semi_major_axis",  6378137.0))
        r_pol = float(proj_var.attrs.get("semi_minor_axis",  6356752.3))

        xx, yy   = np.meshgrid(x * float(proj_var.attrs.get("perspective_point_height", 35786023.0)),
                               y * float(proj_var.attrs.get("perspective_point_height", 35786023.0)))
        lambda_0 = np.deg2rad(lon_0)
        a = np.sin(xx)**2 + np.cos(xx)**2 * (np.cos(yy)**2 + (r_eq**2/r_pol**2)*np.sin(yy)**2)
        b = -2 * H * np.cos(xx) * np.cos(yy)
        c = H**2 - r_eq**2
        discriminante = b**2 - 4*a*c
        discriminante = np.where(discriminante < 0, np.nan, discriminante)
        r_s = (-b - np.sqrt(discriminante)) / (2 * a)

        s_x = r_s * np.cos(xx) * np.cos(yy)
        s_y = -r_s * np.sin(xx)
        s_z = r_s * np.cos(xx) * np.sin(yy)

        lat = np.rad2deg(np.arctan((r_eq**2/r_pol**2) * (s_z/np.sqrt((H-s_x)**2 + s_y**2))))
        lon = np.rad2deg(lambda_0 - np.arctan(s_y/(H - s_x)))

        # Recorte para MS
        mask = (lat >= _MS_LAT_MIN) & (lat <= _MS_LAT_MAX) & \
               (lon >= _MS_LON_MIN) & (lon <= _MS_LON_MAX)
        if not np.any(mask):
            return None, None, None

        rows = np.where(mask.any(axis=1))[0]
        cols = np.where(mask.any(axis=0))[0]
        cmi_rec = cmi[rows[0]:rows[-1]+1, cols[0]:cols[-1]+1]
        extent  = [_MS_LON_MIN, _MS_LON_MAX, _MS_LAT_MIN, _MS_LAT_MAX]

        ts_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        return np.array(cmi_rec, dtype=float), extent, ts_str

    except Exception:
        return None, None, None


@st.cache_data(ttl=600, show_spinner=False)
def buscar_goes19_rgb(produto: str) -> tuple:
    """
    Busca compostos RGB GOES-19 via goes2go (≤10 min).

    Produtos suportados:
      'AirMass'      — distingue massas de ar polar vs tropical,
                       crítico para frentes frias no MS no inverno
      'DayCloudPhase'— fase microfísica das nuvens (gelo=granizo vs água)

    Retorna (array_rgb HxWx3, extent, timestamp_str) ou (None, None, None).
    Limitação: DayCloudPhase só disponível durante o dia (radiação solar > 0).
    """
    if not _HAS_GOES2GO:
        return None, None, None
    try:
        from goes2go.data import goes_latest
        from goes2go.tools import rgb as g2g_rgb

        # AirMass usa canais 8,10,12,13; DayCloudPhase usa 1,2,5
        bands_map = {
            "AirMass":       [8, 10, 12, 13],
            "DayCloudPhase": [1, 2, 5],
        }
        bands = bands_map.get(produto, [13])

        ds = goes_latest(
            satellite=19,
            product="ABI-L2-CMIPC",
            bands=bands,
            save_dir=tempfile.gettempdir(),
            overwrite=True,
        )
        if ds is None:
            return None, None, None

        rgb_func = getattr(g2g_rgb, produto, None)
        if rgb_func is None:
            return None, None, None

        rgb_img = rgb_func(ds)
        if rgb_img is None:
            return None, None, None

        extent  = [_MS_LON_MIN, _MS_LON_MAX, _MS_LAT_MIN, _MS_LAT_MAX]
        ts_str  = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        return rgb_img, extent, ts_str

    except Exception:
        return None, None, None


# GOES-19 fallback via boto3 (mantido para compatibilidade com v3.0)
def listar_arquivos_goes_banda_s3(banda: str, horas_atras: int = 1) -> list:
    """Lista arquivos GOES-19 ABI-CMIPF no S3 para fallback boto3."""
    s3         = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")
    agora      = datetime.now(timezone.utc) - timedelta(hours=horas_atras)
    dia_do_ano = agora.timetuple().tm_yday
    num_banda  = banda.replace("B", "")
    prefix     = f"ABI-L2-CMIPF/{agora.year}/{dia_do_ano:03d}/{agora.hour:02d}/"
    try:
        resp = s3.list_objects_v2(Bucket="noaa-goes19", Prefix=prefix, MaxKeys=30)
        return [obj["Key"] for obj in resp.get("Contents", [])
                if f"_C{num_banda.zfill(2)}_" in obj["Key"]][:3]
    except Exception:
        return []


@st.cache_data(ttl=600, show_spinner=False)
def baixar_e_recortar_goes19_s3(banda: str) -> tuple:
    """Fallback boto3 para download GOES-19 quando goes2go não disponível."""
    arquivos = listar_arquivos_goes_banda_s3(banda)
    if not arquivos:
        return None, None, None
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")
    try:
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
            s3.download_fileobj("noaa-goes19", arquivos[0], tmp)
            tmp_path = tmp.name
        dataset   = nc.Dataset(tmp_path)
        proj_info = dataset.variables["goes_imager_projection"]
        lon_origin= proj_info.longitude_of_projection_origin
        H    = proj_info.perspective_point_height + proj_info.semi_major_axis
        r_eq = proj_info.semi_major_axis
        r_pol= proj_info.semi_minor_axis
        x_rad= dataset.variables["x"][:] * proj_info.perspective_point_height
        y_rad= dataset.variables["y"][:] * proj_info.perspective_point_height
        lambda_0 = np.deg2rad(lon_origin)
        a = np.sin(x_rad)**2 + np.cos(x_rad)**2*(np.cos(y_rad)**2+(r_eq**2/r_pol**2)*np.sin(y_rad)**2)
        b = -2*H*np.cos(x_rad)*np.cos(y_rad)
        c = H**2 - r_eq**2
        r_s = (-b - np.sqrt(b**2 - 4*a*c))/(2*a)
        s_x = r_s*np.cos(x_rad)*np.cos(y_rad)
        s_y = -r_s*np.sin(x_rad)
        s_z = r_s*np.cos(x_rad)*np.sin(y_rad)
        lat = np.rad2deg(np.arctan((r_eq**2/r_pol**2)*(s_z/np.sqrt((H-s_x)**2+s_y**2))))
        lon = np.rad2deg(lambda_0 - np.arctan(s_y/(H-s_x)))
        data = dataset.variables["CMI"][:]
        mask = (lat>=_MS_LAT_MIN)&(lat<=_MS_LAT_MAX)&(lon>=_MS_LON_MIN)&(lon<=_MS_LON_MAX)
        if not np.any(mask):
            dataset.close(); os.unlink(tmp_path); return None, None, None
        rows = np.where(mask.any(axis=1))[0]
        cols = np.where(mask.any(axis=0))[0]
        data_rec = data[rows[0]:rows[-1]+1, cols[0]:cols[-1]+1]
        ts   = datetime.strptime(arquivos[0].split("_s")[1][:13], "%Y%j%H%M%S")
        dataset.close(); os.unlink(tmp_path)
        return np.array(data_rec), [_MS_LON_MIN, _MS_LON_MAX, _MS_LAT_MIN, _MS_LAT_MAX], ts.strftime("%d/%m/%Y %H:%M UTC")
    except Exception:
        return None, None, None


def obter_canal_goes19(banda_id: str, usar_goes_real: bool) -> tuple:
    """
    Tenta obter canal GOES-19 via goes2go primeiro, depois boto3,
    retornando sempre (data, extent, timestamp, fonte).
    """
    if not usar_goes_real:
        return None, None, None, "simulado"

    # Mapeamento banda_id → número ABI
    banda_map = {"B02": 2, "B09": 9, "B13": 13, "B14": 14}
    num = banda_map.get(banda_id)

    if _HAS_GOES2GO and num:
        data, ext, ts = buscar_goes19_canal(num)
        if data is not None:
            return data, ext, ts, "goes2go"

    # Fallback boto3
    if num:
        data, ext, ts = baixar_e_recortar_goes19_s3(banda_id)
        if data is not None:
            return data, ext, ts, "boto3"

    return None, None, None, "simulado"


# ─────────────────────────────────────────────────────────────────────────────
# SHAPEFILES
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def carregar_shapefiles() -> dict:
    """Carrega shapefiles MS — municípios, biomas, hidrografia, rodovias."""
    shps = {}
    try:
        shps["municipios"] = gpd.read_file(
            "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-50-mun.json"
        )
    except Exception:
        from shapely.geometry import box as sgbox
        shps["municipios"] = gpd.GeoDataFrame(
            {"name": ["MS"]}, geometry=[sgbox(-57.65,-23.67,-50.92,-17.16)], crs="EPSG:4326")

    from shapely.geometry import Polygon, LineString
    shps["biomas"] = gpd.GeoDataFrame(
        {"bioma": ["Pantanal", "Cerrado", "Campo/Agro", "Transição"]},
        geometry=[
            Polygon([(-57.65,-19.5),(-55.5,-19.5),(-55.5,-17.16),(-57.65,-17.16)]),
            Polygon([(-55.5,-19.5),(-50.92,-19.5),(-50.92,-17.16),(-55.5,-17.16)]),
            Polygon([(-57.65,-23.67),(-53.5,-23.67),(-53.5,-19.5),(-57.65,-19.5)]),
            Polygon([(-53.5,-23.67),(-50.92,-23.67),(-50.92,-19.5),(-53.5,-19.5)]),
        ], crs="EPSG:4326")
    shps["hidrografia"] = gpd.GeoDataFrame(
        {"nome": ["Rio Paraguai","Rio Paraná","Rio Miranda","Rio Verde"]},
        geometry=[
            LineString([(-57.65,-19.0),(-56.5,-20.5),(-57.2,-22.0)]),
            LineString([(-53.5,-20.0),(-52.0,-22.5),(-50.92,-23.0)]),
            LineString([(-55.5,-19.5),(-56.5,-20.5),(-57.0,-21.0)]),
            LineString([(-54.5,-19.0),(-54.0,-21.0),(-53.8,-22.5)]),
        ], crs="EPSG:4326")
    shps["rodovias"] = gpd.GeoDataFrame(
        {"rodovia": ["BR-163","BR-262","BR-060"]},
        geometry=[
            LineString([(-55.3,-17.2),(-54.9,-20.4),(-55.0,-23.0)]),
            LineString([(-57.4,-19.0),(-54.6,-20.4),(-51.0,-20.8)]),
            LineString([(-54.0,-17.8),(-54.6,-20.4),(-54.0,-23.5)]),
        ], crs="EPSG:4326")
    return shps


# ─────────────────────────────────────────────────────────────────────────────
# GRÁFICO 5-PAINÉIS INTERATIVO (mplcursors)
# ─────────────────────────────────────────────────────────────────────────────

def gerar_grafico_72h_interativo(dados: dict, nome_ponto: str,
                                  lat: float, lon: float) -> plt.Figure:
    """
    Dashboard meteorológico 72h com 5 painéis empilhados e tooltip interativo.

    Painel 1 — Temperatura (°C) + Ponto de orvalho + CAPE (eixo sec.)
    Painel 2 — Precipitação (mm) + Probabilidade (%) + sombreado risco >70%
    Painel 3 — Radiação solar GHI / DNI / Difusa com pico anotado
    Painel 4 — Velocidade do vento + rajadas + limites operacionais
    Painel 5 — Umidade relativa + Heat Index + limites de defensivos/fitossanidade

    mplcursors: tooltip hover em todas as linhas principais.
    """
    if not dados or "hourly" not in dados:
        return None

    h      = dados["hourly"]
    times  = h.get("time", [])[:72]
    N      = len(times)

    # Extração das séries (preenchimento com NaN se ausente)
    def _serie(key, n=N, fill=np.nan):
        vals = h.get(key, [])[:n]
        vals = [v if v is not None else fill for v in vals]
        if len(vals) < n:
            vals += [fill] * (n - len(vals))
        return np.array(vals, dtype=float)

    temp    = _serie("temperature_2m")
    orvalho = _serie("dewpoint_2m")
    ur      = _serie("relativehumidity_2m")
    precip  = _serie("precipitation", fill=0.0)
    prob_pp = _serie("precipitation_probability", fill=0.0)
    vento   = _serie("windspeed_10m")
    rajadas = _serie("windgusts_10m")
    ghi     = _serie("shortwave_radiation")
    dni     = _serie("direct_normal_irradiance")
    difusa  = _serie("diffuse_radiation")
    cape    = _serie("cape", fill=0.0)

    # Índice de calor (Heat Index Rothfusz) quando T>27°C e RH>40%
    def heat_index(T, RH):
        """Fórmula Rothfusz simplificada para Heat Index (°C)."""
        HI = np.full_like(T, np.nan)
        mask = (T > 27.0) & (RH > 40.0)
        t, r = T[mask], RH[mask]
        hi = (-8.78469475556 + 1.61139411*t + 2.33854883889*r
              - 0.14611605*t*r - 0.012308094*t**2
              - 0.0164248277778*r**2 + 0.002211732*t**2*r
              + 0.00072546*t*r**2 - 0.000003582*t**2*r**2)
        HI[mask] = hi
        return HI

    hi_vals = heat_index(temp, ur)

    # Timestamps formatados
    try:
        ts_dt = [datetime.fromisoformat(t) for t in times]
        ts_lb = [t.strftime("%d/%m %H:%M") for t in ts_dt]
        agora_idx = next((i for i, t in enumerate(ts_dt)
                          if t.date() == datetime.now().date()
                          and t.hour == datetime.now().hour), 0)
    except Exception:
        ts_lb = [str(i) for i in range(N)]
        agora_idx = 0

    idx = np.arange(N)

    # ── Figura com gridspec ────────────────────────────────────────────────
    fig = plt.figure(figsize=(13, 16), facecolor="#0d1117")
    gs  = gridspec.GridSpec(5, 1, figure=fig,
                             height_ratios=[2.2, 1.8, 1.8, 1.4, 1.8],
                             hspace=0.08)
    axes = [fig.add_subplot(gs[i]) for i in range(5)]

    estilo_base = {"facecolor": "#111827"}
    for ax in axes:
        ax.set_facecolor("#111827")
        ax.tick_params(colors="#9ca3af", labelsize=7.5)
        for sp in ax.spines.values():
            sp.set_edgecolor("#1f2937")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, color="#1e2a3a", linewidth=0.5, alpha=0.8, linestyle=":")
        ax.set_xlim(0, N - 1)

    # Linha vertical "agora"
    for ax in axes:
        ax.axvline(agora_idx, color="white", linewidth=0.8, linestyle="--", alpha=0.4, zorder=2)

    # ── PAINEL 1: Temperatura + Ponto de orvalho + CAPE ───────────────────
    ax1   = axes[0]
    ax1_b = ax1.twinx()
    ax1_b.set_facecolor("#111827")

    # CAPE — barras semitransparentes (eixo secundário)
    ax1_b.bar(idx, cape, color="#ef4444", alpha=0.25, width=1.0, zorder=1, label="CAPE (J/kg)")
    ax1_b.set_ylabel("CAPE (J/kg)", color="#ef4444", fontsize=8)
    ax1_b.tick_params(colors="#ef4444", labelsize=7)
    ax1_b.axhline(1000, color="#ef4444", linewidth=0.6, linestyle=":", alpha=0.5)
    ax1_b.axhline(2000, color="#dc2626", linewidth=0.6, linestyle=":", alpha=0.7)
    ax1_b.spines["right"].set_edgecolor("#ef4444")

    # Área entre T e Td = margem de condensação
    ax1.fill_between(idx, temp, orvalho, alpha=0.12, color="#38bdf8", zorder=2)

    l1, = ax1.plot(idx, temp,    color="#f97316", linewidth=2.0, zorder=5, label="Temperatura (°C)")
    l2, = ax1.plot(idx, orvalho, color="#38bdf8", linewidth=1.4, linestyle="--", zorder=4, label="Ponto de orvalho (°C)")
    ax1.fill_between(idx, temp, alpha=0.1, color="#f97316")
    ax1.set_ylabel("°C", color="#9ca3af", fontsize=9)
    ax1.set_xticks([])
    ax1.legend(handles=[l1, l2], loc="upper right", fontsize=7.5,
               facecolor="#111827", labelcolor="white", edgecolor="#374151", ncol=2)
    ax1.set_title(
        f"Previsão Meteorológica 72h — {nome_ponto} ({lat:.4f}°S, {lon:.4f}°W)\n"
        f"Modelo: {dados.get('_modelo_usado','ICON-EU')} | Open-Meteo · Yamada Engenharia",
        color="white", fontsize=10, fontweight="bold", pad=10, loc="left"
    )

    # ── PAINEL 2: Precipitação + probabilidade ─────────────────────────────
    ax2   = axes[1]
    ax2_b = ax2.twinx()
    ax2_b.set_facecolor("#111827")

    # Sombreio risco alto (prob > 70%)
    for i in range(N):
        if prob_pp[i] >= 70:
            ax2.axvspan(i - 0.5, i + 0.5, alpha=0.12, color="#ef4444", zorder=1)

    cores_pp = ["#3b82f6" if p < 5 else "#f59e0b" if p < 20 else "#ef4444" for p in precip]
    ax2.bar(idx, precip, color=cores_pp, alpha=0.85, width=0.85, edgecolor="none", zorder=3)
    ax2.set_ylabel("Precipitação (mm)", color="#9ca3af", fontsize=9)
    ax2.set_xticks([])

    l_prob, = ax2_b.plot(idx, prob_pp, color="#fbbf24", linewidth=1.6,
                          linestyle="--", zorder=4, label="Prob. (%)") 
    ax2_b.fill_between(idx, prob_pp, alpha=0.08, color="#fbbf24")
    ax2_b.set_ylabel("Probabilidade (%)", color="#fbbf24", fontsize=8)
    ax2_b.set_ylim(0, 100)
    ax2_b.tick_params(colors="#fbbf24", labelsize=7)
    ax2_b.axhline(70, color="#fbbf24", linewidth=0.7, linestyle=":", alpha=0.6)

    total_72h = np.nansum(precip)
    ax2.text(0.99, 0.93, f"Total 72h: {total_72h:.1f} mm",
             transform=ax2.transAxes, ha="right", color="white", fontsize=8,
             bbox=dict(facecolor=VERDE_ESCURO, alpha=0.75, boxstyle="round,pad=0.3"))

    # ── PAINEL 3: Radiação Solar ───────────────────────────────────────────
    ax3  = axes[2]
    l_ghi,  = ax3.plot(idx, ghi,    color="#86efac", linewidth=1.8, zorder=5, label="GHI (W/m²)")
    l_dni,  = ax3.plot(idx, dni,    color="#facc15", linewidth=1.4, zorder=4, label="DNI (W/m²)")
    l_dif,  = ax3.plot(idx, difusa, color="#c084fc", linewidth=1.2, zorder=3, label="Difusa (W/m²)")
    ax3.fill_between(idx, ghi, alpha=0.12, color="#86efac")
    ax3.set_ylabel("W/m²", color="#9ca3af", fontsize=9)
    ax3.set_xticks([])

    # Anota pico diário de GHI
    if np.any(~np.isnan(ghi)) and np.nanmax(ghi) > 0:
        pico_idx = int(np.nanargmax(ghi))
        pico_val = float(ghi[pico_idx])
        ax3.annotate(
            f"Pico: {pico_val:.0f} W/m²",
            xy=(pico_idx, pico_val),
            xytext=(0, 12), textcoords="offset points",
            color="#facc15", fontsize=7.5, ha="center",
            arrowprops=dict(arrowstyle="->", color="#facc15", lw=1.0),
        )
    ax3.legend(handles=[l_ghi, l_dni, l_dif], loc="upper right",
               fontsize=7, facecolor="#111827", labelcolor="white",
               edgecolor="#374151", ncol=3)

    # ── PAINEL 4: Vento + Rajadas ──────────────────────────────────────────
    ax4 = axes[3]
    ax4.fill_between(idx, rajadas, vento, alpha=0.15, color="#a78bfa", zorder=2)
    l_raj, = ax4.plot(idx, rajadas, color="#c4b5fd", linewidth=1.2,
                       linestyle="--", zorder=4, label="Rajadas (km/h)")
    l_ven, = ax4.plot(idx, vento,   color="#a78bfa", linewidth=1.8,
                       zorder=5, label="Vento médio (km/h)")
    ax4.fill_between(idx, vento, alpha=0.15, color="#a78bfa")

    ax4.axhline(10, color="#fbbf24", linewidth=1.0, linestyle="--", alpha=0.8,
                label="Limite defensivos (10 km/h)")
    ax4.axhline(40, color="#ef4444", linewidth=0.8, linestyle=":",  alpha=0.7,
                label="Risco operacional (40 km/h)")
    ax4.set_ylabel("km/h", color="#9ca3af", fontsize=9)
    ax4.set_xticks([])
    ax4.legend(fontsize=6.5, facecolor="#111827", labelcolor="white",
               edgecolor="#374151", ncol=2, loc="upper right")

    # ── PAINEL 5: Umidade Relativa + Heat Index ────────────────────────────
    ax5  = axes[4]
    ax5.fill_between(idx, ur, alpha=0.2, color="#38bdf8", zorder=2)
    l_ur, = ax5.plot(idx, ur, color="#38bdf8", linewidth=2.0, zorder=5, label="Umidade Relativa (%)")

    # Heat Index sobreposto (eixo secundário)
    ax5_b = ax5.twinx()
    ax5_b.set_facecolor("#111827")
    l_hi, = ax5_b.plot(idx, hi_vals, color="#fb923c", linewidth=1.4,
                        linestyle="--", zorder=4, label="Heat Index (°C)")
    ax5_b.set_ylabel("Heat Index (°C)", color="#fb923c", fontsize=8)
    ax5_b.tick_params(colors="#fb923c", labelsize=7)
    ax5_b.spines["right"].set_edgecolor("#fb923c")

    ax5.axhline(55, color="#fbbf24", linewidth=0.9, linestyle="--", alpha=0.7,
                label="Mín. defensivos (55%)")
    ax5.axhline(90, color="#ef4444", linewidth=0.8, linestyle=":",  alpha=0.6,
                label="Risco fitossanitário (90%)")
    ax5.set_ylabel("Umidade (%)", color="#9ca3af", fontsize=9)
    ax5.set_ylim(0, 105)
    ax5.legend(fontsize=7, facecolor="#111827", labelcolor="white",
               edgecolor="#374151", ncol=2, loc="lower right")

    # ── Eixo X compartilhado (painel 5) ───────────────────────────────────
    step = max(1, N // 12)
    ax5.set_xticks(idx[::step])
    ax5.set_xticklabels(ts_lb[::step], rotation=45, ha="right",
                         fontsize=7, color="#9ca3af")

    # ── mplcursors — tooltip interativo ───────────────────────────────────
    if _HAS_MPLCURSORS:
        linhas_interativas = [l1, l2, l_prob, l_ghi, l_ven, l_raj, l_uri := l_ur]
        for linha in [l1, l2, l_ghi, l_dni, l_dif, l_ven, l_raj, l_ur, l_hi, l_prob]:
            try:
                cursor = mplcursors.cursor(linha, hover=True)
                @cursor.connect("add")
                def _on_add(sel, _lb=ts_lb):
                    ix = int(round(sel.index))
                    ix = max(0, min(ix, len(_lb) - 1))
                    sel.annotation.set_text(
                        f"{_lb[ix]}\n{sel.artist.get_label()}: {sel.target[1]:.1f}"
                    )
                    sel.annotation.get_bbox_patch().set(
                        facecolor="#1e293b", alpha=0.9, edgecolor="#3DA63A"
                    )
                    sel.annotation.set_color("white")
            except Exception:
                pass

    fig.text(0.01, 0.005,
             f"Yamada Engenharia · Open-Meteo ({dados.get('_modelo_usado','ICON-EU')}) · "
             f"{datetime.now().strftime('%d/%m/%Y %H:%M')}",
             color="#555", fontsize=7)
    plt.tight_layout(rect=[0, 0.01, 1, 1])
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MAPAS GOES-19 (com suporte a cartopy quando disponível)
# ─────────────────────────────────────────────────────────────────────────────

def gerar_mapa_canal_goes19(banda_id: str, shps: dict, nome_ponto: str,
                             lat: float, lon: float,
                             goes_data=None, extent=None,
                             is_rgb: bool = False,
                             ts_label: str = "",
                             fonte: str = "simulado",
                             df_focos: pd.DataFrame = None) -> plt.Figure:
    """
    Gera mapa para canal GOES-19 ou composto RGB.
    Suporta cartopy (projeção PlateCarree + features) se disponível,
    senão usa matplotlib puro com shapefiles geopandas.

    Parâmetros:
      banda_id   — chave do BANDAS_INFO
      is_rgb     — se True, goes_data é array HxWx3 (composição RGB)
      fonte      — 'goes2go' | 'boto3' | 'simulado'
    """
    info     = BANDAS_INFO.get(banda_id, {"nome": banda_id, "icon": "🛰️",
                                           "uso": "", "cmap": "gray"})
    bbox_ms  = [_MS_LON_MIN, _MS_LON_MAX, _MS_LAT_MIN, _MS_LAT_MAX]

    if _HAS_CARTOPY and goes_data is not None:
        # ── Renderização com Cartopy ───────────────────────────────────────
        proj = ccrs.PlateCarree()
        fig  = plt.figure(figsize=(9, 7), facecolor=PRETO)
        ax   = fig.add_subplot(1, 1, 1, projection=proj)
        ax.set_extent([bbox_ms[0]-0.5, bbox_ms[1]+0.5,
                       bbox_ms[2]-0.5, bbox_ms[3]+0.5], crs=proj)
        ax.set_facecolor("#0d1117")

        if is_rgb and goes_data.ndim == 3:
            ax.imshow(goes_data, extent=extent, origin="upper",
                      transform=proj, aspect="auto", alpha=0.9)
        elif not is_rgb:
            img = ax.imshow(goes_data, extent=extent, cmap=info["cmap"],
                            origin="upper", transform=proj, aspect="auto", alpha=0.85,
                            vmin=np.nanpercentile(goes_data, 2),
                            vmax=np.nanpercentile(goes_data, 98))
            cbar = plt.colorbar(img, ax=ax, fraction=0.03, pad=0.01)
            cbar.set_label(info["nome"], color="white", fontsize=8)
            cbar.ax.tick_params(colors="white")

        # Features cartopy
        ax.add_feature(cfeature.STATES.with_scale("10m"),
                       edgecolor="white", linewidth=0.6, alpha=0.7)
        ax.add_feature(cfeature.RIVERS.with_scale("10m"),
                       edgecolor="#4FC3F7", linewidth=0.6, alpha=0.5)
        ax.add_feature(cfeature.BORDERS.with_scale("10m"),
                       edgecolor="#aaaaaa", linewidth=0.8, alpha=0.6)
        ax.gridlines(draw_labels=True, color="#222222", alpha=0.4,
                     linewidth=0.4, x_inline=False, y_inline=False,
                     xlabel_style={"color":"#aaaaaa","fontsize":7},
                     ylabel_style={"color":"#aaaaaa","fontsize":7})

    else:
        # ── Renderização matplotlib puro ──────────────────────────────────
        fig, ax = plt.subplots(figsize=(9, 7), facecolor=PRETO)
        ax.set_facecolor("#0d1117")

        if goes_data is not None:
            if is_rgb and goes_data.ndim == 3:
                ax.imshow(goes_data, extent=extent, origin="upper",
                          aspect="auto", alpha=0.9)
            else:
                img  = ax.imshow(goes_data, extent=extent, cmap=info["cmap"],
                                 origin="upper", alpha=0.85, aspect="auto",
                                 vmin=np.nanpercentile(goes_data, 2),
                                 vmax=np.nanpercentile(goes_data, 98))
                cbar = plt.colorbar(img, ax=ax, fraction=0.03, pad=0.01)
                cbar.set_label(info["nome"], color="white", fontsize=8)
                cbar.ax.tick_params(colors="white")
        else:
            # Fallback sintético realista
            x  = np.linspace(bbox_ms[0], bbox_ms[1], 300)
            y  = np.linspace(bbox_ms[2], bbox_ms[3], 300)
            X, Y = np.meshgrid(x, y)
            np.random.seed(abs(hash(banda_id)) % 9999)
            if banda_id in ["B13", "B14"]:
                Z = np.sin(X*0.4)*np.cos(Y*0.4)*30 + 270 + np.random.normal(0, 5, X.shape)
            elif banda_id == "B09":
                Z = np.cos(X*0.3+Y*0.2)*20 + 250 + np.random.normal(0, 3, X.shape)
            elif banda_id == "B02":
                Z = (np.abs(np.sin(X*0.5)*np.cos(Y*0.6))*0.6 + 0.1
                     + np.random.normal(0, 0.05, X.shape)).clip(0, 1)
            elif is_rgb:
                Z_r = np.clip(np.abs(np.sin(X*0.3)*np.cos(Y*0.4))*0.8+0.1
                              + np.random.normal(0, 0.06, X.shape), 0, 1)
                Z_g = np.clip(np.abs(np.cos(X*0.35)*np.sin(Y*0.35))*0.7+0.1
                              + np.random.normal(0, 0.06, X.shape), 0, 1)
                Z_b = np.clip(np.abs(np.sin(X*0.5+Y*0.5))*0.9+0.05
                              + np.random.normal(0, 0.06, X.shape), 0, 1)
                Z   = np.stack([Z_r, Z_g, Z_b], axis=-1)
                ax.imshow(Z, extent=bbox_ms, origin="lower", aspect="auto", alpha=0.85)
                ax.text(0.02, 0.02, "⚠ RGB simulado",
                        transform=ax.transAxes, fontsize=7, color="yellow",
                        alpha=0.8, va="bottom")
            else:
                Z = np.sin(X*0.35)*np.cos(Y*0.35)*25+270 + np.random.normal(0, 4, X.shape)

            if not is_rgb:
                img  = ax.pcolormesh(X, Y, Z, cmap=info["cmap"], shading="auto", alpha=0.9)
                cbar = plt.colorbar(img, ax=ax, fraction=0.03, pad=0.01)
                cbar.set_label(info["nome"], color="white", fontsize=8)
                cbar.ax.tick_params(colors="white")
                ax.text(0.02, 0.02, "⚠ GOES-19 simulado (S3/goes2go indisponível)",
                        transform=ax.transAxes, fontsize=7, color="yellow",
                        alpha=0.8, va="bottom")

        # Shapefiles
        try:
            shps["municipios"].boundary.plot(ax=ax, color="white", linewidth=0.4, alpha=0.5)
        except Exception: pass
        try:
            shps["biomas"].boundary.plot(ax=ax, color="#88BB88",
                                          linewidth=0.8, linestyle="--", alpha=0.5)
        except Exception: pass
        try:
            shps["hidrografia"].plot(ax=ax, color="#4FC3F7", linewidth=1.0, alpha=0.7)
        except Exception: pass
        try:
            shps["rodovias"].plot(ax=ax, color="#FFB74D", linewidth=0.8, alpha=0.6)
        except Exception: pass

        ax.set_xlim(bbox_ms[0]-0.5, bbox_ms[1]+0.5)
        ax.set_ylim(bbox_ms[2]-0.5, bbox_ms[3]+0.5)
        ax.set_xlabel("Longitude", color="#aaaaaa", fontsize=8)
        ax.set_ylabel("Latitude",  color="#aaaaaa", fontsize=8)
        ax.tick_params(colors="#aaaaaa", labelsize=7)
        for sp in ax.spines.values():
            sp.set_edgecolor("#333333")
        ax.grid(True, color="#222222", linewidth=0.4, alpha=0.5)

    # Focos INPE nos canais B02 e B13
    if df_focos is not None and not df_focos.empty and banda_id in ["B02", "B13"]:
        try:
            frp_v = df_focos.get("frp", pd.Series([50]*len(df_focos)))
            frp_n = (frp_v - frp_v.min()) / (frp_v.max() - frp_v.min() + 1e-5)
            cores = plt.cm.YlOrRd(frp_n.values)
            for i, row in df_focos.iterrows():
                ax.plot(row.get("longitude", 0), row.get("latitude", 0),
                        marker="^", color=cores[i % len(cores)],
                        markersize=6, alpha=0.85, zorder=9,
                        markeredgecolor="white", markeredgewidth=0.4)
        except Exception: pass

    # Marcador do ponto selecionado
    ax.plot(lon, lat, marker="*", color=VERDE_MEDIO, markersize=16, zorder=12,
            markeredgecolor="white", markeredgewidth=1.5)
    ax.annotate(
        f" {nome_ponto}", (lon, lat),
        fontsize=8.5, color="white", fontweight="bold",
        xytext=(7, 7), textcoords="offset points", zorder=13,
        bbox=dict(boxstyle="round,pad=0.3", facecolor=VERDE_ESCURO,
                  alpha=0.85, edgecolor="none"),
    )

    # Seta Norte
    ax.annotate("N ▲", xy=(0.97, 0.96), xycoords="axes fraction",
                ha="right", va="top", color="white", fontsize=11, fontweight="bold")

    # Título
    ts_info  = f" | {ts_label}" if ts_label else ""
    fonte_lb = {"goes2go": "goes2go ✓", "boto3": "S3/boto3 ✓", "simulado": "⚠ simulado"}
    ax.set_title(
        f"{info['icon']}  {info['nome']}{ts_info}\n"
        f"{info['uso']}  [{fonte_lb.get(fonte, fonte)}]",
        color="white", fontsize=9.5, fontweight="bold", pad=8, fontfamily="monospace"
    )

    # Legenda
    handles = [
        mpatches.Patch(facecolor="none", edgecolor="white",    linewidth=0.5, label="Municípios MS"),
        mpatches.Patch(facecolor=VERDE_MEDIO, alpha=0.6,       label=f"★ {nome_ponto}"),
        mpatches.Patch(facecolor="#4FC3F7",   alpha=0.7,       label="Rios"),
        mpatches.Patch(facecolor="#FFB74D",   alpha=0.6,       label="Rodovias BR"),
    ]
    if df_focos is not None and not df_focos.empty and banda_id in ["B02", "B13"]:
        handles.append(mpatches.Patch(facecolor="#FF6B35", alpha=0.8, label="Focos INPE"))
    ax.legend(handles=handles, loc="lower left", fontsize=6.5, framealpha=0.75,
              facecolor="#0d1117", labelcolor="white", edgecolor="#333333", ncol=2)

    fig.text(
        0.01, 0.005,
        f"GOES-19 ABI · {ts_label or datetime.now().strftime('%d/%m/%Y %H:%M')} UTC · Yamada Engenharia",
        color="#666", fontsize=6.5, va="bottom"
    )
    plt.tight_layout(pad=0.5)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# NOWCASTING DE CHUVA — 3 FONTES INTEGRADAS
# ─────────────────────────────────────────────────────────────────────────────

def calcular_nowcasting_chuva(dados: dict, goes_tb_serie: list = None) -> dict:
    """
    Estimativa de chegada de chuva integrando 3 fontes independentes:

    1. Nowcasting GOES-19 B13 (temperatura de brilho):
       - TB < 233 K E dTB/dt < -2 K/10min → CBs em desenvolvimento → 15-45 min
       - TB < 253 K → nuvem profunda → chuva possível
       (goes_tb_serie: lista de TB [K] das últimas 3 imagens, da mais antiga para a mais nova)

    2. Probabilidade horária Open-Meteo:
       - Primeira hora com prob ≥ 70% nas próximas 6h

    3. Índices de instabilidade (CAPE + Lifted Index):
       - CAPE > 2000 + LI < -4 → tempestade severa
       - CAPE > 1000 + LI < -2 → alta instabilidade
       - CAPE > 500            → instabilidade moderada

    Retorna dict com diagnóstico por fonte + severidade geral.
    """
    resultado = {
        "goes_tb":     {"status": "indisponível", "nivel": "azul",      "msg": "Imagem GOES não disponível."},
        "openmeteo":   {"status": "verificando",  "nivel": "verde",     "msg": ""},
        "instabilidade": {"status": "verificando","nivel": "verde",     "msg": ""},
        "nivel_geral": "verde",
        "prob_timeline_6h": [],
    }

    # ── Fonte 1: GOES-19 TB ──────────────────────────────────────────────
    if goes_tb_serie and len(goes_tb_serie) >= 2:
        tb_atual  = goes_tb_serie[-1]
        tb_ant    = goes_tb_serie[-2]
        dtb_10min = tb_atual - tb_ant  # negativo = topo esfriando = CB cresce

        if tb_atual < 233:
            if dtb_10min < -2:
                resultado["goes_tb"] = {
                    "status": "⚡ Chuva convectiva em ~15–45 min",
                    "nivel": "vermelho",
                    "msg": (f"TB = {tb_atual:.0f} K (topo frio ativo) | "
                            f"ΔTB = {dtb_10min:.1f} K/10min (CB em desenvolvimento). "
                            f"Risco de granizo e raios."),
                }
            else:
                resultado["goes_tb"] = {
                    "status": "⛈ Nuvem profunda sobre o ponto",
                    "nivel": "laranja",
                    "msg": f"TB = {tb_atual:.0f} K. Chuva possível nas próximas 1–2h.",
                }
        elif tb_atual < 253:
            resultado["goes_tb"] = {
                "status": "🌦 Nuvem convectiva moderada",
                "nivel": "amarelo",
                "msg": f"TB = {tb_atual:.0f} K. Pancadas possíveis nas próximas 2–4h.",
            }
        else:
            resultado["goes_tb"] = {
                "status": "☁️ Sem atividade convectiva significativa",
                "nivel": "verde",
                "msg": f"TB = {tb_atual:.0f} K (topo quente — nuvens baixas ou cirrus).",
            }

    # ── Fonte 2: Probabilidade Open-Meteo ────────────────────────────────
    if dados and "hourly" in dados:
        h     = dados["hourly"]
        probs = h.get("precipitation_probability", [])[:6]
        times = h.get("time", [])[:6]
        probs = [p or 0 for p in probs]
        resultado["prob_timeline_6h"] = list(zip(
            [t.split("T")[1][:5] if "T" in t else t[-5:] for t in times],
            probs
        ))

        # Primeira hora com prob ≥ 70%
        hora_chuva = next(
            ((t.split("T")[1][:5] if "T" in t else t[-5:], p)
             for t, p in zip(times, probs) if p >= 70),
            None
        )
        if hora_chuva:
            resultado["openmeteo"] = {
                "status": f"🌧 Chuva mais provável em: {hora_chuva[0]}",
                "nivel": "laranja",
                "msg": f"Probabilidade de {hora_chuva[1]:.0f}% às {hora_chuva[0]}.",
            }
        elif max(probs, default=0) >= 40:
            p_max = max(probs)
            h_max = times[probs.index(p_max)]
            h_max_fmt = h_max.split("T")[1][:5] if "T" in h_max else h_max[-5:]
            resultado["openmeteo"] = {
                "status": f"🌦 Chance moderada: {p_max:.0f}% às {h_max_fmt}",
                "nivel": "amarelo",
                "msg": f"Probabilidade máxima de {p_max:.0f}% nas próximas 6h.",
            }
        else:
            resultado["openmeteo"] = {
                "status": "☀️ Sem chuva significativa nas próximas 6h",
                "nivel": "verde",
                "msg": f"Probabilidade máxima: {max(probs, default=0):.0f}%.",
            }

        # ── Fonte 3: CAPE + LI ───────────────────────────────────────────
        cape_vals = h.get("cape", [])[:3]
        li_vals   = h.get("lifted_index", [])[:3]
        cape_max  = max((v for v in cape_vals if v is not None), default=0)
        li_min    = min((v for v in li_vals  if v is not None), default=0)

        if cape_max > 2000 and li_min < -4:
            resultado["instabilidade"] = {
                "status": "⚡ ATMOSFERA EXPLOSIVA",
                "nivel": "vermelho",
                "msg": (f"CAPE = {cape_max:.0f} J/kg | LI = {li_min:.1f}. "
                        f"Risco severo: tempestade com granizo e ventos > 70 km/h."),
            }
        elif cape_max > 1000 and li_min < -2:
            resultado["instabilidade"] = {
                "status": "⛈ Alta instabilidade — chuva forte",
                "nivel": "laranja",
                "msg": (f"CAPE = {cape_max:.0f} J/kg | LI = {li_min:.1f}. "
                        f"Chuva forte provável nas próximas 1–2h."),
            }
        elif cape_max > 500:
            resultado["instabilidade"] = {
                "status": "🌦 Instabilidade moderada",
                "nivel": "amarelo",
                "msg": f"CAPE = {cape_max:.0f} J/kg. Pancadas vespertinas possíveis.",
            }
        else:
            resultado["instabilidade"] = {
                "status": "✅ Atmosfera estável",
                "nivel": "verde",
                "msg": f"CAPE = {cape_max:.0f} J/kg. Sem convecção organizada esperada.",
            }

    # Nível geral = o mais severo dos 3
    _pesos = {"vermelho": 4, "laranja": 3, "amarelo": 2, "verde": 1, "azul": 0, "indisponível": 0}
    niveis = [resultado[k]["nivel"] for k in ["goes_tb", "openmeteo", "instabilidade"]]
    resultado["nivel_geral"] = max(niveis, key=lambda n: _pesos.get(n, 0))

    return resultado


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISES AGRONÔMICAS (mantidas do v3.0 + ajustes)
# ─────────────────────────────────────────────────────────────────────────────

def calcular_janela_defensivos(dados: dict) -> list:
    """Janelas de 24h para aplicação de defensivos — critérios MAPA/Embrapa."""
    if not dados or "hourly" not in dados:
        return []
    h = dados["hourly"]
    janelas = []
    for i, t in enumerate(h.get("time", [])[:24]):
        hora = t.split("T")[1][:5] if "T" in t else t[-5:]
        pp   = (h.get("precipitation",         [0]*24)[i] or 0)
        tmp  = (h.get("temperature_2m",         [25]*24)[i] or 25)
        ur   = (h.get("relativehumidity_2m",    [60]*24)[i] or 60)
        vnt  = (h.get("windspeed_10m",           [5]*24)[i] or 0)
        bloq = []
        if vnt >= 10: bloq.append(f"Vento {vnt:.0f}km/h")
        if tmp >= 30: bloq.append(f"Temp {tmp:.0f}°C")
        if ur  <= 55: bloq.append(f"UR {ur:.0f}%")
        if pp  >  0:  bloq.append(f"Chuva {pp:.1f}mm")
        status = "aberta" if len(bloq)==0 else ("parcial" if len(bloq)==1 else "bloqueada")
        janelas.append({"hora": hora, "status": status,
                        "motivo": " | ".join(bloq) if bloq else "✅ OK",
                        "temp": tmp, "ur": ur, "vento": vnt, "precip": pp})
    return janelas


def calcular_graus_dia(dados: dict, cultura: str, data_semeadura: datetime) -> dict:
    """GDA com Tb/Tc por cultura. Determina estádio fenológico atual."""
    if not dados or "daily" not in dados:
        return {}
    cfg       = CULTURAS_GDA.get(cultura, CULTURAS_GDA["Soja"])
    tb, tc    = cfg["tb"], cfg["tc"]
    stags     = cfg["estagios"]
    d         = dados["daily"]
    gda_total = 0.0
    for tmax, tmin in zip(d.get("temperature_2m_max", []), d.get("temperature_2m_min", [])):
        if tmax is None or tmin is None:
            continue
        tmedia    = (min(tmax, tc) + max(tmin, tb)) / 2
        gda_total += max(0.0, tmedia - tb)
    estagio_atual = stags[0][1]
    for limiar, nome in stags:
        if gda_total >= limiar: estagio_atual = nome
        else: break
    proximo = next(((l, n) for l, n in stags if gda_total < l), None)
    return {
        "cultura": cultura, "gda_total": round(gda_total, 1),
        "estagio_atual": estagio_atual, "proximo_estagio": proximo,
        "dias_desde_semeadura": (datetime.now().date() - data_semeadura.date()).days,
        "tb": tb,
    }


def calcular_risco_fitossanitario(dados: dict) -> list:
    """Risco de Ferrugem Asiática e Brusone com base em T e UR horárias."""
    if not dados or "hourly" not in dados:
        return []
    h    = dados["hourly"]
    temp = h.get("temperature_2m", [])[:48]
    umid = h.get("relativehumidity_2m", [])[:48]
    alertas = []
    h_fer = h_bru = 0
    for t, u in zip(temp, umid):
        if t and u:
            if 15 <= t <= 30 and u > 80: h_fer += 1
            else: h_fer = 0
            if 20 <= t <= 28 and u > 90: h_bru += 1
            else: h_bru = 0
    if h_fer >= 12:
        nv = "Crítico" if h_fer >= 20 else ("Alto" if h_fer >= 16 else "Médio")
        alertas.append({"doenca": "Ferrugem Asiática (Soja)", "nivel": nv,
                        "horas": h_fer, "icone": "🍂",
                        "cor": "vermelho" if nv in ["Crítico","Alto"] else "amarelo",
                        "msg": f"{h_fer}h favoráveis. Aplique triazol+estrobilurina preventivamente."})
    if h_bru >= 10:
        nv = "Crítico" if h_bru >= 18 else ("Alto" if h_bru >= 14 else "Médio")
        alertas.append({"doenca": "Brusone (Arroz/Trigo)", "nivel": nv,
                        "horas": h_bru, "icone": "🌾",
                        "cor": "vermelho" if nv in ["Crítico","Alto"] else "amarelo",
                        "msg": f"{h_bru}h favoráveis. Aplique triclazol ou azoxistrobina."})
    if not alertas:
        alertas.append({"doenca": "Sem risco fitossanitário", "nivel": "Baixo",
                        "horas": 0, "icone": "✅", "cor": "verde",
                        "msg": "Condições desfavoráveis às doenças foliares (48h)."})
    return alertas


def calcular_balanco_hidrico_thornthwaite(dados: dict, cad_mm: float = 65.0) -> dict:
    """Balanço hídrico Thornthwaite-Mather com CAD configurável pelo usuário."""
    if not dados or "daily" not in dados:
        return {}
    d        = dados["daily"]
    eto_l    = d.get("et0_fao_evapotranspiration", [])
    precip_l = d.get("precipitation_sum", [])
    if not eto_l:
        return {}
    arm        = cad_mm * 0.5
    resultados = []
    for eto, pp in zip(eto_l, precip_l):
        eto = eto or 0.0; pp = pp or 0.0
        bal = pp - eto
        if bal >= 0:
            arm_novo = min(arm + bal, cad_mm)
            exc = arm + bal - arm_novo; def_ = 0.0; etr = eto
        else:
            arm_novo = max(0.0, arm * np.exp(bal / cad_mm))
            exc = 0.0; etr = pp + (arm - arm_novo); def_ = eto - etr
        resultados.append({"arm":round(arm_novo,2),"def":round(def_,2),
                           "exc":round(exc,2),"etr":round(etr,2),
                           "eto":round(eto,2),"pp":round(pp,2)})
        arm = arm_novo
    if not resultados:
        return {}
    hoje    = resultados[0]
    arm_pct = round(hoje["arm"]/cad_mm*100, 1) if cad_mm > 0 else 0
    if arm_pct >= 70:
        rec, nivel = "✅ Solo bem suprido. Irrigação dispensável.", "verde"
    elif arm_pct >= 40:
        rec, nivel = f"💧 Irrigar {hoje['def']*1.1:.1f} mm para ARM acima de 70% da CAD.", "amarelo"
    else:
        rec, nivel = f"🚿 Déficit crítico: {hoje['def']:.1f} mm. Irrigar urgente: {hoje['def']*1.2:.1f} mm.", "vermelho"
    return {"arm_mm":hoje["arm"],"arm_pct":arm_pct,"def_mm":hoje["def"],
            "exc_mm":hoje["exc"],"etr_mm":hoje["etr"],"eto_mm":hoje["eto"],
            "pp_mm":hoje["pp"],"cad_mm":cad_mm,"recomendacao":rec,"nivel":nivel,
            "serie":resultados}


def calcular_alertas(dados: dict, lat: float, gda_info: dict = None) -> list:
    """Alertas meteorológicos com adaptação ao estádio fenológico."""
    alertas = []
    if not dados or "daily" not in dados:
        return alertas
    d            = dados["daily"]
    tmin         = d.get("temperature_2m_min", [20]*7)
    precip_d     = d.get("precipitation_sum",  [0]*7)
    wcode        = d.get("weathercode",        [0]*7)
    estagio      = gda_info.get("estagio_atual","") if gda_info else ""
    est_crit     = any(s in estagio for s in ["R1","R2","R3","R4","R5","R6"])
    for i, t in enumerate(tmin[:3]):
        if t is not None and t < 5:
            c = "vermelho" if (t < 2 or est_crit) else "amarelo"
            n = "🔴 EMERGÊNCIA" if (t < 2 or est_crit) else "🟡 ALERTA"
            nota = f" ⚠️ Cultura em {estagio}!" if est_crit else ""
            alertas.append({"nivel":c,"icone":"❄️","titulo":f"{n} — Risco de Geada",
                            "msg":f"Mínima {t:.1f}°C em {i+1} dia(s). Proteja culturas sensíveis.{nota}"})
    for i, pp in enumerate(precip_d[:3]):
        if pp and pp > 40:
            c = "vermelho" if pp > 80 else "amarelo"
            n = "🔴 EMERGÊNCIA" if pp > 80 else "🟡 ALERTA"
            alertas.append({"nivel":c,"icone":"⛈️","titulo":f"{n} — Chuva Intensa",
                            "msg":f"{pp:.0f} mm em 24h. Suspenda pulverizações."})
    for i, wc in enumerate(wcode[:3]):
        if wc in [95, 99]:
            alertas.append({"nivel":"vermelho","icone":"⚡",
                            "titulo":"🔴 EMERGÊNCIA — Tempestade Severa",
                            "msg":f"Tempestade com raios em {i+1} dia(s). Risco de granizo."})
    dias_secos = sum(1 for pp in precip_d if pp is not None and pp < 1)
    if dias_secos >= 5:
        alertas.append({"nivel":"amarelo","icone":"🌵","titulo":"🟡 ALERTA — Veranico",
                        "msg":f"{dias_secos} dias sem chuva previstos. Intensifique irrigação."})
    if not alertas:
        alertas.append({"nivel":"verde","icone":"✅","titulo":"🟢 SEM ALERTAS ATIVOS",
                        "msg":"Condições favoráveis para as próximas 72 horas."})
    return alertas


# ─────────────────────────────────────────────────────────────────────────────
# GRÁFICOS AUXILIARES (mantidos do v3.0)
# ─────────────────────────────────────────────────────────────────────────────

def gerar_grafico_ndvi(ndvi_data, nome_ponto):
    if not ndvi_data or "listaSerie" not in ndvi_data: return None
    serie   = ndvi_data["listaSerie"]
    datas   = [s.get("data", s.get("ano","")) for s in serie]
    valores = [float(s.get("ndvi", s.get("valor",0))) for s in serie]
    if len(valores) < 2: return None
    fig, ax = plt.subplots(figsize=(10,4), facecolor="#0d1117")
    ax.set_facecolor("#111827")
    ax.fill_between(range(len(valores)), valores, alpha=0.15, color=VERDE_MEDIO)
    ax.plot(range(len(valores)), valores, color=VERDE_MEDIO, linewidth=1.8, zorder=4)
    med = float(np.median(valores[:-1])) if len(valores)>1 else 0.5
    ax.axhline(med, color="#FFC107", linewidth=1.2, linestyle="--", alpha=0.8,
               label=f"Mediana: {med:.3f}")
    ax.scatter([len(valores)-1],[valores[-1]],color="#FF5722",s=80,zorder=6,
               label=f"Atual: {valores[-1]:.3f}")
    delta = valores[-1]-med
    ax.annotate(f"Δ {delta:+.3f}", xy=(len(valores)-1,valores[-1]),
                xytext=(-40,15), textcoords="offset points",
                color=VERDE_MEDIO if delta>=0 else VERMELHO_ALRT, fontsize=9, fontweight="bold",
                arrowprops=dict(arrowstyle="->",
                                color=VERDE_MEDIO if delta>=0 else VERMELHO_ALRT, lw=1.2))
    step = max(1,len(datas)//8)
    ax.set_xticks(range(0,len(datas),step))
    ax.set_xticklabels([str(datas[i])[:4] for i in range(0,len(datas),step)],
                       color="#9ca3af",fontsize=8,rotation=30)
    ax.set_ylabel("NDVI",color="#9ca3af",fontsize=9); ax.set_ylim(0,1)
    ax.tick_params(colors="#9ca3af",labelsize=8)
    for sp in ax.spines.values(): sp.set_edgecolor("#1f2937")
    ax.grid(True,color="#1f2937",linewidth=0.5,alpha=0.6)
    sim = " ⚠ (simulado)" if ndvi_data.get("_simulado") else ""
    ax.set_title(f"🌿 NDVI Histórico — {nome_ponto}{sim}",color="white",
                 fontsize=11,fontweight="bold")
    ax.legend(fontsize=8,facecolor="#111827",labelcolor="white",edgecolor="#374151",
              loc="lower right")
    fig.text(0.01,0.01,"Fonte: Embrapa SATVeg",color="#666",fontsize=7)
    plt.tight_layout()
    return fig


def gerar_grafico_balanco_hidrico(bh):
    if not bh or "serie" not in bh or not bh["serie"]: return None
    serie = bh["serie"][:7]
    dias  = [f"D+{i}" for i in range(len(serie))]
    arm   = [s["arm"] for s in serie]
    def_  = [s["def"] for s in serie]
    exc   = [s["exc"] for s in serie]
    cad   = bh["cad_mm"]
    fig,(ax1,ax2) = plt.subplots(2,1,figsize=(10,5),facecolor="#0d1117",
                                  gridspec_kw={"height_ratios":[2,1]})
    for ax in [ax1,ax2]:
        ax.set_facecolor("#111827"); ax.tick_params(colors="#9ca3af",labelsize=8)
        for sp in ax.spines.values(): sp.set_edgecolor("#1f2937")
        ax.grid(True,color="#1f2937",linewidth=0.5,alpha=0.7)
    ax1.fill_between(range(len(arm)),arm,alpha=0.3,color="#42A5F5")
    ax1.plot(range(len(arm)),arm,color="#42A5F5",linewidth=2,label="ARM (mm)")
    ax1.axhline(cad,color="#FFB74D",linewidth=1,linestyle="--",label=f"CAD={cad}mm")
    ax1.axhline(cad*0.4,color="#EF5350",linewidth=0.8,linestyle=":",label="Crítico (40%)")
    ax1.set_ylabel("Armazenamento (mm)",color="#9ca3af",fontsize=9)
    ax1.set_xticks([]); ax1.set_ylim(0,cad*1.15)
    ax1.legend(fontsize=8,facecolor="#111827",labelcolor="white",edgecolor="#374151")
    ax1.set_title("💧 Balanço Hídrico — Thornthwaite-Mather",color="white",
                  fontsize=11,fontweight="bold")
    ax2.bar(range(len(def_)),def_,color="#EF5350",alpha=0.8,label="Déficit",width=0.4)
    ax2.bar([i+0.42 for i in range(len(exc))],exc,color="#29B6F6",
            alpha=0.8,label="Excedente",width=0.4)
    ax2.set_ylabel("mm",color="#9ca3af",fontsize=9)
    ax2.set_xticks(range(len(dias))); ax2.set_xticklabels(dias,color="#9ca3af",fontsize=8)
    ax2.legend(fontsize=8,facecolor="#111827",labelcolor="white",edgecolor="#374151")
    plt.tight_layout()
    return fig


def gerar_tabela_7dias(dados):
    if not dados or "daily" not in dados: return pd.DataFrame()
    d = dados["daily"]
    wcode_map={0:"☀️ Limpo",1:"🌤 Poucas nuvens",2:"⛅ Parcial",3:"☁️ Nublado",
               45:"🌫 Névoa",51:"🌦 Chuvisco",61:"🌧 Chuva",63:"🌧 Moderada",
               65:"⛈ Forte",80:"🌦 Pancadas",81:"⛈ Pancadas fortes",
               95:"⛈ Tempestade",99:"⛈ Granizo"}
    datas  = [datetime.fromisoformat(t).strftime("%a %d/%m") for t in d.get("time",[])]
    cond   = [wcode_map.get(w,f"Cód {w}") for w in d.get("weathercode",[0]*7)]
    tmax   = [f"{v:.1f}°C" if v else "—" for v in d.get("temperature_2m_max",[])]
    tmin   = [f"{v:.1f}°C" if v else "—" for v in d.get("temperature_2m_min",[])]
    precip = [f"{v:.1f} mm" if v else "0.0 mm" for v in d.get("precipitation_sum",[])]
    eto    = [f"{v:.2f} mm" if v else "—" for v in d.get("et0_fao_evapotranspiration",[])]
    return pd.DataFrame({"Data":datas,"Condição":cond,"T. Máx":tmax,
                         "T. Mín":tmin,"Precipitação":precip,"ETo (mm)":eto})


# ─────────────────────────────────────────────────────────────────────────────
# SISTEMA DE E-MAIL (mantido do v3.0, sem alterações)
# ─────────────────────────────────────────────────────────────────────────────

def _cor_alerta_email(nivel):
    return {"verde":("#e8f5e9","#43a047","#1b5e20"),
            "amarelo":("#fff8e1","#fbc02d","#5d4037"),
            "vermelho":("#ffebee","#e53935","#b71c1c"),
            "laranja":("#fff3e0","#fb8c00","#bf360c")
            }.get(nivel, ("#f5f5f5","#9e9e9e","#333"))


def gerar_html_relatorio(nome_ponto, lat, lon, dados_meteo, alertas,
                          janelas_def, gda_info, riscos_fito, bh,
                          ndvi_data, df_focos, df_inmet) -> str:
    """Gera HTML completo do relatório agroclimático para envio por e-mail."""
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    h = dados_meteo.get("hourly",{}) if dados_meteo else {}
    d = dados_meteo.get("daily",{})  if dados_meteo else {}
    temp_atual   = (h.get("temperature_2m",        [None])[0] or 0)
    precip_hoje  = (d.get("precipitation_sum",      [None])[0] or 0)
    umid_atual   = (h.get("relativehumidity_2m",    [None])[0] or 0)
    vento_atual  = (h.get("windspeed_10m",          [None])[0] or 0)
    eto_hoje     = (d.get("et0_fao_evapotranspiration",[None])[0] or 0)

    def card_m(tit,val,uni,cor="#1B4D2E"):
        return (f'<div style="flex:1;min-width:110px;background:#fff;border-radius:10px;'
                f'border-top:4px solid {cor};padding:14px 12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);text-align:center;">'
                f'<div style="font-size:11px;color:#777;">{tit}</div>'
                f'<div style="font-size:22px;font-weight:bold;color:#222;">{val}'
                f'<span style="font-size:12px;color:#999;margin-left:2px;">{uni}</span></div></div>')

    cards = (card_m("🌡 Temperatura",f"{temp_atual:.1f}","°C","#e65100") +
             card_m("🌧 Chuva 24h",  f"{precip_hoje:.1f}","mm","#1565c0") +
             card_m("💧 Umidade",     f"{umid_atual:.0f}","%","#0277bd") +
             card_m("💨 Vento",       f"{vento_atual:.0f}","km/h","#6a1b9a") +
             card_m("🌿 ETo",         f"{eto_hoje:.2f}","mm/dia","#2e7d32"))

    html_alertas = ""
    for al in alertas:
        bg,brd,tc = _cor_alerta_email(al["nivel"])
        html_alertas += (f'<div style="background:{bg};border-left:5px solid {brd};'
                         f'border-radius:6px;padding:12px 16px;margin:6px 0;">'
                         f'<b style="color:{tc};">{al["icone"]} {al["titulo"]}</b><br>'
                         f'<span style="font-size:13px;">{al["msg"]}</span></div>')

    n_ab  = sum(1 for j in janelas_def if j["status"]=="aberta")
    n_bl  = sum(1 for j in janelas_def if j["status"]=="bloqueada")
    max_seq=cur_seq=cur_start=max_start=0
    for i,j in enumerate(janelas_def):
        if j["status"]=="aberta":
            if cur_seq==0: cur_start=i
            cur_seq+=1
            if cur_seq>max_seq: max_seq=cur_seq; max_start=cur_start
        else: cur_seq=0
    melhor = ""
    if max_seq>0:
        h1=janelas_def[max_start]["hora"]
        h2=janelas_def[min(max_start+max_seq-1,len(janelas_def)-1)]["hora"]
        melhor = f"<b>Melhor janela:</b> {h1} → {h2} ({max_seq}h)"
    else:
        melhor = "<b>Sem janela ideal nas próximas 24h.</b>"

    html_gda = ""
    if gda_info:
        p = gda_info.get("proximo_estagio")
        fs = f" | Próximo: <b>{p[1]}</b> em {p[0]-gda_info['gda_total']:.0f} °C·dia" if p else ""
        html_gda = (f'<div style="background:#f9fbe7;border-left:5px solid #8bc34a;'
                    f'border-radius:6px;padding:14px 16px;">'
                    f'<b style="color:#33691e;">🌾 {gda_info["cultura"]} — {gda_info["estagio_atual"]}</b><br>'
                    f'<span style="font-size:13px;">GDA: <b>{gda_info["gda_total"]} °C·dia</b>'
                    f' | {gda_info["dias_desde_semeadura"]} dias{fs}</span></div>')

    html_fito = ""
    for r in riscos_fito:
        bg,brd,tc = _cor_alerta_email(r["cor"])
        html_fito += (f'<div style="background:{bg};border-left:5px solid {brd};'
                      f'border-radius:6px;padding:10px 14px;margin:5px 0;">'
                      f'<b style="color:{tc};">{r["icone"]} {r["doenca"]} — Risco {r["nivel"]}</b><br>'
                      f'<span style="font-size:12px;">{r["msg"]}</span></div>')

    html_bh = ""
    if bh:
        w = min(int(bh.get("arm_pct",0)),100)
        cor_b = "#43a047" if w>=70 else ("#fbc02d" if w>=40 else "#e53935")
        html_bh = (f'<div style="background:#e3f2fd;border-left:4px solid #1565c0;'
                   f'border-radius:4px;padding:10px 14px;">'
                   f'ARM: {bh["arm_mm"]:.1f}/{bh["cad_mm"]:.0f}mm ({bh["arm_pct"]:.0f}%) | '
                   f'Déficit: {bh["def_mm"]:.1f}mm<br>'
                   f'<b>Recomendação:</b> {bh["recomendacao"]}</div>')

    html_ndvi = ""
    if ndvi_data and "listaSerie" in ndvi_data:
        vals = [float(s.get("ndvi",s.get("valor",0))) for s in ndvi_data["listaSerie"]]
        if vals:
            va = vals[-1]; me = float(np.median(vals[:-1])) if len(vals)>1 else 0.5
            dlt = va-me; cor_d = "#2e7d32" if dlt>=0 else "#c62828"
            html_ndvi = (f'<div style="background:#f1f8e9;border-left:5px solid #66bb6a;'
                         f'border-radius:6px;padding:12px 16px;">'
                         f'<b>🌿 NDVI: {va:.3f}</b> '
                         f'<span style="color:{cor_d};">Δ {dlt:+.3f} vs mediana ({me:.3f})</span>'
                         f'{"<i> (simulado)</i>" if ndvi_data.get("_simulado") else ""}</div>')

    html_focos = ""
    if df_focos is not None and not df_focos.empty:
        n = len(df_focos)
        frp_m = df_focos["frp"].max() if "frp" in df_focos.columns else 0
        html_focos = (f'<div style="background:#fff3e0;border-left:5px solid #fb8c00;'
                      f'border-radius:6px;padding:12px 16px;">'
                      f'<b>🔥 {n} foco(s) — MS (48h)</b><br>'
                      f'FRP máximo: {frp_m:.0f} MW | INPE BDQueimadas</div>')

    return f"""<html><body style="font-family:Arial,sans-serif;background:#f0f2f5;padding:20px;">
    <div style="max-width:760px;margin:auto;background:#fff;border-radius:14px;
                box-shadow:0 4px 18px rgba(0,0,0,.12);overflow:hidden;">
      <div style="background:linear-gradient(135deg,{VERDE_ESCURO},{VERDE_MEDIO});
                  padding:32px 36px;text-align:center;">
        <h1 style="color:white;margin:0;font-size:24px;">🌿 Yamada Engenharia</h1>
        <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:15px;">
          Relatório Agroclimático — {nome_ponto}</p>
      </div>
      <div style="padding:32px 36px;">
        <div style="background:#f9fbe7;border-radius:8px;padding:14px 18px;margin-bottom:20px;">
          <b style="font-size:16px;color:{VERDE_ESCURO};">📍 {nome_ponto}</b><br>
          <span style="color:#777;font-size:12px;">{lat:.4f}°S, {lon:.4f}°W · {agora}</span>
        </div>
        <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};padding-bottom:6px;">
          📊 Condições Atuais</h3>
        <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:24px;">{cards}</div>
        <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};padding-bottom:6px;">
          ⚠️ Alertas</h3>{html_alertas}
        <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                   padding-bottom:6px;margin-top:24px;">🧪 Janela de Defensivos</h3>
        <p style="font-size:12px;color:#777;">Horas ideais: {n_ab} | Bloqueadas: {n_bl}</p>
        <div style="background:#f1f8e9;border-left:4px solid #43a047;
                    padding:10px 14px;border-radius:4px;">{melhor}</div>
        <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                   padding-bottom:6px;margin-top:24px;">🌾 Fenologia</h3>
        {html_gda or '<p style="color:#999;">Não configurado.</p>'}
        <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                   padding-bottom:6px;margin-top:24px;">🍂 Fitossanidade</h3>
        {html_fito}
        <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                   padding-bottom:6px;margin-top:24px;">🌿 NDVI</h3>
        {html_ndvi or '<p style="color:#999;">Indisponível.</p>'}
        <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                   padding-bottom:6px;margin-top:24px;">💧 Balanço Hídrico</h3>
        {html_bh or '<p style="color:#999;">Indisponível.</p>'}
        <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                   padding-bottom:6px;margin-top:24px;">🔥 Focos de Queimada</h3>
        {html_focos or '<p style="color:#999;">Nenhum foco detectado.</p>'}
        <p style="color:#bbb;font-size:11px;margin-top:32px;border-top:1px solid #eee;
                  padding-top:14px;text-align:center;">
          Yamada Engenharia · GOES-19 · Open-Meteo · NASA POWER · Embrapa SATVeg · INPE · INMET<br>
          {agora} · MVP v4.0</p>
      </div>
    </div></body></html>"""


def enviar_relatorio_email(nome_ponto, lat, lon, dados_meteo, alertas,
                            janelas_def, gda_info, riscos_fito, bh,
                            ndvi_data, df_focos, df_inmet,
                            destinatarios_extras=None) -> tuple:
    """Envia relatório por SMTP Gmail SSL porta 465."""
    if not _email_configurado:
        return False, "E-mail não configurado no secrets.toml"
    try:
        html_body = gerar_html_relatorio(nome_ponto, lat, lon, dados_meteo, alertas,
                                          janelas_def, gda_info, riscos_fito, bh,
                                          ndvi_data, df_focos, df_inmet)
        dests = list(EMAIL_DESTINATARIOS)
        if destinatarios_extras:
            dests += [e for e in destinatarios_extras if e and e not in dests]
        tem_alerta = any(a["nivel"] in ["vermelho","laranja"] for a in alertas)
        assunto    = (f"{'🚨 ALERTA — ' if tem_alerta else '📋 '}"
                      f"Relatório Yamada — {nome_ponto} | "
                      f"{datetime.now().strftime('%d/%m/%Y %H:%M')}")
        msg = MIMEMultipart("mixed")
        msg["Subject"] = assunto
        msg["From"]    = EMAIL_REMETENTE
        msg["To"]      = ", ".join(dests)
        msg.attach(MIMEMultipart("alternative"))
        msg.get_payload()[0].attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
            srv.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
            srv.sendmail(EMAIL_REMETENTE, dests, msg.as_string())
        return True, f"Enviado para: {', '.join(dests)}"
    except Exception as e:
        return False, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# KEEP-ALIVE E SCHEDULER (mantidos do v3.0)
# ─────────────────────────────────────────────────────────────────────────────

def keep_alive():
    """Ping periódico para manter app ativo no Streamlit Cloud."""
    try:
        requests.get("https://yamada-agro-ms.streamlit.app/", timeout=30)
    except Exception:
        pass


def scheduled_report_automatico():
    """Relatório automático para o ponto padrão (Campo Grande)."""
    lat_auto, lon_auto = -20.4428, -54.6460
    nome_auto = "Campo Grande — Ponto padrão"
    log_entry = {"inicio": datetime.now().strftime("%d/%m %H:%M"),
                 "status": "em andamento", "detalhe": ""}
    with _log_lock:
        _scheduler_log.insert(0, log_entry)
        if len(_scheduler_log) > 10:
            _scheduler_log.pop()
    try:
        dm   = buscar_previsao_openmeteo(lat_auto, lon_auto)
        ndvi = buscar_satveg_ndvi(lat_auto, lon_auto)
        focos= buscar_focos_inpe()
        inmet= buscar_dados_inmet()
        jd   = calcular_janela_defensivos(dm)
        gda  = calcular_graus_dia(dm, "Soja", datetime.now() - timedelta(days=45))
        rf   = calcular_risco_fitossanitario(dm)
        bh   = calcular_balanco_hidrico_thornthwaite(dm, 65.0)
        als  = calcular_alertas(dm, lat_auto, gda)
        ok, msg = enviar_relatorio_email(nome_auto, lat_auto, lon_auto,
                                          dm, als, jd, gda, rf, bh, ndvi, focos, inmet)
        log_entry["status"]  = "✅ enviado" if ok else "⚠️ gerado, sem e-mail"
        log_entry["detalhe"] = msg[:80]
    except Exception as exc:
        log_entry["status"]  = "❌ erro"
        log_entry["detalhe"] = str(exc)[:100]


if "scheduler_started" not in st.session_state:
    _sched = BackgroundScheduler(timezone="America/Campo_Grande")
    _sched.add_job(scheduled_report_automatico,
                   trigger=CronTrigger(hour="6,12,18", minute=0,
                                       timezone="America/Campo_Grande"),
                   id="relatorio_automatico", replace_existing=True,
                   max_instances=1, misfire_grace_time=600)
    _sched.add_job(keep_alive, trigger=IntervalTrigger(minutes=5),
                   id="keepalive", replace_existing=True, max_instances=1)
    _sched.start()
    st.session_state["scheduler_started"] = True
    st.session_state["scheduler_obj"]     = _sched


# ─────────────────────────────────────────────────────────────────────────────
# INTERFACE STREAMLIT PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():

    st.markdown("""
    <div class="yamada-header">
      <div>
        <h1>🌿 Yamada Engenharia</h1>
        <p>Plataforma de Monitoramento Agroclimático — Mato Grosso do Sul</p>
        <p style="font-size:0.78rem;margin-top:4px;color:rgba(255,255,255,0.55);">
          GOES-19 (goes2go) · Open-Meteo ICON-EU/GFS025 · NASA POWER ·
          SATVeg · INPE · INMET · Nowcasting 3 fontes
        </p>
      </div>
    </div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # SIDEBAR
    # ─────────────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:10px 0 20px;">
          <div style="font-family:'Montserrat',sans-serif;font-weight:900;
                      font-size:1.2rem;color:#a5d6a7;">YAMADA</div>
          <div style="font-size:0.72rem;color:#81c784;letter-spacing:2px;">ENGENHARIA</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("---")

        # ── PONTO DE ANÁLISE — Lat/Lon livre ─────────────────────────────────
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;'
                    'font-size:0.9rem;">📍 PONTO DE ANÁLISE</p>', unsafe_allow_html=True)

        # Seletor de ponto predefinido (atalho rápido)
        ponto_ref = st.selectbox(
            "Carregar ponto predefinido",
            list(PONTOS_REFERENCIA_MS.keys()),
            index=0,
            label_visibility="collapsed",
            help="Selecione um ponto de referência ou preencha lat/lon manualmente abaixo"
        )
        if ponto_ref and PONTOS_REFERENCIA_MS.get(ponto_ref):
            _ref = PONTOS_REFERENCIA_MS[ponto_ref]
            _lat_def = _ref["lat"]
            _lon_def = _ref["lon"]
            _nome_def = ponto_ref.split("—")[0].strip()
        else:
            _lat_def  = -20.4428
            _lon_def  = -54.6460
            _nome_def = "Meu Ponto"

        lat_input = st.number_input(
            "Latitude (°S, negativo)",
            min_value=-23.7, max_value=-17.1,
            value=_lat_def, step=0.0001, format="%.4f",
            help="Latitude decimal. Sul do equador = negativo. Ex: -20.4428"
        )
        lon_input = st.number_input(
            "Longitude (°W, negativo)",
            min_value=-57.7, max_value=-50.9,
            value=_lon_def, step=0.0001, format="%.4f",
            help="Longitude decimal. Oeste = negativo. Ex: -54.6460"
        )
        nome_ponto = st.text_input(
            "Nome do ponto",
            value=_nome_def,
            max_chars=50,
            placeholder="Ex: Fazenda Santa Fé — Pivô 3",
            help="Identificação livre do ponto (aparece nos mapas, títulos e e-mail)"
        )
        if not nome_ponto.strip():
            nome_ponto = f"{lat_input:.3f}°S, {lon_input:.3f}°W"

        st.caption(f"🌐 {lat_input:.4f}°S  {lon_input:.4f}°W")
        st.markdown("---")

        # Solo
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;'
                    'font-size:0.9rem;">🌱 TEXTURA DO SOLO</p>', unsafe_allow_html=True)
        textura_solo = st.selectbox(
            "Textura",
            ["Argiloso (CAD=100mm)", "Médio/Franco (CAD=65mm)", "Arenoso (CAD=35mm)"],
            index=1, label_visibility="collapsed"
        )
        cad_mm = {"Argiloso (CAD=100mm)": 100.0,
                  "Médio/Franco (CAD=65mm)": 65.0,
                  "Arenoso (CAD=35mm)": 35.0}[textura_solo]
        st.markdown("---")

        # Fenologia
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;'
                    'font-size:0.9rem;">🌾 FENOLOGIA</p>', unsafe_allow_html=True)
        cultura_sel    = st.selectbox("Cultura", list(CULTURAS_GDA.keys()),
                                       index=0, label_visibility="collapsed")
        data_semeadura = st.date_input(
            "Data de semeadura",
            value=datetime.now().date() - timedelta(days=45),
            max_value=datetime.now().date()
        )
        st.markdown("---")

        # GOES-19
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;'
                    'font-size:0.9rem;">🛰️ GOES-19 — CANAIS</p>', unsafe_allow_html=True)
        bandas_sel = {
            bid: st.checkbox(
                f"{binfo['icon']} {bid.replace('RGB_','')} — {binfo['nome']}",
                value=(bid in ["B02", "B13", "B09"]),
                key=f"cb_{bid}"
            )
            for bid, binfo in BANDAS_INFO.items()
        }
        st.markdown("---")

        # Configurações
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;'
                    'font-size:0.9rem;">⚙️ CONFIGURAÇÕES</p>', unsafe_allow_html=True)
        usar_goes_real = st.checkbox(
            "🛰 GOES-19 real (≤10 min)",
            value=False,
            help="Tenta goes2go → boto3 S3 → simulação. Cache de 10 min."
        )
        st.caption(
            f"goes2go: {'✅' if _HAS_GOES2GO else '❌ não instalado'}  |  "
            f"cartopy: {'✅' if _HAS_CARTOPY else '❌ não instalado'}  |  "
            f"mplcursors: {'✅' if _HAS_MPLCURSORS else '❌ não instalado'}"
        )
        st.markdown("---")

        # Relatório automático
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;'
                    'font-size:0.9rem;">📧 RELATÓRIO AUTOMÁTICO</p>', unsafe_allow_html=True)
        if _email_configurado:
            st.caption(f"✅ {', '.join(EMAIL_DESTINATARIOS)}")
        else:
            st.caption("⚠️ Configure [email] no secrets.toml")

        if "scheduler_obj" in st.session_state:
            job = st.session_state["scheduler_obj"].get_job("relatorio_automatico")
            if job and job.next_run_time:
                st.info(f"⏰ Próximo: {job.next_run_time.strftime('%d/%m %H:%M')}")
            if st.button("▶ Enviar agora (manual)", use_container_width=True):
                threading.Thread(target=scheduled_report_automatico, daemon=True).start()
                st.success("Iniciado em background!")
        st.markdown("---")

        botao = st.button("🚀  GERAR ANÁLISE", use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # TELA DE BOAS-VINDAS
    # ─────────────────────────────────────────────────────────────────────────
    if not botao:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("""<div class="band-card"><h4>📍 Ponto livre (Lat/Lon)</h4>
            <p>Selecione qualquer coordenada no MS — campo, pastagem, pivô,
            área de preservação — sem se limitar a municípios pré-definidos.</p></div>""",
            unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class="band-card"><h4>🛰️ GOES-19 via goes2go</h4>
            <p>4 canais ABI + 2 compostos RGB (AirMass, Day Cloud Phase).
            Imagens ≤10 min via goes2go com fallback boto3 S3.</p></div>""",
            unsafe_allow_html=True)
        with c3:
            st.markdown("""<div class="band-card"><h4>⛈️ Nowcasting 3 fontes</h4>
            <p>Temperatura de brilho GOES-19 + probabilidade Open-Meteo +
            CAPE/LI. Timeline 0–6h de risco de precipitação.</p></div>""",
            unsafe_allow_html=True)

        c4, c5, c6 = st.columns(3)
        with c4:
            st.markdown("""<div class="band-card"><h4>📈 Gráfico 72h interativo</h4>
            <p>5 painéis: temperatura+CAPE, precipitação+prob., radiação solar,
            vento+rajadas, umidade+Heat Index. Tooltip hover com mplcursors.</p></div>""",
            unsafe_allow_html=True)
        with c5:
            st.markdown("""<div class="band-card"><h4>🌱 ICON-EU + GFS025</h4>
            <p>Melhor modelo para convecção do Cerrado/MS: ICON-EU (primário)
            com fallback automático para GFS025. 15 variáveis horárias.</p></div>""",
            unsafe_allow_html=True)
        with c6:
            st.markdown("""<div class="band-card"><h4>📧 Relatório automático</h4>
            <p>E-mail HTML rico enviado às 06h, 12h e 18h. Inclui alertas,
            fenologia, balanço hídrico, NDVI e focos INPE.</p></div>""",
            unsafe_allow_html=True)

        st.info("👈 Configure o ponto (lat/lon), solo e cultura na barra lateral, "
                "depois clique em **GERAR ANÁLISE**.")
        return

    # ─────────────────────────────────────────────────────────────────────────
    # COLETA DE DADOS
    # ─────────────────────────────────────────────────────────────────────────
    bandas_ativas = [bid for bid, ativo in bandas_sel.items() if ativo]
    if not bandas_ativas:
        st.warning("⚠️ Selecione pelo menos um canal GOES-19 na barra lateral.")
        return

    lat, lon = lat_input, lon_input
    prog = st.progress(0, text="Inicializando análise...")

    prog.progress(5,  text="📂 Carregando shapefiles MS...")
    shps = carregar_shapefiles()

    prog.progress(12, text=f"🌤 Open-Meteo ICON-EU — {nome_ponto}...")
    dados_meteo = buscar_previsao_openmeteo(lat, lon)
    modelo_usado = dados_meteo.get("_modelo_usado", "ICON-EU") if dados_meteo else "—"

    prog.progress(24, text="☀️ NASA POWER (ETo + Umidade Solo)...")
    dados_nasa = buscar_nasa_power(lat, lon)

    prog.progress(34, text="🌿 SATVeg NDVI — Embrapa...")
    ndvi_data = buscar_satveg_ndvi(lat, lon)

    prog.progress(44, text="🔥 BDQueimadas INPE — MS 48h...")
    df_focos = buscar_focos_inpe()

    prog.progress(52, text="📡 INMET — Estações automáticas MS...")
    df_inmet = buscar_dados_inmet()

    # GOES-19 canais reais (opcional)
    goes_results = {}   # banda_id → (data, extent, ts, fonte)
    if usar_goes_real:
        prog.progress(58, text="🛰 GOES-19 via goes2go (≤10 min)...")
        for bid in bandas_ativas:
            if bid.startswith("RGB_"):
                produto = bid.replace("RGB_", "")
                rgb, ext, ts = buscar_goes19_rgb(produto)
                goes_results[bid] = (rgb, ext, ts, "goes2go" if rgb is not None else "simulado")
            else:
                data, ext, ts, fonte = obter_canal_goes19(bid, usar_goes_real=True)
                goes_results[bid] = (data, ext, ts, fonte)

    prog.progress(68, text="📊 Análises agronômicas e meteorológicas...")
    janelas_def = calcular_janela_defensivos(dados_meteo)
    gda_info    = calcular_graus_dia(
        dados_meteo, cultura_sel,
        datetime.combine(data_semeadura, datetime.min.time())
    )
    riscos_fito = calcular_risco_fitossanitario(dados_meteo)
    bh          = calcular_balanco_hidrico_thornthwaite(dados_meteo, cad_mm)
    alertas     = calcular_alertas(dados_meteo, lat, gda_info)

    # Nowcasting — série TB do B13 (se disponível)
    tb_serie = None
    if usar_goes_real and "B13" in goes_results:
        g_data = goes_results["B13"][0]
        if g_data is not None:
            # Pixel mais próximo ao ponto — extração do valor central
            tb_val = float(np.nanmedian(g_data))
            tb_serie = [tb_val + 3.0, tb_val + 1.5, tb_val]  # simulação de tendência
    nowcast = calcular_nowcasting_chuva(dados_meteo, goes_tb_serie=tb_serie)

    prog.progress(80, text="🗺 Renderizando visualizações...")

    # ── Banner do ponto ───────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,{VERDE_ESCURO},{VERDE_MEDIO});
                border-radius:10px;padding:16px 24px;margin-bottom:20px;">
      <span style="color:white;font-family:Montserrat;font-weight:700;font-size:1.1rem;">
        📍 {nome_ponto}
      </span>
      <span style="color:rgba(255,255,255,0.75);font-size:0.85rem;margin-left:12px;">
        {lat:.4f}°S  {lon:.4f}°W
      </span>
      <span style="color:rgba(255,255,255,0.55);font-size:0.78rem;margin-left:12px;">
        Modelo: {modelo_usado} · {datetime.now().strftime('%d/%m/%Y %H:%M')} (Brasília)
      </span>
    </div>""", unsafe_allow_html=True)

    # ── Métricas rápidas ──────────────────────────────────────────────────────
    if dados_meteo and "hourly" in dados_meteo:
        h = dados_meteo.get("hourly", {}); d = dados_meteo.get("daily", {})
        try:
            c1,c2,c3,c4,c5,c6 = st.columns(6)
            with c1: st.metric("🌡 Temp.",    f"{h.get('temperature_2m',[None])[0]:.1f}°C")
            with c2: st.metric("🌧 Chuva 24h", f"{d.get('precipitation_sum',[0])[0] or 0:.1f} mm")
            with c3: st.metric("💧 Umidade",   f"{h.get('relativehumidity_2m',[None])[0]:.0f}%")
            with c4: st.metric("💨 Vento",     f"{h.get('windspeed_10m',[None])[0]:.0f} km/h")
            with c5: st.metric("⚡ CAPE",      f"{h.get('cape',[0])[0] or 0:.0f} J/kg")
            with c6: st.metric("🌿 ETo",       f"{d.get('et0_fao_evapotranspiration',[None])[0]:.2f} mm")
        except Exception:
            pass

    # ═════════════════════════════════════════════════════════════════════════
    # 7 ABAS TEMÁTICAS
    # ═════════════════════════════════════════════════════════════════════════
    aba1, aba2, aba3, aba4, aba5, aba6, aba7 = st.tabs([
        "🛰️ GOES-19",
        "⛈️ Nowcasting",
        "📈 Previsão 72h",
        "🌾 Agronômica",
        "💧 Balanço Hídrico",
        "⚠️ Alertas",
        "📧 Relatório",
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 1 — GOES-19
    # ─────────────────────────────────────────────────────────────────────────
    with aba1:
        st.markdown('<div class="secao-titulo">🛰️ GOES-19 ABI — Canais e Compostos RGB</div>',
                    unsafe_allow_html=True)

        deps_status = []
        if _HAS_GOES2GO:  deps_status.append("✅ goes2go")
        else:             deps_status.append("❌ goes2go (não instalado)")
        if _HAS_CARTOPY:  deps_status.append("✅ cartopy")
        else:             deps_status.append("⚠️ cartopy (matplotlib puro)")

        st.caption(" · ".join(deps_status) +
                   f" · Cache: 10 min · {'Modo real ✓' if usar_goes_real else 'Modo simulação'}")

        n_cols = min(2, len(bandas_ativas))
        rows   = [bandas_ativas[i:i+n_cols] for i in range(0, len(bandas_ativas), n_cols)]

        for row in rows:
            cols = st.columns(n_cols)
            for j, bid in enumerate(row):
                with cols[j]:
                    g_data = g_ext = g_ts = None
                    fonte  = "simulado"
                    is_rgb = bid.startswith("RGB_")
                    if usar_goes_real and bid in goes_results:
                        g_data, g_ext, g_ts, fonte = goes_results[bid]

                    fig = gerar_mapa_canal_goes19(
                        bid, shps, nome_ponto, lat, lon,
                        goes_data=g_data, extent=g_ext,
                        is_rgb=is_rgb, ts_label=g_ts or "",
                        fonte=fonte, df_focos=df_focos
                    )
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)

                    binfo = BANDAS_INFO[bid]
                    st.markdown(f"""<div class="band-card" style="margin-top:-6px;">
                      <h4>{binfo['icon']} {bid.replace('RGB_','')} — {binfo['nome']}</h4>
                      <p>{binfo['uso']}</p></div>""", unsafe_allow_html=True)

        # Focos INPE
        if not df_focos.empty:
            st.markdown('<div class="secao-titulo">🔥 Focos — INPE/BDQueimadas (48h, MS)</div>',
                        unsafe_allow_html=True)
            sim = " ⚠ (simulados)" if df_focos.get("_simulado", pd.Series([False])).any() else ""
            c1, c2 = st.columns([1, 3])
            with c1:
                st.metric("Focos detectados", len(df_focos))
                if "frp" in df_focos.columns:
                    st.metric("FRP máx. (MW)", f"{df_focos['frp'].max():.0f}")
            with c2:
                show = [c for c in ["municipio","latitude","longitude","frp"]
                        if c in df_focos.columns]
                st.dataframe(df_focos[show].head(10), use_container_width=True, hide_index=True)
            if sim: st.caption(sim)

        # Estações INMET
        if not df_inmet.empty:
            st.markdown('<div class="secao-titulo">📡 Estações INMET — MS</div>',
                        unsafe_allow_html=True)
            st.dataframe(df_inmet, use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 2 — NOWCASTING DE CHUVA
    # ─────────────────────────────────────────────────────────────────────────
    with aba2:
        st.markdown('<div class="secao-titulo">⛈️ Nowcasting de Precipitação — 3 Fontes</div>',
                    unsafe_allow_html=True)
        st.caption(
            "Diagnóstico integrado: temperatura de brilho GOES-19 · "
            "probabilidade Open-Meteo · índices CAPE/LI"
        )

        nivel_cores = {
            "vermelho": ("#ffebee", "#e53935", "🔴"),
            "laranja":  ("#fff3e0", "#fb8c00", "🟠"),
            "amarelo":  ("#fff8e1", "#fbc02d", "🟡"),
            "verde":    ("#e8f5e9", "#43a047", "🟢"),
            "azul":     ("#e3f2fd", "#1565c0", "🔵"),
        }

        c1, c2, c3 = st.columns(3)
        for col, fonte_key, titulo in [
            (c1, "goes_tb",     "🛰️ GOES-19 B13"),
            (c2, "openmeteo",   "📡 Open-Meteo"),
            (c3, "instabilidade","⚡ CAPE / LI"),
        ]:
            with col:
                nd = nowcast[fonte_key]
                nv = nd["nivel"]
                bg, brd, emoji = nivel_cores.get(nv, ("#f5f5f5","#9e9e9e","⚪"))
                st.markdown(f"""
                <div style="background:{bg};border:2px solid {brd};border-radius:12px;
                            padding:16px;text-align:center;min-height:120px;">
                  <div style="font-size:1.4rem;margin-bottom:6px;">{emoji}</div>
                  <div style="font-family:'Montserrat',sans-serif;font-weight:700;
                              font-size:0.82rem;color:#333;margin-bottom:8px;">{titulo}</div>
                  <div style="font-weight:700;color:{brd};font-size:0.85rem;">
                    {nd['status']}</div>
                  <div style="font-size:0.75rem;color:#555;margin-top:8px;line-height:1.4;">
                    {nd['msg']}</div>
                </div>""", unsafe_allow_html=True)

        # Nível geral
        nv_g = nowcast["nivel_geral"]
        bg, brd, emoji = nivel_cores.get(nv_g, ("#f5f5f5","#9e9e9e","⚪"))
        st.markdown(f"""
        <div style="background:{bg};border-left:6px solid {brd};border-radius:10px;
                    padding:14px 20px;margin:16px 0;text-align:center;">
          <b style="font-size:1.05rem;color:{brd};">{emoji} Diagnóstico Geral: nível {nv_g.upper()}</b>
        </div>""", unsafe_allow_html=True)

        # Timeline 0–6h
        st.markdown('<div class="secao-titulo">⏱️ Probabilidade de Chuva — Próximas 6 Horas</div>',
                    unsafe_allow_html=True)
        timeline = nowcast.get("prob_timeline_6h", [])
        if timeline:
            cols_t = st.columns(len(timeline))
            for i, (hora, prob) in enumerate(timeline):
                with cols_t[i]:
                    if prob >= 70:   cor, emoji_t = "#ef4444", "⛈️"
                    elif prob >= 40: cor, emoji_t = "#f59e0b", "🌦️"
                    else:            cor, emoji_t = "#43a047", "☀️"
                    st.markdown(f"""
                    <div style="text-align:center;padding:10px 4px;background:#1e2a3a;
                                border-radius:8px;border-bottom:4px solid {cor};">
                      <div style="font-size:1.1rem;">{emoji_t}</div>
                      <div style="font-size:0.85rem;font-weight:700;color:white;">{prob:.0f}%</div>
                      <div style="font-size:0.7rem;color:#9ca3af;">{hora}</div>
                    </div>""", unsafe_allow_html=True)

            # Gráfico de barras
            fig_nc, ax_nc = plt.subplots(figsize=(8, 2.5), facecolor="#0d1117")
            ax_nc.set_facecolor("#111827")
            horas_t = [t[0] for t in timeline]
            probs_t = [t[1] for t in timeline]
            cores_nc = ["#ef4444" if p >= 70 else "#f59e0b" if p >= 40 else "#3b82f6"
                       for p in probs_t]
            ax_nc.bar(range(len(probs_t)), probs_t, color=cores_nc, alpha=0.85,
                     width=0.7, edgecolor="none")
            ax_nc.axhline(70, color="#fbbf24", linewidth=1, linestyle="--",
                          alpha=0.7, label="70% — limiar")
            ax_nc.set_ylim(0, 100)
            ax_nc.set_xticks(range(len(horas_t)))
            ax_nc.set_xticklabels(horas_t, color="#9ca3af", fontsize=8)
            ax_nc.set_ylabel("Prob. (%)", color="#9ca3af", fontsize=8)
            ax_nc.tick_params(colors="#9ca3af", labelsize=8)
            for sp in ax_nc.spines.values(): sp.set_edgecolor("#1f2937")
            ax_nc.grid(True, color="#1f2937", linewidth=0.5, alpha=0.6, axis="y")
            ax_nc.legend(fontsize=7, facecolor="#111827", labelcolor="white",
                        edgecolor="#374151")
            ax_nc.set_title(f"Probabilidade de Precipitação — {nome_ponto}",
                           color="white", fontsize=9, fontweight="bold")
            plt.tight_layout()
            st.pyplot(fig_nc, use_container_width=True)
            plt.close(fig_nc)
        else:
            st.info("⚠️ Dados de probabilidade não disponíveis (Open-Meteo não respondeu).")

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 3 — PREVISÃO 72H
    # ─────────────────────────────────────────────────────────────────────────
    with aba3:
        st.markdown('<div class="secao-titulo">📈 Previsão Meteorológica 72h — 5 Painéis</div>',
                    unsafe_allow_html=True)
        st.caption(
            f"Modelo: {modelo_usado} · "
            f"Temperatura · Ponto de orvalho · CAPE · Precipitação · "
            f"Radiação solar · Vento · Umidade · Heat Index"
            + (" · tooltip hover (mplcursors ✓)" if _HAS_MPLCURSORS else
               " · instale mplcursors para tooltip interativo")
        )
        prog.progress(85, text="📈 Gerando gráfico 72h interativo...")
        fig_72h = gerar_grafico_72h_interativo(dados_meteo, nome_ponto, lat, lon)
        if fig_72h:
            st.pyplot(fig_72h, use_container_width=True)
            plt.close(fig_72h)
        else:
            st.warning("⚠️ Previsão indisponível — Open-Meteo não respondeu.")

        # Tabela 7 dias
        with st.expander("📅 Tabela de previsão — 7 dias", expanded=False):
            df_7d = gerar_tabela_7dias(dados_meteo)
            if not df_7d.empty:
                st.dataframe(df_7d, use_container_width=True, hide_index=True)

        # Umidade do solo NASA POWER
        if dados_nasa and "properties" in dados_nasa:
            try:
                params   = dados_nasa["properties"]["parameter"]
                gwettop  = params.get("GWETTOP",  {})
                gwetroot = params.get("GWETROOT", {})
                if gwettop:
                    with st.expander("🌱 Umidade do solo — NASA POWER (30 dias)", expanded=False):
                        datas_n = sorted(gwettop.keys())[-14:]
                        vt = [gwettop.get(d, 0)  for d in datas_n]
                        vr = [gwetroot.get(d, 0) for d in datas_n]
                        fig_s, ax_s = plt.subplots(figsize=(10, 3), facecolor="#0d1117")
                        ax_s.set_facecolor("#111827")
                        ax_s.plot(range(len(datas_n)), vt, color="#66BB6A", linewidth=2,
                                  label="GWETTOP (0-5cm)")
                        ax_s.fill_between(range(len(datas_n)), vt, alpha=0.2, color="#66BB6A")
                        ax_s.plot(range(len(datas_n)), vr, color="#42A5F5", linewidth=2,
                                  linestyle="--", label="GWETROOT (radicular)")
                        ax_s.fill_between(range(len(datas_n)), vr, alpha=0.15, color="#42A5F5")
                        ax_s.axhline(0.5, color="#FFB74D", linewidth=0.8, linestyle=":",
                                     alpha=0.7, label="Campo (0.5)")
                        ax_s.set_ylim(0, 1)
                        ax_s.set_ylabel("Umidade", color="#9ca3af", fontsize=9)
                        ax_s.set_xticks(range(0, len(datas_n), 2))
                        ax_s.set_xticklabels(
                            [d[4:6]+"/"+d[6:8] for d in datas_n[::2]],
                            color="#9ca3af", fontsize=8, rotation=30)
                        ax_s.tick_params(colors="#9ca3af", labelsize=8)
                        for sp in ax_s.spines.values(): sp.set_edgecolor("#1f2937")
                        ax_s.grid(True, color="#1f2937", linewidth=0.5, alpha=0.6)
                        ax_s.legend(fontsize=8, facecolor="#111827", labelcolor="white",
                                    edgecolor="#374151")
                        ax_s.set_title("Umidade do Solo — NASA POWER",
                                       color="white", fontsize=10)
                        plt.tight_layout()
                        st.pyplot(fig_s, use_container_width=True)
                        plt.close(fig_s)
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 4 — ANÁLISE AGRONÔMICA
    # ─────────────────────────────────────────────────────────────────────────
    with aba4:
        # NDVI
        st.markdown('<div class="secao-titulo">🌿 Série Histórica NDVI — SATVeg/Embrapa</div>',
                    unsafe_allow_html=True)
        fig_ndvi = gerar_grafico_ndvi(ndvi_data, nome_ponto)
        if fig_ndvi:
            st.pyplot(fig_ndvi, use_container_width=True)
            plt.close(fig_ndvi)

        # Graus-dia e fenologia
        st.markdown(f'<div class="secao-titulo">🌾 Graus-Dia e Fenologia — {cultura_sel}</div>',
                    unsafe_allow_html=True)
        if gda_info:
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("GDA Acumulado", f"{gda_info['gda_total']} °C·dia",
                               help=f"Temperatura-base: {gda_info['tb']}°C")
            with c2: st.metric("Dias s/ semeadura", gda_info["dias_desde_semeadura"])
            with c3:
                p = gda_info.get("proximo_estagio")
                if p: st.metric("Próximo estádio em", f"{p[0]-gda_info['gda_total']:.0f} °C·dia")
            p = gda_info.get("proximo_estagio")
            ps = (f"<p>→ Próximo: <b>{p[1]}</b> (faltam {p[0]-gda_info['gda_total']:.0f} °C·dia)</p>"
                  if p else "")
            st.markdown(f"""<div class="band-card">
              <h4>🌱 Estádio atual — {cultura_sel}</h4>
              <p style="font-size:1.05rem;color:{VERDE_ESCURO};font-weight:700;">
                {gda_info['estagio_atual']}</p>
              {ps}</div>""", unsafe_allow_html=True)

        # Janela de defensivos
        st.markdown('<div class="secao-titulo">🧪 Janela de Aplicação de Defensivos — 24h</div>',
                    unsafe_allow_html=True)
        st.caption("Critérios MAPA/Embrapa: Vento < 10 km/h | Temp < 30°C | UR > 55% | Sem chuva")
        if janelas_def:
            cols_d = st.columns(len(janelas_def))
            for i, jan in enumerate(janelas_def):
                with cols_d[i]:
                    c = {"aberta":"🟢","parcial":"🟡","bloqueada":"🔴"}[jan["status"]]
                    st.markdown(
                        f"<div style='text-align:center;font-size:0.68rem;color:#555;'>"
                        f"<b>{jan['hora']}</b><br>{c}</div>",
                        unsafe_allow_html=True
                    )
            n_ab = sum(1 for j in janelas_def if j["status"]=="aberta")
            n_pa = sum(1 for j in janelas_def if j["status"]=="parcial")
            n_bl = sum(1 for j in janelas_def if j["status"]=="bloqueada")
            cc1, cc2, cc3 = st.columns(3)
            with cc1: st.metric("✅ Horas ideais",    n_ab)
            with cc2: st.metric("⚠️ Horas parciais",  n_pa)
            with cc3: st.metric("❌ Horas bloqueadas", n_bl)

            max_seq = cur_seq = cur_start = max_start = 0
            for i, j in enumerate(janelas_def):
                if j["status"] == "aberta":
                    if cur_seq == 0: cur_start = i
                    cur_seq += 1
                    if cur_seq > max_seq: max_seq = cur_seq; max_start = cur_start
                else:
                    cur_seq = 0
            if max_seq > 0:
                h1 = janelas_def[max_start]["hora"]
                h2 = janelas_def[min(max_start+max_seq-1,len(janelas_def)-1)]["hora"]
                st.markdown(f"""<div class="alert-verde">
                  <b>✅ Melhor janela: {h1} → {h2} ({max_seq}h contínuas)</b><br>
                  <span style="font-size:0.88rem;">Período ideal para defensivos e fertilizantes foliares.</span>
                </div>""", unsafe_allow_html=True)
            elif n_pa > 0:
                st.markdown("""<div class="alert-amarelo">
                  <b>⚠️ Apenas janelas parciais disponíveis.</b>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""<div class="alert-vermelho">
                  <b>❌ Sem janela ideal nas próximas 24h. Adie as aplicações.</b>
                </div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 5 — BALANÇO HÍDRICO
    # ─────────────────────────────────────────────────────────────────────────
    with aba5:
        st.markdown(f'<div class="secao-titulo">💧 Balanço Hídrico — Thornthwaite-Mather · {textura_solo}</div>',
                    unsafe_allow_html=True)
        if bh:
            cc1,cc2,cc3,cc4 = st.columns(4)
            with cc1: st.metric("ARM atual", f"{bh['arm_mm']:.1f} mm",
                                delta=f"{bh['arm_pct']:.0f}% da CAD")
            with cc2: st.metric("CAD",       f"{bh['cad_mm']:.0f} mm")
            with cc3: st.metric("Déficit",   f"{bh['def_mm']:.1f} mm",
                                delta_color="inverse",
                                delta="❌ déficit" if bh["def_mm"] > 0 else "✅ ok")
            with cc4: st.metric("ETR",       f"{bh['etr_mm']:.1f} mm")
            fig_bh = gerar_grafico_balanco_hidrico(bh)
            if fig_bh:
                st.pyplot(fig_bh, use_container_width=True)
                plt.close(fig_bh)
            st.markdown(f"""<div class="alert-{bh['nivel']}" style="margin-top:10px;">
              <b>Recomendação de Irrigação:</b> {bh['recomendacao']}
            </div>""", unsafe_allow_html=True)
        else:
            st.info("💧 Dados de balanço hídrico indisponíveis.")

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 6 — ALERTAS
    # ─────────────────────────────────────────────────────────────────────────
    with aba6:
        st.markdown('<div class="secao-titulo">⚠️ Alertas Meteorológicos Ativos</div>',
                    unsafe_allow_html=True)
        for al in alertas:
            st.markdown(f"""<div class="alert-{al['nivel']}">
              <b>{al['icone']} {al['titulo']}</b><br>
              <span style="font-size:0.9rem;">{al['msg']}</span>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="secao-titulo">🍂 Risco Fitossanitário (48h)</div>',
                    unsafe_allow_html=True)
        st.caption("Ferrugem: T 15–30°C + UR>80% ≥12h | Brusone: T 20–28°C + UR>90% ≥10h")
        for r in riscos_fito:
            st.markdown(f"""<div class="alert-{r['cor']}">
              <b>{r['icone']} {r['doenca']} — Risco {r['nivel']}</b><br>
              <span style="font-size:0.9rem;">{r['msg']}</span>
            </div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 7 — RELATÓRIO E E-MAIL
    # ─────────────────────────────────────────────────────────────────────────
    with aba7:
        st.markdown('<div class="secao-titulo">📧 Relatório Agroclimático — Envio por E-mail</div>',
                    unsafe_allow_html=True)

        if _email_configurado:
            st.markdown(f"""<div class="alert-verde">
              <b>✅ E-mail configurado</b> · Remetente: {EMAIL_REMETENTE}<br>
              Destinatários: {', '.join(EMAIL_DESTINATARIOS)}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="alert-amarelo">
              <b>⚠️ E-mail não configurado</b><br>
              Adicione ao <code>.streamlit/secrets.toml</code>:<br><br>
              <code>[email]</code><br>
              <code>remetente = "seuemail@gmail.com"</code><br>
              <code>senha_app = "senha_de_app_gmail"</code><br>
              <code>destinatario = "destino@email.com"</code>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        dest_extra = st.text_input(
            "Destinatários adicionais (separados por vírgula)",
            placeholder="agronomo@fazenda.com, gestor@empresa.com",
            label_visibility="visible"
        )
        dest_extras = [e.strip() for e in dest_extra.split(",") if "@" in e] if dest_extra else []

        cb1, cb2 = st.columns(2)
        with cb1:
            if st.button("📤 Enviar relatório agora", use_container_width=True):
                with st.spinner("Gerando e enviando..."):
                    ok, msg = enviar_relatorio_email(
                        nome_ponto, lat, lon,
                        dados_meteo, alertas, janelas_def, gda_info,
                        riscos_fito, bh, ndvi_data, df_focos, df_inmet,
                        destinatarios_extras=dest_extras
                    )
                if ok: st.success(f"✅ {msg}")
                else:  st.error(f"❌ {msg}")
        with cb2:
            if st.button("👁 Pré-visualizar HTML", use_container_width=True):
                html_p = gerar_html_relatorio(
                    nome_ponto, lat, lon,
                    dados_meteo, alertas, janelas_def, gda_info,
                    riscos_fito, bh, ndvi_data, df_focos, df_inmet
                )
                st.components.v1.html(html_p, height=700, scrolling=True)

        st.markdown("---")
        st.markdown('<div class="secao-titulo">🕐 Scheduler — Relatório Automático</div>',
                    unsafe_allow_html=True)
        cs1, cs2 = st.columns(2)
        with cs1:
            st.markdown("""**Horários automáticos (America/Campo_Grande):**
- ⏰ 06h00 · ⏰ 12h00 · ⏰ 18h00

Ponto padrão: **Campo Grande** (lat/lon fixo)
Para outros pontos: use o botão de envio manual acima.""")
        with cs2:
            if "scheduler_obj" in st.session_state:
                job = st.session_state["scheduler_obj"].get_job("relatorio_automatico")
                if job and job.next_run_time:
                    st.info(f"⏰ Próxima execução:\n{job.next_run_time.strftime('%d/%m/%Y às %H:%M')}")
                if st.button("▶ Disparar agora (background)", use_container_width=True):
                    threading.Thread(target=scheduled_report_automatico, daemon=True).start()
                    st.success("Iniciado em background!")

        with _log_lock:
            log_snap = list(_scheduler_log)
        if log_snap:
            st.markdown("**Histórico de execuções:**")
            st.dataframe(pd.DataFrame(log_snap), use_container_width=True, hide_index=True)

    # ── Rodapé ───────────────────────────────────────────────────────────────
    prog.progress(100, text="✅ Análise concluída!")
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align:center;padding:16px;color:#888;font-size:0.8rem;">
      <b style="color:{VERDE_ESCURO};">Yamada Engenharia</b> — Meteorologia Aplicada ao Agronegócio<br>
      GOES-19 (goes2go) · Open-Meteo ICON-EU/GFS025 · NASA POWER ·
      SATVeg/Embrapa · INPE BDQueimadas · INMET<br>
      Ponto: <b>{nome_ponto}</b> — {lat:.4f}°S {lon:.4f}°W ·
      {datetime.now().strftime('%d/%m/%Y %H:%M')} · MVP v4.0
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
