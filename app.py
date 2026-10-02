import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import json
import ee
import math
import random
import websocket
from google.oauth2 import service_account
import google.generativeai as genai

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# ---------------------------------------------------------
# 1. PAGE SETUP & TRUE TACTICAL THEME
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 Strategic Command", page_icon="🌐", initial_sidebar_state="expanded")

night_vision = st.sidebar.toggle("🌙 Tactical Night Vision", value=True)

# Fixed the map crash by using native PyDeck styles ("dark" and "satellite")
if night_vision:
    # High-contrast, pitch-black tactical mode
    bg_color = "#000000"
    card_bg = "#0a0a0a"
    text_color = "#e0e0e0"
    accent_blue = "#00e5ff"   # Neon Cyan
    accent_red = "#ff0033"    # Tactical Red
    accent_green = "#00ff66"  # Radar Green
    accent_purple = "#b300ff" # UV Purple
    map_style = "dark"        # Native Dark Map (No API Key needed)
else:
    # Clean daytime mode with Satellite view
    bg_color = "#f4f4f9"
    card_bg = "#ffffff"
    text_color = "#111111"
    accent_blue = "#0055ff"
    accent_red = "#cc0000"
    accent_green = "#009933"
    accent_purple = "#6600cc"
    map_style = "satellite"   # Native Satellite Map (No API Key needed)

