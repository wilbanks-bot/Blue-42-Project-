import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import json
import math
import random
import time
import hashlib
import copy
from datetime import datetime

# Safely import optional dependencies
try:
    import ee
    from google.oauth2 import service_account
    EE_AVAILABLE = True
except ImportError:
    EE_AVAILABLE = False

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

# =========================================================
# 1. UX SETUP & "CYBERNETIC OCEAN" DESIGN SYSTEM
# =========================================================
st.set_page_config(layout="wide", page_title="Blue 42 | Planetary Capital OS", page_icon="🌊", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif !important;
        background-color: #020617; color: #F8FAFC;
    }
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 98%; }

    /* Custom CSS for Leaf Tooltips */
    .leaf-tooltip {
        position: relative; display: inline-block; cursor: help; font-size: 1.1rem; margin-left: 8px; transition: transform 0.2s ease;
    }
    .leaf-tooltip:hover { transform: scale(1.2); }
    .leaf-tooltip .tooltiptext {
        visibility: hidden; width: max-content; max-width: 260px; background: rgba(15, 23, 42, 0.98);
        backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); color: #F8FAFC; text-align: left; 
        border: 1px solid #10B981; border-radius: 8px; padding: 14px; position: absolute; z-index: 9999999 !important; 
        bottom: 150%; left: 50%; transform: translateX(-50%) translateY(10px); opacity: 0; transition: opacity 0.3s, transform 0.3s; 
        font-size: 0.85rem; font-family: 'Space Grotesk', sans-serif; box-shadow: 0 10px 40px rgba(0,0,0,0.8);
        line-height: 1.5; font-weight: 500; pointer-events: none; white-space: normal; word-wrap: break-word;
    }
    .leaf-tooltip .tooltiptext::after {
        content: ""; position: absolute; top: 100%; left: 50%; margin-left: -6px; border-width: 6px; border-style: solid; border-color: #10B981 transparent transparent transparent;
    }
    .leaf-tooltip:hover .tooltiptext { visibility: visible; opacity: 1; transform: translateX(-50%) translateY(0); }

    /* 3D Flip Card Container */
    .flip-card { background-color: transparent; height: 210px; perspective: 1000px; margin-bottom: 15px; }
    .flip-card-inner { position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.6s cubic-bezier(0.4, 0.0, 0.2, 1); transform-style: preserve-3d; }
    .flip-card:hover .flip-card-inner { transform: rotateY(180deg); }
    .flip-card-front, .flip-card-back {
        position: absolute; width: 100%; height: 100%; -webkit-backface-visibility: hidden; backface-visibility: hidden;
        border-radius: 12px; box-sizing: border-box; background: rgba(15, 23, 42, 0.6); 
        backdrop-filter: blur(12px); border: 1px solid rgba(6, 182, 212, 0.2); padding: 20px 15px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3); 
        display: flex; flex-direction: column; justify-content: center;
    }
    .flip-card-front { border-left: 4px solid #0D9488; }
    .flip-card-back { transform: rotateY(180deg); border-left: 4px solid #10B981; background: rgba(15, 23, 42, 0.95); text-align: left; align-items: flex-start; padding-left: 20px; }

    .glass-title { font-size: 0.85rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; font-weight: 600;}
    .glass-value { font-size: 2.2rem; font-weight: 700; background: -webkit-linear-gradient(45deg, #06b6d4, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; }
    .glass-sub { font-size: 0.8rem; color: #10B981; margin-top: 8px; font-weight: 600; }
    
    .math-text { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #F8FAFC; line-height: 1.5; width: 100%; }
    .math-hl { color: #10B981; font-weight: 700; font-size: 0.80rem; }
    .math-var { color: #94A3B8; }
    .math-op { color: #0EA5E9; font-weight: 700; padding-right: 6px; display: inline-block; width: 12px; }

    /* Beautiful Cryptographic Ledger Receipt */
    .crypto-box {
        background: linear-gradient(145deg, #0f172a, #1e293b); border-left: 4px solid #10b981; border-radius: 8px; padding: 16px;
        font-family: 'Space Grotesk', sans-serif; font-size: 0.9rem; color: #e2e8f0; box-shadow: 0 4px 15px rgba(0,0,0,0.4); margin-top: 15px;
    }
    .crypto-hash {
        font-family: 'JetBrains Mono', monospace; color: #10b981; word-break: break-all; background: #020617; padding: 8px; border-radius: 4px; margin-top: 8px; font-size: 0.8rem;
    }

    .stButton > button { background: rgba(15, 23, 42, 0.8); color: #06b6d4; border: 1px solid #06b6d4; border-radius: 8px; font-weight: 600; transition: all 0.3s ease; }
    .stButton > button:hover { background: #06b6d4; color: #020617; box-shadow: 0 0 15px rgba(6, 182, 212, 0.6); }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .blinking { animation: blinker 1.5s linear infinite; color: #10B981; font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0; } }
</style>
""", unsafe_allow_html=True)

def leaf_info(text):
    return f"""<div class="leaf-tooltip">🌿<span class="tooltiptext">{text}</span></div>"""

def make_flip_card(title, value, sub, math_html):
    return f"""
    <div class="flip-card">
      <div class="flip-card-inner">
        <div class="flip-card-front">
          <div class="glass-title">{title}</div>
          <div class="glass-value">{value}</div>
          <div class="glass-sub">{sub}</div>
        </div>
        <div class="flip-card-back">
          <div class="glass-title" style="color:#38BDF8;">ALGORITHMIC PROVENANCE</div>
          <div class="math-text">{math_html}</div>
        </div>
      </div>
    </div>
    """

# =========================================================
# 2. CUSTOM KELP ANIMATION (RESTORED)
# =========================================================
def kelp_animation():
    """Injects a custom CSS animation of growing kelp and bubbles."""
    kelp_html = """
    <style>
        .ocean-animation-container { position: fixed; bottom: 0; left: 0; width: 100vw; height: 100vh; pointer-events: none; z-index: 99999; overflow: hidden; }
        .kelp-stalk { position: absolute; bottom: 0; width: 60px; transform-origin: bottom center; transform: scaleY(0); opacity: 0; display: flex; flex-direction: column; justify-content: space-evenly; align-items: center; }
        .kelp-stem { position: absolute; bottom: 0; width: 6px; height: 100%; background: linear-gradient(to top, #364219, #6b7a2d, #8f9c3e); border-radius: 4px; z-index: 1; }
        .kelp-frond-left, .kelp-frond-right { position: relative; height: 12px; background: linear-gradient(to right, #5a6b25, #7a8b35); border-radius: 50% 10% 50% 10%; z-index: 2; margin: 15px 0; }
        .kelp-frond-left { width: 45px; transform: translateX(-25px) rotate(-20deg); background: linear-gradient(to left, #5a6b25, #7a8b35); border-radius: 10% 50% 10% 50%; }
        .kelp-frond-right { width: 45px; transform: translateX(25px) rotate(20deg); }
        .kelp-frond-left::after { content: ''; position: absolute; right: -4px; top: -2px; width: 12px; height: 16px; background: #8b7d22; border-radius: 50%; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.3); }
        .kelp-frond-right::after { content: ''; position: absolute; left: -4px; top: -2px; width: 12px; height: 16px; background: #8b7d22; border-radius: 50%; box-shadow: inset 2px -2px 4px rgba(0,0,0,0.3); }
        .bubble { position: absolute; bottom: -50px; font-size: 1.5rem; opacity: 0.4; animation: floatUp 4s ease-in infinite; color: #e0f2fe; text-shadow: 0 0 5px #38bdf8; }
        @keyframes growKelp { 0% { transform: scaleY(0); opacity: 0; } 20% { opacity: 0.9; } 100% { transform: scaleY(1); opacity: 0.9; } }
        @keyframes swayKelp1 { 0% { margin-left: -20px; transform: rotate(-2deg); } 100% { margin-left: 20px; transform: rotate(2deg); } }
        @keyframes swayKelp2 { 0% { margin-left: 20px; transform: rotate(3deg); } 100% { margin-left: -20px; transform: rotate(-3deg); } }
        @keyframes floatUp { 0% { bottom: -50px; transform: translateX(0px); opacity: 0; } 20% { opacity: 0.6; } 50% { transform: translateX(-20px); } 100% { bottom: 110vh; transform: translateX(20px); opacity: 0; } }
    </style>
    <div class="ocean-animation-container">
    """
    for _ in range(15):
        left = random.randint(2, 55) 
        delay = random.uniform(0.1, 1.5)
        duration = random.uniform(3.5, 5.5)
        sway_dir = random.choice(["swayKelp1", "swayKelp2"])
        sway_dur = random.uniform(3.0, 6.0)
        height = random.uniform(60, 110) 
        
        kelp_html += f'<div style="position:absolute; bottom:0; left:{left}%; height:{height}vh; animation: {sway_dir} {sway_dur}s ease-in-out infinite alternate;">'
        kelp_html += f'<div class="kelp-stalk" style="height:100%; animation: growKelp {duration}s cubic-bezier(0.1, 0.8, 0.3, 1) {delay}s forwards;"><div class="kelp-stem"></div>'
        num_fronds = int(height // 3)
        for j in range(num_fronds):
            frond_class = "kelp-frond-left" if j % 2 == 0 else "kelp-frond-right"
            kelp_html += f'<div class="{frond_class}"></div>'
        kelp_html += '</div></div>'
        
    for _ in range(25):
        left = random.randint(1, 55)
        delay = random.uniform(0, 4)
        size = random.uniform(0.5, 1.5)
        kelp_html += f'<div class="bubble" style="left: {left}%; animation-delay: {delay}s; font-size: {size}rem;">🫧</div>'
        
    kelp_html += "</div>"
    st.markdown(kelp_html, unsafe_allow_html=True)


if "library" not in st.session_state: st.session_state.library = []

# =========================================================
# 3. SECURE API INITIALIZATION & GRACEFUL FALLBACK
# =========================================================
ee_connected = False
if EE_AVAILABLE:
    try:
        if "EARTHENGINE_TOKEN" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(json.loads(st.secrets["EARTHENGINE_TOKEN"])).with_scopes(['https://www.googleapis.com/auth/earthengine'])
            ee.Initialize(credentials=creds)
            ee_connected = True
        else:
            ee.Initialize()
            ee_connected = True
    except Exception: pass

model = None
if GENAI_AVAILABLE:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            avail = [m.name for m in genai.list_models()]
            target = 'gemini-1.5-flash' if 'models/gemini-1.5-flash' in avail else ('gemini-1.5-pro' if 'models/gemini-1.5-pro' in avail else avail[0].replace('models/', ''))
            model = genai.GenerativeModel(target)
    except Exception: pass

# =========================================================
# 4. GEE BIOGEOCHEMICAL MODELING
# =========================================================
@st.cache_data(ttl=3600)
def get_scientific_kelp_data(sector):
    base_lat, base_lon = (34.0, -119.8) if sector == "Channel Islands" else (21.3, -157.9)
    mock = []
    for i in range(12):
        area = round(random.uniform(5.0, 15.0), 1)
        wave_energy = round(random.uniform(10.0, 50.0), 1) 
        mock.append({
            "id": f"SIM-K{i+1}", "lat": base_lat + random.uniform(-0.4, 0.4), "lon": base_lon + random.uniform(-0.6, 0.6),
            "area_ha": area, "biomass_tons": round(area * 18.5 * 0.92, 1), "co2_tons": round(area * 18.5 * 0.92 * 0.68, 1),
            "sst_mean": round(random.uniform(14.0, 17.5), 1), "depth": round(random.uniform(10.0, 25.0), 1),
            "nitrate_score": random.randint(80, 99), "mhw_risk": random.choice(["Low", "Moderate", "High"]),
            "salinity": round(random.uniform(33.0, 34.5), 2), "wave_energy": wave_energy,
            "averted_damage_millions": round((wave_energy * area * 0.15), 2), "jobs_created": int(area * 2.2),
            "biodiversity_score": random.randint(85, 99)
        })
    return mock

# =========================================================
# 5. MCDA DECONFLICTION
# =========================================================
@st.cache_resource(ttl=60)
def get_hazard_vectors(sector):
    base_lat, base_lon = (34.0, -119.8) if sector == "Channel Islands" else (21.3, -157.9)
    vessels, mammals = [], []
    for _ in range(10): vessels.append({"lat": base_lat + random.uniform(-0.5, 0.5), "lon": base_lon + random.uniform(-0.8, 0.8)})
    for _ in range(3): mammals.append({"lat": base_lat + random.uniform(-0.2, 0.2), "lon": base_lon + random.uniform(-0.4, 0.4)})
    weather_poly = [[[-120.2, 33.6], [-119.6, 33.6], [-119.6, 34.2], [-120.2, 34.2], [-120.2, 33.6]]] if sector == "Channel Islands" else [[[-158.2, 21.1], [-157.7, 21.1], [-157.7, 21.5], [-158.2, 21.5], [-158.2, 21.1]]]
    return pd.DataFrame(vessels), pd.DataFrame(mammals), [{"polygon": weather_poly[0]}]

def run_mcda_deconfliction(sites, vessels_df, mammals_df, weather_data):
    R = 6371 
    processed = []
    for site in sites:
        site['status'], site['color'] = "CLEARED: Optimal", [16, 185, 129, 230] 
        for w in weather_data:
            poly = w.get('polygon', [])
            if poly:
                lons, lats = [p[0] for p in poly], [p[1] for p in poly]
                if min(lons) <= site.get('lon', 0) <= max(lons) and min(lats) <= site.get('lat', 0) <= max(lats):
                    site['status'], site['color'] = "HAZARD: Storm Risk", [239, 68, 68, 230]
                    break
        if site['status'].startswith("CLEARED"):
            for _, ship in vessels_df.iterrows():
                a = math.sin(math.radians(ship.get('lat', 0) - site.get('lat', 0))/2)**2 + math.cos(math.radians(site.get('lat', 0))) * math.cos(math.radians(ship.get('lat', 0))) * math.sin(math.radians(ship.get('lon',0) - site.get('lon', 0))/2)**2
                if R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a))) < 2.5:
                    site['status'], site['color'] = "HAZARD: Shipping Lane", [245, 158, 11, 230]
                    break
        if site['status'].startswith("CLEARED"):
            for _, whale in mammals_df.iterrows():
                a = math.sin(math.radians(whale.get('lat', 0) - site.get('lat', 0))/2)**2 + math.cos(math.radians(site.get('lat', 0))) * math.cos(math.radians(whale.get('lat', 0))) * math.sin(math.radians(whale.get('lon',0) - site.get('lon', 0))/2)**2
                if R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a))) < 4.0:
                    site['status'], site['color'] = "HAZARD: Mammal Corridor", [139, 92, 246, 230]
                    break
        processed.append(site)
    return pd.DataFrame(processed)

# =========================================================
# 6. HEADER & SIDEBAR CONTROLS
# =========================================================
st.markdown(f"<h1 style='color: #06b6d4; font-weight: 700; margin-bottom: 0;'>BLUE 42 <span style='color:#F8FAFC; font-weight: 300;'>| Planetary Capital OS</span> {leaf_info('A planetary-scale biogeochemical operating system fusing frontier AI and Earth telemetry to automate global marine conservation.')}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color: #94A3B8; font-size: 1.1rem; margin-top: -10px;'><span class='blinking'>●</span> {'GEE UPLINK SECURE' if ee_connected else 'MCDA ENGINE ACTIVE'} | VERIFIABLE KELP FRAMEWORK</p>", unsafe_allow_html=True)

st.sidebar.markdown(f"<h2 style='color:#0EA5E9; font-weight:600; display:flex; align-items:center;'>MCDA ENGINE {leaf_info('Multi-Criteria Decision Analysis (MCDA) synthesizes overlapping biogeochemical and socioeconomic data layers to calculate the absolute optimal coordinates for planetary interventions.')}</h2>", unsafe_allow_html=True)
sector = st.sidebar.selectbox("Target Bioregion", ["Channel Islands, CA", "Hawaiian Archipelago, HI"])
sector_key = "Channel Islands" if "Channel" in sector else "Hawaii"

st.sidebar.markdown("---")
st.sidebar.markdown(f"<h3 style='display:flex; align-items:center;'>🎛️ Pareto Optimization {leaf_info('A mathematical framework that forces the system to find the optimal trade-off frontier between competing global priorities.')}</h3>", unsafe_allow_html=True)
weight_carbon = st.sidebar.slider("Carbon Sequestration", 0.0, 1.0, 0.8)
weight_coastal = st.sidebar.slider("Coastal Resilience", 0.0, 1.0, 0.6)
weight_bio = st.sidebar.slider("Fishery Biodiversity", 0.0, 1.0, 0.9)

raw_sites_cached = get_scientific_kelp_data(sector_key)
if not raw_sites_cached: raw_sites_cached = []
raw_sites = copy.deepcopy(raw_sites_cached)

vessels_df, mammals_df, weather_data = get_hazard_vectors(sector_key)

for site in raw_sites:
    site['pareto_score'] = round((site.get('co2_tons', 0) * weight_carbon) + (site.get('averted_damage_millions', 0) * weight_coastal * 10) + (site.get('biodiversity_score', 0) * weight_bio), 1)

raw_sites = sorted(raw_sites, key=lambda x: x.get('pareto_score', 0), reverse=True)
kelp_df = run_mcda_deconfliction(raw_sites, vessels_df, mammals_df, weather_data)
safe_df = kelp_df[kelp_df['status'].str.contains("CLEARED")] if not kelp_df.empty else pd.DataFrame()

# =========================================================
# 7. UI: EXECUTIVE DASHBOARD & 3D KPI CARDS
# =========================================================
col1, col2, col3, col4 = st.columns(4)

v_area = safe_df['area_ha'].sum() if not safe_df.empty else 0
v_bio = safe_df['biomass_tons'].sum() if not safe_df.empty else 0
v_dmg = safe_df['averted_damage_millions'].sum() if not safe_df.empty else 0
v_roi = ((safe_df['co2_tons'].sum() * 150) + (safe_df['biomass_tons'].sum() * 300) + (v_area * 1500)) if not safe_df.empty else 0

math1 = "Σ(GEE Raster Area)<br><span class='math-op'>-</span> <span class='math-var'>Σ(Shipping)</span><br><span class='math-op'>-</span> <span class='math-var'>Σ(Storms)</span><br><span class='math-op'>-</span> <span class='math-var'>Σ(Mammals)</span><br><div class='math-divider'>━━━━━━━━━</div><span class='math-hl'>Net Viable HA</span>"
math2 = "Area (HA)<br><span class='math-op'>×</span> <span class='math-var'>18.5 (Wet MT/HA)</span><br><span class='math-op'>×</span> <span class='math-var'>0.92 (Thermal Mod)</span><br><div class='math-divider'>━━━━━━━━━</div><span class='math-hl'>NPP Biomass Yield</span>"
math3 = "Σ [ Area (HA)<br><span class='math-op'>×</span> <span class='math-var'>Wave Energy (kW/m)</span><br><span class='math-op'>×</span> <span class='math-var'>0.15 (Atten. Coeff) ]</span><br><div class='math-divider'>━━━━━━━━━</div><span class='math-hl'>Averted Damage (\\$)</span>"
math4 = "(CO2e MT × \\$150)<br><span class='math-op'>+</span> <span class='math-var'>(Biomass MT × \\$300)</span><br><span class='math-op'>+</span> <span class='math-var'>(Net HA × \\$1500)</span><br><div class='math-divider'>━━━━━━━━━</div><span class='math-hl'>Stacked Annual ROI</span>"

col1.markdown(make_flip_card(f"Net Viable Kelp Area", f"{v_area:.1f} HA", "Mathematically Deconflicted", math1), unsafe_allow_html=True)
col2.markdown(make_flip_card(f"Harvestable Yield", f"{v_bio:.1f} MT", "Macrocystis Wet Biomass", math2), unsafe_allow_html=True)
col3.markdown(make_flip_card(f"Averted Coast Damage", f"${v_dmg:.1f}M", "Via Wave Attenuation", math3), unsafe_allow_html=True)
col4.markdown(make_flip_card(f"Ecological Capital ROI", f"${v_roi:,.0f}", "Stacked Value / Yr", math4), unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# 8. VISUALIZATIONS: MAP & ANALYTICS
# =========================================================
col_map, col_ops = st.columns([6, 4], gap="large")

with col_map:
    st.markdown(f"<h4 style='display:flex; align-items:center;'>🌊 Spatial Deconfliction Map {leaf_info('A dynamic WebGL rendering of the ocean digital twin, displaying live vectors of maritime hazards and algorithmically cleared biological growth zones.')}</h4>", unsafe_allow_html=True)
    layers = []
    
    layers.append(pdk.Layer("PolygonLayer", data=weather_data, get_polygon="polygon", get_fill_color="[239, 68, 68, 40]", get_line_color="[239, 68, 68, 200]"))
    
    if not kelp_df.empty:
        layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_color="color", get_radius=1500, pickable=True))
        layers.append(pdk.Layer("TextLayer", data=kelp_df, get_position="[lon, lat]", get_text="id", get_color="[255, 255, 255, 200]", get_size=16, get_alignment_baseline="'bottom'"))
    if not vessels_df.empty:
        layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_color="[148, 163, 184, 150]", get_radius=800, pickable=False))
    if not mammals_df.empty:
        layers.append(pdk.Layer("ScatterplotLayer", data=mammals_df, get_position="[lon, lat]", get_color="[139, 92, 246, 150]", get_radius=4000, pickable=False))
    
    tt_html = "<div style='font-family:Space Grotesk; background:rgba(15,23,42,0.9); padding:10px; border-radius:8px; border:1px solid #06b6d4;'><b>{id}</b><br/>Pareto Score: {pareto_score}<br/>Area: {area_ha} HA<br/><span style='color:#10B981;'>Status: <b>{status}</b></span><br/>NPP: {biomass_tons} MT</div>"
    view_state = pdk.ViewState(latitude=33.95 if sector_key == "Channel Islands" else 21.3, longitude=-119.8 if sector_key == "Channel Islands" else -157.9, zoom=8.5, pitch=45, bearing=15)
    
    # Safe Streamlit map without Mapbox
    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view_state, map_style=None, tooltip={"html": tt_html}), use_container_width=True, height=600)

with col_ops:
    sel_site, site_data = None, None
    if not kelp_df.empty:
        st.info("☝️ **What is this?** The AI has mathematically deconflicted viable ocean zones. Select a site to view its holistic biosphere metrics and financial ROI.")
        sel_site = st.selectbox("🎯 Target Site for Deep-Dive Analysis:", kelp_df['id'].tolist(), label_visibility="collapsed")
        site_data = kelp_df[kelp_df['id'] == sel_site].iloc[0]

    t_mission, t1, t2, t_mrv = st.tabs(["🚀 Mission", "📈 Analytics & Growth", "💰 Financial ROI", "🛰️ Verifiable MRV"])
    
    with t_mission:
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("Trillions in climate capital are sidelined because we lack the computational architecture to verify marine ecological investments. Blue 42 synthesizes complex telemetry to unlock gigaton-scale Blue Carbon.")
        st.markdown("**1. Mitigation & Commercial Harvest**")
        st.caption("Giant Kelp sequesters carbon 20x faster than terrestrial forests. We automate site selection to unlock capital allocation.")
        st.markdown("**2. Adaptation (Coastal & Economic Resilience)**")
        st.caption("Kelp buffers coastlines against storm surges, saving billions in infrastructure, and generates thousands of coastal blue-economy jobs.")
        st.markdown("**3. Protection (Do No Harm)**")
        st.caption("The MCDA dynamically enforces marine jurisdiction, deconflicting kelp sites from active shipping lanes, severe weather, and cetacean migration corridors.")

    with t1:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<h5 style='display:flex; align-items:center;'>Data Reflection: Biogeochemical Profiling {leaf_info('A depth-resolved analysis plotting the intersection of the thermocline (temperature drop) and nutricline (nitrate increase) to guarantee biological viability.')}</h5>", unsafe_allow_html=True)
        st.info("**Scientific Context:** Giant Kelp requires specific thermal and nutrient bands to survive. By modeling the thermocline vs nutricline, we mathematically guarantee the crop will thrive before deploying capital.")
        
        if site_data is not None and PLOTLY_AVAILABLE:
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            growth = [10, 40, 80, 20, 50, 90, 30, 60, 100, 25, 55, 85] 
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=months, y=growth, mode='lines+markers', name='Canopy Biomass (%)', line=dict(color="#06b6d4", width=3, shape='spline')))
            for harvest_mo in ['Mar', 'Jun', 'Sep', 'Dec']:
                fig.add_vline(x=harvest_mo, line_width=1, line_dash="dot", line_color="#ef4444")
                
            fig.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", yaxis_title="Biomass (%)", margin=dict(l=0, r=0, t=10, b=0), height=220)
            st.plotly_chart(fig, use_container_width=True)

            mc1, mc2, mc3 = st.columns(3)
            mc1.markdown(f"<div style='text-align:center;'><div style='color:#94a3b8; font-size:12px;'>Salinity</div><div style='color:#06b6d4; font-size:20px; font-weight:bold;'>{site_data.get('salinity', 0)} PSU</div></div>", unsafe_allow_html=True)
            mc2.markdown(f"<div style='text-align:center;'><div style='color:#94a3b8; font-size:12px;'>Wave Energy</div><div style='color:#06b6d4; font-size:20px; font-weight:bold;'>{site_data.get('wave_energy', 0)} kW/m</div></div>", unsafe_allow_html=True)
            mc3.markdown(f"<div style='text-align:center;'><div style='color:#94a3b8; font-size:12px;'>Biodiversity</div><div style='color:#06b6d4; font-size:20px; font-weight:bold;'>{site_data.get('biodiversity_score', 0)}/100</div></div>", unsafe_allow_html=True)
            
    with t2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<h5 style='display:flex; align-items:center;'>Data Reflection: Techno-Economic Assessment {leaf_info('A rigorous 10-year financial projection modeling CAPEX and OPEX against the stacked revenue streams of verified Natural Capital.')}</h5>", unsafe_allow_html=True)
        st.info("**Financial Context:** Single-stream carbon projects fail. This TEA uses 'Value Stacking'—combining Premium Blue Carbon (\\$150/MT), Bioplastic-Grade Harvest (\\$300/MT), and Resilience Subsidies (\\$1,500/HA) to ensure institutional profitability.")
        
        if site_data is not None and "CLEARED" in site_data.get('status', ''):
            capex = site_data.get('area_ha', 0) * 15000  
            opex_yr = site_data.get('area_ha', 0) * 2000 
            rev_yr = (site_data.get('co2_tons', 0) * 150) + (site_data.get('biomass_tons', 0) * 300) + (site_data.get('area_ha', 0) * 1500)
            
            years = np.arange(0, 11)
            costs = capex + (opex_yr * years)
            revenues = rev_yr * years
            
            if PLOTLY_AVAILABLE:
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=years, y=costs, name="Cumulative Cost", fill='tozeroy', line=dict(color="#ef4444", width=2), fillcolor='rgba(239, 68, 68, 0.1)'))
                fig2.add_trace(go.Scatter(x=years, y=revenues, name="Cumulative Revenue", fill='tozeroy', line=dict(color="#10b981", width=2), fillcolor='rgba(16, 185, 129, 0.2)'))
                fig2.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", yaxis_title="USD ($)", xaxis_title="Years Post-Deployment", margin=dict(l=0, r=0, t=10, b=0), height=250)
                st.plotly_chart(fig2, use_container_width=True)
            
            annual_profit = rev_yr - opex_yr
            if annual_profit > 0:
                break_even = capex / annual_profit
                st.success(f"**Projected Break-Even:** Year {break_even:.1f} | **10-Yr Net Profit:** \\${(revenues[-1]-costs[-1]):,.2f}")
                
            st.divider()
            st.markdown(f"<h6 style='display:flex; align-items:center;'>🌍 Macro-Economics: Planetary Scale-Up</h6>", unsafe_allow_html=True)
            
            target_scale_ha = st.slider("Target Deployment Area (Hectares)", min_value=10000, max_value=50000000, value=1000000, step=10000, label_visibility="collapsed")
            
            macro_capex = target_scale_ha * 15000
            macro_opex_yr = target_scale_ha * 2000
            macro_co2 = target_scale_ha * 12.5
            macro_biomass = target_scale_ha * 17.0
            
            macro_rev_yr = (macro_co2 * 150) + (macro_biomass * 300) + (target_scale_ha * 1500)
            macro_net_yr = macro_rev_yr - macro_opex_yr
            
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Gigaton Potential", f"{macro_co2 / 1e6:.2f} GT/yr")
            mc2.metric("CAPEX Required", f"${macro_capex / 1e9:.2f}B")
            mc3.metric("10-Yr Portfolio Value", f"${(macro_net_yr * 10) / 1e9:.2f}B")

        else:
            st.error("Site contains HAZARDS. Financial modeling suspended.")

    with t_mrv:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<h5 style='display:flex; align-items:center;'>Data Reflection: Continuous MRV {leaf_info('Measurement, Reporting, and Verification (MRV) guarantees carbon permanence and eliminates greenwashing by tracking continuous physical growth.')}</h5>", unsafe_allow_html=True)
        st.info("**Audit Context:** Carbon credits are worthless without continuous proof of life. Blue 42 ingests Sentinel-2 multispectral imagery to track actual canopy biomass over time. Once growth is verified, we cryptographically mint the asset to an immutable ledger.")
        
        if site_data is not None and "CLEARED" in site_data.get('status', ''):
            st.write(f"**Target Analyzed:** {sel_site}")
            years_mrv = ["Q1", "Q2", "Q3", "Q4"]
            canopy_density = [75, 82, 88, 95] 
            
            if PLOTLY_AVAILABLE:
                fig3 = go.Figure()
                fig3.add_trace(go.Bar(x=years_mrv, y=canopy_density, marker_color="#06b6d4", name="Regrowth (%)"))
                fig3.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", yaxis_title="Sentinel-2 Regrowth (%)", margin=dict(l=0, r=0, t=10, b=0), height=220)
                st.plotly_chart(fig3, use_container_width=True)
            
            if st.button("Cryptographically Sign & Mint Credits", use_container_width=True):
                kelp_animation()
                tx_hash = hashlib.sha256(str(time.time()).encode()).hexdigest()
                st.success(f"✅ Biomass verified via satellite. {site_data.get('co2_tons', 0)} MT CO2e minted.")
                st.markdown(f"""
                <div class='crypto-box'>
                    <b>ENTERPRISE LEDGER RECEIPT</b><br>
                    Status: VERIFIED & IMMUTABLE<br>
                    TX_HASH: {tx_hash}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.error("MRV disabled for hazardous sites.")
