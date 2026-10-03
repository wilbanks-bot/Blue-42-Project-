import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import json
import ee
import math
import random
import time
from google.oauth2 import service_account
import google.generativeai as genai

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# ---------------------------------------------------------
# 1. PAGE SETUP & ENTERPRISE UX THEME (PALANTIR STYLE)
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 Strategic Command", page_icon="🌐", initial_sidebar_state="expanded")

# Safeguard Session States
if "sar_tasked" not in st.session_state: st.session_state.sar_tasked = False
if "booms_deployed" not in st.session_state: st.session_state.booms_deployed = False
if "library" not in st.session_state: st.session_state.library = []
if "sentinel_logs" not in st.session_state: st.session_state.sentinel_logs = []
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Watchstander AI active. Awaiting strategic queries."}]

night_vision = st.sidebar.toggle("🌙 Executive Dark Mode", value=True)

if night_vision:
    bg_color = "#0B1121"; card_bg = "#1F2937"; text_color = "#F9FAFB"; muted_text = "#9CA3AF"; border_color = "#374151"
    accent_blue = "#38BDF8"; accent_red = "#F43F5E"; accent_green = "#10B981"; accent_purple = "#8B5CF6"; accent_amber = "#F59E0B"
    map_style = "dark"; term_bg = "#000000"; term_color = "#10B981"
else:
    bg_color = "#F8FAFC"; card_bg = "#FFFFFF"; text_color = "#0F172A"; muted_text = "#64748B"; border_color = "#E2E8F0"
    accent_blue = "#0284c7"; accent_red = "#E11D48"; accent_green = "#059669"; accent_purple = "#7C3AED"; accent_amber = "#D97706"
    map_style = "light"; term_bg = "#F1F5F9"; term_color = "#0F172A"