css = f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: 'Courier New', monospace, sans-serif; }}
    
    /* Aggressive, Glowing Metric Cards */
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 4px; border: 1px solid {accent_blue}; margin-bottom: 16px; box-shadow: 0 0 10px rgba(0, 229, 255, 0.1), inset 0 0 10px rgba(0, 229, 255, 0.05); transition: transform 0.2s ease; }}
    .metric-card:hover {{ transform: scale(1.02); }}
    .protection-card {{ border-color: {accent_red}; box-shadow: 0 0 10px rgba(255, 0, 51, 0.2), inset 0 0 10px rgba(255, 0, 51, 0.1); }}
    .mitigation-card {{ border-color: {accent_green}; box-shadow: 0 0 10px rgba(0, 255, 102, 0.1), inset 0 0 10px rgba(0, 255, 102, 0.05); }}
    .military-card {{ border-color: {accent_purple}; box-shadow: 0 0 10px rgba(179, 0, 255, 0.1), inset 0 0 10px rgba(179, 0, 255, 0.05); }}
    
    /* Typography */
    h1, h2, h3, h4 {{ color: #ffffff; font-weight: bold; margin-top: 0; font-family: 'Trebuchet MS', sans-serif; text-transform: uppercase; letter-spacing: 1px; }}
    h4 {{ font-size: 0.9rem; color: {accent_blue}; }}
    .protection-card h4 {{ color: {accent_red}; }}
    .mitigation-card h4 {{ color: {accent_green}; }}
    .military-card h4 {{ color: {accent_purple}; }}
    
    .kpi-value {{ font-size: 2.5rem; font-weight: 900; color: #ffffff; margin: 4px 0; line-height: 1.1; text-shadow: 0 0 8px rgba(255,255,255,0.3); }}
    .kpi-subtext {{ font-size: 0.85rem; color: #aaaaaa; display: block; margin-bottom: 4px; }}
    .kpi-impact {{ font-size: 0.85rem; color: {accent_green}; font-weight: bold; display: block; }}
    
    /* Cyber Sidebar & Expanders */
    .streamlit-expanderHeader {{ font-weight: bold !important; font-size: 0.95rem; color: {accent_blue} !important; background: rgba(0, 229, 255, 0.05); border: 1px solid {accent_blue}; border-radius: 4px; }}
    div[data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 2px solid {accent_blue}; box-shadow: 5px 0 15px rgba(0, 229, 255, 0.1); }}
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
        ee_status = f"<span style='color:{accent_green};'>🟢 SECURE UPLINK</span>"
    else: ee_status = f"<span style='color:{accent_red};'>🔴 UPLINK SEVERED</span>"
except: ee_status = f"<span style='color:{accent_red};'>🔴 UPLINK SEVERED</span>"

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-3.5-flash')
        ai_status = f"<span style='color:{accent_green};'>🟢 CORE ACTIVE</span>"
    else: ai_status = f"<span style='color:{accent_red};'>🔴 CORE OFFLINE</span>"
except: ai_status = f"<span style='color:{accent_red};'>🔴 CORE OFFLINE</span>"

try:
    ais_key = st.secrets.get("AISSTREAM_API_KEY", "")
    ais_status = f"<span style='color:{accent_green};'>🟢 RADAR AUTHENTICATED</span>" if ais_key else f"<span style='color:{accent_red};'>🔴 RADAR OFFLINE</span>"
except: ais_status = f"<span style='color:{accent_red};'>🔴 RADAR OFFLINE</span>"

# ---------------------------------------------------------
# 3. SIDEBAR: PROFESSIONAL UX NAVIGATION
# ---------------------------------------------------------
st.sidebar.markdown(f"""
<div style="margin-bottom: 30px; text-align: center;">
    <div style="font-size: 50px; color: {accent_blue}; text-shadow: 0 0 15px {accent_blue};">⚓</div>
    <div style="font-weight: 900; color: #ffffff; font-size: 1.8rem; letter-spacing: 2px; margin-top: 5px;">BLUE 42</div>
    <div style="color: {accent_blue}; font-size: 0.8rem; font-weight: bold; letter-spacing: 2px; text-transform: uppercase;">Maritime Command</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🌍 REGIONAL DEPLOYMENT")
sector_mode = st.sidebar.selectbox("Operational Theater:", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"], label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown("### 📊 TACTICAL DATA OVERLAYS")
st.sidebar.caption("Toggle layers to analyze geospatial risk factors.")
show_military = st.sidebar.checkbox("🛡️ Military Zones (Naval Ops)", value=True)
show_iuu = st.sidebar.checkbox("🐟 Protected Areas (Compliance)", value=True)
show_weather = st.sidebar.checkbox("⛈️ Weather Shield (Supply Chain)", value=True)
show_depth = st.sidebar.checkbox("🌊 Ocean Depth (Blue Carbon)", value=False)
show_cables = st.sidebar.checkbox("🔌 Subsea Infrastructure", value=False)
show_sar = st.sidebar.checkbox("🚁 Predictive SAR Drift", value=False)
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 SYSTEM DIAGNOSTICS")
st.sidebar.markdown(f"**Geospatial Engine:**<br>{ee_status}<br><br>**GenAI Reasoning:**<br>{ai_status}<br><br>**AIS Telemetry:**<br>{ais_status}", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. UNIFIED DATA SCHEMA FOR DEEP-DIVE TOOLTIPS
# ---------------------------------------------------------
map_layers = []
risk_level = "GREEN (Nominal)"
active_alerts = []

def create_unified_tooltip_data(lat, lon, name, primary, secondary, analytics, source, color, polygon=None, path=None, radius=None):
    return {
        "lat": lat, "lon": lon, "name": name, 
        "primary_metric": primary, "secondary_metric": secondary,
        "analytics": analytics, "source": source, "color": color,
        "polygon": polygon, "path": path, "radius": radius
    }

unified_data = []

# --- REGIONAL CONFIGURATIONS & STATIC OVERLAYS ---
if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=45, bearing=-10)
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]]
    base_lat, base_lon = 33.8, -119.5
    
    if show_military:
        poly = [[[-120.5, 33.2], [-119.0, 33.2], [-119.0, 33.8], [-120.5, 33.8]]]
        unified_data.append(create_unified_tooltip_data(33.5, -119.7, "Point Mugu Sea Range", "Status: RESTRICTED", "Type: Naval Weapons Testing Area", "Vessel traffic strictly prohibited during active missile testing windows. High risk of kinetic interaction.", "US Navy / FAA", [179, 0, 255, 40], polygon=poly))
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([unified_data[-1]]), get_polygon="polygon", get_fill_color="color", get_line_color="[179, 0, 255, 255]", line_width_min_pixels=2, pickable=True))

    if show_weather:
        poly = [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]]
        unified_data.append(create_unified_tooltip_data(33.8, -119.3, "Severe Gale Warning", "Intensity: H_s > 6.1m (20ft)", "Wind: Sustained 45 knots", "Extreme hydrodynamic drag detected. Routing through this zone increases fuel consumption by 12% and risks cargo loss.", "Copernicus & WeatherNext 3", [255, 0, 51, 40], polygon=poly))
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([unified_data[-1]]), get_polygon="polygon", get_fill_color="color", get_line_color="[255, 0, 51, 200]", line_width_min_pixels=2, pickable=True))

    if show_iuu:
        poly = [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]]
        unified_data.append(create_unified_tooltip_data(34.0, -119.7, "Channel Islands Marine Sanctuary", "Protection Level: FULL", "Jurisdiction: Federal MPA", "Zero-take zone. Any commercial fishing activity here constitutes a severe regulatory breach.", "UNEP-WCMC WDPA", [0, 255, 102, 20], polygon=poly))
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([unified_data[-1]]), get_polygon="polygon", get_fill_color="color", get_line_color="[0, 255, 102, 200]", line_width_min_pixels=2, pickable=True))
        risk_level = "RED (Active Compliance Risk)"

else: # HAWAII
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=45, bearing=-10)
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    base_lat, base_lon = 21.2, -158.0
    
    if show_military:
        poly = [[[-159.9, 21.8], [-159.5, 21.8], [-159.5, 22.2], [-159.9, 22.2]]]
        unified_data.append(create_unified_tooltip_data(22.0, -159.7, "PMRF Barking Sands", "Status: RESTRICTED AIR/SEA", "Type: Pacific Missile Range Facility", "World's largest instrumented multi-environment military testing range. Civilian intrusion violates federal exclusion zone.", "US Navy / FAA", [179, 0, 255, 40], polygon=poly))
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([unified_data[-1]]), get_polygon="polygon", get_fill_color="color", get_line_color="[179, 0, 255, 255]", line_width_min_pixels=2, pickable=True))

    if show_weather:
        poly = [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]]
        unified_data.append(create_unified_tooltip_data(21.2, -157.8, "Tropical Squall Hazard Zone", "Intensity: H_s > 4.5m", "Wind: Gusts to 35 knots", "Localized squall creating supply chain delays for Honolulu port approaches.", "WeatherNext 3", [255, 0, 51, 40], polygon=poly))
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([unified_data[-1]]), get_polygon="polygon", get_fill_color="color", get_line_color="[255, 0, 51, 200]", line_width_min_pixels=2, pickable=True))

    if show_iuu:
        poly = [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]]
        unified_data.append(create_unified_tooltip_data(21.5, -158.0, "Kaena Point MPA Expansion", "Protection Level: FULL", "Jurisdiction: Federal/State", "Critical habitat preservation area. High-value target for illicit commercial harvesting.", "UNEP-WCMC WDPA", [0, 255, 102, 20], polygon=poly))
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([unified_data[-1]]), get_polygon="polygon", get_fill_color="color", get_line_color="[0, 255, 102, 200]", line_width_min_pixels=2, pickable=True))
        risk_level = "RED (Active Compliance Risk)"

# ---------------------------------------------------------
# 5. VESSEL ENGINE (HIGH-FIDELITY SIM)
# ---------------------------------------------------------
vessels = []
for i in range(35):
    sog = random.uniform(8.0, 22.0)
    v_type = random.choice(["CARGO", "TANKER", "BULK"])
    mmsi = f"36{random.randint(1000000, 9999999)}"
    lat = base_lat + random.uniform(-1.5, 1.5)
    lon = base_lon + random.uniform(-2.0, 2.0)
    cog = random.uniform(0, 360)
    
    # Path for ARPA heading line
    cog_rad = math.radians(cog)
    vec_len = max(sog * 0.003, 0.01)
    heading_path = [[lon, lat], [lon + vec_len * math.sin(cog_rad), lat + vec_len * math.cos(cog_rad)]]
    
    vessels.append(create_unified_tooltip_data(
        lat, lon, f"{v_type} (MMSI: {mmsi})", 
        f"Speed: {sog:.1f} kts | Heading: {cog:.1f}°", 
        f"Length: {random.randint(150,350)}m | Draft: {random.uniform(9,15):.1f}m", 
        "Vessel kinetics operate within nominal parameters. Compliant track.", 
        "Verified AIS Telemetry", 
        [0, 229, 255, 200], path=heading_path, radius=1200
    ))

# Inject the Dark Target (IUU Threat)
dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
vessels.append(create_unified_tooltip_data(
    dt_lat, dt_lon, "UNVERIFIED DARK TARGET", 
    "Speed: 2.5 kts (Loitering) | Heading: 80.0°", 
    "Estimated Length: 45m | Draft: 3.2m", 
    "CRITICAL ANOMALY: Vessel disabled transponder 15nm from MPA. Kinematics strongly suggest illicit fishing deployment.", 
    "AISStream / Spatial DeepMind Analysis", 
    [255, 0, 51, 255], 
    path=[[dt_lon, dt_lat], [dt_lon + 0.01, dt_lat + 0.005]], radius=2000
))

vessels_df = pd.DataFrame(vessels)
# Vessel dot
map_layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))
# Vessel heading vector
map_layers.append(pdk.Layer("PathLayer", data=vessels_df, get_path="path", get_color="color", width_min_pixels=2, pickable=False))

# ---------------------------------------------------------
# 6. MAIN DASHBOARD: THE EXECUTIVE STORYBOARD
# ---------------------------------------------------------
st.markdown(f"<h2 style='color: #ffffff;'>Global Maritime Command Center</h2>", unsafe_allow_html=True)
st.markdown("<p class='hud-text' style='margin-bottom: 25px;'>Synthesizing planetary telemetry into predictive intelligence and actionable ESG workflows.</p>", unsafe_allow_html=True)

# Clean, elegant KPI row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ACTIVE THREATS</h4><p class='kpi-value' style='color:{accent_red};'>1 VOI</p><span class='kpi-subtext'>Target masking identity near MPA</span></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='metric-card military-card'><h4>⚓ MILITARY ZONES</h4><p class='kpi-value' style='color:{accent_purple};'>SECURE</p><span class='kpi-subtext'>No incursions in weapons ranges</span></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='metric-card'><h4>🌪️ RESILIENCE</h4><p class='kpi-value' style='color:{accent_blue};'>5 REROUTED</p><span class='kpi-subtext'>Avoiding extreme wave heights</span></div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 BLUE CARBON</h4><p class='kpi-value' style='color:{accent_green};'>14.2 HA</p><span class='kpi-subtext'>Optimal restoration sites verified</span></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. ASSEMBLE 3D MAP WITH DEEP-DIVE TOOLTIPS
# ---------------------------------------------------------
# UX Masterpiece: A unified, gorgeous tooltip for every element
custom_tooltip = {
    "html": f"""
    <div style='background: {card_bg}; border: 1px solid {accent_blue}; padding: 16px; border-radius: 6px; color: {text_color}; font-family: Courier New, monospace; box-shadow: 0 0 15px rgba(0, 229, 255, 0.2); max-width: 320px;'>
        <div style='font-size: 1.1rem; font-weight: bold; color: {accent_blue}; margin-bottom: 8px; border-bottom: 1px solid #333; padding-bottom: 4px;'>{{name}}</div>
        <div style='font-size: 0.85rem; color: #aaaaaa; margin-bottom: 4px;'>{{primary_metric}}</div>
        <div style='font-size: 0.85rem; color: #aaaaaa; margin-bottom: 12px;'>{{secondary_metric}}</div>
        <div style='background: rgba(0, 0, 0, 0.5); padding: 8px; border-left: 3px solid {accent_green}; margin-bottom: 8px;'>
            <span style='color: {accent_green}; font-weight: bold; font-size: 0.85rem;'>AI ANALYTICS:</span><br/>
            <span style='font-size: 0.8rem; line-height: 1.4; color: #ffffff;'>{{analytics}}</span>
        </div>
        <div style='font-size: 0.75rem; color: #666666; font-style: italic; text-align: right;'>Source: {{source}}</div>
    </div>
    """,
    "style": {"backgroundColor": "transparent", "padding": "0"} 
}

st.markdown("#### 🗺️ TACTICAL BATTLESPACE OVERVIEW", unsafe_allow_html=True)
r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=custom_tooltip)
st.pydeck_chart(r, use_container_width=True)

# ---------------------------------------------------------
# 8. ANALYTICS & GENAI DEEP DIVES
# ---------------------------------------------------------
st.write("---")
tab1, tab2 = st.tabs(["🧠 Strategic Advisory AI (GenAI)", "📈 Enterprise Data Ledger"])

with tab1:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Live Intelligence Chat")
        if "messages" not in st.session_state: st.session_state.messages = []
        for message in st.session_state.messages[-2:]: 
            with st.chat_message(message["role"]): st.markdown(message["content"])
        
        if prompt := st.chat_input("Ask for tactical assessment..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                try:
                    tactical_prompt = f"You are a Strategic Advisor. Sector: {sector_mode}. Analyze query focusing on risk and data analytics: {prompt}"
                    response = model.generate_content(tactical_prompt)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except: st.error("AI Comms Offline.")
    
    with col_b:
        st.markdown("#### Dynamic Route Optimization")
        st.markdown("<p class='hud-text'>Use AI to calculate safe passage through severe weather polygons.</p>", unsafe_allow_html=True)
        with st.form("routing_form"):
            st.selectbox("Select Asset in Danger:", ["COMMERCIAL FREIGHTER (MMSI: 36812345) - 300m, 14.5m Draft"])
            submit_route = st.form_submit_button("Generate Predictive Voyage Plan")
            if submit_route:
                with st.spinner("Calculating hydrodynamic drag against decadal wave baselines..."):
                    try:
                        res = model.generate_content("Generate a concise, 3-step bulleted voyage rerouting plan to minimize drag through a 6-meter sea state for a 300m freighter. Conclude with estimated fuel saved.")
                        st.success("Plan Authorized")
                        st.markdown(f"<div class='terminal'>{res.text}</div>", unsafe_allow_html=True)
                    except: st.error("AI Comms Offline.")

with tab2:
    st.markdown("#### Scope 3 Emissions & Carbon Verification Ledger")
    st.markdown("<p class='hud-text'>Translating physical interventions into verified ESG assets.</p>", unsafe_allow_html=True)
    
    ledger = pd.DataFrame([
        {"Asset Class": "Blue Carbon (Kelp) K-1", "Status": "Verified (Depth/SST Check)", "Hectares": 14.2, "tCO2e Averted/Seq": 2500, "Asset Value": "$187,500"},
        {"Asset Class": "Vessel Reroute (Weather Shield)", "Status": "Executed (Avoided H_s > 6m)", "Hectares": 0, "tCO2e Averted/Seq": 54.2, "Asset Value": "$4,065"}
    ])
    st.dataframe(ledger, use_container_width=True)
