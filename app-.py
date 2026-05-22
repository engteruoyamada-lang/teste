"""
=============================================================================
YAMADA ENGENHARIA — Plataforma de Monitoramento Agroclimático
MVP Streamlit | GOES-16/19 + Open-Meteo + NASA POWER
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
    color: #555;
    line-height: 1.4;
  }}

  /* Alertas */
  .alert-verde   {{ background:#e8f5e9; border-left:4px solid #43a047; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .alert-amarelo {{ background:#fff8e1; border-left:4px solid #fbc02d; border-radius:8px; padding:12px 16px; margin:6px 0; }}
  .alert-vermelho{{ background:#ffebee; border-left:4px solid #e53935; border-radius:8px; padding:12px 16px; margin:6px 0; }}

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

  /* Sidebar */
  section[data-testid="stSidebar"] {{
    background-color: white;
    border-right: 1px solid #e0e8e0;
  }}
  section[data-testid="stSidebar"] .stSelectbox label,
  section[data-testid="stSidebar"] .stSlider label {{
    font-family: 'Montserrat', sans-serif;
    font-weight: 600;
    font-size: 0.85rem;
    color: {VERDE_ESCURO};
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

BANDAS_INFO = {
    "B02": {
        "nome": "Vermelho Visível (0,64µm)", "icon": "☀️", "cmap": "gray", "cor_card": "#388e3c",
        "uso": "Cobertura de nuvens, frentes de chuva — Só diurno",
        "descricao": (
            "A Banda 2 é a de maior resolução espacial do GOES-16, com 500 metros por pixel — o dobro "
            "da resolução das demais bandas visíveis. Opera exclusivamente durante o período diurno, "
            "captando a luz solar refletida pela superfície e pelas nuvens. "
            "Na agricultura, é usada para identificar a chegada de frentes frias e sistemas de chuva "
            "com grande detalhe visual, monitorar a progressão de nuvens convectivas sobre lavouras "
            "e compor imagens coloridas (RGB) de alta qualidade para o boletim visual. "
            "Pixels muito brancos indicam nuvens espessas com alta refletância — potencial de chuva. "
            "Pixels escuros sobre terra indicam solo exposto ou vegetação com baixa reflectância."
        ),
        "interpretacao": "Branco intenso = nuvem densa | Cinza médio = nuvem fina ou cirro | Escuro = superfície livre",
    },
    "B03": {
        "nome": "Veggie Band – NIR (0,86µm)", "icon": "🌿", "cmap": "YlGn", "cor_card": "#2e7d32",
        "uso": "Saúde da vegetação, estresse hídrico, queimadas recentes",
        "descricao": (
            "Chamada de 'Veggie Band' por ser extremamente sensível à reflectância da vegetação saudável. "
            "A clorofila reflete fortemente no infravermelho próximo: lavouras bem irrigadas e com boa "
            "cobertura vegetal aparecem muito brilhantes nessa banda. Em contraste, áreas com estresse "
            "hídrico, culturas em senescência, solo exposto pós-colheita ou regiões queimadas recentemente "
            "aparecem escuras. É a base para índices como o NDVI quando combinada com a B02. "
            "Para o produtor: valores altos = lavoura em bom estado; queda súbita de brilho numa área "
            "pode indicar início de seca localizada ou passagem de fogo."
        ),
        "interpretacao": "Verde intenso = vegetação saudável | Amarelo = estresse moderado | Escuro = solo exposto ou queimada",
    },
    "B07": {
        "nome": "IR Onda Curta (3,9µm)", "icon": "🔥", "cmap": "hot", "cor_card": "#bf360c",
        "uso": "Focos de incêndio em tempo quase real, nevoeiro matinal",
        "descricao": (
            "A Banda 7 opera na faixa do infravermelho de onda curta e possui sensibilidade excepcional "
            "a fontes de calor intenso. Um foco de incêndio ativo, mesmo pequeno (~ 1 hectare), satura "
            "completamente essa banda, aparecendo como pixel branco brilhante sobre o fundo escuro do "
            "dossel. É a principal banda para detecção de queimadas em tempo quase real — fundamental "
            "para o MS, onde o fogo avança rapidamente sobre pastagens e cana-de-açúcar no período seco. "
            "Durante a madrugada e início da manhã, também detecta nevoeiro radiativo sobre várzeas e "
            "baixadas — dado crítico para o produtor que planeja operações de pulverização aérea."
        ),
        "interpretacao": "Branco/vermelho = foco de calor ativo | Cinza quente = superfície aquecida | Escuro = área fria ou vegetação",
    },
    "B09": {
        "nome": "Vapor d'Água Médio (6,9µm)", "icon": "💧", "cmap": "Blues_r", "cor_card": "#1565c0",
        "uso": "Umidade atmosférica, sistemas convectivos 24–72h",
        "descricao": (
            "Essa banda não enxerga a superfície — ela monitora a concentração de vapor d'água em "
            "camadas médias da atmosfera (entre 300 e 600 hPa, ou ~4.000 a 9.000 metros de altitude). "
            "Regiões úmidas aparecem escuras (alta absorção); regiões secas aparecem claras. "
            "Quando uma pluma de umidade avança sobre o MS vinda da Amazônia ou do oceano Atlântico, "
            "ela aparece como um 'rio' escuro no campo de vapor d'água — sinal de que chuva organizada "
            "está se formando nas próximas 24 a 72 horas. É a banda usada por meteorologistas para "
            "identificar a ZCAS (Zona de Convergência do Atlântico Sul) e sistemas frontais em "
            "desenvolvimento — os maiores produtores de chuva no Centro-Oeste."
        ),
        "interpretacao": "Escuro = ar úmido (chuva provável) | Claro = ar seco | Padrão espiral = ciclone extratropical",
    },
    "B11": {
        "nome": "IR Termal (8,4µm)", "icon": "❄️", "cmap": "RdBu", "cor_card": "#6a1b9a",
        "uso": "Temperatura superficial, risco de geada, nuvens baixas",
        "descricao": (
            "A Banda 11 capta a emissão térmica da superfície do solo e das nuvens baixas com alta "
            "sensibilidade a variações de temperatura. É a banda primária para monitoramento de risco "
            "de geada: quando a temperatura radiativa da superfície cai abaixo de 0°C em áreas sem "
            "cobertura de nuvens, o alerta de geada é acionado. Essencial para produtores de café, "
            "citros, cana-de-açúcar e horticultura no sul do MS. "
            "Também diferencia nuvens baixas (stratus) de médias e altas — as stratus são mais quentes "
            "que os cirros, e sua presença inibe o resfriamento noturno, protegendo as lavouras. "
            "Superfícies aquecidas pelo sol (solo exposto, asfalto) aparecem quentes; florestas e "
            "corpos d'água mantêm temperaturas mais estáveis."
        ),
        "interpretacao": "Azul = superfície fria (risco de geada) | Vermelho = superfície quente | Branco = nuvem alta e gelada",
    },
    "B13": {
        "nome": "IR Clean (10,3µm)", "icon": "⛈️", "cmap": "inferno_r", "cor_card": "#e65100",
        "uso": "Topo de nuvens, alertas de tempestade severa e granizo",
        "descricao": (
            "A Banda 13 é a espinha dorsal do monitoramento convectivo operacional. Mede a temperatura "
            "de brilho (Tb) do topo das nuvens com alta precisão — quanto mais fria a nuvem, mais alta "
            "e intensa ela é. Topos de tempestades severas atingem –60°C a –80°C, indicando nuvens "
            "que ultrapassam 12 km de altitude com forte corrente ascendente, alta probabilidade de "
            "granizo e rajadas de vento superiores a 100 km/h. "
            "O realce T (Enhanced-V) aplicado nessa banda destaca em cores frias (azul/roxo) as regiões "
            "com Tb < –50°C — exatamente onde o risco de tempestade severa é máximo. "
            "É também a banda base para os algoritmos de QPE por satélite e para a composição de "
            "produtos RGB de fase de nuvens. Na imagem abaixo, a animação mostra a evolução temporal "
            "do sistema convectivo sobre o município selecionado."
        ),
        "interpretacao": "Amarelo/branco = topo quente (nuvem baixa, fraca) | Vermelho = topo frio (–40°C) | Roxo/azul = topo glacial (–60°C, tempestade severa)",
    },
    "B14": {
        "nome": "IR Longo – QPE (11,2µm)", "icon": "🌧️", "cmap": "Blues", "cor_card": "#0277bd",
        "uso": "Estimativa de precipitação (QPE) — mm de chuva estimados",
        "descricao": (
            "A Banda 14 é ligeiramente mais longa que a B13 e possui menor interferência de vapor "
            "d'água atmosférico, tornando-a ideal para estimar a quantidade de chuva que cai em uma "
            "determinada área — processo chamado de QPE (Quantitative Precipitation Estimation). "
            "O algoritmo converte a temperatura do topo de nuvem em mm de chuva estimada: topos mais "
            "frios geram mais chuva. Produtos como o IMERG da NASA e o MERGE do INMET usam essa "
            "relação como base. "
            "No boletim da Yamada Engenharia, os valores de QPE aparecem como 'choveu X mm na região "
            "nas últimas 6 horas' — dado gerado a partir dessa banda combinada com dados de pluviômetros "
            "via ajuste por fusão de dados (blending). Quanto mais azul escuro o pixel, maior a chuva estimada."
        ),
        "interpretacao": "Azul escuro = chuva intensa estimada (> 20 mm/h) | Azul claro = chuva fraca | Branco = sem chuva (nuvem quente ou céu limpo)",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE COLETA DE DADOS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def buscar_previsao_openmeteo(lat: float, lon: float) -> dict:
    """Coleta previsão horária (24h) e diária (7 dias) via Open-Meteo."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,precipitation,relativehumidity_2m,windspeed_10m,shortwave_radiation"
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
    """Coleta dados de ETo e radiação solar via NASA POWER."""
    fim   = datetime.now()
    inicio = fim - timedelta(days=30)
    url = (
        f"https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=T2M,RH2M,ALLSKY_SFC_SW_DWN,WS10M,PRECTOTCORR"
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


def listar_arquivos_goes(banda: str, horas_atras: int = 1) -> list:
    """Lista arquivos GOES-16 no S3 para uma banda específica."""
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")
    agora = datetime.now(timezone.utc) - timedelta(hours=horas_atras)
    dia_do_ano = agora.timetuple().tm_yday
    # Produto CMIP (Cloud and Moisture Imagery) Full Disk
    num_banda = banda.replace("B", "")
    prefix = f"ABI-L2-CMIPF/{agora.year}/{dia_do_ano:03d}/{agora.hour:02d}/"
    try:
        resp = s3.list_objects_v2(Bucket="noaa-goes16", Prefix=prefix, MaxKeys=30)
        arquivos = [
            obj["Key"] for obj in resp.get("Contents", [])
            if f"_C{num_banda.zfill(2)}_" in obj["Key"]
        ]
        return arquivos[:3]
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def baixar_e_recortar_goes(banda: str, lat_min: float, lat_max: float,
                            lon_min: float, lon_max: float) -> tuple:
    """
    Baixa arquivo GOES-16 do S3 e retorna array recortado para a bbox do MS.
    Retorna (data_array, extent, timestamp) ou (None, None, None) se falhar.
    """
    arquivos = listar_arquivos_goes(banda)
    if not arquivos:
        return None, None, None

    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")
    chave = arquivos[0]

    try:
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
            s3.download_fileobj("noaa-goes16", chave, tmp)
            tmp_path = tmp.name

        dataset = nc.Dataset(tmp_path)

        # Leitura da projeção GOES
        proj_info = dataset.variables["goes_imager_projection"]
        lon_origin = proj_info.longitude_of_projection_origin
        H = proj_info.perspective_point_height + proj_info.semi_major_axis
        r_eq = proj_info.semi_major_axis
        r_pol = proj_info.semi_minor_axis

        # Ângulos de varredura (radianos)
        x_rad = dataset.variables["x"][:] * proj_info.perspective_point_height
        y_rad = dataset.variables["y"][:] * proj_info.perspective_point_height

        # Conversão para lat/lon
        lambda_0 = np.deg2rad(lon_origin)
        a_var = np.sin(x_rad)**2 + (np.cos(x_rad)**2 * (np.cos(y_rad)**2 + (r_eq**2 / r_pol**2) * np.sin(y_rad)**2))
        b_var = -2 * H * np.cos(x_rad) * np.cos(y_rad)
        c_var = H**2 - r_eq**2
        r_s = (-b_var - np.sqrt(b_var**2 - 4*a_var*c_var)) / (2*a_var)

        s_x = r_s * np.cos(x_rad) * np.cos(y_rad)
        s_y = -r_s * np.sin(x_rad)
        s_z = r_s * np.cos(x_rad) * np.sin(y_rad)

        lat = np.rad2deg(np.arctan((r_eq**2 / r_pol**2) * (s_z / np.sqrt((H - s_x)**2 + s_y**2))))
        lon = np.rad2deg(lambda_0 - np.arctan(s_y / (H - s_x)))

        # Dado principal
        var_name = "CMI"
        data = dataset.variables[var_name][:]

        # Máscara de recorte para MS
        mask_lat = (lat >= lat_min) & (lat <= lat_max)
        mask_lon = (lon >= lon_min) & (lon <= lon_max)
        mask = mask_lat & mask_lon

        if not np.any(mask):
            dataset.close()
            os.unlink(tmp_path)
            return None, None, None

        rows = np.where(mask.any(axis=1))[0]
        cols = np.where(mask.any(axis=0))[0]
        data_recortado = data[rows[0]:rows[-1]+1, cols[0]:cols[-1]+1]

        ts = datetime.strptime(chave.split("_s")[1][:13], "%Y%j%H%M%S")
        extent = [lon_min, lon_max, lat_min, lat_max]

        dataset.close()
        os.unlink(tmp_path)
        return np.array(data_recortado), extent, ts

    except Exception as e:
        return None, None, None


# ─────────────────────────────────────────────────────────────────────────────
# CARREGAMENTO DOS SHAPEFILES
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def carregar_shapefiles():
    """
    Carrega 5 shapefiles de MS via IBGE (GeoJSON público).
    Substitua pelos seus shapefiles locais se preferir.
    Retorna dict com GeoDataFrames.
    """
    shps = {}

    # 1. Municípios de MS
    try:
        url_municipios = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-50-mun.json"
        gdf = gpd.read_file(url_municipios)
        shps["municipios"] = gdf
    except Exception:
        # Fallback: cria bbox simplificada do MS
        from shapely.geometry import box
        gdf = gpd.GeoDataFrame(
            {"name": ["Mato Grosso do Sul"]},
            geometry=[box(-57.65, -23.67, -50.92, -17.16)],
            crs="EPSG:4326"
        )
        shps["municipios"] = gdf

    # 2. Mesorregiões/biomas via simulação (substitua por seus shapefiles)
    # Aqui criamos regiões simplificadas do MS para demonstração
    from shapely.geometry import Polygon
    regioes = {
        "Pantanal":   Polygon([(-57.65,-19.5),(-55.5,-19.5),(-55.5,-17.16),(-57.65,-17.16)]),
        "Cerrado":    Polygon([(-55.5,-19.5),(-50.92,-19.5),(-50.92,-17.16),(-55.5,-17.16)]),
        "Campo/Agro": Polygon([(-57.65,-23.67),(-53.5,-23.67),(-53.5,-19.5),(-57.65,-19.5)]),
        "Transição":  Polygon([(-53.5,-23.67),(-50.92,-23.67),(-50.92,-19.5),(-53.5,-19.5)]),
    }
    gdf_bio = gpd.GeoDataFrame(
        {"bioma": list(regioes.keys())},
        geometry=list(regioes.values()),
        crs="EPSG:4326"
    )
    shps["biomas"] = gdf_bio

    # 3. Hidrografia principal (rios simulados por linhas)
    from shapely.geometry import LineString
    rios = {
        "Rio Paraguai":    LineString([(-57.65,-19.0),(-56.5,-20.5),(-57.2,-22.0)]),
        "Rio Paraná":      LineString([(-53.5,-20.0),(-52.0,-22.5),(-50.92,-23.0)]),
        "Rio Miranda":     LineString([(-55.5,-19.5),(-56.5,-20.5),(-57.0,-21.0)]),
        "Rio Verde":       LineString([(-54.5,-19.0),(-54.0,-21.0),(-53.8,-22.5)]),
    }
    gdf_rios = gpd.GeoDataFrame(
        {"nome": list(rios.keys())},
        geometry=list(rios.values()),
        crs="EPSG:4326"
    )
    shps["hidrografia"] = gdf_rios

    # 4. Rodovias principais (simuladas)
    from shapely.geometry import LineString
    rodovias = {
        "BR-163": LineString([(-55.3,-17.2),(-54.9,-20.4),(-55.0,-23.0)]),
        "BR-262": LineString([(-57.4,-19.0),(-54.6,-20.4),(-51.0,-20.8)]),
        "BR-060": LineString([(-54.0,-17.8),(-54.6,-20.4),(-54.0,-23.5)]),
    }
    gdf_rod = gpd.GeoDataFrame(
        {"rodovia": list(rodovias.keys())},
        geometry=list(rodovias.values()),
        crs="EPSG:4326"
    )
    shps["rodovias"] = gdf_rod

    # 5. Áreas de risco de queimada (simuladas como polígonos)
    from shapely.geometry import Polygon
    import random
    random.seed(42)
    areas_risco = []
    geoms_risco = []
    for i in range(8):
        cx = random.uniform(-57.0, -51.5)
        cy = random.uniform(-23.0, -17.5)
        r = random.uniform(0.2, 0.6)
        pts = [(cx + r*np.cos(a), cy + r*np.sin(a)) for a in np.linspace(0, 2*np.pi, 10)]
        areas_risco.append({"id": i+1, "nivel_risco": random.choice(["Médio","Alto","Crítico"])})
        geoms_risco.append(Polygon(pts))

    gdf_risco = gpd.GeoDataFrame(areas_risco, geometry=geoms_risco, crs="EPSG:4326")
    shps["risco_queimada"] = gdf_risco

    return shps


# ─────────────────────────────────────────────────────────────────────────────
# GERAÇÃO DOS MAPAS
# ─────────────────────────────────────────────────────────────────────────────

def gerar_mapa_banda(
    banda_id: str,
    shps: dict,
    municipio: str,
    coords: dict,
    goes_data=None,
    extent=None,
) -> plt.Figure:
    """Gera um mapa para uma banda GOES-16 com overlays dos shapefiles."""

    info = BANDAS_INFO[banda_id]
    lat, lon = coords["lat"], coords["lon"]

    # Extent do mapa: foco no MS com margem
    bbox_ms = [-57.65, -50.92, -23.67, -17.16]  # lon_min, lon_max, lat_min, lat_max

    fig, ax = plt.subplots(figsize=(9, 7), facecolor=PRETO)
    ax.set_facecolor("#0d1117")

    # ── Fundo de imagem GOES (se disponível) ou gradiente sintético ──
    if goes_data is not None and extent is not None:
        img = ax.imshow(
            goes_data,
            extent=extent,
            cmap=info["cmap"],
            origin="upper",
            alpha=0.85,
            aspect="auto",
            vmin=np.nanpercentile(goes_data, 2),
            vmax=np.nanpercentile(goes_data, 98),
        )
        cbar = plt.colorbar(img, ax=ax, fraction=0.03, pad=0.01)
        cbar.ax.yaxis.label.set_color("white")
        cbar.ax.tick_params(colors="white")
        cbar.set_label(info["nome"], color="white", fontsize=8)
    else:
        # Simulação visual sintética quando GOES não disponível
        x = np.linspace(bbox_ms[0], bbox_ms[1], 300)
        y = np.linspace(bbox_ms[2], bbox_ms[3], 300)
        X, Y = np.meshgrid(x, y)
        np.random.seed(int(banda_id.replace("B","")))

        if banda_id in ["B07", "B13"]:
            # Dados termais: gradiente com ruído
            Z = np.sin(X*0.4)*np.cos(Y*0.4) * 30 + 280 + np.random.normal(0, 5, X.shape)
        elif banda_id in ["B09"]:
            # Vapor d'água: campo mais suave
            Z = np.cos(X*0.3 + Y*0.2) * 20 + 250 + np.random.normal(0, 3, X.shape)
        elif banda_id in ["B02", "B03"]:
            # Visível/NIR: reflexão
            Z = (np.abs(np.sin(X*0.5)*np.cos(Y*0.6)) * 0.6 + 0.1 +
                 np.random.normal(0, 0.05, X.shape)).clip(0, 1)
        else:
            Z = np.sin(X*0.35)*np.cos(Y*0.35) * 25 + 270 + np.random.normal(0, 4, X.shape)

        img = ax.pcolormesh(X, Y, Z, cmap=info["cmap"], shading="auto", alpha=0.9)
        cbar = plt.colorbar(img, ax=ax, fraction=0.03, pad=0.01)
        cbar.set_label(info["nome"], color="white", fontsize=8)
        cbar.ax.tick_params(colors="white")
        ax.text(
            0.02, 0.02,
            "⚠ Imagem GOES simulada (S3 indisponível no ambiente atual)",
            transform=ax.transAxes, fontsize=7, color="yellow", alpha=0.8,
            va="bottom"
        )

    # ── Overlay: Municípios ──
    try:
        gdf_mun = shps["municipios"]
        if "geometry" in gdf_mun.columns:
            gdf_mun.boundary.plot(ax=ax, color="white", linewidth=0.4, alpha=0.5)

        # Destaque do município selecionado
        nome_col = next((c for c in gdf_mun.columns if "nome" in c.lower() or "name" in c.lower()), None)
        if nome_col:
            sel = gdf_mun[gdf_mun[nome_col].str.upper() == municipio.upper()]
            if not sel.empty:
                sel.plot(ax=ax, facecolor="none", edgecolor=VERDE_MEDIO, linewidth=2.0, alpha=0.9)
                sel.plot(ax=ax, facecolor=VERDE_MEDIO, alpha=0.15)
    except Exception:
        pass

    # ── Overlay: Biomas ──
    try:
        shps["biomas"].boundary.plot(ax=ax, color="#88BB88", linewidth=0.8, linestyle="--", alpha=0.5)
    except Exception:
        pass

    # ── Overlay: Hidrografia ──
    try:
        shps["hidrografia"].plot(ax=ax, color="#4FC3F7", linewidth=1.0, alpha=0.7, label="Rios")
    except Exception:
        pass

    # ── Overlay: Rodovias ──
    try:
        shps["rodovias"].plot(ax=ax, color="#FFB74D", linewidth=0.8, linestyle="-", alpha=0.6)
    except Exception:
        pass

    # ── Overlay: Risco de queimada (apenas em B07 e B03) ──
    if banda_id in ["B07", "B03"]:
        try:
            gdf_risco = shps["risco_queimada"]
            cores_risco = {"Médio": "#FFF176", "Alto": "#FF8A65", "Crítico": "#EF5350"}
            for _, row in gdf_risco.iterrows():
                cor = cores_risco.get(row["nivel_risco"], "#EF5350")
                gpd.GeoDataFrame([row], geometry="geometry", crs="EPSG:4326").plot(
                    ax=ax, facecolor=cor, alpha=0.5, edgecolor=cor, linewidth=1
                )
        except Exception:
            pass

    # ── Marcador do município selecionado ──
    ax.plot(lon, lat, marker="*", color=VERDE_MEDIO, markersize=14, zorder=10,
            markeredgecolor="white", markeredgewidth=1.2)
    ax.annotate(
        f" {municipio}",
        (lon, lat), fontsize=9, color="white", fontweight="bold",
        xytext=(6, 6), textcoords="offset points",
        bbox=dict(boxstyle="round,pad=0.3", facecolor=VERDE_ESCURO, alpha=0.8, edgecolor="none"),
        zorder=11
    )

    # ── Limites do mapa ──
    margem = 0.5
    ax.set_xlim(bbox_ms[0] - margem, bbox_ms[1] + margem)
    ax.set_ylim(bbox_ms[2] - margem, bbox_ms[3] + margem)

    # ── Título da banda ──
    ax.set_title(
        f"{info['icon']}  {info['nome']}\n{info['uso']}",
        color="white", fontsize=10, fontweight="bold", pad=10,
        fontfamily="monospace"
    )

    # ── Grade e eixos ──
    ax.set_xlabel("Longitude", color="#aaaaaa", fontsize=8)
    ax.set_ylabel("Latitude", color="#aaaaaa", fontsize=8)
    ax.tick_params(colors="#aaaaaa", labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")
    ax.grid(True, color="#222222", linewidth=0.4, alpha=0.5)

    # ── Escala / Norte ──
    ax.annotate("N ▲", xy=(0.97, 0.95), xycoords="axes fraction",
                ha="right", va="top", color="white", fontsize=11, fontweight="bold")

    # ── Legenda (biomas / rios) ──
    handles = [
        mpatches.Patch(facecolor="none", edgecolor="white", linewidth=0.4, label="Municípios MS"),
        mpatches.Patch(facecolor="none", edgecolor=VERDE_MEDIO, linewidth=1.5, label=f"▶ {municipio}"),
        mpatches.Patch(facecolor="#4FC3F7", alpha=0.7, label="Rios principais"),
        mpatches.Patch(facecolor="#FFB74D", alpha=0.6, label="Rodovias (BR)"),
    ]
    if banda_id in ["B07", "B03"]:
        handles += [
            mpatches.Patch(facecolor="#FFF176", alpha=0.5, label="Risco Médio"),
            mpatches.Patch(facecolor="#FF8A65", alpha=0.5, label="Risco Alto"),
            mpatches.Patch(facecolor="#EF5350", alpha=0.5, label="Risco Crítico"),
        ]

    leg = ax.legend(handles=handles, loc="lower left", fontsize=7,
                    framealpha=0.75, facecolor="#0d1117", labelcolor="white",
                    edgecolor="#333333", ncol=2)

    # ── Rodapé Yamada ──
    fig.text(0.01, 0.005,
             f"Yamada Engenharia  •  GOES-16 ABI  •  {datetime.now().strftime('%d/%m/%Y %H:%M')} UTC-4",
             color="#888888", fontsize=7, va="bottom")

    plt.tight_layout(pad=0.5)
    return fig


def gerar_grafico_previsao(dados: dict, municipio: str) -> plt.Figure:
    """Gera gráfico combinado: precipitação 24h + temperatura."""
    if not dados or "hourly" not in dados:
        return None

    h = dados["hourly"]
    times_raw = h.get("time", [])[:24]
    precip    = h.get("precipitation", [0]*24)[:24]
    temp      = h.get("temperature_2m", [20]*24)[:24]
    umid      = h.get("relativehumidity_2m", [60]*24)[:24]
    vento     = h.get("windspeed_10m", [0]*24)[:24]

    horas = [t.split("T")[1][:5] if "T" in t else t[-5:] for t in times_raw]
    idx = list(range(len(horas)))

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), facecolor="#0d1117",
                              gridspec_kw={"height_ratios": [2, 2, 1.2]})
    fig.suptitle(
        f"⏱  Previsão 24 Horas — {municipio}",
        color="white", fontsize=13, fontweight="bold", y=0.98
    )

    for ax in axes:
        ax.set_facecolor("#111827")
        ax.tick_params(colors="#9ca3af", labelsize=8)
        for sp in ax.spines.values():
            sp.set_edgecolor("#1f2937")
        ax.grid(True, color="#1f2937", linewidth=0.5, alpha=0.8)

    # ── Painel 1: Precipitação (barras) ──
    ax1 = axes[0]
    cores_pp = [VERDE_MEDIO if p < 5 else AMARELO_ALERT if p < 20 else VERMELHO_ALRT for p in precip]
    ax1.bar(idx, precip, color=cores_pp, alpha=0.85, width=0.7, edgecolor="none")
    ax1.set_ylabel("Precipitação (mm)", color="#9ca3af", fontsize=9)
    ax1.set_xticks([])
    total_pp = sum(p for p in precip if p)
    ax1.text(0.99, 0.92, f"Total 24h: {total_pp:.1f} mm",
             transform=ax1.transAxes, ha="right", color="white", fontsize=9,
             bbox=dict(facecolor=VERDE_ESCURO, alpha=0.7, boxstyle="round,pad=0.3"))

    # ── Painel 2: Temperatura + Umidade ──
    ax2 = axes[1]
    ax2b = ax2.twinx()
    line_t = ax2.plot(idx, temp, color="#f97316", linewidth=2.2, label="Temp (°C)", zorder=5)
    ax2.fill_between(idx, temp, alpha=0.15, color="#f97316")
    line_u = ax2b.plot(idx, umid, color="#38bdf8", linewidth=1.8,
                       linestyle="--", label="Umidade (%)", zorder=4)
    ax2b.fill_between(idx, umid, alpha=0.07, color="#38bdf8")
    ax2.set_ylabel("Temperatura (°C)", color="#f97316", fontsize=9)
    ax2b.set_ylabel("Umidade (%)", color="#38bdf8", fontsize=9)
    ax2b.tick_params(colors="#38bdf8", labelsize=8)
    ax2.set_xticks([])
    lines = line_t + line_u
    labs  = [l.get_label() for l in lines]
    ax2.legend(lines, labs, loc="upper right", fontsize=8,
               facecolor="#111827", labelcolor="white", edgecolor="#374151")

    # ── Painel 3: Vento ──
    ax3 = axes[2]
    ax3.plot(idx, vento, color="#a78bfa", linewidth=1.6, label="Vento (km/h)")
    ax3.fill_between(idx, vento, alpha=0.15, color="#a78bfa")
    ax3.set_ylabel("Vento (km/h)", color="#a78bfa", fontsize=9)
    ax3.set_xticks(idx[::2])
    ax3.set_xticklabels(horas[::2], rotation=45, ha="right", fontsize=7, color="#9ca3af")

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    return fig


