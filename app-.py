"""
=============================================================================
YAMADA ENGENHARIA — Plataforma de Monitoramento Agroclimático
MVP Streamlit | GOES-19 + Open-Meteo + NASA POWER + INPE + SATVeg + INMET
Mato Grosso do Sul — Análise por Município

VERSÃO 3.0 — Melhorias:
  • Organização em 6 abas temáticas
  • Sistema de relatório por e-mail (integrado do Monitor PM2.5/PM10)
  • Scheduler automático (APScheduler) para envio às 06h, 12h e 18h
  • Keep-alive para evitar que o app adormeça no Streamlit Cloud
=============================================================================
"""

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
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

# ── E-mail ────────────────────────────────────────────────────────────────────
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# ── Scheduler (relatórios automáticos) ───────────────────────────────────────
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import threading
import logging
logging.getLogger("apscheduler").setLevel(logging.WARNING)

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

  /* Sidebar — fundo escuro com textos claros */
  section[data-testid="stSidebar"] {{
    background-color: #1a2e1c !important;
    border-right: 1px solid #2d5a30;
  }}
  section[data-testid="stSidebar"] * {{ color: #e8f5e9 !important; }}
  section[data-testid="stSidebar"] .stSelectbox label,
  section[data-testid="stSidebar"] .stSlider label,
  section[data-testid="stSidebar"] .stCheckbox label,
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
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DE E-MAIL (via st.secrets)
#
# No arquivo .streamlit/secrets.toml, adicione:
#
#   [email]
#   remetente     = "seuemail@gmail.com"
#   senha_app     = "sua_senha_de_app_gmail"
#   destinatario  = "destino@email.com"        # pode ser lista: "a@b.com,c@d.com"
#
# Para gerar a senha de app Gmail:
#   Conta Google → Segurança → Verificação em 2 etapas → Senhas de app
# ─────────────────────────────────────────────────────────────────────────────
try:
    EMAIL_REMETENTE     = st.secrets["email"]["remetente"]
    EMAIL_SENHA_APP     = st.secrets["email"]["senha_app"]
    _dest_raw           = st.secrets["email"]["destinatario"]
    if isinstance(_dest_raw, str):
        EMAIL_DESTINATARIOS = [e.strip() for e in _dest_raw.split(",") if e.strip()]
    else:
        EMAIL_DESTINATARIOS = list(_dest_raw)
    _email_configurado  = True
except (KeyError, Exception):
    EMAIL_DESTINATARIOS = []
    _email_configurado  = False

# ── Variáveis globais do scheduler ────────────────────────────────────────────
_scheduler_log: list = []
_log_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────────────────
# DADOS ESTÁTICOS
# ─────────────────────────────────────────────────────────────────────────────
MUNICIPIOS_MS = {
    "Campo Grande":    {"lat": -20.4428, "lon": -54.6460, "regiao": "Centro"},
    "Dourados":        {"lat": -22.2212, "lon": -54.8056, "regiao": "Sul"},
    "Três Lagoas":     {"lat": -20.7519, "lon": -51.6783, "regiao": "Leste"},
    "Corumbá":         {"lat": -19.0078, "lon": -57.6500, "regiao": "Oeste (Pantanal)"},
    "Ponta Porã":      {"lat": -22.5361, "lon": -55.7253, "regiao": "Sul (Fronteira)"},
    "Naviraí":         {"lat": -23.0622, "lon": -54.1914, "regiao": "Sul"},
    "Nova Andradina":  {"lat": -22.2333, "lon": -53.3444, "regiao": "Leste"},
    "Aquidauana":      {"lat": -20.4700, "lon": -55.7869, "regiao": "Centro-Oeste"},
    "Sidrolândia":     {"lat": -20.9319, "lon": -54.9600, "regiao": "Centro"},
    "Maracaju":        {"lat": -21.6108, "lon": -55.1681, "regiao": "Sul"},
    "Rio Brilhante":   {"lat": -21.8028, "lon": -54.5447, "regiao": "Sul"},
    "Coxim":           {"lat": -18.5069, "lon": -54.7600, "regiao": "Norte"},
    "Sonora":          {"lat": -17.5583, "lon": -54.7611, "regiao": "Norte"},
    "Chapadão do Sul": {"lat": -18.7919, "lon": -52.6267, "regiao": "Nordeste"},
    "Costa Rica":      {"lat": -18.5447, "lon": -53.1278, "regiao": "Nordeste"},
}

BANDAS_INFO = {
    "B02": {"nome": "Vermelho Visível (0,64µm)",  "icon": "☀️",  "uso": "Cobertura de nuvens, frentes de chuva — Só diurno",                 "cmap": "gray",      },
    "B03": {"nome": "Veggie Band – NIR (0,86µm)", "icon": "🌿",  "uso": "Saúde da vegetação, estresse hídrico, queimadas recentes",          "cmap": "YlGn",      },
    "B07": {"nome": "IR Onda Curta (3,9µm)",       "icon": "🔥",  "uso": "Focos de incêndio (produto FDC oficial), nevoeiro matinal",         "cmap": "hot",       },
    "B09": {"nome": "Vapor d'Água Médio (6,9µm)",  "icon": "💧",  "uso": "Umidade atmosférica, sistemas convectivos 24–72h",                  "cmap": "Blues_r",   },
    "B11": {"nome": "IR Termal (8,4µm)",           "icon": "❄️",  "uso": "Temperatura superficial, risco de geada, nuvens baixas",           "cmap": "RdBu",      },
    "B13": {"nome": "IR Clean (10,3µm)",           "icon": "⛈️",  "uso": "Topo de nuvens, alertas de tempestade severa e granizo",           "cmap": "inferno_r", },
    "B14": {"nome": "IR Longo – QPE (11,2µm)",     "icon": "🌧️",  "uso": "Estimativa de precipitação — produto RRQPE oficial GOES-19",      "cmap": "Blues",     },
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
# SISTEMA DE E-MAIL
# Adaptado do Monitor PM2.5/PM10 — geração de HTML rico com tabelas,
# cards de métricas e alertas coloridos, enviado via SMTP Gmail (SSL porta 465).
# ─────────────────────────────────────────────────────────────────────────────

def _cor_alerta_email(nivel: str) -> tuple:
    """Retorna (bg, border, text) para cada nível de alerta no HTML do e-mail."""
    mapa = {
        "verde":    ("#e8f5e9", "#43a047", "#1b5e20"),
        "amarelo":  ("#fff8e1", "#fbc02d", "#5d4037"),
        "vermelho": ("#ffebee", "#e53935", "#b71c1c"),
        "laranja":  ("#fff3e0", "#fb8c00", "#bf360c"),
    }
    return mapa.get(nivel, ("#f5f5f5", "#9e9e9e", "#333"))


def gerar_html_relatorio(
    municipio: str,
    coords: dict,
    dados_meteo: dict,
    alertas: list,
    janelas_def: list,
    gda_info: dict,
    riscos_fito: list,
    bh: dict,
    ndvi_data: dict,
    df_focos: pd.DataFrame,
    df_inmet: pd.DataFrame,
) -> str:
    """
    Gera o HTML completo do relatório agroclimático para envio por e-mail.
    Inclui: métricas rápidas, alertas, janela de defensivos, GDA/fenologia,
    risco fitossanitário, balanço hídrico, NDVI e focos de queimada.
    """
    agora    = datetime.now().strftime("%d/%m/%Y às %H:%M")
    lat, lon = coords["lat"], coords["lon"]
    regiao   = coords["regiao"]

    # ── Métricas rápidas ──────────────────────────────────────────────────────
    h = dados_meteo.get("hourly", {}) if dados_meteo else {}
    d = dados_meteo.get("daily",  {}) if dados_meteo else {}
    temp_atual  = (h.get("temperature_2m",        [None])[0] or 0)
    precip_hoje = (d.get("precipitation_sum",      [None])[0] or 0)
    umid_atual  = (h.get("relativehumidity_2m",    [None])[0] or 0)
    vento_atual = (h.get("windspeed_10m",          [None])[0] or 0)
    eto_hoje    = (d.get("et0_fao_evapotranspiration", [None])[0] or 0)

    def card_metrica(titulo, valor, unidade, cor="#1B4D2E"):
        return f"""
        <div style="flex:1;min-width:110px;background:#fff;border-radius:10px;
                    border-top:4px solid {cor};padding:14px 12px;
                    box-shadow:0 2px 8px rgba(0,0,0,0.08);text-align:center;">
          <div style="font-size:11px;color:#777;font-family:Arial;">{titulo}</div>
          <div style="font-size:22px;font-weight:bold;color:#222;">
            {valor}<span style="font-size:12px;color:#999;margin-left:2px;">{unidade}</span>
          </div>
        </div>"""

    cards = (
        card_metrica("🌡 Temperatura",  f"{temp_atual:.1f}",  "°C",    "#e65100") +
        card_metrica("🌧 Chuva 24h",    f"{precip_hoje:.1f}", "mm",    "#1565c0") +
        card_metrica("💧 Umidade",       f"{umid_atual:.0f}",  "%",     "#0277bd") +
        card_metrica("💨 Vento",         f"{vento_atual:.0f}", "km/h",  "#6a1b9a") +
        card_metrica("🌿 ETo",           f"{eto_hoje:.2f}",   "mm/dia","#2e7d32")
    )

    # ── Alertas ───────────────────────────────────────────────────────────────
    html_alertas = ""
    for al in alertas:
        bg, brd, tc = _cor_alerta_email(al["nivel"])
        html_alertas += f"""
        <div style="background:{bg};border-left:5px solid {brd};border-radius:6px;
                    padding:12px 16px;margin:6px 0;">
          <b style="color:{tc};">{al['icone']} {al['titulo']}</b><br>
          <span style="font-size:13px;color:#333;">{al['msg']}</span>
        </div>"""

    # ── Janela de defensivos ──────────────────────────────────────────────────
    n_aberta  = sum(1 for j in janelas_def if j["status"] == "aberta")
    n_parcial = sum(1 for j in janelas_def if j["status"] == "parcial")
    n_bloq    = sum(1 for j in janelas_def if j["status"] == "bloqueada")
    cor_jan   = "#43a047" if n_aberta >= 6 else ("#fbc02d" if n_aberta > 0 else "#e53935")

    # Melhor janela contínua
    max_seq = max_start = cur_seq = cur_start = 0
    for i, j in enumerate(janelas_def):
        if j["status"] == "aberta":
            if cur_seq == 0: cur_start = i
            cur_seq += 1
            if cur_seq > max_seq:
                max_seq = cur_seq; max_start = cur_start
        else:
            cur_seq = 0
    melhor_jan = ""
    if max_seq > 0:
        h_ini = janelas_def[max_start]["hora"]
        h_fim = janelas_def[min(max_start + max_seq - 1, len(janelas_def)-1)]["hora"]
        melhor_jan = f"<b>Melhor janela:</b> {h_ini} → {h_fim} ({max_seq}h contínuas)"
    else:
        melhor_jan = "<b>Sem janela ideal nas próximas 24h.</b> Adie as aplicações."

    html_defensivos = f"""
    <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
      <tr>
        <td style="padding:8px 12px;background:#e8f5e9;border-radius:6px;text-align:center;">
          <span style="font-size:20px;font-weight:bold;color:#2e7d32;">{n_aberta}</span><br>
          <span style="font-size:11px;color:#555;">Horas ideais</span>
        </td>
        <td style="padding:8px 12px;background:#fff8e1;border-radius:6px;text-align:center;">
          <span style="font-size:20px;font-weight:bold;color:#f57f17;">{n_parcial}</span><br>
          <span style="font-size:11px;color:#555;">Horas parciais</span>
        </td>
        <td style="padding:8px 12px;background:#ffebee;border-radius:6px;text-align:center;">
          <span style="font-size:20px;font-weight:bold;color:#c62828;">{n_bloq}</span><br>
          <span style="font-size:11px;color:#555;">Horas bloqueadas</span>
        </td>
      </tr>
    </table>
    <div style="background:#f1f8e9;border-left:4px solid {cor_jan};padding:10px 14px;
                border-radius:4px;font-size:13px;">{melhor_jan}</div>"""

    # ── GDA / Fenologia ───────────────────────────────────────────────────────
    html_gda = ""
    if gda_info:
        proximo    = gda_info.get("proximo_estagio")
        faltam_str = f" | Próximo em {proximo[0]-gda_info['gda_total']:.0f} °C·dia: <b>{proximo[1]}</b>" if proximo else ""
        html_gda = f"""
        <div style="background:#f9fbe7;border-left:5px solid #8bc34a;border-radius:6px;
                    padding:14px 16px;margin:6px 0;">
          <b style="color:#33691e;">🌾 {gda_info['cultura']} — {gda_info['estagio_atual']}</b><br>
          <span style="font-size:13px;color:#555;">
            GDA acumulado: <b>{gda_info['gda_total']} °C·dia</b>
            | {gda_info['dias_desde_semeadura']} dias desde semeadura
            {faltam_str}
          </span>
        </div>"""

    # ── Risco fitossanitário ──────────────────────────────────────────────────
    html_fito = ""
    for r in riscos_fito:
        bg, brd, tc = _cor_alerta_email(r["cor"])
        html_fito += f"""
        <div style="background:{bg};border-left:5px solid {brd};border-radius:6px;
                    padding:10px 14px;margin:5px 0;">
          <b style="color:{tc};">{r['icone']} {r['doenca']} — Risco {r['nivel']}</b><br>
          <span style="font-size:12px;color:#333;">{r['msg']}</span>
        </div>"""

    # ── Balanço Hídrico ───────────────────────────────────────────────────────
    html_bh = ""
    if bh:
        arm_pct = bh.get("arm_pct", 0)
        cor_bh  = "#43a047" if arm_pct >= 70 else ("#fbc02d" if arm_pct >= 40 else "#e53935")
        barra_w = min(int(arm_pct), 100)
        html_bh = f"""
        <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px;">
          <tr>
            <td style="padding:6px 10px;color:#555;width:140px;">Armazenamento (ARM)</td>
            <td style="padding:6px 10px;">
              <div style="background:#e0e0e0;border-radius:6px;height:14px;">
                <div style="background:{cor_bh};border-radius:6px;height:14px;width:{barra_w}%;"></div>
              </div>
            </td>
            <td style="padding:6px 10px;white-space:nowrap;font-weight:bold;">
              {bh['arm_mm']:.1f} / {bh['cad_mm']:.0f} mm ({arm_pct:.0f}%)
            </td>
          </tr>
          <tr>
            <td style="padding:6px 10px;color:#555;">Déficit hoje</td>
            <td colspan="2" style="padding:6px 10px;font-weight:bold;color:#c62828;">
              {bh['def_mm']:.1f} mm
            </td>
          </tr>
          <tr>
            <td style="padding:6px 10px;color:#555;">ETo / ETR</td>
            <td colspan="2" style="padding:6px 10px;">
              {bh['eto_mm']:.2f} mm / {bh['etr_mm']:.2f} mm
            </td>
          </tr>
        </table>
        <div style="background:#e3f2fd;border-left:4px solid #1565c0;padding:10px 14px;
                    border-radius:4px;font-size:13px;">
          <b>Recomendação:</b> {bh['recomendacao']}
        </div>"""

    # ── NDVI ──────────────────────────────────────────────────────────────────
    html_ndvi = ""
    if ndvi_data and "listaSerie" in ndvi_data:
        serie   = ndvi_data["listaSerie"]
        valores = [float(s.get("ndvi", s.get("valor", 0))) for s in serie]
        if valores:
            val_atual = valores[-1]
            mediana   = float(np.median(valores[:-1])) if len(valores) > 1 else 0.5
            delta     = val_atual - mediana
            cor_d     = "#2e7d32" if delta >= 0 else "#c62828"
            sim_note  = " <i>(dados simulados)</i>" if ndvi_data.get("_simulado") else ""
            html_ndvi = f"""
            <div style="background:#f1f8e9;border-left:5px solid #66bb6a;border-radius:6px;
                        padding:12px 16px;margin:6px 0;">
              <b style="color:#2e7d32;">🌿 NDVI Atual: {val_atual:.3f}</b>
              <span style="font-size:12px;color:{cor_d};margin-left:10px;">
                Δ {delta:+.3f} vs mediana histórica ({mediana:.3f})
              </span>{sim_note}<br>
              <span style="font-size:12px;color:#555;">
                Fonte: Embrapa SATVeg — série histórica desde 2000
              </span>
            </div>"""

    # ── Focos de queimada ─────────────────────────────────────────────────────
    html_focos = ""
    if df_focos is not None and not df_focos.empty:
        n_focos = len(df_focos)
        frp_max = df_focos["frp"].max() if "frp" in df_focos.columns else 0
        cor_foc = "#e53935" if n_focos > 10 else ("#fbc02d" if n_focos > 3 else "#43a047")
        html_focos = f"""
        <div style="background:#fff3e0;border-left:5px solid {cor_foc};border-radius:6px;
                    padding:12px 16px;margin:6px 0;">
          <b style="color:#bf360c;">🔥 {n_focos} foco(s) detectado(s) nas últimas 48h — MS</b><br>
          <span style="font-size:12px;color:#555;">
            FRP máximo: {frp_max:.0f} MW | Fonte: INPE BDQueimadas
          </span>
        </div>"""

    # ── Previsão 7 dias ───────────────────────────────────────────────────────
    tmax_l   = d.get("temperature_2m_max",        [])
    tmin_l   = d.get("temperature_2m_min",        [])
    precip_l = d.get("precipitation_sum",          [])
    eto_l    = d.get("et0_fao_evapotranspiration", [])
    datas_l  = d.get("time",                       [])
    wcode_l  = d.get("weathercode",               [])
    wcode_map = {
        0:"☀️ Limpo",1:"🌤 Poucas nuvens",2:"⛅ Parcial",3:"☁️ Nublado",
        45:"🌫 Névoa",51:"🌦 Chuvisco",61:"🌧 Chuva",63:"🌧 Moderada",
        65:"⛈ Forte",80:"🌦 Pancadas",81:"⛈ Pancadas fortes",
        95:"⛈ Tempestade",99:"⛈ Granizo",
    }
    rows_7d = ""
    for i in range(min(7, len(datas_l))):
        try:
            data_fmt = datetime.fromisoformat(datas_l[i]).strftime("%a %d/%m")
        except Exception:
            data_fmt = datas_l[i]
        wc       = wcode_l[i] if i < len(wcode_l) else 0
        cond     = wcode_map.get(wc, f"Cód {wc}")
        tmax_v   = f"{tmax_l[i]:.0f}°C"   if i < len(tmax_l)   and tmax_l[i]   else "—"
        tmin_v   = f"{tmin_l[i]:.0f}°C"   if i < len(tmin_l)   and tmin_l[i]   else "—"
        pp_v     = f"{precip_l[i]:.1f}mm"  if i < len(precip_l) and precip_l[i] else "0mm"
        eto_v    = f"{eto_l[i]:.2f}mm"     if i < len(eto_l)    and eto_l[i]    else "—"
        bg_row   = "#f5f5f5" if i % 2 == 0 else "#fff"
        rows_7d += f"""
        <tr style="background:{bg_row};">
          <td style="padding:7px 10px;">{data_fmt}</td>
          <td style="padding:7px 10px;">{cond}</td>
          <td style="padding:7px 10px;text-align:center;">{tmax_v}</td>
          <td style="padding:7px 10px;text-align:center;">{tmin_v}</td>
          <td style="padding:7px 10px;text-align:center;">{pp_v}</td>
          <td style="padding:7px 10px;text-align:center;">{eto_v}</td>
        </tr>"""

    html_7dias = f"""
    <table style="border-collapse:collapse;width:100%;font-size:13px;">
      <thead>
        <tr style="background:{VERDE_ESCURO};color:white;">
          <th style="padding:8px 10px;text-align:left;">Data</th>
          <th style="padding:8px 10px;text-align:left;">Condição</th>
          <th style="padding:8px 10px;">T.Máx</th>
          <th style="padding:8px 10px;">T.Mín</th>
          <th style="padding:8px 10px;">Precip.</th>
          <th style="padding:8px 10px;">ETo</th>
        </tr>
      </thead>
      <tbody>{rows_7d}</tbody>
    </table>"""

    # ── Estações INMET ────────────────────────────────────────────────────────
    html_inmet = ""
    if df_inmet is not None and not df_inmet.empty:
        rows_inmet = ""
        for _, row in df_inmet.iterrows():
            rows_inmet += f"""
            <tr>
              <td style="padding:6px 10px;border-bottom:1px solid #eee;">{row.get('Estação','—')}</td>
              <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">{row.get('Lat','—')}</td>
              <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">{row.get('Lon','—')}</td>
              <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">{row.get('Alt (m)','—')}</td>
              <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">{row.get('Cod','—')}</td>
            </tr>"""
        html_inmet = f"""
        <table style="border-collapse:collapse;width:100%;font-size:13px;">
          <thead>
            <tr style="background:#e8f5e9;">
              <th style="padding:7px 10px;text-align:left;">Estação</th>
              <th style="padding:7px 10px;">Lat</th>
              <th style="padding:7px 10px;">Lon</th>
              <th style="padding:7px 10px;">Alt (m)</th>
              <th style="padding:7px 10px;">Código</th>
            </tr>
          </thead>
          <tbody>{rows_inmet}</tbody>
        </table>"""

    # ── HTML FINAL ────────────────────────────────────────────────────────────
    return f"""
    <html>
    <body style="font-family:Arial,sans-serif;background:#f0f2f5;padding:20px;margin:0;">
      <div style="max-width:760px;margin:auto;background:#fff;border-radius:14px;
                  box-shadow:0 4px 18px rgba(0,0,0,.12);overflow:hidden;">

        <!-- CABEÇALHO -->
        <div style="background:linear-gradient(135deg,{VERDE_ESCURO},{VERDE_MEDIO});
                    padding:32px 36px;text-align:center;">
          <h1 style="color:white;margin:0;font-size:24px;letter-spacing:.5px;">
            🌿 Yamada Engenharia
          </h1>
          <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:15px;">
            Relatório Agroclimático — Mato Grosso do Sul
          </p>
        </div>

        <div style="padding:32px 36px;">

          <!-- INFO DO MUNICÍPIO -->
          <div style="background:#f9fbe7;border-radius:8px;padding:14px 18px;margin-bottom:20px;">
            <b style="font-size:16px;color:{VERDE_ESCURO};">📍 {municipio}</b>
            <span style="color:#555;font-size:13px;margin-left:12px;">{regiao}</span><br>
            <span style="color:#777;font-size:12px;">
              {lat:.4f}°S, {lon:.4f}°W · Gerado em {agora}
            </span>
          </div>

          <!-- MÉTRICAS RÁPIDAS -->
          <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                     padding-bottom:6px;margin-top:0;">📊 Condições Atuais</h3>
          <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:24px;">
            {cards}
          </div>

          <!-- ALERTAS -->
          <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};padding-bottom:6px;">
            ⚠️ Alertas Ativos
          </h3>
          {html_alertas}

          <!-- DEFENSIVOS -->
          <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                     padding-bottom:6px;margin-top:24px;">
            🧪 Janela de Aplicação de Defensivos (próximas 24h)
          </h3>
          <p style="font-size:12px;color:#777;">
            Critérios: Vento &lt;10km/h | Temp &lt;30°C | UR &gt;55% | Sem chuva
          </p>
          {html_defensivos}

          <!-- FENOLOGIA -->
          <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                     padding-bottom:6px;margin-top:24px;">
            🌾 Graus-Dia e Estádio Fenológico
          </h3>
          {html_gda if html_gda else '<p style="color:#999;">Dados não disponíveis.</p>'}

          <!-- RISCO FITOSSANITÁRIO -->
          <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                     padding-bottom:6px;margin-top:24px;">
            🍂 Risco Fitossanitário
          </h3>
          {html_fito}

          <!-- NDVI -->
          <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                     padding-bottom:6px;margin-top:24px;">
            🌿 NDVI — SATVeg/Embrapa
          </h3>
          {html_ndvi if html_ndvi else '<p style="color:#999;">Dados não disponíveis.</p>'}

          <!-- BALANÇO HÍDRICO -->
          <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                     padding-bottom:6px;margin-top:24px;">
            💧 Balanço Hídrico do Solo (Thornthwaite-Mather)
          </h3>
          {html_bh if html_bh else '<p style="color:#999;">Dados não disponíveis.</p>'}

          <!-- FOCOS -->
          <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                     padding-bottom:6px;margin-top:24px;">
            🔥 Focos de Queimada — INPE
          </h3>
          {html_focos if html_focos else '<p style="color:#999;">Nenhum foco detectado.</p>'}

          <!-- PREVISÃO 7 DIAS -->
          <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                     padding-bottom:6px;margin-top:24px;">
            📅 Previsão 7 Dias
          </h3>
          {html_7dias}

          <!-- ESTAÇÕES INMET -->
          <h3 style="color:{VERDE_ESCURO};border-bottom:2px solid {VERDE_MEDIO};
                     padding-bottom:6px;margin-top:24px;">
            📡 Estações INMET — MS
          </h3>
          {html_inmet if html_inmet else '<p style="color:#999;">Dados não disponíveis.</p>'}

          <!-- RODAPÉ -->
          <p style="color:#bbb;font-size:11px;margin-top:32px;border-top:1px solid #eee;
                    padding-top:14px;text-align:center;">
            Relatório gerado automaticamente pela <b>Yamada Engenharia</b>.<br>
            Dados: Open-Meteo · NASA POWER · Embrapa SATVeg · INPE BDQueimadas · INMET · GOES-19<br>
            {agora} · MVP v3.0
          </p>
        </div>
      </div>
    </body>
    </html>"""


def enviar_relatorio_email(
    municipio: str,
    coords: dict,
    dados_meteo: dict,
    alertas: list,
    janelas_def: list,
    gda_info: dict,
    riscos_fito: list,
    bh: dict,
    ndvi_data: dict,
    df_focos: pd.DataFrame,
    df_inmet: pd.DataFrame,
    destinatarios_extras: list = None,
) -> tuple:
    """
    Envia o relatório agroclimático completo por e-mail (Gmail SMTP SSL).

    Parâmetros:
      municipio           — Nome do município analisado
      coords              — Dict com lat, lon, regiao
      dados_meteo         — JSON do Open-Meteo
      alertas             — Lista de alertas calculados
      janelas_def         — Lista de janelas de defensivos
      gda_info            — Dict com info de graus-dia
      riscos_fito         — Lista de riscos fitossanitários
      bh                  — Dict do balanço hídrico
      ndvi_data           — Dict do SATVeg
      df_focos            — DataFrame de focos INPE
      df_inmet            — DataFrame de estações INMET
      destinatarios_extras— Lista adicional de e-mails (soma aos do secrets)

    Retorna: (True, "Enviado") ou (False, "Mensagem de erro")
    """
    if not _email_configurado:
        return False, "E-mail não configurado no secrets.toml"

    try:
        html_body = gerar_html_relatorio(
            municipio, coords, dados_meteo, alertas,
            janelas_def, gda_info, riscos_fito, bh,
            ndvi_data, df_focos, df_inmet
        )

        destinatarios = list(EMAIL_DESTINATARIOS)
        if destinatarios_extras:
            for e in destinatarios_extras:
                if e and e not in destinatarios:
                    destinatarios.append(e)

        agora    = datetime.now()
        tem_alerta = any(a["nivel"] in ["vermelho", "laranja"] for a in alertas)
        prefixo  = "🚨 ALERTA — " if tem_alerta else "📋 "
        assunto  = (f"{prefixo}Relatório Agroclimático — {municipio} | "
                    f"{agora.strftime('%d/%m/%Y %H:%M')}")

        msg            = MIMEMultipart("mixed")
        msg["Subject"] = assunto
        msg["From"]    = EMAIL_REMETENTE
        msg["To"]      = ", ".join(destinatarios)

        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(html_body, "html"))
        msg.attach(alt_part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
            srv.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
            srv.sendmail(EMAIL_REMETENTE, destinatarios, msg.as_string())

        return True, f"Enviado para: {', '.join(destinatarios)}"

    except Exception as e:
        return False, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# KEEP-ALIVE — Ping periódico para manter o app ativo no Streamlit Cloud
# ─────────────────────────────────────────────────────────────────────────────
def keep_alive():
    """Ping no próprio app a cada 5 minutos para evitar sleep no Streamlit Cloud."""
    APP_URL = "https://yamada-agro-ms.streamlit.app/"  # ← substitua pela URL real
    try:
        requests.get(APP_URL, timeout=30)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# RELATÓRIO AUTOMÁTICO (APScheduler — roda em background)
# Executa às 06h, 12h e 18h (horário de Campo Grande) para o município padrão.
# ─────────────────────────────────────────────────────────────────────────────
def scheduled_report_automatico():
    """
    Coleta todos os dados do município padrão (Campo Grande) e envia
    o relatório por e-mail automaticamente.
    Chamado pelo APScheduler — não bloqueia a interface Streamlit.
    """
    municipio_auto = "Campo Grande"
    coords_auto    = MUNICIPIOS_MS[municipio_auto]
    lat, lon       = coords_auto["lat"], coords_auto["lon"]

    log_entry = {
        "inicio":  datetime.now().strftime("%d/%m/%Y %H:%M"),
        "status":  "em andamento",
        "detalhe": "",
    }
    with _log_lock:
        _scheduler_log.insert(0, log_entry)
        if len(_scheduler_log) > 10:
            _scheduler_log.pop()

    try:
        dados_meteo   = buscar_previsao_openmeteo(lat, lon)
        dados_nasa    = buscar_nasa_power(lat, lon)
        ndvi_data     = buscar_satveg_ndvi(lat, lon)
        df_focos      = buscar_focos_inpe()
        df_inmet      = buscar_dados_inmet()
        janelas_def   = calcular_janela_defensivos(dados_meteo)
        gda_info      = calcular_graus_dia(
            dados_meteo, "Soja",
            datetime.now() - timedelta(days=45)
        )
        riscos_fito   = calcular_risco_fitossanitario(dados_meteo)
        bh            = calcular_balanco_hidrico_thornthwaite(dados_meteo, 65.0)
        alertas       = calcular_alertas(dados_meteo, lat, gda_info)

        ok, msg = enviar_relatorio_email(
            municipio=municipio_auto,
            coords=coords_auto,
            dados_meteo=dados_meteo,
            alertas=alertas,
            janelas_def=janelas_def,
            gda_info=gda_info,
            riscos_fito=riscos_fito,
            bh=bh,
            ndvi_data=ndvi_data,
            df_focos=df_focos,
            df_inmet=df_inmet,
        )

        log_entry["status"]  = "✅ enviado" if ok else "⚠️ gerado, sem e-mail"
        log_entry["detalhe"] = msg[:80]

    except Exception as exc:
        log_entry["status"]  = "❌ erro"
        log_entry["detalhe"] = str(exc)[:100]


# ─────────────────────────────────────────────────────────────────────────────
# INICIALIZAÇÃO DO SCHEDULER (uma única vez por processo Streamlit)
# ─────────────────────────────────────────────────────────────────────────────
if "scheduler_started" not in st.session_state:
    _sched = BackgroundScheduler(timezone="America/Campo_Grande")

    # Relatório automático às 06h, 12h e 18h
    _sched.add_job(
        scheduled_report_automatico,
        trigger=CronTrigger(hour="6,12,18", minute=0, timezone="America/Campo_Grande"),
        id="relatorio_automatico",
        name="Relatório Yamada — Campo Grande",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=600,
    )

    # Keep-alive a cada 5 minutos
    _sched.add_job(
        keep_alive,
        trigger=IntervalTrigger(minutes=5),
        id="keepalive",
        name="Keep Alive",
        replace_existing=True,
        max_instances=1,
    )

    _sched.start()
    st.session_state["scheduler_started"] = True
    st.session_state["scheduler_obj"]     = _sched


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE COLETA DE DADOS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def buscar_previsao_openmeteo(lat: float, lon: float) -> dict:
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,precipitation,relativehumidity_2m,"
        f"windspeed_10m,shortwave_radiation,dewpoint_2m"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"weathercode,windspeed_10m_max,et0_fao_evapotranspiration"
        f"&timezone=America%2FCampo_Grande&forecast_days=7&models=best_match"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"❌ Open-Meteo erro: {e}")
        return {}


@st.cache_data(ttl=1800, show_spinner=False)
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
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"⚠️ NASA POWER indisponível: {e}")
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_satveg_ndvi(lat: float, lon: float) -> dict:
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
        ndvi_base = []
        for a in anos:
            v = 0.55 + 0.15 * np.sin(2 * np.pi * (a - 2000) / 10) + np.random.normal(0, 0.04)
            ndvi_base.append(round(float(np.clip(v, 0.2, 0.9)), 3))
        return {"listaSerie": [{"data": str(a), "ndvi": v} for a, v in zip(anos, ndvi_base)],
                "_simulado": True}


@st.cache_data(ttl=1800, show_spinner=False)
def buscar_focos_inpe() -> pd.DataFrame:
    try:
        url    = "https://queimadas.dgi.inpe.br/api/focos/"
        params = {"pais_id": 33, "estado_id": 50, "satelite": "AQUA_M-T"}
        r      = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data   = r.json()
        if isinstance(data, list) and data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    except Exception:
        np.random.seed(42)
        n    = 12
        lons = np.random.uniform(-57.0, -51.5, n)
        lats = np.random.uniform(-23.0, -17.5, n)
        frp  = np.random.uniform(5, 120, n)
        return pd.DataFrame({
            "latitude": lats, "longitude": lons, "frp": frp,
            "_simulado": [True]*n,
            "municipio": [list(MUNICIPIOS_MS.keys())[i % len(MUNICIPIOS_MS)] for i in range(n)]
        })


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_dados_inmet() -> pd.DataFrame:
    try:
        r = requests.get("https://apitempo.inmet.gov.br/estacoes/T", timeout=15)
        r.raise_for_status()
        est_ms = [e for e in r.json() if e.get("SG_ESTADO") == "MS"][:5]
        if not est_ms:
            raise ValueError("sem estações MS")
        return pd.DataFrame([{
            "Estação": e.get("DC_NOME", "—"), "Lat": float(e.get("VL_LATITUDE", 0)),
            "Lon": float(e.get("VL_LONGITUDE", 0)),
            "Alt (m)": e.get("VL_ALTITUDE", "—"), "Cod": e.get("CD_ESTACAO", "—"),
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
# FUNÇÕES GOES-19
# ─────────────────────────────────────────────────────────────────────────────

def listar_arquivos_goes_banda(banda: str, horas_atras: int = 1) -> list:
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


@st.cache_data(ttl=3600, show_spinner=False)
def baixar_e_recortar_goes19(banda: str, lat_min, lat_max, lon_min, lon_max) -> tuple:
    arquivos = listar_arquivos_goes_banda(banda)
    if not arquivos:
        return None, None, None
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")
    try:
        with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tmp:
            s3.download_fileobj("noaa-goes19", arquivos[0], tmp)
            tmp_path = tmp.name
        dataset   = nc.Dataset(tmp_path)
        proj_info = dataset.variables["goes_imager_projection"]
        lon_origin = proj_info.longitude_of_projection_origin
        H    = proj_info.perspective_point_height + proj_info.semi_major_axis
        r_eq = proj_info.semi_major_axis
        r_pol= proj_info.semi_minor_axis
        x_rad= dataset.variables["x"][:] * proj_info.perspective_point_height
        y_rad= dataset.variables["y"][:] * proj_info.perspective_point_height
        lambda_0 = np.deg2rad(lon_origin)
        a_var = np.sin(x_rad)**2 + np.cos(x_rad)**2*(np.cos(y_rad)**2+(r_eq**2/r_pol**2)*np.sin(y_rad)**2)
        b_var = -2*H*np.cos(x_rad)*np.cos(y_rad)
        c_var = H**2 - r_eq**2
        r_s   = (-b_var - np.sqrt(b_var**2 - 4*a_var*c_var))/(2*a_var)
        s_x   = r_s*np.cos(x_rad)*np.cos(y_rad)
        s_y   = -r_s*np.sin(x_rad)
        s_z   = r_s*np.cos(x_rad)*np.sin(y_rad)
        lat   = np.rad2deg(np.arctan((r_eq**2/r_pol**2)*(s_z/np.sqrt((H-s_x)**2+s_y**2))))
        lon   = np.rad2deg(lambda_0 - np.arctan(s_y/(H-s_x)))
        data  = dataset.variables["CMI"][:]
        mask  = (lat>=lat_min)&(lat<=lat_max)&(lon>=lon_min)&(lon<=lon_max)
        if not np.any(mask):
            dataset.close(); os.unlink(tmp_path); return None, None, None
        rows = np.where(mask.any(axis=1))[0]
        cols = np.where(mask.any(axis=0))[0]
        data_rec = data[rows[0]:rows[-1]+1, cols[0]:cols[-1]+1]
        ts   = datetime.strptime(arquivos[0].split("_s")[1][:13], "%Y%j%H%M%S")
        dataset.close(); os.unlink(tmp_path)
        return np.array(data_rec), [lon_min, lon_max, lat_min, lat_max], ts
    except Exception:
        return None, None, None


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISES AGRONÔMICAS
# ─────────────────────────────────────────────────────────────────────────────

def calcular_janela_defensivos(dados: dict) -> list:
    if not dados or "hourly" not in dados:
        return []
    h = dados["hourly"]
    janelas = []
    for i, t in enumerate(h.get("time",[])[:24]):
        hora  = t.split("T")[1][:5] if "T" in t else t[-5:]
        pp    = (h.get("precipitation",[0]*24)[i] or 0)
        tmp   = (h.get("temperature_2m",[25]*24)[i] or 25)
        ur    = (h.get("relativehumidity_2m",[60]*24)[i] or 60)
        vnt   = (h.get("windspeed_10m",[5]*24)[i] or 0)
        bloq  = []
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
    if not dados or "daily" not in dados:
        return {}
    cfg    = CULTURAS_GDA.get(cultura, CULTURAS_GDA["Soja"])
    tb, tc = cfg["tb"], cfg["tc"]
    stags  = cfg["estagios"]
    d      = dados["daily"]
    gda_total = 0.0
    for tmax, tmin in zip(d.get("temperature_2m_max",[]), d.get("temperature_2m_min",[])):
        if tmax is None or tmin is None:
            continue
        tmedia = (min(tmax, tc) + max(tmin, tb)) / 2
        gda_total += max(0.0, tmedia - tb)
    estagio_atual = stags[0][1]
    for limiar, nome in stags:
        if gda_total >= limiar: estagio_atual = nome
        else: break
    proximo = next(((lim, nome) for lim, nome in stags if gda_total < lim), None)
    return {
        "cultura": cultura, "gda_total": round(gda_total, 1),
        "estagio_atual": estagio_atual, "proximo_estagio": proximo,
        "dias_desde_semeadura": (datetime.now().date() - data_semeadura.date()).days,
        "tb": tb,
    }


def calcular_risco_fitossanitario(dados: dict) -> list:
    if not dados or "hourly" not in dados:
        return []
    h    = dados["hourly"]
    temp = h.get("temperature_2m",[])[:48]
    umid = h.get("relativehumidity_2m",[])[:48]
    alertas = []
    h_fer = h_bru = 0
    for t, u in zip(temp, umid):
        if t and u:
            if 15 <= t <= 30 and u > 80: h_fer += 1
            else: h_fer = 0
            if 20 <= t <= 28 and u > 90: h_bru += 1
            else: h_bru = 0
    if h_fer >= 12:
        nivel = "Crítico" if h_fer>=20 else ("Alto" if h_fer>=16 else "Médio")
        alertas.append({"doenca":"Ferrugem Asiática (Soja)","nivel":nivel,"horas":h_fer,
                         "icone":"🍂","cor":"vermelho" if nivel in ["Crítico","Alto"] else "amarelo",
                         "msg":f"{h_fer}h favoráveis. Aplique triazol+estrobilurina preventivamente."})
    if h_bru >= 10:
        nivel = "Crítico" if h_bru>=18 else ("Alto" if h_bru>=14 else "Médio")
        alertas.append({"doenca":"Brusone (Arroz/Trigo)","nivel":nivel,"horas":h_bru,
                         "icone":"🌾","cor":"vermelho" if nivel in ["Crítico","Alto"] else "amarelo",
                         "msg":f"{h_bru}h favoráveis. Risco no espigamento. Aplique triclazol."})
    if not alertas:
        alertas.append({"doenca":"Sem risco fitossanitário","nivel":"Baixo","horas":0,
                         "icone":"✅","cor":"verde",
                         "msg":"Condições desfavoráveis ao desenvolvimento de doenças foliares (48h)."})
    return alertas


def calcular_balanco_hidrico_thornthwaite(dados: dict, cad_mm: float = 65.0) -> dict:
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
    alertas = []
    if not dados or "daily" not in dados:
        return alertas
    d  = dados["daily"]
    tmin         = d.get("temperature_2m_min", [20]*7)
    precip_diario= d.get("precipitation_sum", [0]*7)
    wcode        = d.get("weathercode", [0]*7)
    estagio_atual= gda_info.get("estagio_atual","") if gda_info else ""
    est_crit     = any(s in estagio_atual for s in ["R1","R2","R3","R4","R5","R6"])
    for i, t in enumerate(tmin[:3]):
        if t is not None and t < 5:
            classe = "vermelho" if (t < 2 or est_crit) else "amarelo"
            nivel  = "🔴 EMERGÊNCIA" if (t < 2 or est_crit) else "🟡 ALERTA"
            nota   = f" ⚠️ Cultura em {estagio_atual}!" if est_crit else ""
            alertas.append({"nivel":classe,"icone":"❄️",
                            "titulo":f"{nivel} — Risco de Geada",
                            "msg":f"Mínima {t:.1f}°C em {i+1} dia(s). Proteja culturas sensíveis.{nota}"})
    for i, pp in enumerate(precip_diario[:3]):
        if pp is not None and pp > 40:
            classe = "vermelho" if pp > 80 else "amarelo"
            nivel  = "🔴 EMERGÊNCIA" if pp > 80 else "🟡 ALERTA"
            alertas.append({"nivel":classe,"icone":"⛈️",
                            "titulo":f"{nivel} — Chuva Intensa",
                            "msg":f"{pp:.0f} mm em 24h. Risco de enxurrada. Suspenda pulverizações."})
    for i, wc in enumerate(wcode[:3]):
        if wc in [95, 99]:
            alertas.append({"nivel":"vermelho","icone":"⚡",
                            "titulo":"🔴 EMERGÊNCIA — Tempestade Severa",
                            "msg":f"Tempestade com raios em {i+1} dia(s). Risco granizo/ventos >60km/h."})
    dias_secos = sum(1 for pp in precip_diario if pp is not None and pp < 1)
    if dias_secos >= 5:
        alertas.append({"nivel":"amarelo","icone":"🌵",
                        "titulo":"🟡 ALERTA — Veranico",
                        "msg":f"{dias_secos} dias sem chuva previstos. Intensifique irrigação."})
    if not alertas:
        alertas.append({"nivel":"verde","icone":"✅",
                        "titulo":"🟢 SEM ALERTAS ATIVOS",
                        "msg":"Condições favoráveis para as próximas 72 horas."})
    return alertas


# ─────────────────────────────────────────────────────────────────────────────
# CARREGAMENTO DOS SHAPEFILES
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def carregar_shapefiles():
    shps = {}
    try:
        url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-50-mun.json"
        shps["municipios"] = gpd.read_file(url)
    except Exception:
        from shapely.geometry import box as sgbox
        shps["municipios"] = gpd.GeoDataFrame(
            {"name":["MS"]}, geometry=[sgbox(-57.65,-23.67,-50.92,-17.16)], crs="EPSG:4326")
    from shapely.geometry import Polygon, LineString
    shps["biomas"] = gpd.GeoDataFrame(
        {"bioma":["Pantanal","Cerrado","Campo/Agro","Transição"]},
        geometry=[
            Polygon([(-57.65,-19.5),(-55.5,-19.5),(-55.5,-17.16),(-57.65,-17.16)]),
            Polygon([(-55.5,-19.5),(-50.92,-19.5),(-50.92,-17.16),(-55.5,-17.16)]),
            Polygon([(-57.65,-23.67),(-53.5,-23.67),(-53.5,-19.5),(-57.65,-19.5)]),
            Polygon([(-53.5,-23.67),(-50.92,-23.67),(-50.92,-19.5),(-53.5,-19.5)]),
        ], crs="EPSG:4326")
    shps["hidrografia"] = gpd.GeoDataFrame(
        {"nome":["Rio Paraguai","Rio Paraná","Rio Miranda","Rio Verde"]},
        geometry=[
            LineString([(-57.65,-19.0),(-56.5,-20.5),(-57.2,-22.0)]),
            LineString([(-53.5,-20.0),(-52.0,-22.5),(-50.92,-23.0)]),
            LineString([(-55.5,-19.5),(-56.5,-20.5),(-57.0,-21.0)]),
            LineString([(-54.5,-19.0),(-54.0,-21.0),(-53.8,-22.5)]),
        ], crs="EPSG:4326")
    shps["rodovias"] = gpd.GeoDataFrame(
        {"rodovia":["BR-163","BR-262","BR-060"]},
        geometry=[
            LineString([(-55.3,-17.2),(-54.9,-20.4),(-55.0,-23.0)]),
            LineString([(-57.4,-19.0),(-54.6,-20.4),(-51.0,-20.8)]),
            LineString([(-54.0,-17.8),(-54.6,-20.4),(-54.0,-23.5)]),
        ], crs="EPSG:4326")
    return shps


# ─────────────────────────────────────────────────────────────────────────────
# GERAÇÃO DOS GRÁFICOS
# ─────────────────────────────────────────────────────────────────────────────

def gerar_mapa_banda(banda_id, shps, municipio, coords,
                     goes_data=None, extent=None, df_focos=None):
    info    = BANDAS_INFO[banda_id]
    lat, lon= coords["lat"], coords["lon"]
    bbox_ms = [-57.65, -50.92, -23.67, -17.16]
    fig, ax = plt.subplots(figsize=(9, 7), facecolor=PRETO)
    ax.set_facecolor("#0d1117")
    if goes_data is not None and extent is not None:
        img  = ax.imshow(goes_data, extent=extent, cmap=info["cmap"], origin="upper",
                         alpha=0.85, aspect="auto",
                         vmin=np.nanpercentile(goes_data,2), vmax=np.nanpercentile(goes_data,98))
        cbar = plt.colorbar(img, ax=ax, fraction=0.03, pad=0.01)
        cbar.set_label(info["nome"], color="white", fontsize=8)
        cbar.ax.tick_params(colors="white")
    else:
        x = np.linspace(bbox_ms[0],bbox_ms[1],300)
        y = np.linspace(bbox_ms[2],bbox_ms[3],300)
        X,Y = np.meshgrid(x,y)
        np.random.seed(int(banda_id.replace("B","")))
        if banda_id in ["B07","B13"]:
            Z = np.sin(X*0.4)*np.cos(Y*0.4)*30+280+np.random.normal(0,5,X.shape)
        elif banda_id=="B09":
            Z = np.cos(X*0.3+Y*0.2)*20+250+np.random.normal(0,3,X.shape)
        elif banda_id in ["B02","B03"]:
            Z = (np.abs(np.sin(X*0.5)*np.cos(Y*0.6))*0.6+0.1+np.random.normal(0,0.05,X.shape)).clip(0,1)
        else:
            Z = np.sin(X*0.35)*np.cos(Y*0.35)*25+270+np.random.normal(0,4,X.shape)
        img  = ax.pcolormesh(X,Y,Z,cmap=info["cmap"],shading="auto",alpha=0.9)
        cbar = plt.colorbar(img, ax=ax, fraction=0.03, pad=0.01)
        cbar.set_label(info["nome"], color="white", fontsize=8)
        cbar.ax.tick_params(colors="white")
        ax.text(0.02,0.02,"⚠ GOES-19 simulado",transform=ax.transAxes,
                fontsize=7,color="yellow",alpha=0.8,va="bottom")
    try:
        gdf = shps["municipios"]
        gdf.boundary.plot(ax=ax, color="white", linewidth=0.4, alpha=0.5)
        col = next((c for c in gdf.columns if "nome" in c.lower() or "name" in c.lower()), None)
        if col:
            sel = gdf[gdf[col].str.upper() == municipio.upper()]
            if not sel.empty:
                sel.plot(ax=ax, facecolor="none", edgecolor=VERDE_MEDIO, linewidth=2.0, alpha=0.9)
                sel.plot(ax=ax, facecolor=VERDE_MEDIO, alpha=0.15)
    except Exception: pass
    try: shps["biomas"].boundary.plot(ax=ax,color="#88BB88",linewidth=0.8,linestyle="--",alpha=0.5)
    except Exception: pass
    try: shps["hidrografia"].plot(ax=ax,color="#4FC3F7",linewidth=1.0,alpha=0.7)
    except Exception: pass
    try: shps["rodovias"].plot(ax=ax,color="#FFB74D",linewidth=0.8,alpha=0.6)
    except Exception: pass
    if banda_id in ["B07","B03"] and df_focos is not None and not df_focos.empty:
        try:
            frp_v = df_focos.get("frp", pd.Series([50]*len(df_focos)))
            frp_n = (frp_v - frp_v.min()) / (frp_v.max() - frp_v.min() + 1e-5)
            cores = plt.cm.YlOrRd(frp_n.values)
            for i, row in df_focos.iterrows():
                ax.plot(row.get("longitude",0), row.get("latitude",0),
                        marker="^", color=cores[i%len(cores)], markersize=6,
                        alpha=0.85, zorder=9, markeredgecolor="white", markeredgewidth=0.4)
        except Exception: pass
    ax.plot(lon,lat,marker="*",color=VERDE_MEDIO,markersize=14,zorder=10,
            markeredgecolor="white",markeredgewidth=1.2)
    ax.annotate(f" {municipio}",(lon,lat),fontsize=9,color="white",fontweight="bold",
                xytext=(6,6),textcoords="offset points",zorder=11,
                bbox=dict(boxstyle="round,pad=0.3",facecolor=VERDE_ESCURO,alpha=0.8,edgecolor="none"))
    ax.set_xlim(bbox_ms[0]-.5,bbox_ms[1]+.5); ax.set_ylim(bbox_ms[2]-.5,bbox_ms[3]+.5)
    ax.set_title(f"{info['icon']}  {info['nome']}\n{info['uso']}",
                 color="white",fontsize=10,fontweight="bold",pad=10,fontfamily="monospace")
    ax.set_xlabel("Longitude",color="#aaaaaa",fontsize=8)
    ax.set_ylabel("Latitude",color="#aaaaaa",fontsize=8)
    ax.tick_params(colors="#aaaaaa",labelsize=7)
    for sp in ax.spines.values(): sp.set_edgecolor("#333333")
    ax.grid(True,color="#222222",linewidth=0.4,alpha=0.5)
    ax.annotate("N ▲",xy=(0.97,0.95),xycoords="axes fraction",
                ha="right",va="top",color="white",fontsize=11,fontweight="bold")
    handles = [
        mpatches.Patch(facecolor="none",edgecolor="white",linewidth=0.4,label="Municípios MS"),
        mpatches.Patch(facecolor="none",edgecolor=VERDE_MEDIO,linewidth=1.5,label=f"▶ {municipio}"),
        mpatches.Patch(facecolor="#4FC3F7",alpha=0.7,label="Rios"),
        mpatches.Patch(facecolor="#FFB74D",alpha=0.6,label="Rodovias"),
    ]
    if banda_id in ["B07","B03"]:
        handles.append(mpatches.Patch(facecolor="#FF6B35",alpha=0.8,label="Focos INPE"))
    ax.legend(handles=handles,loc="lower left",fontsize=7,framealpha=0.75,
              facecolor="#0d1117",labelcolor="white",edgecolor="#333333",ncol=2)
    fig.text(0.01,0.005,
             f"Yamada Engenharia  •  GOES-19 ABI  •  {datetime.now().strftime('%d/%m/%Y %H:%M')} UTC-4",
             color="#888888",fontsize=7,va="bottom")
    plt.tight_layout(pad=0.5)
    return fig


def gerar_grafico_previsao(dados, municipio):
    if not dados or "hourly" not in dados: return None
    h  = dados["hourly"]
    tr = h.get("time",[])[:24]
    pp = h.get("precipitation",[0]*24)[:24]
    te = h.get("temperature_2m",[20]*24)[:24]
    ur = h.get("relativehumidity_2m",[60]*24)[:24]
    vt = h.get("windspeed_10m",[0]*24)[:24]
    hs = [t.split("T")[1][:5] if "T" in t else t[-5:] for t in tr]
    idx= list(range(len(hs)))
    fig,axes = plt.subplots(3,1,figsize=(11,8),facecolor="#0d1117",
                             gridspec_kw={"height_ratios":[2,2,1.2]})
    fig.suptitle(f"⏱ Previsão 24h — {municipio}",color="white",fontsize=13,fontweight="bold",y=0.98)
    for ax in axes:
        ax.set_facecolor("#111827"); ax.tick_params(colors="#9ca3af",labelsize=8)
        for sp in ax.spines.values(): sp.set_edgecolor("#1f2937")
        ax.grid(True,color="#1f2937",linewidth=0.5,alpha=0.8)
    cores=[VERDE_MEDIO if p<5 else AMARELO_ALERT if p<20 else VERMELHO_ALRT for p in pp]
    axes[0].bar(idx,pp,color=cores,alpha=0.85,width=0.7,edgecolor="none")
    axes[0].set_ylabel("Precipitação (mm)",color="#9ca3af",fontsize=9); axes[0].set_xticks([])
    axes[0].text(0.99,0.92,f"Total 24h: {sum(p for p in pp if p):.1f} mm",
                 transform=axes[0].transAxes,ha="right",color="white",fontsize=9,
                 bbox=dict(facecolor=VERDE_ESCURO,alpha=0.7,boxstyle="round,pad=0.3"))
    ax2b = axes[1].twinx()
    lt=axes[1].plot(idx,te,color="#f97316",linewidth=2.2,label="Temp (°C)",zorder=5)
    axes[1].fill_between(idx,te,alpha=0.15,color="#f97316")
    lu=ax2b.plot(idx,ur,color="#38bdf8",linewidth=1.8,linestyle="--",label="Umidade (%)",zorder=4)
    ax2b.fill_between(idx,ur,alpha=0.07,color="#38bdf8")
    axes[1].set_ylabel("Temperatura (°C)",color="#f97316",fontsize=9)
    ax2b.set_ylabel("Umidade (%)",color="#38bdf8",fontsize=9)
    ax2b.tick_params(colors="#38bdf8",labelsize=8); axes[1].set_xticks([])
    lines=lt+lu
    axes[1].legend(lines,[l.get_label() for l in lines],loc="upper right",fontsize=8,
                   facecolor="#111827",labelcolor="white",edgecolor="#374151")
    axes[2].plot(idx,vt,color="#a78bfa",linewidth=1.6)
    axes[2].fill_between(idx,vt,alpha=0.15,color="#a78bfa")
    axes[2].axhline(10,color="yellow",linewidth=0.8,linestyle="--",alpha=0.6,label="Lim. defensivos")
    axes[2].set_ylabel("Vento (km/h)",color="#a78bfa",fontsize=9)
    axes[2].set_xticks(idx[::2])
    axes[2].set_xticklabels(hs[::2],rotation=45,ha="right",fontsize=7,color="#9ca3af")
    axes[2].legend(fontsize=7,facecolor="#111827",labelcolor="white",edgecolor="#374151")
    plt.tight_layout(rect=[0,0,1,0.97])
    return fig


def gerar_grafico_ndvi(ndvi_data, municipio):
    if not ndvi_data or "listaSerie" not in ndvi_data: return None
    serie   = ndvi_data["listaSerie"]
    datas   = [s.get("data", s.get("ano","")) for s in serie]
    valores = [float(s.get("ndvi", s.get("valor",0))) for s in serie]
    if len(valores) < 2: return None
    fig, ax = plt.subplots(figsize=(10,4),facecolor="#0d1117")
    ax.set_facecolor("#111827")
    ax.fill_between(range(len(valores)),valores,alpha=0.15,color=VERDE_MEDIO)
    ax.plot(range(len(valores)),valores,color=VERDE_MEDIO,linewidth=1.8,zorder=4)
    med = float(np.median(valores[:-1])) if len(valores)>1 else 0.5
    ax.axhline(med,color="#FFC107",linewidth=1.2,linestyle="--",alpha=0.8,label=f"Mediana: {med:.3f}")
    ax.scatter([len(valores)-1],[valores[-1]],color="#FF5722",s=80,zorder=6,label=f"Atual: {valores[-1]:.3f}")
    delta = valores[-1]-med
    ax.annotate(f"Δ {delta:+.3f}",xy=(len(valores)-1,valores[-1]),
                xytext=(-40,15),textcoords="offset points",
                color=VERDE_MEDIO if delta>=0 else VERMELHO_ALRT,fontsize=9,fontweight="bold",
                arrowprops=dict(arrowstyle="->",color=VERDE_MEDIO if delta>=0 else VERMELHO_ALRT,lw=1.2))
    step = max(1,len(datas)//8)
    ax.set_xticks(range(0,len(datas),step))
    ax.set_xticklabels([str(datas[i])[:4] for i in range(0,len(datas),step)],
                       color="#9ca3af",fontsize=8,rotation=30)
    ax.set_ylabel("NDVI",color="#9ca3af",fontsize=9); ax.set_ylim(0,1)
    ax.tick_params(colors="#9ca3af",labelsize=8)
    for sp in ax.spines.values(): sp.set_edgecolor("#1f2937")
    ax.grid(True,color="#1f2937",linewidth=0.5,alpha=0.6)
    sim = " ⚠ (simulado)" if ndvi_data.get("_simulado") else ""
    ax.set_title(f"🌿 NDVI Histórico — {municipio}{sim}",color="white",fontsize=11,fontweight="bold")
    ax.legend(fontsize=8,facecolor="#111827",labelcolor="white",edgecolor="#374151",loc="lower right")
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
    ax1.axhline(cad*0.4,color="#EF5350",linewidth=0.8,linestyle=":",label="Limite crítico (40%)")
    ax1.set_ylabel("Armazenamento (mm)",color="#9ca3af",fontsize=9); ax1.set_xticks([])
    ax1.set_ylim(0,cad*1.15)
    ax1.legend(fontsize=8,facecolor="#111827",labelcolor="white",edgecolor="#374151")
    ax1.set_title("💧 Balanço Hídrico — Thornthwaite-Mather",color="white",fontsize=11,fontweight="bold")
    ax2.bar(range(len(def_)),def_,color="#EF5350",alpha=0.8,label="Déficit",width=0.4)
    ax2.bar([i+0.42 for i in range(len(exc))],exc,color="#29B6F6",alpha=0.8,label="Excedente",width=0.4)
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
               65:"⛈ Forte",80:"🌦 Pancadas",81:"⛈ Pancadas fortes",95:"⛈ Tempestade",99:"⛈ Granizo"}
    datas  = [datetime.fromisoformat(t).strftime("%a %d/%m") for t in d.get("time",[])]
    cond   = [wcode_map.get(w,f"Cód {w}") for w in d.get("weathercode",[0]*7)]
    tmax   = [f"{v:.1f}°C" if v else "—" for v in d.get("temperature_2m_max",[])]
    tmin   = [f"{v:.1f}°C" if v else "—" for v in d.get("temperature_2m_min",[])]
    precip = [f"{v:.1f} mm" if v else "0.0 mm" for v in d.get("precipitation_sum",[])]
    eto    = [f"{v:.2f} mm" if v else "—" for v in d.get("et0_fao_evapotranspiration",[])]
    return pd.DataFrame({"Data":datas,"Condição":cond,"T. Máx":tmax,
                         "T. Mín":tmin,"Precipitação":precip,"ETo (mm)":eto})


# ─────────────────────────────────────────────────────────────────────────────
# INTERFACE PRINCIPAL — MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():

    # ── Header ──
    st.markdown("""
    <div class="yamada-header">
      <div>
        <h1>🌿 Yamada Engenharia</h1>
        <p>Plataforma de Monitoramento Agroclimático — Mato Grosso do Sul</p>
        <p style="font-size:0.78rem;margin-top:4px;color:rgba(255,255,255,0.55);">
          GOES-19 ABI · Open-Meteo · NASA POWER · SATVeg · INPE · INMET
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)

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

        # Município
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.9rem;">📍 MUNICÍPIO ALVO</p>', unsafe_allow_html=True)
        municipio_sel = st.selectbox("Município", list(MUNICIPIOS_MS.keys()), index=0, label_visibility="collapsed")
        coords        = MUNICIPIOS_MS[municipio_sel]
        st.caption(f"🌐 {coords['lat']:.4f}°S, {coords['lon']:.4f}°W")
        st.caption(f"📌 Região: {coords['regiao']}")
        st.markdown("---")

        # Solo
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.9rem;">🌱 TEXTURA DO SOLO</p>', unsafe_allow_html=True)
        textura_solo = st.selectbox("Textura",
            ["Argiloso (CAD=100mm)","Médio/Franco (CAD=65mm)","Arenoso (CAD=35mm)"],
            index=1, label_visibility="collapsed")
        cad_mm = {"Argiloso (CAD=100mm)":100.0,"Médio/Franco (CAD=65mm)":65.0,"Arenoso (CAD=35mm)":35.0}[textura_solo]
        st.markdown("---")

        # Fenologia
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.9rem;">🌾 FENOLOGIA</p>', unsafe_allow_html=True)
        cultura_sel    = st.selectbox("Cultura", list(CULTURAS_GDA.keys()), index=0, label_visibility="collapsed")
        data_semeadura = st.date_input("Data de semeadura",
            value=datetime.now().date()-timedelta(days=45),
            max_value=datetime.now().date())
        st.markdown("---")

        # Bandas GOES
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.9rem;">🛰️ BANDAS GOES-19</p>', unsafe_allow_html=True)
        bandas_sel = {bid: st.checkbox(f"{binfo['icon']} {bid} — {binfo['nome'].split('(')[0].strip()}",
                         value=(bid in ["B02","B13","B07"]), key=f"cb_{bid}")
                      for bid, binfo in BANDAS_INFO.items()}
        st.markdown("---")

        # Config
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.9rem;">⚙️ CONFIGURAÇÕES</p>', unsafe_allow_html=True)
        usar_goes_real = st.checkbox("🛰 Tentar GOES-19 Real (S3)", value=False)
        horas_atras    = st.slider("Horas atrás para GOES", 1, 6, 2)
        st.markdown("---")

        # ── Painel do scheduler / e-mail ──────────────────────────────────────
        st.markdown('<p style="font-family:Montserrat;font-weight:700;color:#a5d6a7;font-size:0.9rem;">📧 RELATÓRIO AUTOMÁTICO</p>', unsafe_allow_html=True)

        if _email_configurado:
            st.caption(f"✅ E-mail configurado para: {', '.join(EMAIL_DESTINATARIOS)}")
        else:
            st.caption("⚠️ Configure [email] no secrets.toml para ativar.")

        if "scheduler_obj" in st.session_state:
            _sched_ref = st.session_state["scheduler_obj"]
            _job = _sched_ref.get_job("relatorio_automatico")
            if _job and _job.next_run_time:
                st.info(f"⏰ Próximo envio automático:\n{_job.next_run_time.strftime('%d/%m/%Y %H:%M')}")
            if st.button("▶ Enviar agora (manual)", use_container_width=True):
                threading.Thread(target=scheduled_report_automatico, daemon=True).start()
                st.success("Iniciado em background!")

        with _log_lock:
            _log_snap = list(_scheduler_log)
        if _log_snap:
            st.markdown("**Histórico:**")
            for entry in _log_snap[:3]:
                st.caption(f"{entry['inicio']} — {entry['status']}" +
                           (f"\n_{entry['detalhe']}_" if entry['detalhe'] else ""))
        st.markdown("---")

        botao = st.button("🚀  GERAR ANÁLISE", use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # TELA DE BOAS-VINDAS
    # ─────────────────────────────────────────────────────────────────────────
    if not botao:
        c1,c2,c3 = st.columns(3)
        with c1:
            st.markdown("""<div class="band-card"><h4>🛰️ GOES-19 + INPE</h4>
            <p>7 bandas ABI + produtos FDC (focos) e RRQPE (precipitação). Focos reais via BDQueimadas.</p></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class="band-card"><h4>🌡️ Previsão + Análise</h4>
            <p>Janela de defensivos, graus-dia, fenologia, risco fitossanitário e balanço hídrico TM.</p></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown("""<div class="band-card"><h4>📧 Relatório Automático</h4>
            <p>E-mail rico com métricas, alertas, tabelas e recomendações enviado às 06h, 12h e 18h.</p></div>""", unsafe_allow_html=True)
        st.info("👈 Configure o município, solo e cultura na barra lateral, depois clique em **GERAR ANÁLISE**.")
        return

    # ─────────────────────────────────────────────────────────────────────────
    # COLETA DE DADOS
    # ─────────────────────────────────────────────────────────────────────────
    bandas_ativas = [bid for bid, ativo in bandas_sel.items() if ativo]
    if not bandas_ativas:
        st.warning("⚠️ Selecione pelo menos uma banda GOES-19.")
        return

    lat, lon  = coords["lat"], coords["lon"]
    progress  = st.progress(0, text="Inicializando...")

    progress.progress(5,  text="📂 Shapefiles MS...")
    shps = carregar_shapefiles()

    progress.progress(15, text="🌤 Open-Meteo...")
    dados_meteo = buscar_previsao_openmeteo(lat, lon)

    progress.progress(28, text="☀️ NASA POWER...")
    dados_nasa = buscar_nasa_power(lat, lon)

    progress.progress(38, text="🌿 SATVeg NDVI...")
    ndvi_data = buscar_satveg_ndvi(lat, lon)

    progress.progress(48, text="🔥 INPE Queimadas...")
    df_focos = buscar_focos_inpe()

    progress.progress(55, text="📡 INMET estações...")
    df_inmet = buscar_dados_inmet()

    goes_results = {}
    if usar_goes_real:
        progress.progress(60, text="🛰 GOES-19 S3...")
        for bid in bandas_ativas:
            d_arr, ext, ts = baixar_e_recortar_goes19(bid,-23.67,-17.16,-57.65,-50.92)
            goes_results[bid] = (d_arr, ext, ts)

    progress.progress(70, text="📊 Análises agronômicas...")
    janelas_def = calcular_janela_defensivos(dados_meteo)
    gda_info    = calcular_graus_dia(dados_meteo, cultura_sel,
                                     datetime.combine(data_semeadura, datetime.min.time()))
    riscos_fito = calcular_risco_fitossanitario(dados_meteo)
    bh          = calcular_balanco_hidrico_thornthwaite(dados_meteo, cad_mm)
    alertas     = calcular_alertas(dados_meteo, lat, gda_info)

    progress.progress(80, text="🗺 Renderizando...")

    # ── Banner do município ───────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,{VERDE_ESCURO},{VERDE_MEDIO});
                border-radius:10px;padding:16px 24px;margin-bottom:20px;">
      <span style="color:white;font-family:Montserrat;font-weight:700;font-size:1.1rem;">
        📍 {municipio_sel} — {coords['regiao']}
      </span>
      <span style="color:rgba(255,255,255,0.75);font-size:0.85rem;margin-left:16px;">
        {datetime.now().strftime('%d/%m/%Y  %H:%M')} (Horário de Brasília)
      </span>
    </div>""", unsafe_allow_html=True)

    # ── Métricas rápidas ──────────────────────────────────────────────────────
    if dados_meteo and "hourly" in dados_meteo:
        h = dados_meteo.get("hourly",{}); d = dados_meteo.get("daily",{})
        try:
            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.metric("🌡 Temperatura",  f"{h.get('temperature_2m',[None])[0]:.1f}°C")
            with c2: st.metric("🌧 Chuva 24h",    f"{d.get('precipitation_sum',[0])[0] or 0:.1f} mm")
            with c3: st.metric("💧 Umidade",       f"{h.get('relativehumidity_2m',[None])[0]:.0f}%")
            with c4: st.metric("💨 Vento",         f"{h.get('windspeed_10m',[None])[0]:.0f} km/h")
            with c5: st.metric("🌿 ETo",           f"{d.get('et0_fao_evapotranspiration',[None])[0]:.2f} mm")
        except Exception: pass

    # ═════════════════════════════════════════════════════════════════════════
    # ABAS TEMÁTICAS
    # ═════════════════════════════════════════════════════════════════════════
    aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
        "🛰️ Satélite GOES-19",
        "📈 Previsão Meteorológica",
        "🌾 Análise Agronômica",
        "💧 Balanço Hídrico & Solo",
        "⚠️ Alertas & Fitossanidade",
        "📧 Relatório & E-mail",
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 1 — SATÉLITE GOES-19
    # Mapas de todas as bandas selecionadas + focos de queimada INPE
    # ─────────────────────────────────────────────────────────────────────────
    with aba1:
        st.markdown('<div class="secao-titulo">🛰️ Mapas de Satélite GOES-19</div>', unsafe_allow_html=True)
        st.caption(f"Satélite operacional Leste desde abril/2025 · {len(bandas_ativas)} banda(s) selecionada(s)")

        n_cols    = min(2, len(bandas_ativas))
        rows_map  = [bandas_ativas[i:i+n_cols] for i in range(0, len(bandas_ativas), n_cols)]

        for row in rows_map:
            cols = st.columns(n_cols)
            for j, bid in enumerate(row):
                with cols[j]:
                    g_data = g_ext = None
                    if usar_goes_real and bid in goes_results:
                        g_data, g_ext, _ = goes_results[bid]
                    fig = gerar_mapa_banda(bid, shps, municipio_sel, coords,
                                           goes_data=g_data, extent=g_ext, df_focos=df_focos)
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)
                    binfo = BANDAS_INFO[bid]
                    st.markdown(f"""<div class="band-card" style="margin-top:-6px;">
                      <h4>{binfo['icon']} {bid} — {binfo['nome']}</h4>
                      <p>{binfo['uso']}</p></div>""", unsafe_allow_html=True)

        # Focos de queimada
        if not df_focos.empty:
            st.markdown('<div class="secao-titulo">🔥 Focos de Queimada — INPE/BDQueimadas</div>', unsafe_allow_html=True)
            sim_label = " ⚠ (dados simulados)" if df_focos.get("_simulado",pd.Series([False])).any() else ""
            c1,c2 = st.columns([1,3])
            with c1:
                st.metric("Focos nas últimas 48h", len(df_focos), help="MS — INPE")
                if "frp" in df_focos.columns:
                    st.metric("FRP máximo (MW)", f"{df_focos['frp'].max():.0f}")
            with c2:
                show_cols = [c for c in ["municipio","latitude","longitude","frp"] if c in df_focos.columns]
                st.dataframe(df_focos[show_cols].head(10), use_container_width=True, hide_index=True)
            if sim_label:
                st.caption(sim_label)

        # Estações INMET
        st.markdown('<div class="secao-titulo">📡 Estações INMET — Mato Grosso do Sul</div>', unsafe_allow_html=True)
        if not df_inmet.empty:
            st.dataframe(df_inmet, use_container_width=True, hide_index=True)
            st.caption("Estações automáticas | Fonte: INMET (apitempo.inmet.gov.br)")

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 2 — PREVISÃO METEOROLÓGICA
    # Gráfico 24h, tabela 7 dias, umidade do solo NASA POWER
    # ─────────────────────────────────────────────────────────────────────────
    with aba2:
        st.markdown('<div class="secao-titulo">📈 Previsão Horária — Próximas 24 Horas</div>', unsafe_allow_html=True)
        fig_prev = gerar_grafico_previsao(dados_meteo, municipio_sel)
        if fig_prev:
            st.pyplot(fig_prev, use_container_width=True)
            plt.close(fig_prev)
        else:
            st.warning("⚠️ Previsão horária indisponível.")

        st.markdown('<div class="secao-titulo">📅 Previsão 7 Dias</div>', unsafe_allow_html=True)
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
                    st.markdown('<div class="secao-titulo">🌱 Umidade do Solo — NASA POWER (últimos 14 dias)</div>', unsafe_allow_html=True)
                    datas_n = sorted(gwettop.keys())[-14:]
                    vt = [gwettop.get(d,0)  for d in datas_n]
                    vr = [gwetroot.get(d,0) for d in datas_n]
                    fig_s,ax_s = plt.subplots(figsize=(10,3.5),facecolor="#0d1117")
                    ax_s.set_facecolor("#111827")
                    ax_s.plot(range(len(datas_n)),vt, color="#66BB6A",linewidth=2,label="GWETTOP (0-5cm)")
                    ax_s.fill_between(range(len(datas_n)),vt,alpha=0.2,color="#66BB6A")
                    ax_s.plot(range(len(datas_n)),vr,color="#42A5F5",linewidth=2,linestyle="--",label="GWETROOT (radicular)")
                    ax_s.fill_between(range(len(datas_n)),vr,alpha=0.15,color="#42A5F5")
                    ax_s.axhline(0.5,color="#FFB74D",linewidth=0.8,linestyle=":",alpha=0.7,label="Campo (0.5)")
                    ax_s.set_ylim(0,1); ax_s.set_ylabel("Umidade relativa",color="#9ca3af",fontsize=9)
                    ax_s.set_xticks(range(0,len(datas_n),2))
                    ax_s.set_xticklabels([d[4:6]+"/"+d[6:8] for d in datas_n[::2]],
                                         color="#9ca3af",fontsize=8,rotation=30)
                    ax_s.tick_params(colors="#9ca3af",labelsize=8)
                    for sp in ax_s.spines.values(): sp.set_edgecolor("#1f2937")
                    ax_s.grid(True,color="#1f2937",linewidth=0.5,alpha=0.6)
                    ax_s.legend(fontsize=8,facecolor="#111827",labelcolor="white",edgecolor="#374151")
                    ax_s.set_title("Umidade do Solo — NASA POWER (GWETTOP & GWETROOT)",
                                   color="white",fontsize=10)
                    plt.tight_layout()
                    st.pyplot(fig_s, use_container_width=True)
                    plt.close(fig_s)
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 3 — ANÁLISE AGRONÔMICA
    # NDVI histórico (SATVeg), Graus-dia/fenologia, janela de defensivos
    # ─────────────────────────────────────────────────────────────────────────
    with aba3:
        # NDVI histórico
        st.markdown('<div class="secao-titulo">🌿 Série Histórica NDVI — SATVeg/Embrapa</div>', unsafe_allow_html=True)
        fig_ndvi = gerar_grafico_ndvi(ndvi_data, municipio_sel)
        if fig_ndvi:
            st.pyplot(fig_ndvi, use_container_width=True)
            plt.close(fig_ndvi)

        # Graus-dia
        st.markdown(f'<div class="secao-titulo">🌾 Graus-Dia (GDA) e Fenologia — {cultura_sel}</div>', unsafe_allow_html=True)
        if gda_info:
            c1,c2,c3 = st.columns(3)
            with c1: st.metric("GDA Acumulado", f"{gda_info['gda_total']} °C·dia",
                               help=f"Tb={gda_info['tb']}°C")
            with c2: st.metric("Dias desde semeadura", gda_info["dias_desde_semeadura"])
            with c3:
                p = gda_info.get("proximo_estagio")
                if p: st.metric("Próximo estádio em", f"{p[0]-gda_info['gda_total']:.0f} °C·dia")
            proximo = gda_info.get("proximo_estagio")
            prox_str = (f"<p>→ Próximo: <b>{proximo[1]}</b> (faltam {proximo[0]-gda_info['gda_total']:.0f} °C·dia)</p>"
                        if proximo else "")
            st.markdown(f"""<div class="band-card">
              <h4>🌱 Estádio Fenológico Atual — {cultura_sel}</h4>
              <p style="font-size:1rem;color:{VERDE_ESCURO};font-weight:700;">{gda_info['estagio_atual']}</p>
              {prox_str}</div>""", unsafe_allow_html=True)

        # Janela de defensivos
        st.markdown('<div class="secao-titulo">🧪 Janela de Aplicação de Defensivos — Próximas 24h</div>', unsafe_allow_html=True)
        st.caption("Critérios MAPA/Embrapa: Vento < 10 km/h | Temp < 30°C | UR > 55% | Sem chuva")
        if janelas_def:
            cols_def = st.columns(len(janelas_def))
            for i, jan in enumerate(janelas_def):
                with cols_def[i]:
                    cor = {"aberta":"🟢","parcial":"🟡","bloqueada":"🔴"}[jan["status"]]
                    st.markdown(f"<div style='text-align:center;font-size:0.7rem;color:#555;'>"
                                f"<b>{jan['hora']}</b><br>{cor}</div>", unsafe_allow_html=True)

            n_ab = sum(1 for j in janelas_def if j["status"]=="aberta")
            n_pa = sum(1 for j in janelas_def if j["status"]=="parcial")
            n_bl = sum(1 for j in janelas_def if j["status"]=="bloqueada")
            c1,c2,c3 = st.columns(3)
            with c1: st.metric("✅ Horas ideais",    n_ab)
            with c2: st.metric("⚠️ Horas parciais",  n_pa)
            with c3: st.metric("❌ Horas bloqueadas", n_bl)

            # Melhor janela contínua
            max_seq=max_start=cur_seq=cur_start=0
            for i,j in enumerate(janelas_def):
                if j["status"]=="aberta":
                    if cur_seq==0: cur_start=i
                    cur_seq+=1
                    if cur_seq>max_seq: max_seq=cur_seq; max_start=cur_start
                else: cur_seq=0

            if max_seq > 0:
                h_ini = janelas_def[max_start]["hora"]
                h_fim = janelas_def[min(max_start+max_seq-1, len(janelas_def)-1)]["hora"]
                st.markdown(f"""<div class="alert-verde">
                  <b>✅ Melhor janela: {h_ini} → {h_fim} ({max_seq}h)</b><br>
                  <span style="font-size:0.88rem;">Período ideal para aplicação de defensivos e fertilizantes foliares.</span>
                </div>""", unsafe_allow_html=True)
            elif n_pa > 0:
                st.markdown("""<div class="alert-amarelo"><b>⚠️ Apenas janelas parciais disponíveis.</b></div>""", unsafe_allow_html=True)
            else:
                st.markdown("""<div class="alert-vermelho"><b>❌ Sem janela nas próximas 24h. Adie aplicações.</b></div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 4 — BALANÇO HÍDRICO & SOLO
    # Thornthwaite-Mather, umidade NASA POWER, ETo
    # ─────────────────────────────────────────────────────────────────────────
    with aba4:
        st.markdown(f'<div class="secao-titulo">💧 Balanço Hídrico do Solo (Thornthwaite-Mather) — {textura_solo}</div>', unsafe_allow_html=True)
        if bh:
            c1,c2,c3,c4 = st.columns(4)
            with c1: st.metric("ARM atual", f"{bh['arm_mm']:.1f} mm",
                               delta=f"{bh['arm_pct']:.0f}% da CAD")
            with c2: st.metric("CAD",       f"{bh['cad_mm']:.0f} mm")
            with c3: st.metric("Déficit",   f"{bh['def_mm']:.1f} mm",
                               delta_color="inverse",
                               delta=f"{'❌' if bh['def_mm']>0 else '✅'}")
            with c4: st.metric("ETR",       f"{bh['etr_mm']:.1f} mm")

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
    # ABA 5 — ALERTAS & FITOSSANIDADE
    # Alertas meteorológicos + risco fitossanitário calculado
    # ─────────────────────────────────────────────────────────────────────────
    with aba5:
        st.markdown('<div class="secao-titulo">⚠️ Alertas Meteorológicos Ativos</div>', unsafe_allow_html=True)
        for al in alertas:
            st.markdown(f"""<div class="alert-{al['nivel']}">
              <b>{al['icone']} {al['titulo']}</b><br>
              <span style="font-size:0.9rem;">{al['msg']}</span>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="secao-titulo">🍂 Risco Fitossanitário — Doenças Foliares (48h)</div>', unsafe_allow_html=True)
        st.caption("Ferrugem Asiática: T 15–30°C + UR>80% por 12h+ | Brusone: T 20–28°C + UR>90% por 10h+")
        for r in riscos_fito:
            st.markdown(f"""<div class="alert-{r['cor']}">
              <b>{r['icone']} {r['doenca']} — Risco {r['nivel']}</b><br>
              <span style="font-size:0.9rem;">{r['msg']}</span>
            </div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ABA 6 — RELATÓRIO & E-MAIL
    # Envio manual, pré-visualização HTML, configuração de destinatários,
    # histórico do scheduler
    # ─────────────────────────────────────────────────────────────────────────
    with aba6:
        st.markdown('<div class="secao-titulo">📧 Relatório Agroclimático — Envio por E-mail</div>', unsafe_allow_html=True)

        # Status da configuração
        if _email_configurado:
            st.markdown(f"""<div class="alert-verde">
              <b>✅ E-mail configurado</b><br>
              Remetente: {EMAIL_REMETENTE}<br>
              Destinatários padrão: {', '.join(EMAIL_DESTINATARIOS)}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="alert-amarelo">
              <b>⚠️ E-mail não configurado</b><br>
              Adicione ao <code>.streamlit/secrets.toml</code>:<br><br>
              <code>[email]</code><br>
              <code>remetente = "seuemail@gmail.com"</code><br>
              <code>senha_app = "sua_senha_de_app_gmail"</code><br>
              <code>destinatario = "destino@email.com"</code><br><br>
              Para gerar a senha de app: Conta Google → Segurança → Verificação em 2 etapas → Senhas de app
            </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # Destinatários extras
        st.markdown("**Destinatários adicionais (opcional):**")
        dest_extra_str = st.text_input(
            "E-mails separados por vírgula",
            placeholder="agrônomo@fazenda.com, gestor@empresa.com",
            label_visibility="collapsed"
        )
        dest_extras = [e.strip() for e in dest_extra_str.split(",") if "@" in e] if dest_extra_str else []

        col_btn1, col_btn2 = st.columns(2)

        # Botão de envio manual
        with col_btn1:
            if st.button("📤 Enviar Relatório Agora", use_container_width=True):
                with st.spinner("Gerando e enviando relatório..."):
                    ok, msg = enviar_relatorio_email(
                        municipio=municipio_sel,
                        coords=coords,
                        dados_meteo=dados_meteo,
                        alertas=alertas,
                        janelas_def=janelas_def,
                        gda_info=gda_info,
                        riscos_fito=riscos_fito,
                        bh=bh,
                        ndvi_data=ndvi_data,
                        df_focos=df_focos,
                        df_inmet=df_inmet,
                        destinatarios_extras=dest_extras,
                    )
                if ok:
                    st.success(f"✅ Relatório enviado com sucesso!\n{msg}")
                else:
                    st.error(f"❌ Falha no envio: {msg}")

        # Botão de pré-visualização
        with col_btn2:
            if st.button("👁 Pré-visualizar HTML", use_container_width=True):
                html_prev = gerar_html_relatorio(
                    municipio_sel, coords, dados_meteo, alertas,
                    janelas_def, gda_info, riscos_fito, bh,
                    ndvi_data, df_focos, df_inmet
                )
                st.components.v1.html(html_prev, height=700, scrolling=True)

        st.markdown("---")

        # Scheduler — configuração e histórico
        st.markdown('<div class="secao-titulo">🕐 Relatório Automático (Scheduler)</div>', unsafe_allow_html=True)

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("""**Horários automáticos:**
- ⏰ 06h00 — Relatório matinal
- ⏰ 12h00 — Relatório do meio-dia
- ⏰ 18h00 — Relatório vespertino

Município padrão: **Campo Grande**
_(Para outros municípios, use o botão de envio manual acima)_""")

        with col_s2:
            if "scheduler_obj" in st.session_state:
                _sched_ref = st.session_state["scheduler_obj"]
                _job = _sched_ref.get_job("relatorio_automatico")
                if _job and _job.next_run_time:
                    st.info(f"⏰ **Próxima execução:**\n{_job.next_run_time.strftime('%d/%m/%Y às %H:%M')}")
                    st.caption("Fuso horário: America/Campo_Grande")

                if st.button("▶ Disparar agora (background)", use_container_width=True):
                    threading.Thread(target=scheduled_report_automatico, daemon=True).start()
                    st.success("Relatório automático iniciado em background!")

        # Histórico de execuções
        with _log_lock:
            _log_snap = list(_scheduler_log)

        if _log_snap:
            st.markdown("**Histórico de execuções automáticas:**")
            df_log = pd.DataFrame(_log_snap)
            st.dataframe(df_log, use_container_width=True, hide_index=True)
        else:
            st.caption("Nenhuma execução automática registrada ainda.")

        st.markdown("---")
        st.markdown("""**📋 Conteúdo do relatório por e-mail:**
- 📊 Métricas rápidas (temperatura, chuva, umidade, vento, ETo)
- ⚠️ Alertas ativos com coloração por severidade
- 🧪 Janela de aplicação de defensivos (resumo + melhor horário)
- 🌾 Graus-dia acumulados e estádio fenológico
- 🍂 Risco fitossanitário (ferrugem, brusone)
- 🌿 NDVI atual vs mediana histórica (SATVeg/Embrapa)
- 💧 Balanço hídrico com recomendação de irrigação
- 🔥 Focos de queimada INPE (últimas 48h)
- 📅 Tabela de previsão para 7 dias
- 📡 Estações INMET ativas no MS""")

    # ─────────────────────────────────────────────────────────────────────────
    # RODAPÉ
    # ─────────────────────────────────────────────────────────────────────────
    progress.progress(100, text="✅ Análise concluída!")
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align:center;padding:16px;color:#888;font-size:0.8rem;">
      <b style="color:{VERDE_ESCURO};">Yamada Engenharia</b> — Meteorologia Aplicada ao Agronegócio<br>
      GOES-19 ABI · Open-Meteo · NASA POWER · SATVeg · INPE · INMET<br>
      Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} · MVP v3.0
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
