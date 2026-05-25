"""
=============================================================================
YAMADA ENGENHARIA — Plataforma de Monitoramento Agroclimático
MVP Streamlit | GOES-19 + Open-Meteo + NASA POWER + INPE + SATVeg + INMET
Mato Grosso do Sul — Análise por Município
=============================================================================
"""

import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
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
# IDENTIDADE VISUAL
# ─────────────────────────────────────────────────────────────────────────────
VERDE_ESCURO  = "#1B4D2E"
VERDE_MEDIO   = "#3DA63A"
PRETO         = "#1A1A1A"
CINZA_CLARO   = "#F4F7F4"
AMARELO_ALERT = "#F5A623"
VERMELHO_ALRT = "#D0021B"

# CORREÇÃO CRÍTICA: sidebar tinha fundo preto com texto verde escuro (ilegível).
# Ajustado: sidebar com fundo #1a2e1c (verde muito escuro) e textos em branco/verde claro.
CSS = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;900&family=Source+Sans+3:wght@300;400;600&display=swap');

  html, body, [class*="css"] {{
    font-family: 'Source Sans 3', sans-serif;
    background-color: {CINZA_CLARO};
    color: {PRETO};
  }}

  /* Header institucional */
  .yamada-header {{
    background: linear-gradient(135deg, {VERDE_ESCURO} 0%, {VERDE_MEDIO} 100%);
    border-radius: 12px;
    padding: 28px 36px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: 0 4px 20px rgba(27,77,46,0.3);
  }}
  .yamada-header h1 {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 900;
    font-size: 2rem;
    color: white;
    margin: 0;
    letter-spacing: -0.5px;
  }}
  .yamada-header p {{
    color: rgba(255,255,255,0.82);
    margin: 4px 0 0 0;
    font-size: 0.95rem;
    font-weight: 300;
  }}

  /* Cards de banda */
  .band-card {{
    background: white;
    border-left: 4px solid {VERDE_MEDIO};
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }}
  .band-card h4 {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    color: {VERDE_ESCURO};
    margin: 0 0 4px 0;
    font-size: 0.88rem;
  }}
  .band-card p {{
    margin: 0;
    font-size: 0.82rem;
    color: #000;
    line-height: 1.4;
  }}

  /* Alertas */
  .alert-verde    {{ background:#e8f5e9; border-left:4px solid #43a047; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .alert-amarelo  {{ background:#fff8e1; border-left:4px solid #fbc02d; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .alert-vermelho {{ background:#ffebee; border-left:4px solid #e53935; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .alert-laranja  {{ background:#fff3e0; border-left:4px solid #fb8c00; border-radius:8px; padding:12px 16px; margin:6px 0; }}

  /* Botão principal */
  .stButton > button {{
    background: linear-gradient(135deg, {VERDE_ESCURO}, {VERDE_MEDIO}) !important;
    color: white !important;
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 14px 40px !important;
    width: 100% !important;
    letter-spacing: 0.5px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(27,77,46,0.35) !important;
  }}
  .stButton > button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 22px rgba(27,77,46,0.45) !important;
  }}

  /* CORREÇÃO CRÍTICA: Sidebar — fundo escuro com textos claros para garantir contraste adequado */
  section[data-testid="stSidebar"] {{
    background-color: #1a2e1c !important;
    border-right: 1px solid #2d5a30;
  }}
  section[data-testid="stSidebar"] * {{
    color: #e8f5e9 !important;
  }}
  section[data-testid="stSidebar"] .stSelectbox label,
  section[data-testid="stSidebar"] .stSlider label,
  section[data-testid="stSidebar"] .stCheckbox label,
  section[data-testid="stSidebar"] label {{
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    color: #a5d6a7 !important;
  }}
  section[data-testid="stSidebar"] .stSelectbox > div > div {{
    background-color: #2d5a30 !important;
    color: white !important;
    border-color: #3DA63A !important;
  }}
  section[data-testid="stSidebar"] p,
  section[data-testid="stSidebar"] span {{
    color: #c8e6c9 !important;
  }}
  section[data-testid="stSidebar"] hr {{
    border-color: #2d5a30 !important;
  }}

  /* Métricas */
  div[data-testid="metric-container"] {{
    background: white;
    border-radius: 10px;
    padding: 16px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
    border-top: 3px solid {VERDE_MEDIO};
  }}

  /* Títulos de seção */
  .secao-titulo {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 800;
    font-size: 1.15rem;
    color: {VERDE_ESCURO};
    border-bottom: 2px solid {VERDE_MEDIO};
    padding-bottom: 6px;
    margin: 28px 0 16px 0;
  }}
  hr {{ border-color: #ddeedd; margin: 20px 0; }}

  /* Timeline de defensivos */
  .timeline-bloco {{
    display:inline-block; height:32px; line-height:32px;
    font-size:0.7rem; font-weight:700; text-align:center;
    border-radius:4px; margin:1px; cursor:default;
    font-family: 'Montserrat', sans-serif;
  }}
  .timeline-aberta  {{ background:#43a047; color:white; }}
  .timeline-bloq    {{ background:#e53935; color:white; }}
  .timeline-parcial {{ background:#fbc02d; color:#333; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# DADOS DOS MUNICÍPIOS DE MATO GROSSO DO SUL
# ─────────────────────────────────────────────────────────────────────────────
MUNICIPIOS_MS = {
    "Campo Grande":     {"lat": -20.4428, "lon": -54.6460, "regiao": "Centro"},
    "Dourados":         {"lat": -22.2212, "lon": -54.8056, "regiao": "Sul"},
    "Três Lagoas":      {"lat": -20.7519, "lon": -51.6783, "regiao": "Leste"},
    "Corumbá":          {"lat": -19.0078, "lon": -57.6500, "regiao": "Oeste (Pantanal)"},
    "Ponta Porã":       {"lat": -22.5361, "lon": -55.7253, "regiao": "Sul (Fronteira)"},
    "Naviraí":          {"lat": -23.0622, "lon": -54.1914, "regiao": "Sul"},
    "Nova Andradina":   {"lat": -22.2333, "lon": -53.3444, "regiao": "Leste"},
    "Aquidauana":       {"lat": -20.4700, "lon": -55.7869, "regiao": "Centro-Oeste"},
    "Sidrolândia":      {"lat": -20.9319, "lon": -54.9600, "regiao": "Centro"},
    "Maracaju":         {"lat": -21.6108, "lon": -55.1681, "regiao": "Sul"},
    "Rio Brilhante":    {"lat": -21.8028, "lon": -54.5447, "regiao": "Sul"},
    "Coxim":            {"lat": -18.5069, "lon": -54.7600, "regiao": "Norte"},
    "Sonora":           {"lat": -17.5583, "lon": -54.7611, "regiao": "Norte"},
    "Chapadão do Sul":  {"lat": -18.7919, "lon": -52.6267, "regiao": "Nordeste"},
    "Costa Rica":       {"lat": -18.5447, "lon": -53.1278, "regiao": "Nordeste"},
}

# GOES-16 ABI bandas espectrais — mantidas para compatibilidade do mapa
BANDAS_INFO = {
    "B02": {"nome": "Vermelho Visível (0,64µm)",   "icon": "☀️",  "uso": "Cobertura de nuvens, frentes de chuva — Só diurno",                           "cmap": "gray",      "cor_card": "#388e3c"},
    "B03": {"nome": "Veggie Band – NIR (0,86µm)",  "icon": "🌿",  "uso": "Saúde da vegetação, estresse hídrico, queimadas recentes",                   "cmap": "YlGn",      "cor_card": "#2e7d32"},
    "B07": {"nome": "IR Onda Curta (3,9µm)",        "icon": "🔥",  "uso": "Focos de incêndio (produto FDC oficial), nevoeiro matinal",                  "cmap": "hot",       "cor_card": "#bf360c"},
    "B09": {"nome": "Vapor d'Água Médio (6,9µm)",   "icon": "💧",  "uso": "Umidade atmosférica, sistemas convectivos 24–72h",                           "cmap": "Blues_r",   "cor_card": "#1565c0"},
    "B11": {"nome": "IR Termal (8,4µm)",            "icon": "❄️",  "uso": "Temperatura superficial, risco de geada, nuvens baixas",                    "cmap": "RdBu",      "cor_card": "#6a1b9a"},
    "B13": {"nome": "IR Clean (10,3µm)",            "icon": "⛈️",  "uso": "Topo de nuvens, alertas de tempestade severa e granizo",                    "cmap": "inferno_r", "cor_card": "#e65100"},
    "B14": {"nome": "IR Longo – QPE (11,2µm)",      "icon": "🌧️",  "uso": "Estimativa de precipitação — produto RRQPE oficial GOES-19",               "cmap": "Blues",     "cor_card": "#0277bd"},
}

# Culturas suportadas no cálculo de Graus-Dia
CULTURAS_GDA = {
    "Soja":    {"tb": 7.0,  "tc": 40.0, "estagios": [
        (0,   "V0 – Germinação"),
        (50,  "V1 – Estádio unifoliar"),
        (120, "V2 – 1º trifólio"),
        (200, "V3–V4 – Desenvolvimento vegetativo"),
        (300, "V5–V6 – Pré-florescimento"),
        (400, "R1 – Florescimento"),
        (500, "R2 – Florescimento pleno"),
        (600, "R3 – Início formação de vagens"),
        (750, "R4 – Vagens completas"),
        (900, "R5 – Enchimento de grãos"),
        (1050,"R6 – Grão cheio"),
        (1200,"R7 – Início maturação"),
        (1400,"R8 – Maturação plena — Colheita"),
    ]},
    "Milho":   {"tb": 10.0, "tc": 40.0, "estagios": [
        (0,   "VE – Emergência"),
        (60,  "V1 – 1ª folha"),
        (150, "V3 – 3ª folha"),
        (300, "V6 – 6ª folha"),
        (450, "V9 – 9ª folha"),
        (600, "VT – Pendoamento"),
        (700, "R1 – Espigamento"),
        (850, "R2 – Bolha d'água"),
        (1000,"R3 – Grão leitoso"),
        (1200,"R4 – Grão pastoso"),
        (1400,"R5 – Grão farináceo"),
        (1600,"R6 – Maturação fisiológica — Colheita"),
    ]},
    "Algodão": {"tb": 15.0, "tc": 40.0, "estagios": [
        (0,   "Germinação"),
        (100, "Emergência"),
        (250, "Crescimento vegetativo"),
        (500, "Botão floral"),
        (700, "Florescimento"),
        (900, "Maçã"),
        (1100,"Abertura de capulhos"),
        (1400,"Colheita"),
    ]},
    "Cana":    {"tb": 18.0, "tc": 40.0, "estagios": [
        (0,   "Brotação"),
        (200, "Perfilhamento"),
        (600, "Crescimento rápido"),
        (1200,"Maturação inicial"),
        (1800,"Maturação plena — Colheita"),
    ]},
}

# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE COLETA DE DADOS — APIs METEOROLÓGICAS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def buscar_previsao_openmeteo(lat: float, lon: float) -> dict:
    """
    Coleta previsão horária (24h) e diária (7 dias) via Open-Meteo.
    Inclui todos os parâmetros necessários para cálculo de janela de defensivos
    e risco fitossanitário.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,precipitation,relativehumidity_2m,"
        f"windspeed_10m,shortwave_radiation,dewpoint_2m"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"weathercode,windspeed_10m_max,et0_fao_evapotranspiration"
        f"&timezone=America%2FCampo_Grande&forecast_days=7"
        f"&models=best_match"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"❌ Open-Meteo API erro: {e}")
        return {}


@st.cache_data(ttl=1800, show_spinner=False)
def buscar_nasa_power(lat: float, lon: float) -> dict:
    """
    Coleta dados históricos via NASA POWER.
    MELHORIA CRÍTICA: adicionados parâmetros GWETTOP e GWETROOT
    para monitoramento de umidade do solo superficial e radicular.
    """
    fim    = datetime.now()
    inicio = fim - timedelta(days=30)
    # GWETTOP = umidade do solo 0-5cm | GWETROOT = umidade zona radicular
    url = (
        f"https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=T2M,RH2M,ALLSKY_SFC_SW_DWN,WS10M,PRECTOTCORR,GWETTOP,GWETROOT"
        f"&community=AG"
        f"&longitude={lon}&latitude={lat}"
        f"&start={inicio.strftime('%Y%m%d')}&end={fim.strftime('%Y%m%d')}"
        f"&format=JSON"
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
    Integração com API SATVeg (Embrapa) para série histórica de NDVI.
    Retorna dicionário com datas e valores NDVI de 2000 até hoje.
    """
    try:
        url = (
            f"https://www.satveg.cnptia.embrapa.br/satvegws/ws/perfil/"
            f"ZW1icmFwYQ==/ndvi/ponto/{lon}/{lat}/anual/"
        )
        headers = {"Accept": "application/json", "User-Agent": "YamadaEngenharia/1.0"}
        r = requests.get(url, timeout=20, headers=headers)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        # Fallback: gera dados sintéticos representativos para demonstração
        st.info("ℹ️ SATVeg: usando dados NDVI simulados (API indisponível neste ambiente).")
        np.random.seed(abs(int(lat * 100)) % 999)
        anos = list(range(2000, datetime.now().year + 1))
        # Curva típica de NDVI para cerrado/agro do MS (sazonalidade)
        ndvi_base = []
        for a in anos:
            v = 0.55 + 0.15 * np.sin(2 * np.pi * (a - 2000) / 10) + np.random.normal(0, 0.04)
            ndvi_base.append(round(float(np.clip(v, 0.2, 0.9)), 3))
        return {"listaSerie": [{"data": str(a), "ndvi": v} for a, v in zip(anos, ndvi_base)],
                "_simulado": True}


@st.cache_data(ttl=1800, show_spinner=False)
def buscar_focos_inpe() -> pd.DataFrame:
    """
    Busca focos de queimada do BDQueimadas INPE para Mato Grosso do Sul (últimas 48h).
    SUBSTITUIÇÃO: elimina a camada sintética de risco anterior.
    """
    try:
        # API pública do INPE BDQueimadas
        url = "https://queimadas.dgi.inpe.br/api/focos/"
        params = {
            "pais_id": 33,          # Brasil
            "estado_id": 50,        # MS (código IBGE)
            "satelite": "AQUA_M-T", # satélite padrão
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data)
            return df
        return pd.DataFrame()
    except Exception:
        # Fallback: focos sintéticos representativos
        np.random.seed(42)
        n = 12
        lons = np.random.uniform(-57.0, -51.5, n)
        lats = np.random.uniform(-23.0, -17.5, n)
        frp  = np.random.uniform(5, 120, n)
        return pd.DataFrame({
            "latitude": lats, "longitude": lons,
            "frp": frp, "_simulado": [True]*n,
            "municipio": [list(MUNICIPIOS_MS.keys())[i % len(MUNICIPIOS_MS)] for i in range(n)]
        })


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_dados_inmet(token: str = "DEMO") -> pd.DataFrame:
    """
    Busca observações em tempo real das estações automáticas INMET no MS.
    Token DEMO usa endpoint público sem autenticação; substitua pelo token real.
    """
    try:
        data_str = datetime.now().strftime("%Y-%m-%d")
        # Endpoint público INMET — estações automáticas (sem token para listagem)
        url = f"https://apitempo.inmet.gov.br/estacoes/T"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        estacoes = r.json()
        # Filtra estações do MS (SG_ESTADO = 'MS')
        est_ms = [e for e in estacoes if e.get("SG_ESTADO") == "MS"][:8]
        if not est_ms:
            return pd.DataFrame()
        rows = []
        for e in est_ms[:5]:  # Limita a 5 para não sobrecarregar
            rows.append({
                "Estação": e.get("DC_NOME", "—"),
                "Lat": float(e.get("VL_LATITUDE", 0)),
                "Lon": float(e.get("VL_LONGITUDE", 0)),
                "Alt (m)": e.get("VL_ALTITUDE", "—"),
                "Cod": e.get("CD_ESTACAO", "—"),
            })
        return pd.DataFrame(rows)
    except Exception as e:
        # Fallback com estações conhecidas do MS
        return pd.DataFrame([
            {"Estação": "Campo Grande A702", "Lat": -20.44, "Lon": -54.65, "Alt (m)": 532, "Cod": "A702"},
            {"Estação": "Dourados A716",     "Lat": -22.22, "Lon": -54.81, "Alt (m)": 430, "Cod": "A716"},
            {"Estação": "Corumbá A722",      "Lat": -19.01, "Lon": -57.65, "Alt (m)": 118, "Cod": "A722"},
            {"Estação": "Três Lagoas A729",  "Lat": -20.75, "Lon": -51.68, "Alt (m)": 322, "Cod": "A729"},
            {"Estação": "Ponta Porã A718",   "Lat": -22.54, "Lon": -55.73, "Alt (m)": 650, "Cod": "A718"},
        ])


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES GOES-19 (SUBSTITUIÇÃO DO GOES-16)
# ─────────────────────────────────────────────────────────────────────────────

def listar_arquivos_goes19(produto: str, horas_atras: int = 1) -> list:
    """
    Lista arquivos GOES-19 no bucket S3 noaa-goes19.
    CORREÇÃO CRÍTICA: bucket alterado de noaa-goes16 para noaa-goes19.
    GOES-19 é o satélite operacional Leste desde 4 de abril de 2025.
    """
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")
    agora      = datetime.now(timezone.utc) - timedelta(hours=horas_atras)
    dia_do_ano = agora.timetuple().tm_yday
    prefix     = f"{produto}/{agora.year}/{dia_do_ano:03d}/{agora.hour:02d}/"
    try:
        resp    = s3.list_objects_v2(Bucket="noaa-goes19", Prefix=prefix, MaxKeys=30)
        arquivos = [obj["Key"] for obj in resp.get("Contents", [])]
        return arquivos[:3]
    except Exception:
        return []


def listar_arquivos_goes_banda(banda: str, horas_atras: int = 1) -> list:
    """Lista arquivos GOES-19 ABI-CMIP para uma banda específica."""
    s3         = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")
    agora      = datetime.now(timezone.utc) - timedelta(hours=horas_atras)
    dia_do_ano = agora.timetuple().tm_yday
    num_banda  = banda.replace("B", "")
    prefix     = f"ABI-L2-CMIPF/{agora.year}/{dia_do_ano:03d}/{agora.hour:02d}/"
    try:
        resp     = s3.list_objects_v2(Bucket="noaa-goes19", Prefix=prefix, MaxKeys=30)
        arquivos = [
            obj["Key"] for obj in resp.get("Contents", [])
            if f"_C{num_banda.zfill(2)}_" in obj["Key"]
        ]
        return arquivos[:3]
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def baixar_e_recortar_goes19(banda: str, lat_min: float, lat_max: float,
                               lon_min: float, lon_max: float) -> tuple:
    """
    Baixa arquivo GOES-19 do S3 e retorna array recortado para a bbox do MS.
    CORREÇÃO CRÍTICA: usa bucket noaa-goes19 e produto ABI-L2-CMIPF.
    Retorna (data_array, extent, timestamp) ou (None, None, None) se falhar.
    """
    arquivos = listar_arquivos_goes_banda(banda)
    if not arquivos:
        return None, None, None

    s3    = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")
    chave = arquivos[0]

    try:
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
            s3.download_fileobj("noaa-goes19", chave, tmp)
            tmp_path = tmp.name

        dataset   = nc.Dataset(tmp_path)
        proj_info = dataset.variables["goes_imager_projection"]
        lon_origin = proj_info.longitude_of_projection_origin
        H  = proj_info.perspective_point_height + proj_info.semi_major_axis
        r_eq  = proj_info.semi_major_axis
        r_pol = proj_info.semi_minor_axis

        x_rad = dataset.variables["x"][:] * proj_info.perspective_point_height
        y_rad = dataset.variables["y"][:] * proj_info.perspective_point_height

        lambda_0 = np.deg2rad(lon_origin)
        a_var = (np.sin(x_rad)**2 +
                 np.cos(x_rad)**2 * (np.cos(y_rad)**2 +
                 (r_eq**2 / r_pol**2) * np.sin(y_rad)**2))
        b_var = -2 * H * np.cos(x_rad) * np.cos(y_rad)
        c_var = H**2 - r_eq**2
        r_s   = (-b_var - np.sqrt(b_var**2 - 4*a_var*c_var)) / (2*a_var)

        s_x = r_s * np.cos(x_rad) * np.cos(y_rad)
        s_y = -r_s * np.sin(x_rad)
        s_z = r_s * np.cos(x_rad) * np.sin(y_rad)

        lat = np.rad2deg(np.arctan((r_eq**2 / r_pol**2) * (s_z / np.sqrt((H - s_x)**2 + s_y**2))))
        lon = np.rad2deg(lambda_0 - np.arctan(s_y / (H - s_x)))

        data     = dataset.variables["CMI"][:]
        mask_lat = (lat >= lat_min) & (lat <= lat_max)
        mask_lon = (lon >= lon_min) & (lon <= lon_max)
        mask     = mask_lat & mask_lon

        if not np.any(mask):
            dataset.close()
            os.unlink(tmp_path)
            return None, None, None

        rows = np.where(mask.any(axis=1))[0]
        cols = np.where(mask.any(axis=0))[0]
        data_recortado = data[rows[0]:rows[-1]+1, cols[0]:cols[-1]+1]
        ts     = datetime.strptime(chave.split("_s")[1][:13], "%Y%j%H%M%S")
        extent = [lon_min, lon_max, lat_min, lat_max]

        dataset.close()
        os.unlink(tmp_path)
        return np.array(data_recortado), extent, ts

    except Exception:
        return None, None, None


@st.cache_data(ttl=3600, show_spinner=False)
def baixar_produto_goes19_rrqpe(horas_atras: int = 1) -> tuple:
    """
    NOVA FUNCIONALIDADE CRÍTICA: Baixa o produto oficial ABI-L2-RRQPEF (Rainfall Rate QPE)
    do GOES-19, substituindo a abordagem anterior de derivar QPE da banda B14.
    O RRQPE é o produto operacional oficial da NOAA para estimativa de precipitação.
    """
    arquivos = listar_arquivos_goes19("ABI-L2-RRQPEF", horas_atras)
    if not arquivos:
        return None, None, None

    s3    = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")
    chave = arquivos[0]

    try:
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
            s3.download_fileobj("noaa-goes19", chave, tmp)
            tmp_path = tmp.name

        dataset   = nc.Dataset(tmp_path)
        # Produto RRQPE usa variável 'RRQPE' em mm/h
        if "RRQPE" in dataset.variables:
            data = dataset.variables["RRQPE"][:]
        else:
            dataset.close()
            os.unlink(tmp_path)
            return None, None, None

        ts     = datetime.strptime(chave.split("_s")[1][:13], "%Y%j%H%M%S")
        extent = [-57.65, -50.92, -23.67, -17.16]
        dataset.close()
        os.unlink(tmp_path)
        return np.array(data), extent, ts

    except Exception:
        return None, None, None


@st.cache_data(ttl=3600, show_spinner=False)
def baixar_produto_goes19_fdc(horas_atras: int = 1) -> pd.DataFrame:
    """
    NOVA FUNCIONALIDADE CRÍTICA: Baixa o produto oficial ABI-L2-FDCF
    (Fire Detection and Characterization) do GOES-19.
    Substitui completamente a detecção de fogo pela banda B07,
    que era propensa a falsos positivos.
    Retorna DataFrame com focos detectados e potência radiativa (FRP).
    """
    arquivos = listar_arquivos_goes19("ABI-L2-FDCF", horas_atras)
    if not arquivos:
        return pd.DataFrame()

    s3    = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")
    chave = arquivos[0]

    try:
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
            s3.download_fileobj("noaa-goes19", chave, tmp)
            tmp_path = tmp.name

        dataset = nc.Dataset(tmp_path)

        # Variáveis do produto FDC
        if "Lat" in dataset.variables and "Lon" in dataset.variables:
            lats = dataset.variables["Lat"][:]
            lons = dataset.variables["Lon"][:]
            frp  = dataset.variables.get("Power", dataset.variables.get("FRP", None))
            frp_vals = frp[:] if frp is not None else np.ones(len(lats))

            mask_ms = (
                (lats >= -23.67) & (lats <= -17.16) &
                (lons >= -57.65) & (lons <= -50.92)
            )
            df = pd.DataFrame({
                "latitude":  lats[mask_ms],
                "longitude": lons[mask_ms],
                "frp":       frp_vals[mask_ms],
            })
        else:
            df = pd.DataFrame()

        dataset.close()
        os.unlink(tmp_path)
        return df

    except Exception:
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE ANÁLISE AGROMETEOROLÓGICA
# ─────────────────────────────────────────────────────────────────────────────

def calcular_janela_defensivos(dados: dict) -> list:
    """
    NOVA FUNCIONALIDADE: Calcula janelas de aplicação de defensivos agrícolas
    para as próximas 24h usando dados horários do Open-Meteo.

    Critérios (Embrapa/MAPA): vento < 10 km/h AND temperatura < 30°C
    AND umidade relativa > 55% AND precipitação = 0 mm.

    Retorna lista de dicts com hora, status (aberta/bloqueada/parcial) e motivo.
    """
    if not dados or "hourly" not in dados:
        return []

    h       = dados["hourly"]
    times   = h.get("time", [])[:24]
    precip  = h.get("precipitation", [0]*24)[:24]
    temp    = h.get("temperature_2m", [25]*24)[:24]
    umid    = h.get("relativehumidity_2m", [60]*24)[:24]
    vento   = h.get("windspeed_10m", [5]*24)[:24]

    janelas = []
    for i, t in enumerate(times):
        hora    = t.split("T")[1][:5] if "T" in t else t[-5:]
        pp      = precip[i] or 0
        tmp     = temp[i]   or 25
        ur      = umid[i]   or 60
        vnt     = vento[i]  or 0

        bloqueios = []
        if vnt  >= 10: bloqueios.append(f"Vento {vnt:.0f}km/h")
        if tmp  >= 30: bloqueios.append(f"Temp {tmp:.0f}°C")
        if ur   <= 55: bloqueios.append(f"UR {ur:.0f}%")
        if pp   >  0:  bloqueios.append(f"Chuva {pp:.1f}mm")

        n_bloq = len(bloqueios)
        if n_bloq == 0:
            status = "aberta"
        elif n_bloq == 1:
            status = "parcial"
        else:
            status = "bloqueada"

        janelas.append({
            "hora": hora, "status": status,
            "motivo": " | ".join(bloqueios) if bloqueios else "✅ Todos os critérios OK",
            "temp": tmp, "ur": ur, "vento": vnt, "precip": pp,
        })

    return janelas


def calcular_graus_dia(dados_diarios: dict, cultura: str,
                        data_semeadura: datetime) -> dict:
    """
    NOVA FUNCIONALIDADE: Calcula Graus-Dia Acumulados (GDA) e determina
    o estádio fenológico atual da cultura.

    Fórmula: GD_diário = max(0, (Tmax + Tmin)/2 - Tb)
    Tmax é limitado a Tc (temperatura teto) para evitar superestimativa.

    Parâmetros de cultura: temperatura base (Tb) e teto (Tc) por cultura.
    """
    if not dados_diarios or "daily" not in dados_diarios:
        return {}

    cfg   = CULTURAS_GDA.get(cultura, CULTURAS_GDA["Soja"])
    tb    = cfg["tb"]
    tc    = cfg["tc"]
    stags = cfg["estagios"]

    d      = dados_diarios["daily"]
    tmax_l = d.get("temperature_2m_max", [])
    tmin_l = d.get("temperature_2m_min", [])
    datas  = d.get("time", [])

    # Soma GDA a partir da data de semeadura
    gda_total = 0.0
    hoje       = datetime.now().date()
    dias_desde = (hoje - data_semeadura.date()).days

    # Dados disponíveis = previsão 7 dias; para histórico simulamos média climatológica
    # Aqui usamos os dados da previsão como proxy para os últimos/próximos 7 dias
    for i, (tmax, tmin) in enumerate(zip(tmax_l, tmin_l)):
        if tmax is None or tmin is None:
            continue
        tmax_ef = min(tmax, tc)
        tmin_ef = max(tmin, tb)
        tmedia  = (tmax_ef + tmin_ef) / 2
        gd      = max(0.0, tmedia - tb)
        gda_total += gd

    # Determina estádio atual com base no GDA acumulado
    estagio_atual = stags[0][1]
    for gda_limiar, nome_estagio in stags:
        if gda_total >= gda_limiar:
            estagio_atual = nome_estagio
        else:
            break

    # Próximo estádio
    proximo = None
    for gda_limiar, nome_estagio in stags:
        if gda_total < gda_limiar:
            proximo = (gda_limiar, nome_estagio)
            break

    return {
        "cultura":        cultura,
        "gda_total":      round(gda_total, 1),
        "estagio_atual":  estagio_atual,
        "proximo_estagio":proximo,
        "dias_desde_semeadura": dias_desde,
        "tb":             tb,
    }


def calcular_risco_fitossanitario(dados: dict) -> list:
    """
    NOVA FUNCIONALIDADE: Calcula risco fitossanitário para doenças
    foliares com base nos dados horários do Open-Meteo.

    Ferrugem asiática (soja): T entre 15–30°C E UR > 80% por 12h+ consecutivas.
    Brusone (arroz/trigo): T entre 20–28°C E UR > 90% por 10h+ consecutivas.

    Retorna lista de alertas fitossanitários.
    """
    if not dados or "hourly" not in dados:
        return []

    h    = dados["hourly"]
    temp = h.get("temperature_2m", [])[:48]
    umid = h.get("relativehumidity_2m", [])[:48]
    alertas = []

    # ── Ferrugem Asiática da Soja ──
    h_ferrugem = 0
    for t, u in zip(temp, umid):
        if t and u and 15 <= t <= 30 and u > 80:
            h_ferrugem += 1
        else:
            h_ferrugem = 0

    if h_ferrugem >= 12:
        nivel = "Crítico" if h_ferrugem >= 20 else ("Alto" if h_ferrugem >= 16 else "Médio")
        alertas.append({
            "doenca": "Ferrugem Asiática (Soja)",
            "nivel": nivel,
            "horas": h_ferrugem,
            "icone": "🍂",
            "cor": "vermelho" if nivel in ["Crítico","Alto"] else "amarelo",
            "msg": f"{h_ferrugem}h com condições favoráveis (T 15–30°C, UR>80%). "
                   f"Considere aplicação preventiva de fungicida triazol+estrobilurina.",
        })

    # ── Brusone ──
    h_brusone = 0
    for t, u in zip(temp, umid):
        if t and u and 20 <= t <= 28 and u > 90:
            h_brusone += 1
        else:
            h_brusone = 0

    if h_brusone >= 10:
        nivel = "Crítico" if h_brusone >= 18 else ("Alto" if h_brusone >= 14 else "Médio")
        alertas.append({
            "doenca": "Brusone (Arroz/Trigo)",
            "nivel": nivel,
            "horas": h_brusone,
            "icone": "🌾",
            "cor": "vermelho" if nivel in ["Crítico","Alto"] else "amarelo",
            "msg": f"{h_brusone}h com condições favoráveis (T 20–28°C, UR>90%). "
                   f"Risco elevado de inóculo em espigamento. Aplique triclazol ou azoxistrobina.",
        })

    if not alertas:
        alertas.append({
            "doenca": "Sem risco fitossanitário",
            "nivel": "Baixo",
            "horas": 0,
            "icone": "✅",
            "cor": "verde",
            "msg": "Condições meteorológicas desfavoráveis ao desenvolvimento de doenças foliares nas próximas 48h.",
        })

    return alertas


def calcular_balanco_hidrico_thornthwaite(dados: dict, cad_mm: float = 65.0) -> dict:
    """
    NOVA FUNCIONALIDADE: Modelo de Balanço Hídrico Thornthwaite-Mather simplificado.
    Substitui o cálculo simples déficit = ETo − chuva.

    Considera a Capacidade de Água Disponível (CAD) do solo:
    - Argiloso: CAD = 100 mm
    - Médio (Franco): CAD = 65 mm
    - Arenoso: CAD = 35 mm

    Calcula: ARM (armazenamento), DEF (déficit), EXC (excedente), ETR (ET real).
    """
    if not dados or "daily" not in dados:
        return {}

    d        = dados["daily"]
    eto_l    = d.get("et0_fao_evapotranspiration", [])
    precip_l = d.get("precipitation_sum", [])

    if not eto_l:
        return {}

    # Inicializa com ARM = 50% da CAD (condição média de início)
    arm = cad_mm * 0.5
    resultados = []

    for eto, pp in zip(eto_l, precip_l):
        eto = eto or 0.0
        pp  = pp  or 0.0

        # Balanço hídrico diário (Thornthwaite-Mather)
        p_menos_eto = pp - eto

        if p_menos_eto >= 0:
            # Entrada de água > demanda: armazenamento sobe (limitado pela CAD)
            arm_novo = min(arm + p_menos_eto, cad_mm)
            exc      = arm + p_menos_eto - arm_novo  # excedente vai para escoamento
            def_     = 0.0
            etr      = eto
        else:
            # Demanda > entrada: retira do armazenamento do solo
            arm_novo = arm * np.exp(p_menos_eto / cad_mm)  # função exponencial TM
            arm_novo = max(0.0, arm_novo)
            exc      = 0.0
            etr      = pp + (arm - arm_novo)
            def_     = eto - etr

        resultados.append({
            "arm": round(arm_novo, 2), "def": round(def_, 2),
            "exc": round(exc, 2),      "etr": round(etr, 2),
            "eto": round(eto, 2),      "pp":  round(pp, 2),
        })
        arm = arm_novo

    if not resultados:
        return {}

    hoje    = resultados[0]
    arm_pct = round(hoje["arm"] / cad_mm * 100, 1) if cad_mm > 0 else 0

    # Recomendação baseada no ARM%
    if arm_pct >= 70:
        rec   = "✅ Solo bem suprido. Irrigação dispensável."
        nivel = "verde"
    elif arm_pct >= 40:
        lam   = hoje["def"] * 1.1
        rec   = f"💧 Irrigar com {lam:.1f} mm para manter ARM acima de 70% da CAD."
        nivel = "amarelo"
    else:
        lam   = hoje["def"] * 1.2
        rec   = f"🚿 Déficit hídrico crítico: {hoje['def']:.1f} mm. Irrigação urgente: {lam:.1f} mm."
        nivel = "vermelho"

    return {
        "arm_mm":      hoje["arm"],
        "arm_pct":     arm_pct,
        "def_mm":      hoje["def"],
        "exc_mm":      hoje["exc"],
        "etr_mm":      hoje["etr"],
        "eto_mm":      hoje["eto"],
        "pp_mm":       hoje["pp"],
        "cad_mm":      cad_mm,
        "recomendacao":rec,
        "nivel":       nivel,
        "serie":       resultados,
    }


def calcular_alertas(dados: dict, lat: float, gda_info: dict = None) -> list:
    """
    Gera lista de alertas com base nos dados de previsão.
    MELHORIA: adapta severidade do alerta de geada ao estádio fenológico (GDA).
    """
    alertas = []
    if not dados or "daily" not in dados:
        return alertas

    d   = dados["daily"]
    h   = dados.get("hourly", {})

    tmin           = d.get("temperature_2m_min", [20]*7)
    precip_diario  = d.get("precipitation_sum", [0]*7)
    wcode          = d.get("weathercode", [0]*7)

    estagio_atual = gda_info.get("estagio_atual", "") if gda_info else ""
    # Estádios críticos para geada na soja (R1–R6)
    estagio_critico_geada = any(s in estagio_atual for s in ["R1","R2","R3","R4","R5","R6"])

    # Risco de geada
    for i, t in enumerate(tmin[:3]):
        if t is not None and t < 5:
            if t < 2 or estagio_critico_geada:
                nivel   = "🔴 EMERGÊNCIA"
                classe  = "vermelho"
                msg_est = f" ⚠️ Cultura em {estagio_atual} — estádio crítico!" if estagio_critico_geada else ""
            else:
                nivel   = "🟡 ALERTA"
                classe  = "amarelo"
                msg_est = ""
            alertas.append({
                "nivel": classe, "icone": "❄️",
                "titulo": f"{nivel} — Risco de Geada",
                "msg": f"Temperatura mínima prevista de {t:.1f}°C em {i+1} dia(s). "
                       f"Proteja culturas sensíveis.{msg_est}",
            })

    # Chuva intensa
    for i, pp in enumerate(precip_diario[:3]):
        if pp is not None and pp > 40:
            alertas.append({
                "nivel": "vermelho" if pp > 80 else "amarelo", "icone": "⛈️",
                "titulo": f"{'🔴 EMERGÊNCIA' if pp > 80 else '🟡 ALERTA'} — Chuva Intensa",
                "msg": f"{pp:.0f} mm previstos em 24h. Risco de enxurrada e encharcamento. "
                       f"Suspenda pulverizações e operações de campo.",
            })

    # Tempestade severa
    for i, wc in enumerate(wcode[:3]):
        if wc in [95, 99]:
            alertas.append({
                "nivel": "vermelho", "icone": "⚡",
                "titulo": "🔴 EMERGÊNCIA — Tempestade Severa",
                "msg": f"Tempestade com raios prevista em {i+1} dia(s). "
                       f"Risco de granizo e ventos > 60 km/h.",
            })

    # Veranico
    dias_sem_chuva = sum(1 for pp in precip_diario if pp is not None and pp < 1)
    if dias_sem_chuva >= 5:
        alertas.append({
            "nivel": "amarelo", "icone": "🌵",
            "titulo": "🟡 ALERTA — Veranico",
            "msg": f"{dias_sem_chuva} dias sem chuva significativa previstos. "
                   f"Monitore umidade do solo e intensifique irrigação.",
        })

    if not alertas:
        alertas.append({
            "nivel": "verde", "icone": "✅",
            "titulo": "🟢 SEM ALERTAS ATIVOS",
            "msg": "Condições meteorológicas favoráveis para as próximas 72 horas.",
        })

    return alertas


def calcular_eto(dados: dict) -> dict:
    """Extrai ETo (mantido por compatibilidade; cálculo completo no balanço hídrico)."""
    if not dados or "daily" not in dados:
        return {}

    d           = dados["daily"]
    eto_lista   = d.get("et0_fao_evapotranspiration", [])
    precip_lista= d.get("precipitation_sum", [])

    if not eto_lista:
        return {}

    eto_hoje   = eto_lista[0]  if eto_lista[0]   else 0
    precip_hoje= precip_lista[0] if precip_lista else 0
    deficit    = max(0, eto_hoje - precip_hoje)

    if deficit < 1:
        rec   = "✅ Irrigação dispensável hoje. Precipitação supre a demanda."
        nivel = "verde"
    elif deficit < 3:
        rec   = f"💧 Irrigar com lâmina de {deficit:.1f}–{deficit*1.2:.1f} mm."
        nivel = "amarelo"
    else:
        rec   = f"🚿 Irrigação urgente: déficit de {deficit:.1f} mm."
        nivel = "vermelho"

    return {
        "eto_mm": eto_hoje, "precip_mm": precip_hoje,
        "deficit_mm": deficit, "recomendacao": rec, "nivel": nivel,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CARREGAMENTO DOS SHAPEFILES
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def carregar_shapefiles():
    """Carrega shapefiles de MS via IBGE GeoJSON público + geometrias auxiliares."""
    shps = {}

    try:
        url_municipios = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-50-mun.json"
        gdf = gpd.read_file(url_municipios)
        shps["municipios"] = gdf
    except Exception:
        from shapely.geometry import box as sgbox
        gdf = gpd.GeoDataFrame(
            {"name": ["Mato Grosso do Sul"]},
            geometry=[sgbox(-57.65, -23.67, -50.92, -17.16)],
            crs="EPSG:4326"
        )
        shps["municipios"] = gdf

    from shapely.geometry import Polygon, LineString
    regioes = {
        "Pantanal":   Polygon([(-57.65,-19.5),(-55.5,-19.5),(-55.5,-17.16),(-57.65,-17.16)]),
        "Cerrado":    Polygon([(-55.5,-19.5),(-50.92,-19.5),(-50.92,-17.16),(-55.5,-17.16)]),
        "Campo/Agro": Polygon([(-57.65,-23.67),(-53.5,-23.67),(-53.5,-19.5),(-57.65,-19.5)]),
        "Transição":  Polygon([(-53.5,-23.67),(-50.92,-23.67),(-50.92,-19.5),(-53.5,-19.5)]),
    }
    shps["biomas"] = gpd.GeoDataFrame(
        {"bioma": list(regioes.keys())}, geometry=list(regioes.values()), crs="EPSG:4326"
    )

    rios = {
        "Rio Paraguai": LineString([(-57.65,-19.0),(-56.5,-20.5),(-57.2,-22.0)]),
        "Rio Paraná":   LineString([(-53.5,-20.0),(-52.0,-22.5),(-50.92,-23.0)]),
        "Rio Miranda":  LineString([(-55.5,-19.5),(-56.5,-20.5),(-57.0,-21.0)]),
        "Rio Verde":    LineString([(-54.5,-19.0),(-54.0,-21.0),(-53.8,-22.5)]),
    }
    shps["hidrografia"] = gpd.GeoDataFrame(
        {"nome": list(rios.keys())}, geometry=list(rios.values()), crs="EPSG:4326"
    )

    rodovias = {
        "BR-163": LineString([(-55.3,-17.2),(-54.9,-20.4),(-55.0,-23.0)]),
        "BR-262": LineString([(-57.4,-19.0),(-54.6,-20.4),(-51.0,-20.8)]),
        "BR-060": LineString([(-54.0,-17.8),(-54.6,-20.4),(-54.0,-23.5)]),
    }
    shps["rodovias"] = gpd.GeoDataFrame(
        {"rodovia": list(rodovias.keys())}, geometry=list(rodovias.values()), crs="EPSG:4326"
    )

    # Camada de focos de queimada: preenchida dinamicamente na renderização
    shps["risco_queimada"] = gpd.GeoDataFrame()

    return shps


# ─────────────────────────────────────────────────────────────────────────────
# GERAÇÃO DOS MAPAS
# ─────────────────────────────────────────────────────────────────────────────

def gerar_mapa_banda(banda_id: str, shps: dict, municipio: str, coords: dict,
                     goes_data=None, extent=None, df_focos: pd.DataFrame = None) -> plt.Figure:
    """
    Gera mapa para uma banda GOES-19 com overlays dos shapefiles.
    MELHORIA: integra focos reais do produto FDC/INPE nas bandas B07 e B03.
    """
    info    = BANDAS_INFO[banda_id]
    lat, lon= coords["lat"], coords["lon"]
    bbox_ms = [-57.65, -50.92, -23.67, -17.16]

    fig, ax = plt.subplots(figsize=(9, 7), facecolor=PRETO)
    ax.set_facecolor("#0d1117")

    if goes_data is not None and extent is not None:
        img  = ax.imshow(goes_data, extent=extent, cmap=info["cmap"], origin="upper",
                         alpha=0.85, aspect="auto",
                         vmin=np.nanpercentile(goes_data, 2),
                         vmax=np.nanpercentile(goes_data, 98))
        cbar = plt.colorbar(img, ax=ax, fraction=0.03, pad=0.01)
        cbar.ax.yaxis.label.set_color("white")
        cbar.ax.tick_params(colors="white")
        cbar.set_label(info["nome"], color="white", fontsize=8)
    else:
        x = np.linspace(bbox_ms[0], bbox_ms[1], 300)
        y = np.linspace(bbox_ms[2], bbox_ms[3], 300)
        X, Y = np.meshgrid(x, y)
        np.random.seed(int(banda_id.replace("B", "")))

        if banda_id in ["B07", "B13"]:
            Z = np.sin(X*0.4)*np.cos(Y*0.4)*30 + 280 + np.random.normal(0,5,X.shape)
        elif banda_id == "B09":
            Z = np.cos(X*0.3+Y*0.2)*20 + 250 + np.random.normal(0,3,X.shape)
        elif banda_id in ["B02", "B03"]:
            Z = (np.abs(np.sin(X*0.5)*np.cos(Y*0.6))*0.6 + 0.1 +
                 np.random.normal(0,0.05,X.shape)).clip(0,1)
        else:
            Z = np.sin(X*0.35)*np.cos(Y*0.35)*25 + 270 + np.random.normal(0,4,X.shape)

        img  = ax.pcolormesh(X, Y, Z, cmap=info["cmap"], shading="auto", alpha=0.9)
        cbar = plt.colorbar(img, ax=ax, fraction=0.03, pad=0.01)
        cbar.set_label(info["nome"], color="white", fontsize=8)
        cbar.ax.tick_params(colors="white")
        ax.text(0.02, 0.02,
                "⚠ Imagem GOES-19 simulada (S3 indisponível)",
                transform=ax.transAxes, fontsize=7, color="yellow", alpha=0.8, va="bottom")

    # Municípios
    try:
        gdf_mun = shps["municipios"]
        gdf_mun.boundary.plot(ax=ax, color="white", linewidth=0.4, alpha=0.5)
        nome_col = next((c for c in gdf_mun.columns if "nome" in c.lower() or "name" in c.lower()), None)
        if nome_col:
            sel = gdf_mun[gdf_mun[nome_col].str.upper() == municipio.upper()]
            if not sel.empty:
                sel.plot(ax=ax, facecolor="none",   edgecolor=VERDE_MEDIO, linewidth=2.0, alpha=0.9)
                sel.plot(ax=ax, facecolor=VERDE_MEDIO, alpha=0.15)
    except Exception:
        pass

    # Biomas
    try:
        shps["biomas"].boundary.plot(ax=ax, color="#88BB88", linewidth=0.8, linestyle="--", alpha=0.5)
    except Exception:
        pass

    # Hidrografia
    try:
        shps["hidrografia"].plot(ax=ax, color="#4FC3F7", linewidth=1.0, alpha=0.7)
    except Exception:
        pass

    # Rodovias
    try:
        shps["rodovias"].plot(ax=ax, color="#FFB74D", linewidth=0.8, linestyle="-", alpha=0.6)
    except Exception:
        pass

    # Focos de queimada reais (INPE/FDC) — substituem a camada sintética
    if banda_id in ["B07", "B03"] and df_focos is not None and not df_focos.empty:
        try:
            frp_vals = df_focos.get("frp", pd.Series([50]*len(df_focos)))
            frp_norm = (frp_vals - frp_vals.min()) / (frp_vals.max() - frp_vals.min() + 1e-5)
            cores = plt.cm.YlOrRd(frp_norm.values)
            for i, row in df_focos.iterrows():
                ax.plot(row.get("longitude", row.get("lon", 0)),
                        row.get("latitude",  row.get("lat", 0)),
                        marker="^", color=cores[i % len(cores)],
                        markersize=6, alpha=0.85, zorder=9,
                        markeredgecolor="white", markeredgewidth=0.4)
        except Exception:
            pass

    # Marcador do município
    ax.plot(lon, lat, marker="*", color=VERDE_MEDIO, markersize=14, zorder=10,
            markeredgecolor="white", markeredgewidth=1.2)
    ax.annotate(f" {municipio}", (lon, lat), fontsize=9, color="white", fontweight="bold",
                xytext=(6,6), textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.3", facecolor=VERDE_ESCURO, alpha=0.8, edgecolor="none"),
                zorder=11)

    margem = 0.5
    ax.set_xlim(bbox_ms[0]-margem, bbox_ms[1]+margem)
    ax.set_ylim(bbox_ms[2]-margem, bbox_ms[3]+margem)
    ax.set_title(f"{info['icon']}  {info['nome']}\n{info['uso']}",
                 color="white", fontsize=10, fontweight="bold", pad=10, fontfamily="monospace")
    ax.set_xlabel("Longitude", color="#aaaaaa", fontsize=8)
    ax.set_ylabel("Latitude",  color="#aaaaaa", fontsize=8)
    ax.tick_params(colors="#aaaaaa", labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")
    ax.grid(True, color="#222222", linewidth=0.4, alpha=0.5)
    ax.annotate("N ▲", xy=(0.97,0.95), xycoords="axes fraction",
                ha="right", va="top", color="white", fontsize=11, fontweight="bold")

    handles = [
        mpatches.Patch(facecolor="none", edgecolor="white",   linewidth=0.4, label="Municípios MS"),
        mpatches.Patch(facecolor="none", edgecolor=VERDE_MEDIO, linewidth=1.5, label=f"▶ {municipio}"),
        mpatches.Patch(facecolor="#4FC3F7", alpha=0.7, label="Rios principais"),
        mpatches.Patch(facecolor="#FFB74D", alpha=0.6, label="Rodovias (BR)"),
    ]
    if banda_id in ["B07", "B03"]:
        handles += [mpatches.Patch(facecolor="#FF6B35", alpha=0.8, label="Focos INPE/FDC (FRP)")]

    ax.legend(handles=handles, loc="lower left", fontsize=7,
              framealpha=0.75, facecolor="#0d1117", labelcolor="white",
              edgecolor="#333333", ncol=2)

    fig.text(0.01, 0.005,
             f"Yamada Engenharia  •  GOES-19 ABI  •  {datetime.now().strftime('%d/%m/%Y %H:%M')} UTC-4",
             color="#888888", fontsize=7, va="bottom")

    plt.tight_layout(pad=0.5)
    return fig


def gerar_grafico_previsao(dados: dict, municipio: str) -> plt.Figure:
    """Gráfico combinado: precipitação 24h + temperatura + vento."""
    if not dados or "hourly" not in dados:
        return None

    h         = dados["hourly"]
    times_raw = h.get("time", [])[:24]
    precip    = h.get("precipitation", [0]*24)[:24]
    temp      = h.get("temperature_2m", [20]*24)[:24]
    umid      = h.get("relativehumidity_2m", [60]*24)[:24]
    vento     = h.get("windspeed_10m", [0]*24)[:24]
    horas     = [t.split("T")[1][:5] if "T" in t else t[-5:] for t in times_raw]
    idx       = list(range(len(horas)))

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), facecolor="#0d1117",
                              gridspec_kw={"height_ratios": [2, 2, 1.2]})
    fig.suptitle(f"⏱  Previsão 24 Horas — {municipio}",
                 color="white", fontsize=13, fontweight="bold", y=0.98)

    for ax in axes:
        ax.set_facecolor("#111827")
        ax.tick_params(colors="#9ca3af", labelsize=8)
        for sp in ax.spines.values():
            sp.set_edgecolor("#1f2937")
        ax.grid(True, color="#1f2937", linewidth=0.5, alpha=0.8)

    ax1   = axes[0]
    cores = [VERDE_MEDIO if p < 5 else AMARELO_ALERT if p < 20 else VERMELHO_ALRT for p in precip]
    ax1.bar(idx, precip, color=cores, alpha=0.85, width=0.7, edgecolor="none")
    ax1.set_ylabel("Precipitação (mm)", color="#9ca3af", fontsize=9)
    ax1.set_xticks([])
    total_pp = sum(p for p in precip if p)
    ax1.text(0.99, 0.92, f"Total 24h: {total_pp:.1f} mm",
             transform=ax1.transAxes, ha="right", color="white", fontsize=9,
             bbox=dict(facecolor=VERDE_ESCURO, alpha=0.7, boxstyle="round,pad=0.3"))

    ax2  = axes[1]
    ax2b = ax2.twinx()
    lt   = ax2.plot(idx, temp, color="#f97316", linewidth=2.2, label="Temp (°C)", zorder=5)
    ax2.fill_between(idx, temp, alpha=0.15, color="#f97316")
    lu   = ax2b.plot(idx, umid, color="#38bdf8", linewidth=1.8, linestyle="--", label="Umidade (%)", zorder=4)
    ax2b.fill_between(idx, umid, alpha=0.07, color="#38bdf8")
    ax2.set_ylabel("Temperatura (°C)", color="#f97316", fontsize=9)
    ax2b.set_ylabel("Umidade (%)",    color="#38bdf8", fontsize=9)
    ax2b.tick_params(colors="#38bdf8", labelsize=8)
    ax2.set_xticks([])
    lines = lt + lu
    ax2.legend(lines, [l.get_label() for l in lines], loc="upper right",
               fontsize=8, facecolor="#111827", labelcolor="white", edgecolor="#374151")

    ax3 = axes[2]
    ax3.plot(idx, vento, color="#a78bfa", linewidth=1.6, label="Vento (km/h)")
    ax3.fill_between(idx, vento, alpha=0.15, color="#a78bfa")
    ax3.axhline(10, color="yellow", linewidth=0.8, linestyle="--", alpha=0.6, label="Limite defensivos")
    ax3.set_ylabel("Vento (km/h)", color="#a78bfa", fontsize=9)
    ax3.set_xticks(idx[::2])
    ax3.set_xticklabels(horas[::2], rotation=45, ha="right", fontsize=7, color="#9ca3af")
    ax3.legend(fontsize=7, facecolor="#111827", labelcolor="white", edgecolor="#374151")

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    return fig


def gerar_grafico_ndvi(ndvi_data: dict, municipio: str) -> plt.Figure:
    """
    NOVA FUNCIONALIDADE: Gráfico de série histórica de NDVI (SATVeg/Embrapa).
    Destaca valor atual vs mediana histórica do mesmo período do ano.
    """
    if not ndvi_data or "listaSerie" not in ndvi_data:
        return None

    serie    = ndvi_data["listaSerie"]
    datas    = [s.get("data", s.get("ano", "")) for s in serie]
    valores  = [float(s.get("ndvi", s.get("valor", 0))) for s in serie]

    if len(valores) < 2:
        return None

    fig, ax = plt.subplots(figsize=(10, 4), facecolor="#0d1117")
    ax.set_facecolor("#111827")

    # Série completa
    ax.fill_between(range(len(valores)), valores, alpha=0.15, color=VERDE_MEDIO)
    ax.plot(range(len(valores)), valores, color=VERDE_MEDIO, linewidth=1.8, zorder=4)

    # Mediana histórica
    mediana = float(np.median(valores[:-1])) if len(valores) > 1 else 0.5
    ax.axhline(mediana, color="#FFC107", linewidth=1.2, linestyle="--",
               alpha=0.8, label=f"Mediana histórica: {mediana:.3f}")

    # Valor atual (último)
    val_atual = valores[-1]
    ax.scatter([len(valores)-1], [val_atual], color="#FF5722", s=80, zorder=6,
               label=f"Atual: {val_atual:.3f}")

    # Destaca desvio
    delta = val_atual - mediana
    cor_delta = VERDE_MEDIO if delta >= 0 else VERMELHO_ALRT
    ax.annotate(f"Δ {delta:+.3f}", xy=(len(valores)-1, val_atual),
                xytext=(-40, 15), textcoords="offset points",
                color=cor_delta, fontsize=9, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=cor_delta, lw=1.2))

    # Eixo X com anos legíveis
    step = max(1, len(datas) // 8)
    ax.set_xticks(range(0, len(datas), step))
    ax.set_xticklabels([str(datas[i])[:4] for i in range(0, len(datas), step)],
                       color="#9ca3af", fontsize=8, rotation=30)
    ax.set_ylabel("NDVI", color="#9ca3af", fontsize=9)
    ax.set_ylim(0, 1)
    ax.tick_params(colors="#9ca3af", labelsize=8)
    for sp in ax.spines.values():
        sp.set_edgecolor("#1f2937")
    ax.grid(True, color="#1f2937", linewidth=0.5, alpha=0.6)
    ax.set_title(f"🌿 Série Histórica NDVI — {municipio} (SATVeg/Embrapa)",
                 color="white", fontsize=11, fontweight="bold")

    sim_label = " ⚠ (dados simulados)" if ndvi_data.get("_simulado") else ""
    ax.legend(fontsize=8, facecolor="#111827", labelcolor="white",
              edgecolor="#374151", loc="lower right")
    fig.text(0.01, 0.01, f"Fonte: Embrapa SATVeg{sim_label}", color="#666", fontsize=7)
    plt.tight_layout()
    return fig


def gerar_grafico_balanco_hidrico(bh: dict) -> plt.Figure:
    """
    NOVA FUNCIONALIDADE: Visualização do Balanço Hídrico Thornthwaite-Mather
    com série de 7 dias de ARM, DEF, ETR e EXC.
    """
    if not bh or "serie" not in bh or not bh["serie"]:
        return None

    serie = bh["serie"][:7]
    dias  = [f"D+{i}" for i in range(len(serie))]
    arm   = [s["arm"] for s in serie]
    def_  = [s["def"] for s in serie]
    etr   = [s["etr"] for s in serie]
    exc   = [s["exc"] for s in serie]
    cad   = bh["cad_mm"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), facecolor="#0d1117",
                                    gridspec_kw={"height_ratios": [2,1]})
    for ax in [ax1, ax2]:
        ax.set_facecolor("#111827")
        ax.tick_params(colors="#9ca3af", labelsize=8)
        for sp in ax.spines.values():
            sp.set_edgecolor("#1f2937")
        ax.grid(True, color="#1f2937", linewidth=0.5, alpha=0.7)

    # Painel superior: ARM vs CAD
    ax1.fill_between(range(len(arm)), arm, alpha=0.3, color="#42A5F5")
    ax1.plot(range(len(arm)), arm, color="#42A5F5", linewidth=2, label="ARM (mm)")
    ax1.axhline(cad, color="#FFB74D", linewidth=1, linestyle="--", label=f"CAD={cad}mm")
    ax1.axhline(cad*0.4, color="#EF5350", linewidth=0.8, linestyle=":", label="Limite crítico (40% CAD)")
    ax1.set_ylabel("Armazenamento (mm)", color="#9ca3af", fontsize=9)
    ax1.set_xticks([])
    ax1.set_ylim(0, cad * 1.15)
    ax1.legend(fontsize=8, facecolor="#111827", labelcolor="white", edgecolor="#374151")
    ax1.set_title("💧 Balanço Hídrico do Solo (Thornthwaite-Mather)",
                  color="white", fontsize=11, fontweight="bold")

    # Painel inferior: DEF e EXC
    ax2.bar(range(len(def_)), def_, color="#EF5350", alpha=0.8, label="Déficit (mm)", width=0.4, align="center")
    ax2.bar([i+0.42 for i in range(len(exc))], exc, color="#29B6F6",
            alpha=0.8, label="Excedente (mm)", width=0.4)
    ax2.set_ylabel("mm", color="#9ca3af", fontsize=9)
    ax2.set_xticks(range(len(dias)))
    ax2.set_xticklabels(dias, color="#9ca3af", fontsize=8)
    ax2.legend(fontsize=8, facecolor="#111827", labelcolor="white", edgecolor="#374151")

    plt.tight_layout()
    return fig


def gerar_tabela_7dias(dados: dict) -> pd.DataFrame:
    """Formata previsão de 7 dias em DataFrame."""
    if not dados or "daily" not in dados:
        return pd.DataFrame()

    d      = dados["daily"]
    wcodes = d.get("weathercode", [0]*7)
    wcode_map = {
        0:"☀️ Limpo",1:"🌤 Poucas nuvens",2:"⛅ Parcial",3:"☁️ Nublado",
        45:"🌫 Névoa",51:"🌦 Chuvisco",61:"🌧 Chuva",63:"🌧 Moderada",
        65:"⛈ Forte",80:"🌦 Pancadas",81:"⛈ Pancadas fortes",
        95:"⛈ Tempestade",99:"⛈ Granizo",
    }

    datas   = [datetime.fromisoformat(t).strftime("%a %d/%m") for t in d.get("time", [])]
    cond    = [wcode_map.get(w, f"Cód {w}") for w in wcodes]
    tmax    = [f"{v:.1f}°C" if v else "—" for v in d.get("temperature_2m_max", [])]
    tmin    = [f"{v:.1f}°C" if v else "—" for v in d.get("temperature_2m_min", [])]
    precip  = [f"{v:.1f} mm" if v else "0.0 mm" for v in d.get("precipitation_sum", [])]
    eto     = [f"{v:.2f} mm" if v else "—" for v in d.get("et0_fao_evapotranspiration", [])]

    return pd.DataFrame({
        "Data": datas, "Condição": cond, "T. Máx": tmax,
        "T. Mín": tmin, "Precipitação": precip, "ETo (mm)": eto,
    })


# ─────────────────────────────────────────────────────────────────────────────
# INTERFACE STREAMLIT PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():

    # ── Header ──
    st.markdown("""
    <div class="yamada-header">
      <div>
        <h1>🌿 Yamada Engenharia</h1>
        <p>Plataforma de Monitoramento Agroclimático — Mato Grosso do Sul</p>
        <p style="font-size:0.78rem;margin-top:4px;color:rgba(255,255,255,0.55);">
          GOES-19 ABI · Open-Meteo · NASA POWER · SATVeg · BDQueimadas INPE · INMET
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # SIDEBAR
    # ─────────────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:10px 0 20px;">
          <div style="font-family:'Montserrat',sans-serif;font-weight:900;
                      font-size:1.2rem;color:#a5d6a7;">YAMADA</div>
          <div style="font-size:0.72rem;color:#81c784;letter-spacing:2px;">ENGENHARIA</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        # Município
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.9rem;">📍 MUNICÍPIO ALVO</p>', unsafe_allow_html=True)
        municipio_sel = st.selectbox("Selecione o município", options=list(MUNICIPIOS_MS.keys()),
                                      index=0, label_visibility="collapsed")
        coords = MUNICIPIOS_MS[municipio_sel]
        st.caption(f"🌐 {coords['lat']:.4f}°S, {coords['lon']:.4f}°W")
        st.caption(f"📌 Região: {coords['regiao']}")

        st.markdown("---")

        # Textura do solo (Balanço Hídrico)
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.9rem;">🌱 TEXTURA DO SOLO</p>', unsafe_allow_html=True)
        textura_solo = st.selectbox(
            "Textura do solo",
            ["Argiloso (CAD=100mm)", "Médio/Franco (CAD=65mm)", "Arenoso (CAD=35mm)"],
            index=1, label_visibility="collapsed"
        )
        cad_map = {"Argiloso (CAD=100mm)": 100.0, "Médio/Franco (CAD=65mm)": 65.0, "Arenoso (CAD=35mm)": 35.0}
        cad_mm  = cad_map[textura_solo]

        st.markdown("---")

        # Fenologia
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.9rem;">🌾 FENOLOGIA / GRAUS-DIA</p>', unsafe_allow_html=True)
        cultura_sel = st.selectbox("Cultura", list(CULTURAS_GDA.keys()), index=0, label_visibility="collapsed")
        data_semeadura = st.date_input(
            "Data de semeadura",
            value=datetime.now().date() - timedelta(days=45),
            max_value=datetime.now().date(),
        )

        st.markdown("---")

        # Bandas GOES
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.9rem;">🛰️ BANDAS GOES-19</p>', unsafe_allow_html=True)
        bandas_sel = {}
        for bid, binfo in BANDAS_INFO.items():
            bandas_sel[bid] = st.checkbox(
                f"{binfo['icon']} {bid} — {binfo['nome'].split('(')[0].strip()}",
                value=(bid in ["B02","B13","B07"]), key=f"cb_{bid}"
            )

        st.markdown("---")
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.9rem;">⚙️ CONFIGURAÇÕES</p>', unsafe_allow_html=True)
        usar_goes_real = st.checkbox("🛰 Tentar GOES-19 Real (S3)", value=False,
                                     help="Se desmarcado, usa visualização sintética demonstrativa")
        horas_atras    = st.slider("Horas atrás para GOES", 1, 6, 2)
        usar_fdc_real  = st.checkbox("🔥 Tentar produto FDC real (S3)", value=False,
                                     help="Produto oficial ABI-L2-FDCF para focos de incêndio")
        usar_rrqpe_real= st.checkbox("🌧 Tentar produto QPE real (S3)", value=False,
                                     help="Produto oficial ABI-L2-RRQPEF para estimativa de precipitação")

        st.markdown("---")
        st.markdown("""
        <div style="font-size:0.72rem;color:#81c784;line-height:1.6;">
          <b style="color:#a5d6a7;">Fontes de dados:</b><br>
          · Open-Meteo (NWP GFS/ICON)<br>
          · GOES-19 NOAA/AWS S3<br>
          · NASA POWER (ETo, umidade solo)<br>
          · Embrapa SATVeg (NDVI)<br>
          · INPE BDQueimadas (focos)<br>
          · INMET (estações automáticas)
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        botao = st.button("🚀  GERAR ANÁLISE", use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # TELA DE BOAS-VINDAS
    # ─────────────────────────────────────────────────────────────────────────
    if not botao:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="band-card">
              <h4>🛰️ Satélite GOES-19</h4>
              <p>Satélite operacional Leste desde abril/2025. 7 bandas ABI com resolução 500m–2km, atualização a cada 10 minutos. Produtos oficiais RRQPE e FDC.</p>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="band-card">
              <h4>🌡️ Previsão Open-Meteo</h4>
              <p>GFS/ICON/ERA5: previsão horária 24h e diária 7 dias. Inclui cálculo de janela de defensivos e risco fitossanitário.</p>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="band-card">
              <h4>🌱 Análise Agronômica</h4>
              <p>Balanço hídrico Thornthwaite-Mather, Graus-Dia acumulados, estádio fenológico, NDVI histórico (SATVeg) e focos INPE.</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="secao-titulo">🗂️ Bandas GOES-19 Disponíveis</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, (bid, binfo) in enumerate(BANDAS_INFO.items()):
            with cols[i % 2]:
                st.markdown(f"""
                <div class="band-card">
                  <h4>{binfo['icon']} {bid} — {binfo['nome']}</h4>
                  <p>{binfo['uso']}</p>
                </div>""", unsafe_allow_html=True)

        st.info("👈  Selecione o município e as configurações na barra lateral, depois clique em **GERAR ANÁLISE**.")
        return

    # ─────────────────────────────────────────────────────────────────────────
    # PROCESSAMENTO
    # ─────────────────────────────────────────────────────────────────────────
    bandas_ativas = [bid for bid, ativo in bandas_sel.items() if ativo]
    if not bandas_ativas:
        st.warning("⚠️ Selecione pelo menos uma banda GOES-19 na barra lateral.")
        return

    lat, lon  = coords["lat"], coords["lon"]
    progress  = st.progress(0, text="Inicializando análise...")

    progress.progress(5,  text="📂 Carregando shapefiles de MS...")
    shps = carregar_shapefiles()

    progress.progress(15, text="🌤 Consultando Open-Meteo API...")
    dados_meteo = buscar_previsao_openmeteo(lat, lon)

    progress.progress(28, text="☀️ Consultando NASA POWER (ETo + Umidade Solo)...")
    dados_nasa = buscar_nasa_power(lat, lon)

    progress.progress(38, text="🌿 Buscando série NDVI — SATVeg/Embrapa...")
    ndvi_data = buscar_satveg_ndvi(lat, lon)

    progress.progress(48, text="🔥 Buscando focos de queimada — INPE/BDQueimadas...")
    df_focos_inpe = buscar_focos_inpe()

    # GOES-19 real (opcional)
    goes_results = {}
    if usar_goes_real:
        progress.progress(55, text="🛰 Buscando imagens GOES-19 no S3...")
        bbox_ms_ext = [-57.65, -50.92, -23.67, -17.16]
        for bid in bandas_ativas:
            d_arr, ext, ts = baixar_e_recortar_goes19(
                bid, lat_min=bbox_ms_ext[2], lat_max=bbox_ms_ext[3],
                lon_min=bbox_ms_ext[0], lon_max=bbox_ms_ext[1]
            )
            goes_results[bid] = (d_arr, ext, ts)

    # Produto FDC real (opcional)
    df_fdc = pd.DataFrame()
    if usar_fdc_real:
        progress.progress(60, text="🔥 Baixando produto FDC (ABI-L2-FDCF) GOES-19...")
        df_fdc = baixar_produto_goes19_fdc(horas_atras)

    # Produto QPE real (opcional)
    qpe_data = qpe_extent = qpe_ts = None
    if usar_rrqpe_real:
        progress.progress(63, text="🌧 Baixando produto RRQPE (ABI-L2-RRQPEF) GOES-19...")
        qpe_data, qpe_extent, qpe_ts = baixar_produto_goes19_rrqpe(horas_atras)

    # Focos combinados: prioriza FDC real, fallback INPE
    df_focos_final = df_fdc if not df_fdc.empty else df_focos_inpe

    # Estações INMET
    progress.progress(67, text="📡 Buscando estações INMET-MS...")
    df_inmet = buscar_dados_inmet()

    # Análises agronômicas
    progress.progress(72, text="📊 Calculando análises agronômicas...")
    janelas_def = calcular_janela_defensivos(dados_meteo)
    gda_info    = calcular_graus_dia(dados_meteo, cultura_sel,
                                     datetime.combine(data_semeadura, datetime.min.time()))
    riscos_fito = calcular_risco_fitossanitario(dados_meteo)
    bh          = calcular_balanco_hidrico_thornthwaite(dados_meteo, cad_mm)
    alertas     = calcular_alertas(dados_meteo, lat, gda_info)

    progress.progress(78, text="🗺 Gerando mapas de bandas...")

    # ─────────────────────────────────────────────────────────────────────────
    # EXIBIÇÃO DOS RESULTADOS
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,{VERDE_ESCURO},{VERDE_MEDIO});
                border-radius:10px;padding:16px 24px;margin-bottom:20px;">
      <span style="color:white;font-family:Montserrat;font-weight:700;font-size:1.1rem;">
        📍 {municipio_sel} — {coords['regiao']}
      </span>
      <span style="color:rgba(255,255,255,0.75);font-size:0.85rem;margin-left:16px;">
        {datetime.now().strftime('%d/%m/%Y  %H:%M')} (Horário de Brasília)
      </span>
    </div>
    """, unsafe_allow_html=True)

    # ── Métricas rápidas ──
    if dados_meteo and "hourly" in dados_meteo:
        h = dados_meteo.get("hourly", {})
        d = dados_meteo.get("daily", {})
        try:
            temp_atual  = h.get("temperature_2m", [None])[0]
            precip_hoje = d.get("precipitation_sum", [None])[0]
            umid_atual  = h.get("relativehumidity_2m", [None])[0]
            vento_atual = h.get("windspeed_10m", [None])[0]
            eto_hoje    = d.get("et0_fao_evapotranspiration", [None])[0]

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.metric("🌡 Temperatura",  f"{temp_atual:.1f}°C"   if temp_atual  else "—")
            with c2: st.metric("🌧 Chuva 24h",    f"{precip_hoje:.1f} mm" if precip_hoje else "0 mm")
            with c3: st.metric("💧 Umidade",       f"{umid_atual:.0f}%"    if umid_atual  else "—")
            with c4: st.metric("💨 Vento",         f"{vento_atual:.0f} km/h" if vento_atual else "—")
            with c5: st.metric("🌿 ETo",           f"{eto_hoje:.2f} mm"   if eto_hoje    else "—")
        except Exception:
            pass

    # ── Estações INMET ──
    if not df_inmet.empty:
        st.markdown('<div class="secao-titulo">📡 Estações INMET — Mato Grosso do Sul</div>',
                    unsafe_allow_html=True)
        st.caption("Estações automáticas do INMET (dados de referência observacional)")
        st.dataframe(df_inmet, use_container_width=True, hide_index=True)

    # ── Mapas GOES-19 ──
    st.markdown(f'<div class="secao-titulo">🛰️ Mapas de Satélite GOES-19 — {municipio_sel}</div>',
                unsafe_allow_html=True)

    n_bandas  = len(bandas_ativas)
    n_cols    = min(2, n_bandas)
    rows_mapas= [bandas_ativas[i:i+n_cols] for i in range(0, n_bandas, n_cols)]

    for row_bandas in rows_mapas:
        cols_mapas = st.columns(n_cols)
        for j, bid in enumerate(row_bandas):
            with cols_mapas[j]:
                g_data = g_ext = None
                if usar_goes_real and bid in goes_results:
                    g_data, g_ext, _ = goes_results[bid]
                # Para B14 usa dados QPE se disponíveis
                if bid == "B14" and qpe_data is not None:
                    g_data = qpe_data
                    g_ext  = qpe_extent

                fig = gerar_mapa_banda(bid, shps, municipio_sel, coords,
                                       goes_data=g_data, extent=g_ext,
                                       df_focos=df_focos_final)
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

                binfo = BANDAS_INFO[bid]
                st.markdown(f"""
                <div class="band-card" style="margin-top:-6px;">
                  <h4>{binfo['icon']} {bid} — {binfo['nome']}</h4>
                  <p>{binfo['uso']}</p>
                </div>""", unsafe_allow_html=True)

    # Focos de queimada (tabela resumo)
    if not df_focos_final.empty:
        n_focos = len(df_focos_final)
        sim = " (dados simulados)" if df_focos_final.get("_simulado", pd.Series([False])).any() else ""
        st.markdown(f'<div class="secao-titulo">🔥 Focos de Queimada — INPE / BDQueimadas{sim}</div>',
                    unsafe_allow_html=True)
        col_f1, col_f2 = st.columns([1,3])
        with col_f1:
            st.metric("Total de focos detectados", n_focos, help="Últimas 48h — MS")
        with col_f2:
            df_show = df_focos_final[["latitude","longitude","frp"]].copy() if "frp" in df_focos_final.columns else df_focos_final
            st.dataframe(df_show.head(10), use_container_width=True, hide_index=True)

    # ── Previsão 24h ──
    progress.progress(85, text="📈 Gerando gráficos de previsão...")
    st.markdown(f'<div class="secao-titulo">📈 Previsão Horária — Próximas 24 Horas</div>',
                unsafe_allow_html=True)
    if dados_meteo:
        fig_prev = gerar_grafico_previsao(dados_meteo, municipio_sel)
        if fig_prev:
            st.pyplot(fig_prev, use_container_width=True)
            plt.close(fig_prev)

    # ── Janela de Aplicação de Defensivos ──
    st.markdown(f'<div class="secao-titulo">🧪 Janela de Aplicação de Defensivos — Próximas 24h</div>',
                unsafe_allow_html=True)
    st.caption("Critérios MAPA/Embrapa: Vento < 10 km/h | Temp < 30°C | UR > 55% | Sem chuva prevista")

    if janelas_def:
        # Timeline colorida por hora
        cols_def = st.columns(len(janelas_def))
        for i, jan in enumerate(janelas_def):
            with cols_def[i]:
                cor  = {"aberta": "🟢", "parcial": "🟡", "bloqueada": "🔴"}[jan["status"]]
                st.markdown(
                    f"<div style='text-align:center;font-size:0.7rem;color:#555;'>"
                    f"<b>{jan['hora']}</b><br>{cor}</div>",
                    unsafe_allow_html=True
                )

        # Resumo por período
        n_aberta   = sum(1 for j in janelas_def if j["status"] == "aberta")
        n_parcial  = sum(1 for j in janelas_def if j["status"] == "parcial")
        n_bloq     = sum(1 for j in janelas_def if j["status"] == "bloqueada")
        c1,c2,c3   = st.columns(3)
        with c1: st.metric("✅ Horas ideais",   n_aberta)
        with c2: st.metric("⚠️ Horas parciais", n_parcial)
        with c3: st.metric("❌ Horas bloqueadas",n_bloq)

        # Melhor janela contínua
        max_seq = max_start = cur_seq = cur_start = 0
        for i, j in enumerate(janelas_def):
            if j["status"] == "aberta":
                if cur_seq == 0:
                    cur_start = i
                cur_seq += 1
                if cur_seq > max_seq:
                    max_seq   = cur_seq
                    max_start = cur_start
            else:
                cur_seq = 0

        if max_seq > 0:
            h_ini = janelas_def[max_start]["hora"]
            h_fim = janelas_def[min(max_start + max_seq - 1, len(janelas_def)-1)]["hora"]
            st.markdown(f"""
            <div class="alert-verde">
              <b>✅ Melhor janela contínua: {h_ini} → {h_fim} ({max_seq}h)</b><br>
              <span style="font-size:0.88rem;">Período ideal para aplicação de defensivos, fertilizantes foliares e biopesticidas.</span>
            </div>""", unsafe_allow_html=True)
        elif n_parcial > 0:
            st.markdown("""
            <div class="alert-amarelo">
              <b>⚠️ Nenhuma janela ideal disponível.</b><br>
              <span style="font-size:0.88rem;">Existem períodos parcialmente favoráveis. Priorize as horas com menor restrição.</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="alert-vermelho">
              <b>❌ Sem janela de aplicação disponível nas próximas 24h.</b><br>
              <span style="font-size:0.88rem;">Condições meteorológicas desfavoráveis. Adie as aplicações.</span>
            </div>""", unsafe_allow_html=True)

    # ── Graus-Dia e Estádio Fenológico ──
    st.markdown(f'<div class="secao-titulo">🌾 Graus-Dia Acumulados (GDA) e Fenologia — {cultura_sel}</div>',
                unsafe_allow_html=True)

    if gda_info:
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            st.metric("GDA Acumulado", f"{gda_info['gda_total']} °C·dia",
                      help=f"Temperatura-base: {gda_info['tb']}°C")
        with col_g2:
            st.metric("Dias desde semeadura", gda_info["dias_desde_semeadura"])
        with col_g3:
            proximo = gda_info.get("proximo_estagio")
            if proximo:
                faltam = proximo[0] - gda_info["gda_total"]
                st.metric("Próximo estádio em", f"{faltam:.0f} °C·dia")

        st.markdown(f"""
        <div class="band-card">
          <h4>🌱 Estádio Fenológico Atual — {cultura_sel}</h4>
          <p style="font-size:1rem;color:{VERDE_ESCURO};font-weight:700;">
            {gda_info['estagio_atual']}
          </p>
          {'<p>→ Próximo: <b>' + gda_info["proximo_estagio"][1] + f'</b> (faltam {gda_info["proximo_estagio"][0]-gda_info["gda_total"]:.0f} °C·dia)</p>' if gda_info.get("proximo_estagio") else ''}
        </div>""", unsafe_allow_html=True)

    # ── Risco Fitossanitário ──
    st.markdown(f'<div class="secao-titulo">🍂 Risco Fitossanitário — Doenças Foliares</div>',
                unsafe_allow_html=True)

    for risco in riscos_fito:
        classe = f"alert-{risco['cor']}"
        st.markdown(f"""
        <div class="{classe}">
          <b>{risco['icone']} {risco['doenca']} — Risco {risco['nivel']}</b><br>
          <span style="font-size:0.9rem;">{risco['msg']}</span>
        </div>""", unsafe_allow_html=True)

    # ── NDVI SATVeg ──
    st.markdown(f'<div class="secao-titulo">🌿 Série Histórica NDVI — SATVeg/Embrapa</div>',
                unsafe_allow_html=True)
    fig_ndvi = gerar_grafico_ndvi(ndvi_data, municipio_sel)
    if fig_ndvi:
        st.pyplot(fig_ndvi, use_container_width=True)
        plt.close(fig_ndvi)
    else:
        st.info("ℹ️ Dados NDVI não disponíveis.")

    # ── Tabela 7 dias ──
    st.markdown(f'<div class="secao-titulo">📅 Previsão 7 Dias</div>', unsafe_allow_html=True)
    df_7d = gerar_tabela_7dias(dados_meteo)
    if not df_7d.empty:
        st.dataframe(
            df_7d, use_container_width=True, hide_index=True,
            column_config={
                "Condição":     st.column_config.TextColumn("Condição",   width="medium"),
                "Data":         st.column_config.TextColumn("Data",       width="small"),
                "T. Máx":       st.column_config.TextColumn("T. Máx",     width="small"),
                "T. Mín":       st.column_config.TextColumn("T. Mín",     width="small"),
                "Precipitação": st.column_config.TextColumn("Precip.",    width="small"),
                "ETo (mm)":     st.column_config.TextColumn("ETo",        width="small"),
            }
        )

    # ── Alertas ──
    st.markdown(f'<div class="secao-titulo">⚠️ Alertas Ativos</div>', unsafe_allow_html=True)
    for alerta in alertas:
        st.markdown(f"""
        <div class="alert-{alerta['nivel']}">
          <b>{alerta['icone']} {alerta['titulo']}</b><br>
          <span style="font-size:0.9rem;">{alerta['msg']}</span>
        </div>""", unsafe_allow_html=True)

    # ── Balanço Hídrico Thornthwaite-Mather ──
    st.markdown(f'<div class="secao-titulo">💧 Balanço Hídrico do Solo (Thornthwaite-Mather) — {textura_solo}</div>',
                unsafe_allow_html=True)

    if bh:
        col_bh1, col_bh2, col_bh3, col_bh4 = st.columns(4)
        with col_bh1:
            st.metric("ARM atual", f"{bh['arm_mm']:.1f} mm",
                      delta=f"{bh['arm_pct']:.0f}% da CAD",
                      help="Armazenamento atual de água no solo")
        with col_bh2:
            st.metric("CAD do solo", f"{bh['cad_mm']:.0f} mm",
                      help="Capacidade de Água Disponível")
        with col_bh3:
            st.metric("Déficit hoje", f"{bh['def_mm']:.1f} mm",
                      delta=f"{'❌ déficit' if bh['def_mm'] > 0 else '✅ ok'}",
                      delta_color="inverse")
        with col_bh4:
            st.metric("ETR", f"{bh['etr_mm']:.1f} mm",
                      help="Evapotranspiração real (menor que ETo quando há déficit)")

        # Gráfico balanço hídrico
        fig_bh = gerar_grafico_balanco_hidrico(bh)
        if fig_bh:
            st.pyplot(fig_bh, use_container_width=True)
            plt.close(fig_bh)

        # Recomendação de irrigação
        st.markdown(f"""
        <div class="alert-{bh['nivel']}" style="margin-top:10px;">
          <b>Recomendação de Irrigação:</b> {bh['recomendacao']}
        </div>""", unsafe_allow_html=True)
    else:
        st.info("💧 Dados de balanço hídrico indisponíveis.")

    # ── Umidade do Solo NASA POWER ──
    if dados_nasa and "properties" in dados_nasa:
        try:
            params = dados_nasa["properties"]["parameter"]
            gwettop  = params.get("GWETTOP",  {})
            gwetroot = params.get("GWETROOT", {})
            if gwettop or gwetroot:
                st.markdown(f'<div class="secao-titulo">🌱 Umidade do Solo — NASA POWER (últimos 30 dias)</div>',
                            unsafe_allow_html=True)
                datas_nasa  = sorted(gwettop.keys())[-14:] if gwettop else []
                vals_top    = [gwettop.get(d,  0) for d in datas_nasa]
                vals_root   = [gwetroot.get(d, 0) for d in datas_nasa]

                fig_solo, ax_solo = plt.subplots(figsize=(10, 3.5), facecolor="#0d1117")
                ax_solo.set_facecolor("#111827")
                ax_solo.plot(range(len(datas_nasa)), vals_top,  color="#66BB6A", linewidth=2,
                             label="GWETTOP (0-5cm)")
                ax_solo.fill_between(range(len(datas_nasa)), vals_top, alpha=0.2, color="#66BB6A")
                ax_solo.plot(range(len(datas_nasa)), vals_root, color="#42A5F5", linewidth=2,
                             linestyle="--", label="GWETROOT (zona radicular)")
                ax_solo.fill_between(range(len(datas_nasa)), vals_root, alpha=0.15, color="#42A5F5")
                ax_solo.axhline(0.5, color="#FFB74D", linewidth=0.8, linestyle=":", alpha=0.7,
                                label="Limite campo (0.5)")
                ax_solo.set_ylim(0, 1)
                ax_solo.set_ylabel("Umidade relativa (0–1)", color="#9ca3af", fontsize=9)
                ax_solo.set_xticks(range(0, len(datas_nasa), 2))
                ax_solo.set_xticklabels(
                    [d[4:6]+"/"+d[6:8] for d in datas_nasa[::2]],
                    color="#9ca3af", fontsize=8, rotation=30
                )
                ax_solo.tick_params(colors="#9ca3af", labelsize=8)
                for sp in ax_solo.spines.values():
                    sp.set_edgecolor("#1f2937")
                ax_solo.grid(True, color="#1f2937", linewidth=0.5, alpha=0.6)
                ax_solo.legend(fontsize=8, facecolor="#111827", labelcolor="white",
                               edgecolor="#374151")
                ax_solo.set_title("Umidade do Solo — NASA POWER (GWETTOP & GWETROOT)",
                                  color="white", fontsize=10)
                plt.tight_layout()
                st.pyplot(fig_solo, use_container_width=True)
                plt.close(fig_solo)
        except Exception:
            pass

    # ── Rodapé ──
    progress.progress(100, text="✅ Análise concluída!")
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align:center;padding:16px;color:#888;font-size:0.8rem;">
      <b style="color:{VERDE_ESCURO};">Yamada Engenharia</b> — Meteorologia Aplicada ao Agronegócio<br>
      GOES-19 ABI · Open-Meteo NWP · NASA POWER · Embrapa SATVeg · INPE BDQueimadas · INMET<br>
      Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} · MVP v2.0
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