def gerar_tabela_7dias(dados: dict) -> pd.DataFrame:
    """Formata previsão de 7 dias em DataFrame."""
    if not dados or "daily" not in dados:
        return pd.DataFrame()

    d = dados["daily"]
    wcodes = d.get("weathercode", [0]*7)

    wcode_map = {
        0: "☀️ Limpo", 1: "🌤 Poucas nuvens", 2: "⛅ Parcialmente nublado",
        3: "☁️ Nublado", 45: "🌫 Névoa", 51: "🌦 Chuvisco",
        61: "🌧 Chuva", 63: "🌧 Chuva moderada", 65: "⛈ Chuva forte",
        80: "🌦 Pancadas", 81: "⛈ Pancadas fortes", 95: "⛈ Tempestade",
        99: "⛈ Tempestade c/ granizo"
    }

    datas = [datetime.fromisoformat(t).strftime("%a %d/%m") for t in d.get("time", [])]
    condicao = [wcode_map.get(w, f"Cód {w}") for w in wcodes]
    tmax = [f"{v:.1f}°C" if v else "—" for v in d.get("temperature_2m_max", [])]
    tmin = [f"{v:.1f}°C" if v else "—" for v in d.get("temperature_2m_min", [])]
    precip = [f"{v:.1f} mm" if v else "0.0 mm" for v in d.get("precipitation_sum", [])]
    eto = [f"{v:.2f} mm" if v else "—" for v in d.get("et0_fao_evapotranspiration", [])]

    return pd.DataFrame({
        "Data": datas,
        "Condição": condicao,
        "T. Máx": tmax,
        "T. Mín": tmin,
        "Precipitação": precip,
        "ETo (mm)": eto,
    })


