import streamlit as st
import pydeck as pdk
import pandas as pd
import json
import ee
import math
import random
import websocket
from google.oauth2 import service_account
import google.generativeai as genai

# ---------------------------------------------------------
# 1. PAGE SETUP & CLEAN ENTERPRISE THEME
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 Strategic Command", page_icon="🌐", initial_sidebar_state="collapsed")

# Hardcoded to the clean, high-contrast dark mode for optimal presentation
bg_color = "#0B1120"; card_bg = "#1E293B"; text_color = "#F8FAFC"
accent_blue = "#38BDF8"; accent_red = "#F43F5E"; accent_green = "#10B981"
map_style = "dark"

css = f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: -apple-system, sans-serif; }}
    .metric-card {{ background-color: {card_bg}; padding: 24px; border-radius: 8px; border-top: 4px solid {accent_blue}; margin-bottom: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
    .alert-card {{ border-top: 4px solid {accent_red}; background-color: rgba(244, 63, 94, 0.05); }}
    .success-card {{ border-top: 4px solid {accent_green}; background-color: rgba(16, 185, 129, 0.05); }}
    h1, h2, h3, h4 {{ color: {text_color}; font-weight: 600; margin-top: 0; }}
    h4 {{ font-size: 1rem; text-transform: uppercase; color: #94A3B8; letter-spacing: 1px; }}
    .kpi-value {{ font-size: 2.5rem; font-weight: 700; color: {text_color}; margin: 8px 0; line-height: 1.1; }}
    .bottom-line {{ font-size: 1.1rem; color: #cbd5e1; border-left: 4px solid {accent_blue}; padding-left: 15px; margin-bottom: 20px; font-style: italic; }}
    .stRadio div[role="radiogroup"] {{ flex-direction: row; justify-content: center; background-color: {card_bg}; padding: 10px; border-radius: 8px; }}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. SECURE API INITIALIZATION
# ---------------------------------------------------------
try:
    if "EARTHENGINE_TOKEN" in st.secrets:
        key_dict = json.loads(st.secrets["EARTHENGINE_TOKEN"])
        creds = service_account.Credentials.from_service_account_info(key_dict).with_scopes(['https://www.googleapis.com/auth/earthengine'])
        ee.Initialize(credentials=creds, project=key_dict.get("project_id"))
except: pass

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-3.5-flash')
except: pass

# ---------------------------------------------------------
# 3. HEADER & MISSION SELECTOR
# ---------------------------------------------------------
st.markdown(f"<h1 style='text-align: center; color: {accent_blue}; font-size: 3rem;'>🌐 PROJECT BLUE 42</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94A3B8; font-size: 1.2rem; margin-bottom: 30px;'>Transforming Planetary Telemetry into Auditable Business Value.</p>", unsafe_allow_html=True)

# This is the core UI change. The user selects ONE story at a time.
mission = st.radio(
    "SELECT STRATEGIC FOCUS:",
    ["🛡️ Protection (Maritime Security)", "🌪️ Adaptation (Supply Chain Resilience)", "🌱 Mitigation (ESG Blue Carbon)"],
    index=0
)

st.write("---")

# ---------------------------------------------------------
# 4. DATA & MAP LOGIC PER MISSION
# ---------------------------------------------------------
layers = []
view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=45, bearing=0)

# Base Vessels (Always present to show context)
vessels_df = pd.DataFrame([
    {"lat": 34.12, "lon": -119.85, "name": "CARGO VESSEL", "color": [37, 99, 235, 150], "sog": 12.4, "cog": 135},
    {"lat": 33.80, "lon": -119.60, "name": "CONTAINER SHIP", "color": [37, 99, 235, 150], "sog": 15.2, "cog": 110}
])
layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_fill_color="color", get_radius=2000))

# --- SCENARIO 1: PROTECTION ---
if "Protection" in mission:
    st.markdown("<div class='bottom-line'><b>The Bottom Line:</b> Marine reserves and subsea cables are impossible to patrol manually. Blue 42 uses AI to instantly detect illicit behavior and dispatch authorities before the damage is done.</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1]) # Map takes 2/3, Analytics takes 1/3
    
    with col1:
        # Map Layers for Protection
        mpa_data = pd.DataFrame([{"polygon": [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]], "name": "Protected Marine Sanctuary"}])
        layers.append(pdk.Layer("PolygonLayer", data=mpa_data, get_polygon="polygon", get_fill_color="[56, 189, 248, 30]", get_line_color="[56, 189, 248, 200]", line_width_min_pixels=2))
        
        cable_data = pd.DataFrame([{"path": [[-121.0, 33.5], [-119.0, 33.8], [-118.0, 34.2]], "name": "Tier-1 Subsea Data Cable"}])
        layers.append(pdk.Layer("PathLayer", data=cable_data, get_path="path", get_color="[56, 189, 248, 255]", width_min_pixels=3))
        
        threat_df = pd.DataFrame([{"lat": 33.95, "lon": -120.15, "name": "DARK TARGET (Transponder Disabled)", "color": [225, 29, 72, 255], "sog": 9.1, "cog": 80}])
        layers.append(pdk.Layer("ScatterplotLayer", data=threat_df, get_position="[lon, lat]", get_fill_color="color", get_radius=3500))
        
        r = pdk.Deck(layers=layers, initial_view_state=view_state, map_style=map_style, tooltip={"html": "<b>{name}</b>"})
        st.pydeck_chart(r, use_container_width=True)
        
    with col2:
        st.markdown("<div class='metric-card alert-card'><h4>⚠️ Active Threat Detected</h4><p class='kpi-value' style='color:#F43F5E;'>CRITICAL</p><p>Vessel masking identity inside Protected Sanctuary limits.</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='metric-card'><h4>Asset Valuation at Risk</h4><p class='kpi-value'>$1.2B</p><p>Combined value of threatened marine biomass and subsea telecom infrastructure.</p></div>", unsafe_allow_html=True)
        if st.button("Generate Interdiction Report", use_container_width=True):
            st.success("Report Generated: Dispatching USCG Cutter to intercept coordinates Lat 33.95, Lon -120.15 based on AIS anomaly correlation with WDPA boundaries.")

# --- SCENARIO 2: ADAPTATION ---
elif "Adaptation" in mission:
    st.markdown("<div class='bottom-line'><b>The Bottom Line:</b> Extreme weather costs the shipping industry billions in fuel and lost cargo. Blue 42 predicts the storms and actively reroutes fleets to ensure global supply chain continuity.</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Map Layers for Adaptation
        storm_data = pd.DataFrame([{"polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]], "name": "Severe Gale (Waves > 20ft)"}])
        layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[225, 29, 72, 40]", get_line_color="[225, 29, 72, 150]", line_width_min_pixels=2))
        
        route_data = pd.DataFrame([{"path": [[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]], "name": "AI Optimized Safe Route"}])
        layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[16, 185, 129, 255]", width_min_pixels=4))
        
        r = pdk.Deck(layers=layers, initial_view_state=view_state, map_style=map_style, tooltip={"html": "<b>{name}</b>"})
        st.pydeck_chart(r, use_container_width=True)
        
    with col2:
        st.markdown("<div class='metric-card success-card'><h4>✅ Fleet Rerouted</h4><p class='kpi-value' style='color:#10B981;'>5 SHIPS</p><p>Successfully bypassed extreme hydrodynamic drag.</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='metric-card'><h4>Financial & Carbon Ledger</h4><p class='kpi-value'>$450K</p><p>Fuel capital saved.</p><p class='kpi-value' style='font-size:1.5rem; margin-top:10px;'>54 MT</p><p>Scope 3 CO2e emissions averted via WeatherNext 3 optimization.</p></div>", unsafe_allow_html=True)
        
        # Embedded GenAI Routing
        st.write("---")
        st.write("<b>GenAI Routing Engine</b>", unsafe_allow_html=True)
        if st.button("Calculate New Route via Gemini", use_container_width=True):
            with st.spinner("AI calculating..."):
                try:
                    response = model.generate_content("Write a 2-sentence highly technical marine logistics summary explaining how avoiding 20-foot waves reduces bunker fuel consumption.")
                    st.info(response.text)
                except:
                    st.error("AI Comms Offline.")

# --- SCENARIO 3: MITIGATION ---
elif "Mitigation" in mission:
    st.markdown("<div class='bottom-line'><b>The Bottom Line:</b> Investors want to fund 'Blue Carbon' (kelp forests) but fear the plants will die. Blue 42 uses deep ocean data to mathematically guarantee the planting sites are safe and viable, unlocking millions in ESG capital.</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Map Layers for Mitigation
        depth_data = pd.DataFrame([{"polygon": [[[-119.7, 33.9], [-119.4, 33.9], [-119.4, 34.1], [-119.7, 34.1]]], "name": "Optimal Bathymetric Shelf (-5m to -30m)"}])
        layers.append(pdk.Layer("PolygonLayer", data=depth_data, get_polygon="polygon", get_fill_color="[45, 212, 191, 50]", get_line_color="[45, 212, 191, 200]", line_width_min_pixels=2))
        
        kelp_df = pd.DataFrame([
            {"lat": 34.02, "lon": -119.55, "name": "Verified Carbon Sink K-1 (98% Viability)"},
            {"lat": 33.98, "lon": -119.60, "name": "Verified Carbon Sink K-2 (95% Viability)"}
        ])
        layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_fill_color="[16, 185, 129, 255]", get_radius=3000))
        
        r = pdk.Deck(layers=layers, initial_view_state=view_state, map_style=map_style, tooltip={"html": "<b>{name}</b>"})
        st.pydeck_chart(r, use_container_width=True)
        
    with col2:
        st.markdown("<div class='metric-card success-card'><h4>🌱 Blue Carbon Verified</h4><p class='kpi-value' style='color:#10B981;'>14.2 HA</p><p>Area vetted by DeepMind Species Distribution Models.</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='metric-card'><h4>ESG Asset Valuation</h4><p class='kpi-value'>2,500 tCO₂e</p><p>Projected annual carbon drawdown.</p><p class='kpi-value' style='font-size:1.5rem; margin-top:10px;'>$187,500</p><p>Verified carbon credit value (pegged at $75/ton compliance market rate).</p></div>", unsafe_allow_html=True)