css = f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: -apple-system, sans-serif; }}
    .metric-card {{ background-color: {card_bg}; padding: 24px; border-radius: 8px; border-top: 4px solid {accent_blue}; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    .protection-card {{ border-top-color: {accent_red}; }}
    .mitigation-card {{ border-top-color: {accent_green}; }}
    .military-card {{ border-top-color: {accent_purple}; }}
    .logistics-card {{ border-top-color: {accent_amber}; }}
    h2, h3, h4 {{ color: {text_color}; font-weight: 600; margin-top: 0; letter-spacing: -0.01em; }}
    h4 {{ font-size: 0.85rem; text-transform: uppercase; color: {muted_text}; margin-bottom: 12px; }}
    .kpi-value {{ font-size: 2.2rem; font-weight: 700; margin: 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.85rem; color: {muted_text}; margin-top: 6px; display: block; }}
    .terminal {{ background-color: {term_bg}; padding: 16px; border-radius: 6px; border-left: 4px solid {accent_blue}; color: {term_color}; font-family: monospace; font-size: 0.85rem; white-space: pre-wrap; }}
    div[data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid {border_color}; }}
    .ticker-wrap {{ width: 100%; overflow: hidden; background-color: {card_bg}; border-bottom: 1px solid {border_color}; padding: 8px 0; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    .ticker {{ display: inline-block; white-space: nowrap; padding-right: 100%; animation: ticker 30s linear infinite; }}
    .ticker-item {{ display: inline-block; padding: 0 2rem; font-family: monospace; font-size: 0.9rem; color: {accent_blue}; font-weight: 600; }}
    @keyframes ticker {{ 0% {{ transform: translate3d(0, 0, 0); }} 100% {{ transform: translate3d(-100%, 0, 0); }} }}
    .stTabs [data-baseweb="tab"] {{ height: 50px; background-color: transparent; border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px; font-weight: 500; }}
    .stTabs [aria-selected="true"] {{ background-color: {card_bg}; border-bottom: 2px solid {accent_blue}; color: {accent_blue}; font-weight: 700; }}
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
        ee_status = "🟢 SECURE UPLINK"
    else: ee_status = "🔴 UPLINK SEVERED"
except: ee_status = "🔴 UPLINK SEVERED"

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = 'gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0].replace('models/', '')
        model = genai.GenerativeModel(target_model)
        ai_status = f"🟢 CORE ACTIVE"
    else: ai_status = "🔴 CORE OFFLINE"
except: ai_status = "🔴 CORE OFFLINE"

try:
    ais_key = st.secrets.get("AISSTREAM_API_KEY", "")
    ais_status = "🟢 RADAR AUTHENTICATED" if ais_key else "🔴 RADAR OFFLINE"
except: ais_status = "🔴 RADAR OFFLINE"

# ---------------------------------------------------------
# 3. SIDEBAR: TACTICAL CONTROLS & OVERLAYS
# ---------------------------------------------------------
st.sidebar.markdown(f"""
<div style="margin-bottom: 30px; text-align: center;">
    <div style="font-size: 40px; color: {accent_blue}; line-height: 1;">🌊</div>
    <div style="font-weight: 800; color: {text_color}; font-size: 1.5rem; letter-spacing: 2px; margin-top: 10px;">BLUE 42 COMMAND</div>
    <div style="color: {muted_text}; font-size: 0.75rem; font-weight: 600; letter-spacing: 1px; text-transform: uppercase;">Global Blue Economy OS</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 👤 OPERATOR ALIGNMENT")
operator_role = st.sidebar.selectbox("Active Profile:", ["Strategic Commander", "ESG Financial Auditor", "Logistics Fleet Director"], label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown(f"<div style='font-size: 0.8rem; color: {muted_text}; margin-bottom: 2rem; text-align: center;'><b>GEO:</b> {ee_status} | <b>AI:</b> {ai_status} | <b>AIS:</b> {ais_status}</div>", unsafe_allow_html=True)

st.sidebar.markdown("### 🌍 REGIONAL DEPLOYMENT")
sector_mode = st.sidebar.selectbox("Operational Theater:", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"], label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 LIVE TELEMETRY")
live_ais = st.sidebar.toggle("Connect Live Satellite AIS Feed", value=False)
st.sidebar.markdown("---")

# THE FIX: ALL MULTI-DOMAIN OVERLAY VARIABLES ARE NOW SECURELY DEFINED
st.sidebar.markdown("### 📊 MULTI-DOMAIN OVERLAYS")
show_iuu = st.sidebar.checkbox("🛡️ Marine Protected Areas", value=True)
show_weather = st.sidebar.checkbox("⛈️ Extreme Weather Hazards", value=True)
show_depth = st.sidebar.checkbox("🌱 Blue Carbon Sites", value=True)
show_military = st.sidebar.checkbox("⚓ Naval Exclusion Zones", value=True)
show_currents = st.sidebar.checkbox("🌊 Ocean Microcurrents", value=True)
show_whales = st.sidebar.checkbox("🐋 Marine Mammal Habitats", value=True)
show_spill = st.sidebar.checkbox("🛢️ Oil Spill Trajectories", value=False)
show_cables = st.sidebar.checkbox("🔌 Subsea Infrastructure", value=False)

# ---------------------------------------------------------
# 4. EXECUTIVE STORYBOARD & MACRO TICKER
# ---------------------------------------------------------
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker">
        <span class="ticker-item">⚠️ GLOBAL SUPPLY CHAIN VALUE AT RISK (H_s > 6.1m): $4.2B</span>
        <span class="ticker-item">✅ SCOPE 3 EMISSIONS AVERTED (24HR): 1,245 MT CO2e</span>
        <span class="ticker-item">🌱 VERIFIED BLUE CARBON ASSETS: $12.4M</span>
        <span class="ticker-item">🚨 ACTIVE IUU / SLAVERY THREATS TRACKED: 2</span>
        <span class="ticker-item">🐋 MARINE MAMMAL STRIKES AVERTED: 14</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"<h2 style='color: {text_color}; text-align: center; margin-bottom: 8px;'>Global Maritime Command Center</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='color: {muted_text}; text-align: center; font-size: 1.1rem; margin-bottom: 30px;'>Synthesizing planetary telemetry into predictive intelligence and actionable workflows.</p>", unsafe_allow_html=True)

focus_mode = st.radio("SELECT STRATEGIC FOCUS TO FILTER BATTLESPACE & ANALYTICS:", 
    ["🌍 Global Overview", "🛡️ Human Rights & Ecocide", "🌪️ Macro-Economic Resilience", "🌱 Planetary Capital (ESG)"], 
    horizontal=True)
st.write("")

col1, col2, col3, col4 = st.columns(4)
with col1: st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ACTIVE THREATS</h4><p class='kpi-value' style='color:{accent_red};'>2 VOI</p><span class='kpi-subtext'>High risk of forced labor / IUU</span></div>", unsafe_allow_html=True)
with col2: st.markdown(f"<div class='metric-card military-card'><h4>⚓ CRISIS RESPONSE</h4><p class='kpi-value' style='color:{accent_amber};'>STANDBY</p><span class='kpi-subtext'>Spill/SAR algorithms ready</span></div>", unsafe_allow_html=True)
with col3: st.markdown(f"<div class='metric-card'><h4>🌪️ MACRO-ECONOMICS</h4><p class='kpi-value' style='color:{accent_blue};'>5 REROUTED</p><span class='kpi-subtext'>Inflationary supply shocks averted</span></div>", unsafe_allow_html=True)
with col4: st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 PLANETARY CAPITAL</h4><p class='kpi-value' style='color:{accent_green};'>14.2 HA</p><span class='kpi-subtext'>Optimal bio-sinks verified</span></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. UNIFIED DATA SCHEMA FOR DEEP-DIVE TOOLTIPS
# ---------------------------------------------------------
map_layers = []

tooltip_config = {
    "html": f"<b>{{name}}</b><hr style='margin:6px 0; border-color: {border_color};'/>"
            f"<div style='color:{muted_text}; font-size:0.85rem;'>{{primary_metric}}</div>"
            f"<div style='color:{muted_text}; font-size:0.85rem; margin-bottom:8px;'>{{secondary_metric}}</div>"
            f"<b style='color:{accent_green}; font-size:0.8rem;'>AI ANALYTICS:</b><br/>"
            f"<span style='color:{text_color}; font-size:0.85rem; line-height:1.4;'>{{analytics}}</span><br/><br/>"
            f"<i style='color:{muted_text}; font-size:0.75rem;'>Source: {{source}}</i>",
    "style": {
        "backgroundColor": card_bg, "color": text_color, "border": f"1px solid {accent_blue}", 
        "borderRadius": "8px", "padding": "16px", "fontFamily": "-apple-system, sans-serif",
        "maxWidth": "320px", "boxShadow": "0 10px 15px -3px rgba(0,0,0,0.5)"
    }
}

def create_unified_tooltip_data(lat, lon, name, primary, secondary, analytics, source, color, polygon=None, path=None, radius=None, elevation=0):
    return {"lat": lat, "lon": lon, "name": name, "primary_metric": primary, "secondary_metric": secondary, "analytics": analytics, "source": source, "color": color, "polygon": polygon, "path": path, "radius": radius, "elevation": elevation}

def get_battleship_polygon(lat, lon, cog, length_m, width_m):
    cog_rad = math.radians(cog)
    scale = 3.5 
    L, W = length_m * scale, width_m * scale
    lat_deg_per_m = 1.0 / 111111.0
    lon_deg_per_m = 1.0 / (111111.0 * math.cos(math.radians(lat)))
    pts = [(-W/2, -L/2), (W/2, -L/2), (W/2, L/4), (0, L/2), (-W/2, L/4)]
    poly = []
    for dx, dy in pts:
        x_rot = dx * math.cos(cog_rad) + dy * math.sin(cog_rad)
        y_rot = -dx * math.sin(cog_rad) + dy * math.cos(cog_rad)
        poly.append([lon + x_rot * lon_deg_per_m, lat + y_rot * lat_deg_per_m])
    return [poly]

# ---------------------------------------------------------
# 6. DYNAMIC MAP LOGIC (STATIC ZONES & OVERLAYS)
# ---------------------------------------------------------
static_data = []

if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=50, bearing=-15)
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]]
    base_lat, base_lon = 33.8, -119.5
    regional_ports = ["Port of Los Angeles", "Port of Long Beach", "Port Hueneme"]
    
    if show_iuu:
        poly = [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]]
        static_data.append(create_unified_tooltip_data(34.0, -119.7, "Channel Islands Marine Sanctuary", "Protection Level: FULL", "Jurisdiction: Federal", "Zero-take zone. Continuous AI surveillance active to detect 'dark fleet' incursions.", "UNEP-WCMC", [56, 189, 248, 40], polygon=poly))
    
    if show_weather:
        poly = [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]]
        static_data.append(create_unified_tooltip_data(33.8, -119.3, "Severe Gale Warning", "Intensity: H_s > 6.1m (20ft)", "Wind: Sustained 45 knots", "Extreme hydrodynamic drag detected. Routing through this zone increases fuel consumption by 12% and risks cargo loss.", "WeatherNext 3", [239, 68, 68, 50], polygon=poly))
        
        path = [[[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]]]
        static_data.append(create_unified_tooltip_data(33.4, -119.3, "AI Optimized Logistics Route", "Status: ACTIVE REROUTE", "Fuel Averted: 54 MT", "Predictive vector safely circumvents the Gale Warning polygon, preserving operational continuity.", "AlphaEarth", [16, 185, 129, 200], path=path[0]))
        
    if show_depth:
        poly = [[[-119.7, 33.9], [-119.4, 33.9], [-119.4, 34.1], [-119.7, 34.1]]]
        static_data.append(create_unified_tooltip_data(34.0, -119.55, "Optimal Bathymetric Shelf", "Layer: Ocean Topography", "Range: -5m to -30m", "Highly viable blue carbon zone.", "Copernicus Marine", [45, 212, 191, 30], polygon=poly))
        static_data.append(create_unified_tooltip_data(34.02, -119.55, "Verified Carbon Sink K-1", "Area: 5.1 HA", "Viability Index: 98%", "Depth 14m, SST 16.5°C. Site meets all thermal survivability thresholds. Safe for capital allocation.", "DeepMind SDM", [16, 185, 129, 255], radius=3000, elevation=8980))
        static_data.append(create_unified_tooltip_data(33.98, -119.60, "Verified Carbon Sink K-2", "Area: 4.8 HA", "Viability Index: 95%", "Deep-water thermal refuge. High resilience to warming.", "DeepMind SDM", [16, 185, 129, 255], radius=3000, elevation=8450))

    if show_military:
        poly = [[[-120.5, 33.2], [-119.0, 33.2], [-119.0, 33.8], [-120.5, 33.8]]]
        static_data.append(create_unified_tooltip_data(33.5, -119.7, "Point Mugu Sea Range", "Status: RESTRICTED", "Type: Naval Weapons Area", "Geofence: ACTIVE | Status: LIVE FIRE. High kinetic risk.", "US Navy", [139, 92, 246, 40], polygon=poly))

    if show_currents:
        path = [[[-120.5, 34.5], [-119.8, 33.8], [-119.2, 33.0]]]
        static_data.append(create_unified_tooltip_data(33.8, -119.8, "California Microcurrent Stream", "Velocity: 1.2 kts Southbound", "Status: Favorable Surf Zone", "Surfing this current allows a 10% reduction in engine RPM while maintaining SOG.", "Copernicus Ocean Physics", [56, 189, 248, 200], path=path[0]))

    if show_whales:
        poly = [[[-120.0, 33.5], [-119.5, 33.5], [-119.3, 34.0], [-119.8, 34.0]]]
        static_data.append(create_unified_tooltip_data(33.7, -119.6, "Dynamic Whale Pod Migration", "Status: 10-Knot Speed Limit Active", "Species: Blue Whale", "DeepMind SDM indicates high probability of plankton bloom.", "DeepMind SDM", [139, 92, 246, 40], polygon=poly))

    if show_spill:
        poly = [[[-119.8, 33.9], [-119.6, 33.8], [-119.5, 33.9], [-119.7, 34.0]]]
        static_data.append(create_unified_tooltip_data(33.9, -119.6, "72-Hour Spill Trajectory", "Contaminant: Heavy Fuel Oil", "Impact Risk: Critical", "AlphaEarth leeway models project slick impacting Santa Cruz Island in 48 hours. Deploy containment booms immediately.", "AlphaEarth", [245, 158, 11, 70], polygon=poly))

    if show_cables:
        path = [[[-121.0, 33.5], [-119.0, 33.8], [-118.0, 34.2]]]
        static_data.append(create_unified_tooltip_data(33.8, -119.0, "Tier-1 Subsea Data Cable", "Asset: Transpacific Trunk", "Vulnerability: Exposed to anchor drag", "Critical infrastructure carrying billions in daily financial transactions.", "Submarine Cable Map", [203, 213, 225, 200], path=path[0]))

else: # HAWAII
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=50, bearing=-15)
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    base_lat, base_lon = 21.2, -158.0
    regional_ports = ["Honolulu Harbor", "Pearl Harbor", "Kahului"]
    
    if show_iuu:
        poly = [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]]
        static_data.append(create_unified_tooltip_data(21.5, -158.0, "Kaena Point MPA Expansion", "Protection Level: FULL", "Jurisdiction: Federal/State", "Critical habitat preservation area. High-value target for illicit commercial harvesting.", "UNEP-WCMC", [56, 189, 248, 40], polygon=poly))

    if show_weather:
        poly = [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]]
        static_data.append(create_unified_tooltip_data(21.2, -157.8, "Tropical Squall Hazard Zone", "Intensity: H_s > 4.5m", "Wind: Gusts to 35 knots", "Localized squall creating supply chain delays.", "WeatherNext 3", [239, 68, 68, 50], polygon=poly))

    if show_depth:
        poly = [[[-158.0, 21.3], [-157.6, 21.3], [-157.6, 21.6], [-158.0, 21.6]]]
        static_data.append(create_unified_tooltip_data(21.45, -157.8, "Reef Bathymetric Contour", "Layer: Ocean Topography", "Range: -5m to -30m", "Optimal thermal and depth envelope.", "Copernicus Marine", [45, 212, 191, 30], polygon=poly))
        static_data.append(create_unified_tooltip_data(21.45, -157.8, "Verified Reef Restoration R-1", "Area: 6.5 HA", "Viability Index: 96%", "Optimal ESG rehabilitation zone.", "DeepMind SDM", [16, 185, 129, 255], radius=3000, elevation=11440))

    if show_military:
        poly = [[[-159.9, 21.8], [-159.5, 21.8], [-159.5, 22.2], [-159.9, 22.2]]]
        static_data.append(create_unified_tooltip_data(22.0, -159.7, "PMRF Barking Sands", "Status: RESTRICTED", "Type: Pacific Missile Range", "Civilian intrusion violates federal exclusion zone.", "US Navy", [139, 92, 246, 40], polygon=poly))

# Parse Static Layers
static_df = pd.DataFrame(static_data)
if not static_df.empty:
    polygons = static_df[static_df['polygon'].notnull()]
    if not polygons.empty: map_layers.append(pdk.Layer("PolygonLayer", data=polygons, get_polygon="polygon", get_fill_color="color", get_line_color="[255,255,255,100]", line_width_min_pixels=1, pickable=True, auto_highlight=True))
    paths = static_df[static_df['path'].notnull()]
    if not paths.empty: map_layers.append(pdk.Layer("PathLayer", data=paths, get_path="path", get_color="color", width_min_pixels=3, pickable=True, auto_highlight=True))
    columns = static_df[static_df['radius'] > 0]
    if not columns.empty: map_layers.append(pdk.Layer("ColumnLayer", data=columns, get_position="[lon, lat]", get_elevation="elevation", elevation_scale=1, radius="radius", get_fill_color="color", pickable=True, extruded=True, auto_highlight=True))

# ---------------------------------------------------------
# 7. HIGH-FIDELITY VESSEL SIMULATION & 3D BATTLESHIPS
# ---------------------------------------------------------
live_vessels_data = []

if live_ais and ais_key and WEBSOCKET_AVAILABLE:
    with st.sidebar.status("📡 Correlating Live AIS with Threat Matrix...", expanded=True) as status:
        try:
            ws = websocket.create_connection("wss://stream.aisstream.io/v0/stream", timeout=4)
            ws.send(json.dumps({"APIKey": ais_key, "BoundingBoxes": ais_bounds, "FilterMessageTypes": ["PositionReport"]}))
            start_time = time.time()
            while time.time() - start_time < 3.0: 
                try:
                    data = json.loads(ws.recv())
                    if data.get("MessageType") == "PositionReport":
                        pr = data["Message"]["PositionReport"]
                        mmsi = str(data.get("MetaData", {}).get("MMSI", "UNKNOWN"))
                        name = data.get("MetaData", {}).get("ShipName", "").strip() or f"MMSI: {mmsi}"
                        lat, lon = pr.get('Latitude', 0), pr.get('Longitude', 0)
                        if lat != 0 and lon != 0:
                            sog, cog = pr.get('Sog', 0), pr.get('Cog', 0)
                            v_len = int(random.uniform(150, 350))
                            v_width = int(v_len*0.15)
                            live_vessels_data.append({
                                "MMSI": mmsi, "Vessel Name": name, "lat": lat, "lon": lon, 
                                "sog": sog, "cog": cog, "Length (m)": v_len, "Width (m)": v_width, "Draft (m)": round(random.uniform(8.0, 15.0), 1),
                                "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
                            })
                        if len(live_vessels_data) >= 30: break
                except websocket.WebSocketTimeoutException: break
            ws.close()
            status.update(label=f"Tracking {len(live_vessels_data)} verified vessels.", state="complete")
        except Exception as e: status.update(label=f"Uplink failed: {e}", state="error")

if len(live_vessels_data) < 3:
    for i in range(35):
        sog = random.uniform(8.0, 22.0)
        v_type = random.choice(["CARGO", "TANKER", "BULK"])
        mmsi = f"36{random.randint(1000000, 9999999)}"
        v_len = int(random.uniform(150,350))
        live_vessels_data.append({
            "MMSI": mmsi, "Vessel Name": f"{v_type} {mmsi[-4:]}",
            "lat": base_lat + random.uniform(-1.5, 1.5), "lon": base_lon + random.uniform(-2.0, 2.0),
            "sog": round(sog,1), "cog": round(random.uniform(0, 360),1),
            "Length (m)": v_len, "Width (m)": int(v_len*0.15), "Draft (m)": round(random.uniform(9.0,16.0), 1),
            "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
        })

# The Critical Dark Targets (IUU/Slavery Threats)
dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
live_vessels_data.append({
    "MMSI": "413000000", "Vessel Name": "UNVERIFIED DARK TARGET ALPHA", "Type": "SUSPECT",
    "lat": dt_lat, "lon": dt_lon, "sog": 1.5, "cog": 80.0,
    "Length (m)": 45, "Width (m)": 8, "Draft (m)": 3.2,
    "Risk Status": "CRITICAL ANOMALY", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
})
live_vessels_data.append({
    "MMSI": "413000001", "Vessel Name": "UNVERIFIED DARK TARGET BRAVO", "Type": "SUSPECT",
    "lat": dt_lat + 0.005, "lon": dt_lon + 0.005, "sog": 1.5, "cog": 260.0,
    "Length (m)": 120, "Width (m)": 18, "Draft (m)": 6.5,
    "Risk Status": "CRITICAL ANOMALY", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
})

# SAR DRONE SWARM DEPLOYMENT
if st.session_state.sar_tasked:
    for i in range(4):
        live_vessels_data.append({
            "MMSI": f"DRONE-0{i}", "Vessel Name": "USCG AUTONOMOUS DRONE", "Type": "DRONE",
            "lat": dt_lat + random.uniform(-0.02, 0.02), "lon": dt_lon + random.uniform(-0.02, 0.02),
            "sog": 45.0, "cog": random.uniform(0, 360),
            "Length (m)": 10, "Width (m)": 5, "Draft (m)": 1.0,
            "Risk Status": "INTERCEPT ASSET", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
        })

vessels = []
path_data = []

for v in live_vessels_data:
    is_threat = v['Risk Status'] in ["CRITICAL ANOMALY", "TRANSSHIPMENT DETECTED"]
    is_drone = v['Risk Status'] == "INTERCEPT ASSET"
    
    if focus_mode == "🌱 Planetary Capital (ESG)" and not is_threat: continue
    
    cog_rad = math.radians(v['cog'])
    vec_len = max(v['sog'] * 0.003, 0.01)
    
    if is_threat: color = [239, 68, 68, 255]
    elif is_drone: color = [250, 204, 21, 255]
    else: color = [56, 189, 248, 180]
    
    if is_threat: analysis = "HUMAN RIGHTS ANOMALY: Converging kinematic tracks indicate illegal ship-to-ship transfer (Transshipment) of forced labor or IUU catch."
    elif is_drone: analysis = "Autonomous Verification Asset. Transmitting visual evidence."
    else: analysis = "Vessel kinetics operate within nominal parameters. Compliant track."
    
    ship_poly = get_battleship_polygon(v['lat'], v['lon'], v['cog'], v['Length (m)'], v['Width (m)'])
    elevation = 150 if is_threat else max(30, v['Length (m)'] / 4.0)
    
    vessels.append(create_unified_tooltip_data(
        v['lat'], v['lon'], v['Vessel Name'], f"Speed: {v['sog']} kts | Heading: {v['cog']}°", 
        f"Length: {v['Length (m)']}m | Draft: {v['Draft (m)']}m", analysis, 
        "Verified AIS Telemetry", color, polygon=ship_poly, elevation=elevation
    ))
    path_data.append({"path": [[v['lon'], v['lat']], [v['lon'] + vec_len * math.sin(cog_rad), v['lat'] + vec_len * math.cos(cog_rad)]], "color": color})

vessels_df = pd.DataFrame(vessels)
if not vessels_df.empty:
    vessels_df['coordinates'] = vessels_df.apply(lambda r: [r['lon'], r['lat']], axis=1) # Failsafe Coordinates
    map_layers.append(pdk.Layer("PolygonLayer", data=vessels_df, get_polygon="polygon", get_fill_color="color", get_line_color="[255,255,255,100]", line_width_min_pixels=1, extruded=True, get_elevation="elevation", pickable=True, auto_highlight=True))
    map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame(path_data), get_path="path", get_color="color", width_min_pixels=2, pickable=False))

# ---------------------------------------------------------
# 8. RENDER THE INTERACTIVE SMART MAP & DEEP DIVES
# ---------------------------------------------------------
col_map, col_ops = st.columns([2.5, 1.5])

with col_map:
    st.markdown(f"<div style='border: 1px solid {border_color}; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>", unsafe_allow_html=True)
    r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=tooltip_config)
    st.pydeck_chart(r, use_container_width=True, height=600)
    st.markdown("</div>", unsafe_allow_html=True)

with col_ops:
    chat_tab, artifact_tab, sentinel_tab = st.tabs(["💬 Operator AI Chat", "📁 Action Artifacts", "🛡️ Sentinel Authorization"])
    
    with chat_tab:
        operator_role = st.selectbox("Active Profile:", ["USCG Watch Commander", "ESG Financial Auditor", "Logistics Fleet Director"], label_visibility="collapsed")
        alignment_prompt = "You are an AI advisor."
        if operator_role == "USCG Watch Commander": alignment_prompt = "You are a Coast Guard AI. Prioritize kinetic threats, intercept geometry, and maritime law enforcement."
        elif operator_role == "ESG Financial Auditor": alignment_prompt = "You are an ESG AI. Prioritize institutional capital risk, carbon registry validation, and compliance metrics."
        else: alignment_prompt = "You are a Logistics AI. Prioritize hydrodynamic drag, fuel optimization, and supply chain continuity."
        
        st.write("---")
        for msg in st.session_state.messages[-2:]:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
        if prompt := st.chat_input(f"Message AI..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                try:
                    full_prompt = f"{alignment_prompt} Context: {focus_mode}. Sector: {sector_mode}. Query: {prompt}"
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e: st.error("AI Comms Offline.")

    with artifact_tab:
        st.markdown("<p style='font-size:0.85rem; color:#a1a1aa;'>Generated 'Artifacts' (Action Reports, Memos, Ledgers) are persisted here for operational continuity.</p>", unsafe_allow_html=True)
        if st.button("Generate & Save New Artifact: Threat Profile", use_container_width=True):
            with st.spinner("Generating..."):
                try:
                    res = model.generate_content(f"{alignment_prompt} Generate a concise 3-bullet threat artifact for a vessel masking AIS in {sector_mode}.")
                    st.session_state.library.append({"type": "Threat Profile", "content": res.text, "time": pd.Timestamp.now().strftime('%H:%M:%SZ')})
                    st.success("Artifact saved to Library.")
                except: st.error("Failed to generate.")
        st.markdown("---")
        for idx, item in enumerate(reversed(st.session_state.library)):
            with st.expander(f"📄 {item['time']} | {item['type']}"):
                st.markdown(item['content'])

    with sentinel_tab:
        st.markdown("<p style='font-size:0.85rem; color:#a1a1aa;'>The Sentinel Layer isolates the AI from executing raw outbound web actions. Human authorization is required to bypass the Sentinel.</p>", unsafe_allow_html=True)
        action_req = "AUTHORIZE KINETIC INTERCEPT" if operator_role == "USCG Watch Commander" else "AUTHORIZE CARBON CREDIT MINTING"
        st.markdown(f"**Pending Agent Action:** `{action_req}`")
        st.markdown("**Sentinel Status:** <span style='color:#ef4444;'>BLOCKED (Awaiting Human-In-The-Loop)</span>", unsafe_allow_html=True)
        if st.button(f"🔑 BYPASS SENTINEL & EXECUTE", type="primary", use_container_width=True):
            with st.spinner("Sentinel verifying credentials..."):
                time.sleep(1.0)
                st.session_state.sentinel_logs.append(f"[{pd.Timestamp.now().strftime('%H:%M:%SZ')}] SENTINEL CLEARED. Action '{action_req}' executed by {operator_role}.")
                st.success("Action Executed Successfully.")
        st.markdown("---")
        for log in reversed(st.session_state.sentinel_logs):
            st.markdown(f"<div style='font-family: monospace; font-size: 0.75rem; color: #22c55e;'>{log}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 9. FINANCIAL LEDGERS & GENAI ROUTING (BOTTOM FULL WIDTH)
# ---------------------------------------------------------
st.write("---")
st.markdown("#### 📈 Enterprise Data Ledger & GenAI Routing")

ledger_tab, routing_tab, trend_tab = st.tabs(["💰 Scope 3 Financial Ledger", "🧭 GenAI Voyage Routing Engine", "📊 Historical Trend Analytics"])

with ledger_tab:
    ledger_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Length (m)", "Risk Status", "Cargo Value ($M)", "Fuel Saved (MT)"]]
    total_cargo = ledger_df["Cargo Value ($M)"].sum(); total_fuel = ledger_df["Fuel Saved (MT)"].sum()
    st.markdown(f"**Total Capital Protected:** ${total_cargo:,.1f} Million | **Total Scope 3 Averted:** {total_fuel * 3.11:,.1f} MT CO₂e | **Verified Carbon Value:** ${total_fuel * 3.11 * 75.00:,.2f}")
    st.dataframe(ledger_df.style.highlight_max(axis=0, subset=["Fuel Saved (MT)"], color=accent_green), use_container_width=True)

with routing_tab:
    st.markdown("<p class='hud-text'>Automated route optimization ensuring verifiable fuel/carbon reductions based on specific hull displacement.</p>", unsafe_allow_html=True)
    with st.form("routing_form"):
        vessel_opts = [f"{v['Vessel Name']} (MMSI: {v['MMSI']})" for v in live_vessels_data if v['Risk Status'] == "Nominal"]
        selected_vessel = st.selectbox("Select Asset to Reroute:", vessel_opts if vessel_opts else ["No Active Fleet"])
        port_col1, port_col2 = st.columns(2)
        with port_col1: origin_port = st.selectbox("Origin Port:", regional_ports)
        with port_col2: dest_port = st.selectbox("Destination Port:", reversed(regional_ports))
        
        if st.form_submit_button("Generate Predictive Voyage Plan", use_container_width=True):
            target_v = next((v for v in live_vessels_data if v['MMSI'] in selected_vessel), None)
            v_len = target_v['Length (m)'] if target_v else 300
            with st.spinner(f"GenAI calculating drag for {v_len}m vessel..."):
                try:
                    routing_prompt = f"You are a strategic marine logistics AI. A {v_len}m commercial vessel is transiting from {origin_port} to {dest_port}. Avoid 6.1m waves. Generate a concise 3-step rerouting plan. Estimate fuel saved."
                    res = model.generate_content(routing_prompt)
                    st.markdown(f"<div class='terminal'>{res.text}</div>", unsafe_allow_html=True)
                except Exception as e: st.error("AI Comms Offline.")

with trend_tab:
    st.markdown("<p class='hud-text'>Longitudinal decadal data analysis to justify capital intervention and ESG reporting.</p>", unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown("**10-Year Wave Height Extremes (Meters)**")
        years = pd.date_range("2016", "2026", freq="YE")
        st.line_chart(pd.DataFrame({"Max Wave Height (m)": [5.2, 5.4, 5.1, 5.8, 6.0, 5.9, 6.2, 6.5, 6.4, 6.8]}, index=years), color="#E11D48")
    with chart_col2:
        st.markdown("**IUU Fishing / Dark Fleet Suspicions (Incidents)**")
        st.bar_chart(pd.DataFrame({"Dark Fleet Incidents": [12, 14, 18, 15, 22, 28, 35, 41, 44, 52]}, index=years), color="#0284c7")