def calcular_alertas(dados: dict, lat: float) -> list:
    """Gera lista de alertas com base nos dados de previsão."""
    alertas = []
    if not dados or "daily" not in dados:
        return alertas

    d   = dados["daily"]
    h   = dados.get("hourly", {})

    tmin = d.get("temperature_2m_min", [20]*7)
    precip_diario = d.get("precipitation_sum", [0]*7)
    wcode = d.get("weathercode", [0]*7)
    precip_horario = h.get("precipitation", [0]*24)

    # Risco de geada (regiões sul/MS com T < 5°C)
    for i, t in enumerate(tmin[:3]):
        if t is not None and t < 5:
            nivel = "🔴 EMERGÊNCIA" if t < 2 else "🟡 ALERTA"
            alertas.append({
                "nivel": "vermelho" if t < 2 else "amarelo",
                "icone": "❄️",
                "titulo": f"{nivel} — Risco de Geada",
                "msg": f"Temperatura mínima prevista de {t:.1f}°C em {i+1} dia(s). Proteja culturas sensíveis."
            })

    # Chuva intensa
    for i, pp in enumerate(precip_diario[:3]):
        if pp is not None and pp > 40:
            alertas.append({
                "nivel": "vermelho" if pp > 80 else "amarelo",
                "icone": "⛈️",
                "titulo": f"{'🔴 EMERGÊNCIA' if pp > 80 else '🟡 ALERTA'} — Chuva Intensa",
                "msg": f"{pp:.0f} mm previstos em 24h. Risco de enxurrada e encharcamento. Suspenda pulverizações."
            })

    # Tempestade severa
    for i, wc in enumerate(wcode[:3]):
        if wc in [95, 99]:
            alertas.append({
                "nivel": "vermelho",
                "icone": "⚡",
                "titulo": "🔴 EMERGÊNCIA — Tempestade Severa",
                "msg": f"Tempestade com raios prevista em {i+1} dia(s). Risco de granizo e ventos > 60 km/h."
            })

    # Veranico (sem chuva por 5+ dias)
    dias_sem_chuva = sum(1 for pp in precip_diario if pp is not None and pp < 1)
    if dias_sem_chuva >= 5:
        alertas.append({
            "nivel": "amarelo",
            "icone": "🌵",
            "titulo": "🟡 ALERTA — Veranico",
            "msg": f"{dias_sem_chuva} dias sem chuva significativa previstos. Monitore umidade do solo e intensifique irrigação."
        })

    if not alertas:
        alertas.append({
            "nivel": "verde",
            "icone": "✅",
            "titulo": "🟢 SEM ALERTAS ATIVOS",
            "msg": "Condições meteorológicas favoráveis para as próximas 72 horas."
        })

    return alertas


def calcular_eto(dados: dict) -> dict:
    """Extrai ETo e gera recomendação de irrigação."""
    if not dados or "daily" not in dados:
        return {}

    eto_lista = dados["daily"].get("et0_fao_evapotranspiration", [])
    precip_lista = dados["daily"].get("precipitation_sum", [])

    if not eto_lista:
        return {}

    eto_hoje = eto_lista[0] if eto_lista[0] else 0
    precip_hoje = precip_lista[0] if precip_lista else 0
    deficit = max(0, eto_hoje - precip_hoje)

    if deficit < 1:
        recomendacao = "✅ Irrigação dispensável hoje. Precipitação supre a demanda evapotranspirativa."
        nivel = "verde"
    elif deficit < 3:
        recomendacao = f"💧 Irrigar com lâmina de {deficit:.1f}–{deficit*1.2:.1f} mm para repor déficit hídrico."
        nivel = "amarelo"
    else:
        recomendacao = f"🚿 Irrigação urgente: déficit de {deficit:.1f} mm. Aplique {deficit:.1f} mm a {deficit*1.3:.1f} mm conforme textura do solo."
        nivel = "vermelho"

    return {
        "eto_mm": eto_hoje,
        "precip_mm": precip_hoje,
        "deficit_mm": deficit,
        "recomendacao": recomendacao,
        "nivel": nivel,
    }


# ─────────────────────────────────────────────────────────────────────────────
# REALCE T (ENHANCED-V) — B13 TEMPERATURA DE BRILHO
# ─────────────────────────────────────────────────────────────────────────────

def criar_colormap_realce_T():
    """
    Colormap operacional Enhanced-T para B13 (IR 10,3µm).
    Reproduz o padrão usado pelo NOAA/INMET:
      > -40°C : cinza/branco (nuvem fria comum)
      -40 a -50°C : amarelo/laranja (convecção moderada)
      -50 a -60°C : vermelho (tempestade forte)
      < -60°C : roxo/azul/branco (topo glacial, tempestade severa)
    A temperatura de brilho em K é convertida para °C internamente.
    """
    # Definimos por faixas de Tb em °C mapeadas para cores
    # A escala vai de +20°C (superfície quente) a -80°C (topo glacial)
    cores = [
        # Tb °C  →  cor RGBA
        (+20,  (0.92, 0.92, 0.92, 1.0)),  # cinza claro — superfície
        (  0,  (0.80, 0.80, 0.80, 1.0)),  # cinza médio — nuvem baixa
        (-20,  (0.70, 0.70, 0.70, 1.0)),  # cinza — nuvem média
        (-40,  (1.00, 1.00, 0.00, 1.0)),  # amarelo — conv. moderada
        (-45,  (1.00, 0.60, 0.00, 1.0)),  # laranja
        (-50,  (1.00, 0.10, 0.10, 1.0)),  # vermelho — tempestade forte
        (-55,  (0.80, 0.00, 0.80, 1.0)),  # magenta
        (-60,  (0.40, 0.00, 1.00, 1.0)),  # roxo — topo glacial
        (-65,  (0.00, 0.40, 1.00, 1.0)),  # azul
        (-70,  (0.00, 0.90, 1.00, 1.0)),  # ciano
        (-80,  (1.00, 1.00, 1.00, 1.0)),  # branco — overshooting top
    ]
    # Normaliza de -80 a +20 (range 100°C)
    tb_min, tb_max = -80.0, 20.0
    vals  = [(t - tb_min) / (tb_max - tb_min) for t, _ in cores]
    rgbas = [c for _, c in cores]
    cmap  = mcolors.LinearSegmentedColormap.from_list(
        "enhanced_T",
        list(zip(vals, rgbas)),
        N=512
    )
    return cmap, tb_min, tb_max


def gerar_mapa_realce_T(shps: dict, municipio: str, coords: dict,
                         goes_data=None, extent=None) -> plt.Figure:
    """
    Gera o mapa B13 com colormap Enhanced-T realçado.
    Mostra temperatura de brilho em °C com cores operacionais.
    """
    cmap_T, tb_min, tb_max = criar_colormap_realce_T()
    lat, lon = coords["lat"], coords["lon"]
    bbox_ms  = [-57.65, -50.92, -23.67, -17.16]

    fig, ax = plt.subplots(figsize=(10, 7.5), facecolor="#050a0f")
    ax.set_facecolor("#050a0f")

    # Dados de temperatura de brilho (Tb) em °C
    if goes_data is not None and extent is not None:
        # GOES real: CMI vem em K, converte para °C
        Tb_C = np.array(goes_data, dtype=float) - 273.15
    else:
        # Simulação sintética realista
        x = np.linspace(bbox_ms[0], bbox_ms[1], 400)
        y = np.linspace(bbox_ms[2], bbox_ms[3], 400)
        X, Y = np.meshgrid(x, y)
        np.random.seed(13)

        # Célula convectiva centrada perto do município
        cx, cy = lon + np.random.uniform(-1.5, 1.5), lat + np.random.uniform(-1, 1)
        dist = np.sqrt((X - cx)**2 + (Y - cy)**2)

        # Campo base: superfície quente, nuvens cirrus no fundo
        Tb_C = 15 - dist * 3 + np.random.normal(0, 4, X.shape)

        # Célula convectiva principal (topo frio, –65°C no centro)
        nucleo = np.exp(-dist**2 / 0.8) * 80
        Tb_C -= nucleo

        # Bandas de anvil (bigorna) ao redor
        anvil = np.exp(-dist**2 / 3.5) * 35
        Tb_C -= anvil

        # Segunda célula menor
        cx2 = cx + np.random.uniform(0.8, 1.5)
        cy2 = cy + np.random.uniform(-0.5, 0.5)
        dist2 = np.sqrt((X - cx2)**2 + (Y - cy2)**2)
        Tb_C -= np.exp(-dist2**2 / 0.4) * 55

        Tb_C = Tb_C.clip(tb_min, tb_max)
        extent = bbox_ms

    norm = mcolors.Normalize(vmin=tb_min, vmax=tb_max)
    img  = ax.imshow(
        Tb_C, extent=extent, cmap=cmap_T, norm=norm,
        origin="upper", aspect="auto", alpha=1.0
    )

    # Colorbar com marcações de temperatura
    cbar = plt.colorbar(img, ax=ax, fraction=0.028, pad=0.01,
                        ticks=[-80,-70,-60,-50,-45,-40,-20,0,20])
    cbar.set_label("Temperatura de Brilho (°C)", color="white", fontsize=9)
    cbar.ax.tick_params(colors="white", labelsize=8)
    cbar.ax.set_yticklabels([f"{t}°C" for t in [-80,-70,-60,-50,-45,-40,-20,0,20]],
                             color="white", fontsize=7)

    # Linhas de contorno para destacar limiares críticos
    if isinstance(Tb_C, np.ndarray) and Tb_C.shape[0] > 1:
        ext = extent if extent != bbox_ms else bbox_ms
        x_c = np.linspace(ext[0], ext[1], Tb_C.shape[1])
        y_c = np.linspace(ext[2], ext[3], Tb_C.shape[0])
        try:
            cs = ax.contour(x_c, y_c, Tb_C,
                            levels=[-60, -50, -40],
                            colors=["white", "#ffcc00", "#ff6600"],
                            linewidths=[0.8, 0.6, 0.5], alpha=0.7)
            ax.clabel(cs, fmt="%d°C", fontsize=7, colors="white")
        except Exception:
            pass

    # Overlays shapefiles
    try:
        shps["municipios"].boundary.plot(ax=ax, color="white", linewidth=0.4, alpha=0.4)
        nome_col = next((c for c in shps["municipios"].columns
                         if "nome" in c.lower() or "name" in c.lower()), None)
        if nome_col:
            sel = shps["municipios"][shps["municipios"][nome_col].str.upper() == municipio.upper()]
            if not sel.empty:
                sel.boundary.plot(ax=ax, color=VERDE_MEDIO, linewidth=1.8, alpha=0.9)
    except Exception:
        pass
    try:
        shps["hidrografia"].plot(ax=ax, color="#4FC3F7", linewidth=0.8, alpha=0.5)
    except Exception:
        pass

    # Marcador do município
    ax.plot(lon, lat, marker="*", color=VERDE_MEDIO, markersize=14, zorder=10,
            markeredgecolor="white", markeredgewidth=1.0)
    ax.annotate(f" {municipio}", (lon, lat), fontsize=9, color="white", fontweight="bold",
                xytext=(6, 6), textcoords="offset points", zorder=11,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#0d1117", alpha=0.85))

    # Legenda de limiares
    leg_items = [
        mpatches.Patch(color="#ffff00", label="–40°C: Conv. moderada"),
        mpatches.Patch(color="#ff1a1a", label="–50°C: Tempestade forte"),
        mpatches.Patch(color="#6600ff", label="–60°C: Topo glacial ⚠"),
        mpatches.Patch(color="#00e5ff", label="–70°C: Overshooting top 🔴"),
    ]
    ax.legend(handles=leg_items, loc="lower left", fontsize=7.5,
              facecolor="#0d1117", labelcolor="white", edgecolor="#333",
              framealpha=0.85, title="Limiares Operacionais",
              title_fontsize=7)

    ax.set_xlim(bbox_ms[0]-0.3, bbox_ms[1]+0.3)
    ax.set_ylim(bbox_ms[2]-0.3, bbox_ms[3]+0.3)
    ax.set_title("⛈️  B13 — IR Clean 10,3µm  |  Realce-T Temperatura de Brilho",
                 color="white", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Longitude", color="#888", fontsize=8)
    ax.set_ylabel("Latitude", color="#888", fontsize=8)
    ax.tick_params(colors="#888", labelsize=7)
    for sp in ax.spines.values():
        sp.set_edgecolor("#222")
    ax.grid(True, color="#111", linewidth=0.4, alpha=0.6)
    ax.annotate("N ▲", xy=(0.97, 0.96), xycoords="axes fraction",
                ha="right", va="top", color="white", fontsize=11, fontweight="bold")
    fig.text(0.01, 0.005,
             f"Yamada Engenharia · GOES-16 B13 Enhanced-T · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
             color="#666", fontsize=7)
    plt.tight_layout(pad=0.5)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# ANIMAÇÃO DE TEMPESTADE — SEQUÊNCIA DE FRAMES B13
# ─────────────────────────────────────────────────────────────────────────────

def gerar_frames_animacao(municipio: str, coords: dict, shps: dict,
                           n_frames: int = 12) -> list:
    """
    Gera lista de figuras matplotlib simulando a evolução temporal
    de um sistema convectivo sobre o município (sequência de +10min cada frame).
    Cada frame usa o colormap Enhanced-T da B13.
    Retorna lista de figuras prontas para exibição no Streamlit.
    """
    cmap_T, tb_min, tb_max = criar_colormap_realce_T()
    norm = mcolors.Normalize(vmin=tb_min, vmax=tb_max)

    lat, lon = coords["lat"], coords["lon"]
    bbox_ms  = [-57.65, -50.92, -23.67, -17.16]

    x = np.linspace(bbox_ms[0], bbox_ms[1], 300)
    y = np.linspace(bbox_ms[2], bbox_ms[3], 300)
    X, Y = np.meshgrid(x, y)

    # Parâmetros da célula convectiva
    np.random.seed(42)
    cx0 = lon + 2.5   # a célula começa a leste e se move para oeste
    cy0 = lat - 1.0
    vx  = -0.30       # velocidade lon (graus/frame)
    vy  =  0.10       # velocidade lat (graus/frame)

    figuras = []
    horario_base = datetime.now(timezone(timedelta(hours=-3)))

    for i in range(n_frames):
        fig, ax = plt.subplots(figsize=(8, 6), facecolor="#050a0f")
        ax.set_facecolor("#050a0f")

        # Posição atual da célula
        cx = cx0 + vx * i
        cy = cy0 + vy * i

        # Intensidade cresce até frame 6 depois enfraquece
        intensidade = 1.0 + 0.6 * np.sin(np.pi * i / (n_frames - 1))

        dist  = np.sqrt((X - cx)**2 + (Y - cy)**2)
        dist2 = np.sqrt((X - cx - 0.6)**2 + (Y - cy + 0.3)**2)

        # Campo de temperatura de brilho
        Tb = 15 - dist * 2 + np.random.normal(0, 2, X.shape)
        Tb -= np.exp(-dist**2  / (0.6 * intensidade)) * (60 * intensidade)
        Tb -= np.exp(-dist**2  / (3.0 * intensidade)) * (30 * intensidade)  # anvil
        Tb -= np.exp(-dist2**2 / 0.35) * 40  # célula secundária
        # Ruído de textura
        Tb += np.random.normal(0, 3, X.shape)
        Tb  = Tb.clip(tb_min, tb_max)

        ax.imshow(Tb, extent=bbox_ms, cmap=cmap_T, norm=norm,
                  origin="upper", aspect="auto")

        # Contornos operacionais
        try:
            cs = ax.contour(x, y, Tb, levels=[-60, -50, -40],
                            colors=["white", "#ffcc00", "#ff6600"],
                            linewidths=[0.7, 0.5, 0.4], alpha=0.8)
        except Exception:
            pass

        # Overlays
        try:
            shps["municipios"].boundary.plot(ax=ax, color="white", linewidth=0.35, alpha=0.4)
            nome_col = next((c for c in shps["municipios"].columns
                             if "nome" in c.lower() or "name" in c.lower()), None)
            if nome_col:
                sel = shps["municipios"][shps["municipios"][nome_col].str.upper() == municipio.upper()]
                if not sel.empty:
                    sel.boundary.plot(ax=ax, color=VERDE_MEDIO, linewidth=1.5, alpha=0.9)
        except Exception:
            pass

        # Vetor de movimento da célula (seta)
        if i < n_frames - 1:
            ax.annotate("", xy=(cx + vx*2, cy + vy*2), xytext=(cx, cy),
                        arrowprops=dict(arrowstyle="->", color="white",
                                        lw=1.5, connectionstyle="arc3,rad=0"))

        # Marcador do município
        ax.plot(lon, lat, marker="*", color=VERDE_MEDIO, markersize=12, zorder=10,
                markeredgecolor="white", markeredgewidth=0.8)
        ax.annotate(f" {municipio}", (lon, lat), fontsize=8, color="white",
                    xytext=(5, 5), textcoords="offset points", zorder=11,
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="#0d1117", alpha=0.8))

        # Horário do frame
        ts_frame = horario_base + timedelta(minutes=10 * i)
        ts_str   = ts_frame.strftime("%d/%m  %H:%M")
        ax.text(0.02, 0.97, f"⏱ {ts_str} BRT  |  +{i*10:02d} min",
                transform=ax.transAxes, fontsize=9, color="white", va="top",
                bbox=dict(facecolor="#050a0f", alpha=0.8, boxstyle="round,pad=0.3"))

        # Indicador de intensidade
        fase = ["Iniciando", "Iniciando", "Crescendo", "Crescendo",
                "Maturidade", "Maturidade", "Maturidade", "Pico",
                "Dissipando", "Dissipando", "Enfraquecendo", "Residual"]
        cores_fase = {
            "Iniciando": "#aaaaaa", "Crescendo": "#ffcc00",
            "Maturidade": "#ff6600", "Pico": "#ff0000",
            "Dissipando": "#ff6600", "Enfraquecendo": "#ffcc00", "Residual": "#aaaaaa"
        }
        fase_atual = fase[i] if i < len(fase) else "Residual"
        ax.text(0.98, 0.97, f"Fase: {fase_atual}",
                transform=ax.transAxes, fontsize=8, color=cores_fase[fase_atual],
                ha="right", va="top", fontweight="bold",
                bbox=dict(facecolor="#050a0f", alpha=0.8, boxstyle="round,pad=0.3"))

        ax.set_xlim(bbox_ms[0]-0.2, bbox_ms[1]+0.2)
        ax.set_ylim(bbox_ms[2]-0.2, bbox_ms[3]+0.2)
        ax.set_title(f"⛈️  Evolução Convectiva — B13 Realce-T  |  Frame {i+1}/{n_frames}",
                     color="white", fontsize=10, fontweight="bold", pad=8)
        ax.tick_params(colors="#666", labelsize=7)
        for sp in ax.spines.values():
            sp.set_edgecolor("#1a1a1a")
        ax.grid(True, color="#0d0d0d", linewidth=0.4, alpha=0.5)

        plt.tight_layout(pad=0.4)
        figuras.append(fig)

    return figuras


# ─────────────────────────────────────────────────────────────────────────────
# INTERFACE STREAMLIT
# ─────────────────────────────────────────────────────────────────────────────

def main():

    # ── Header ──
    st.markdown("""
    <div class="yamada-header">
      <div>
        <h1>🌿 Yamada Engenharia</h1>
        <p>Plataforma de Monitoramento Agroclimático — Mato Grosso do Sul</p>
        <p style="font-size:0.78rem; margin-top:4px; color:rgba(255,255,255,0.55);">
          GOES-16/19 ABI · Open-Meteo · NASA POWER · Shapefiles MS
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center; padding:10px 0 20px;">
          <div style="font-family:'Montserrat',sans-serif; font-weight:900;
                      font-size:1.2rem; color:{VERDE_ESCURO};">
            YAMADA
          </div>
          <div style="font-size:0.72rem; color:#666; letter-spacing:2px;">ENGENHARIA</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        st.markdown(f'<p style="font-family:Montserrat;font-weight:700;color:{VERDE_ESCURO};font-size:0.9rem;">📍 MUNICÍPIO ALVO</p>', unsafe_allow_html=True)
        municipio_sel = st.selectbox(
            "Selecione o município",
            options=list(MUNICIPIOS_MS.keys()),
            index=0,
            label_visibility="collapsed"
        )
        coords = MUNICIPIOS_MS[municipio_sel]
        st.caption(f"🌐 {coords['lat']:.4f}°S, {coords['lon']:.4f}°W")
        st.caption(f"📌 Região: {coords['regiao']}")

        st.markdown("---")
        st.markdown(f'<p style="font-family:Montserrat;font-weight:700;color:{VERDE_ESCURO};font-size:0.9rem;">🛰️ BANDAS GOES-16</p>', unsafe_allow_html=True)

        bandas_sel = {}
        for bid, binfo in BANDAS_INFO.items():
            bandas_sel[bid] = st.checkbox(
                f"{binfo['icon']} {bid} — {binfo['nome'].split('(')[0].strip()}",
                value=(bid in ["B02", "B13", "B07"]),
                key=f"cb_{bid}"
            )

        st.markdown("---")
        st.markdown(f'<p style="font-family:Montserrat;font-weight:700;color:{VERDE_ESCURO};font-size:0.9rem;">⚙️ CONFIGURAÇÕES</p>', unsafe_allow_html=True)
        usar_goes_real = st.checkbox("🛰 Tentar GOES-16 Real (S3)", value=False,
                                     help="Se desmarcado, usa visualização sintética demonstrativa")
        horas_atras = st.slider("Horas atrás para GOES", 1, 6, 2)

        st.markdown("---")
        st.markdown("""
        <div style="font-size:0.72rem; color:#999; line-height:1.6;">
          <b>Fontes de dados:</b><br>
          · Open-Meteo (previsão NWP)<br>
          · GOES-16 NOAA/AWS S3<br>
          · NASA POWER (ETo)<br>
          · IBGE / Shapefiles MS
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        botao = st.button("🚀  GERAR ANÁLISE", use_container_width=True)

    # ── Conteúdo Principal ──
    if not botao:
        # Tela de boas-vindas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="band-card">
              <h4>🛰️ Satélite GOES-16</h4>
              <p>7 bandas espectrais ABI cobrindo toda a América do Sul com resolução de 500m–2km, atualização a cada 10 minutos.</p>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="band-card">
              <h4>🌡️ Previsão Open-Meteo</h4>
              <p>Modelos GFS/ICON/ERA5 com previsão horária 24h e diária 7 dias: temperatura, precipitação, vento, umidade e ETo.</p>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="band-card">
              <h4>💧 ETo NASA POWER</h4>
              <p>Evapotranspiração de referência (Penman-Monteith) para recomendação precisa de lâmina d'água e manejo de irrigação.</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f'<div class="secao-titulo">🗂️ Bandas GOES-16 Disponíveis</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, (bid, binfo) in enumerate(BANDAS_INFO.items()):
            with cols[i % 2]:
                st.markdown(f"""
                <div class="band-card">
                  <h4>{binfo['icon']} {bid} — {binfo['nome']}</h4>
                  <p>{binfo['uso']}</p>
                </div>""", unsafe_allow_html=True)

        st.info("👈  Selecione o município e as bandas na barra lateral, depois clique em **GERAR ANÁLISE**.")
        return

    # ── PROCESSAMENTO ──
    bandas_ativas = [bid for bid, ativo in bandas_sel.items() if ativo]
    if not bandas_ativas:
        st.warning("⚠️ Selecione pelo menos uma banda GOES-16 na barra lateral.")
        return

    lat, lon = coords["lat"], coords["lon"]

    # Progress bar
    progress = st.progress(0, text="Inicializando análise...")

    # 1. Carregar shapefiles
    progress.progress(10, text="📂 Carregando shapefiles de MS...")
    with st.spinner("Carregando shapefiles..."):
        shps = carregar_shapefiles()

    # 2. Buscar previsão Open-Meteo
    progress.progress(25, text="🌤 Consultando Open-Meteo API...")
    dados_meteo = buscar_previsao_openmeteo(lat, lon)

    # 3. NASA POWER
    progress.progress(40, text="☀️ Consultando NASA POWER (ETo)...")
    dados_nasa = buscar_nasa_power(lat, lon)

    # 4. GOES-16
    progress.progress(55, text="🛰 Buscando imagens GOES-16 no S3...")
    goes_results = {}
    if usar_goes_real:
        bbox_ms_ext = [-57.65, -50.92, -23.67, -17.16]  # lon_min, lon_max, lat_min, lat_max
        for bid in bandas_ativas:
            data_arr, extent, ts = baixar_e_recortar_goes(
                bid,
                lat_min=bbox_ms_ext[2], lat_max=bbox_ms_ext[3],
                lon_min=bbox_ms_ext[0], lon_max=bbox_ms_ext[1]
            )
            goes_results[bid] = (data_arr, extent, ts)

    progress.progress(70, text="🗺 Gerando mapas de bandas...")

    # ── RESULTADOS ──
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,{VERDE_ESCURO},{VERDE_MEDIO});
                border-radius:10px; padding:16px 24px; margin-bottom:20px;">
      <span style="color:white;font-family:Montserrat;font-weight:700;font-size:1.1rem;">
        📍 {municipio_sel} — {coords['regiao']}
      </span>
      <span style="color:rgba(255,255,255,0.75);font-size:0.85rem;margin-left:16px;">
        {datetime.now().strftime('%d/%m/%Y  %H:%M')} (Horário de Brasília)
      </span>
    </div>
    """, unsafe_allow_html=True)

    # ── Métricas rápidas ──
    if dados_meteo and "current_units" in dados_meteo or "hourly" in dados_meteo:
        h = dados_meteo.get("hourly", {})
        d = dados_meteo.get("daily", {})
        try:
            temp_atual  = h.get("temperature_2m", [None])[0]
            precip_hoje = d.get("precipitation_sum", [None])[0]
            umid_atual  = h.get("relativehumidity_2m", [None])[0]
            vento_atual = h.get("windspeed_10m", [None])[0]
            eto_hoje    = d.get("et0_fao_evapotranspiration", [None])[0]

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("🌡 Temperatura", f"{temp_atual:.1f}°C" if temp_atual else "—")
            with c2:
                st.metric("🌧 Chuva 24h", f"{precip_hoje:.1f} mm" if precip_hoje else "0 mm")
            with c3:
                st.metric("💧 Umidade", f"{umid_atual:.0f}%" if umid_atual else "—")
            with c4:
                st.metric("💨 Vento", f"{vento_atual:.0f} km/h" if vento_atual else "—")
            with c5:
                st.metric("🌿 ETo", f"{eto_hoje:.2f} mm" if eto_hoje else "—")
        except Exception:
            pass

    # ── Mapas GOES-16 ──
    st.markdown(f'<div class="secao-titulo">🛰️ Mapas de Satélite GOES-16 — {municipio_sel}</div>',
                unsafe_allow_html=True)

    n_bandas = len(bandas_ativas)
    n_cols = min(2, n_bandas)
    rows_mapas = [bandas_ativas[i:i+n_cols] for i in range(0, n_bandas, n_cols)]

    pct_step = 20 // max(n_bandas, 1)
    pct_atual = 70

    for row_bandas in rows_mapas:
        cols_mapas = st.columns(n_cols)
        for j, bid in enumerate(row_bandas):
            with cols_mapas[j]:
                goes_data = goes_ext = goes_ts = None
                if usar_goes_real and bid in goes_results:
                    goes_data, goes_ext, goes_ts = goes_results[bid]

                fig = gerar_mapa_banda(
                    bid, shps, municipio_sel, coords,
                    goes_data=goes_data, extent=goes_ext
                )
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

                binfo = BANDAS_INFO[bid]
                st.markdown(f"""
                <div class="band-card" style="margin-top:-6px;">
                  <h4>{binfo['icon']} {bid} — {binfo['nome']}</h4>
                  <p>{binfo['uso']}</p>
                </div>""", unsafe_allow_html=True)

        pct_atual = min(pct_atual + pct_step * n_cols, 88)
        progress.progress(int(pct_atual), text="🗺 Renderizando mapas...")

    # ── Previsão 24 horas ──
    progress.progress(90, text="📈 Gerando gráficos de previsão...")
    st.markdown(f'<div class="secao-titulo">📈 Previsão Horária — Próximas 24 Horas</div>',
                unsafe_allow_html=True)
    if dados_meteo:
        fig_prev = gerar_grafico_previsao(dados_meteo, municipio_sel)
        if fig_prev:
            st.pyplot(fig_prev, use_container_width=True)
            plt.close(fig_prev)
    else:
        st.warning("⚠️ Previsão horária indisponível (Open-Meteo não respondeu).")

    # ── Tabela 7 dias ──
    st.markdown(f'<div class="secao-titulo">📅 Previsão 7 Dias</div>', unsafe_allow_html=True)
    df_7d = gerar_tabela_7dias(dados_meteo)
    if not df_7d.empty:
        st.dataframe(
            df_7d,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Condição":    st.column_config.TextColumn("Condição", width="medium"),
                "Data":        st.column_config.TextColumn("Data", width="small"),
                "T. Máx":      st.column_config.TextColumn("T. Máx", width="small"),
                "T. Mín":      st.column_config.TextColumn("T. Mín", width="small"),
                "Precipitação":st.column_config.TextColumn("Precip.", width="small"),
                "ETo (mm)":    st.column_config.TextColumn("ETo", width="small"),
            }
        )

    # ── Alertas ──
    st.markdown(f'<div class="secao-titulo">⚠️ Alertas Ativos</div>', unsafe_allow_html=True)
    alertas = calcular_alertas(dados_meteo, lat)
    for alerta in alertas:
        nivel = alerta["nivel"]
        classe = f"alert-{nivel}"
        st.markdown(f"""
        <div class="{classe}">
          <b>{alerta['icone']} {alerta['titulo']}</b><br>
          <span style="font-size:0.9rem;">{alerta['msg']}</span>
        </div>""", unsafe_allow_html=True)

    # ── ETo e Irrigação ──
    st.markdown(f'<div class="secao-titulo">💧 Evapotranspiração e Recomendação de Irrigação</div>',
                unsafe_allow_html=True)
    eto_info = calcular_eto(dados_meteo)
    if eto_info:
        col_eto1, col_eto2, col_eto3 = st.columns(3)
        with col_eto1:
            st.metric("ETo Referência", f"{eto_info['eto_mm']:.2f} mm/dia",
                      help="Penman-Monteith FAO-56")
        with col_eto2:
            st.metric("Chuva Prevista", f"{eto_info['precip_mm']:.1f} mm")
        with col_eto3:
            st.metric("Déficit Hídrico", f"{eto_info['deficit_mm']:.2f} mm",
                      delta=f"{'💧 irrigar' if eto_info['deficit_mm'] > 1 else '✅ ok'}")

        nivel_eto = eto_info["nivel"]
        classe_eto = f"alert-{nivel_eto}"
        st.markdown(f"""
        <div class="{classe_eto}" style="margin-top:10px;">
          <b>Recomendação:</b> {eto_info['recomendacao']}
        </div>""", unsafe_allow_html=True)
    else:
        st.info("💧 Dados de ETo indisponível. Verifique a API Open-Meteo.")

    # ── Rodapé ──
    progress.progress(100, text="✅ Análise concluída!")
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align:center; padding:16px; color:#888; font-size:0.8rem;">
      <b style="color:{VERDE_ESCURO};">Yamada Engenharia</b> — Meteorologia Aplicada ao Agronegócio<br>
      Dados: Open-Meteo API · NOAA GOES-16 · NASA POWER · IBGE/Shapefiles MS<br>
      Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} · MVP v1.0
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
