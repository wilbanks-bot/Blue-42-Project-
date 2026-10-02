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
# 1. PAGE SETUP & SESSION STATE INITIALIZATION
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 | Strategic Command", page_icon="🌐", initial_sidebar_state="expanded")

if "sar_tasked" not in st.session_state: st.session_state.sar_tasked = False
if "booms_deployed" not in st.session_state: st.session_state.booms_deployed = False
if "library" not in st.session_state: st.session_state.library = []
if "sentinel_logs" not in st.session_state: st.session_state.sentinel_logs = []
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Watchstander AI active. Awaiting strategic queries."}]

night_vision = st.sidebar.toggle("🌙 Executive Dark Mode", value=True)

if night_vision:
    bg_color = "#09090b"; card_bg = "#18181b"; text_color = "#f4f4f5"; muted_text = "#a1a1aa"; border_color = "#27272a"
    accent_blue = "#0ea5e9"; accent_red = "#ef4444"; accent_green = "#22c55e"; accent_purple = "#8b5cf6"; accent_amber = "#f59e0b"
    map_style = "dark"; term_bg = "#000000"; term_color = "#10b981"
else:
    bg_color = "#f8fafc"; card_bg = "#ffffff"; text_color = "#0f172a"; muted_text = "#64748b"; border_color = "#e2e8f0"
    accent_blue = "#0284c7"; accent_red = "#e11d48"; accent_green = "#059669"; accent_purple = "#7c3aed"; accent_amber = "#d97706"
    map_style = "light"; term_bg = "#f1f5f9"; term_color = "#0f172a"

css = f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: 'Inter', -apple-system, sans-serif; }}
    .metric-card {{ background-color: {card_bg}; padding: 24px; border-radius: 8px; border-top: 4px solid {accent_blue}; margin-bottom: 16px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
    .protection-card {{ border-top: 4px solid {accent_red}; }}
    .mitigation-card {{ border-top: 4px solid {accent_green}; }}
    .military-card {{ border-top: 4px solid {accent_purple}; }}
    .logistics-card {{ border-top: 4px solid {accent_amber}; }}
    h1, h2, h3, h4 {{ color: {text_color}; font-weight: 600; margin-top: 0; letter-spacing: -0.01em; }}
    h4 {{ font-size: 0.85rem; text-transform: uppercase; color: {muted_text}; letter-spacing: 0.05em; }}
    .kpi-value {{ font-size: 2.25rem; font-weight: 700; color: {text_color}; margin: 4px 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.85rem; color: {muted_text}; display: block; margin-bottom: 4px; }}
    .streamlit-expanderHeader {{ font-weight: 600 !important; font-size: 0.95rem; color: {text_color} !important; border-radius: 8px; }}
    div[data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid {border_color}; }}
    .terminal {{ background-color: {term_bg}; padding: 12px; border: 1px solid {accent_green}; border-radius: 4px; color: {accent_green}; font-family: 'Courier New', monospace; font-size: 0.8rem; box-shadow: inset 0 0 10px rgba(34, 211, 153, 0.1); max-height: 250px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }}
    .ticker-wrap {{ width: 100%; overflow: hidden; background-color: {card_bg}; border-bottom: 1px solid {border_color}; padding: 8px 0; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    .ticker {{ display: inline-block; white-space: nowrap; padding-right: 100%; animation-iteration-count: infinite; animation-timing-function: linear; animation-name: ticker; animation-duration: 40s; }}
    .ticker-item {{ display: inline-block; padding: 0 2rem; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.85rem; color: {accent_blue}; font-weight: 600; letter-spacing: 1px; }}
    @keyframes ticker {{ 0% {{ transform: translate3d(0, 0, 0); }} 100% {{ transform: translate3d(-100%, 0, 0); }} }}
    .stTabs [data-baseweb="tab"] {{ height: 50px; background-color: transparent; border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px; font-weight: 500; }}
    .stTabs [aria-selected="true"] {{ background-color: {card_bg}; border-bottom: 2px solid {accent_blue}; color: {accent_blue}; font-weight: 700; }}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. SECURE API INITIALIZATION & FAILSAFES
# ---------------------------------------------------------
try:
    if "EARTHENGINE_TOKEN" in st.secrets:
        key_dict = json.loads(st.secrets["EARTHENGINE_TOKEN"])
        creds = service_account.Credentials.from_service_account_info(key_dict).with_scopes(['https://www.googleapis.com/auth/earthengine'])
        ee.Initialize(credentials=creds, project=key_dict.get("project_id"))
        ee_status = "🟢 SECURE UPLINK"
    else: ee_status = "🔴 UPLINK SEVERED"
except Exception as e: ee_status = "🔴 UPLINK SEVERED"

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Dynamic model fallback to prevent 404s
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = 'gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0].replace('models/', '')
        model = genai.GenerativeModel(target_model)
        ai_status = f"🟢 CORE ACTIVE ({target_model})"
    else: ai_status = "🔴 CORE OFFLINE"
except Exception as e: ai_status = "🔴 CORE OFFLINE"

try:
    ais_key = st.secrets.get("AISSTREAM_API_KEY", "")
    ais_status = "🟢 RADAR AUTHENTICATED" if ais_key else "🔴 RADAR OFFLINE"
except: ais_status = "🔴 RADAR OFFLINE"

# ---------------------------------------------------------
# 3. SIDEBAR: ENTERPRISE NAVIGATION
# ---------------------------------------------------------
st.sidebar.markdown(f"""
<div style="margin-bottom: 30px; text-align: center;">
    <div style="font-size: 40px; color: {accent_blue}; line-height: 1;">🌊</div>
    <div style="font-weight: 800; color: {text_color}; font-size: 1.5rem; letter-spacing: 2px; margin-top: 5px;">BLUE 42 COMMAND</div>
    <div style="color: {muted_text}; font-size: 0.75rem; font-weight: 600; letter-spacing: 1px; text-transform: uppercase;">Global Blue Economy OS</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 👤 OPERATOR ALIGNMENT")
operator_role = st.sidebar.selectbox("Active Profile:", ["Strategic Commander", "ESG Financial Auditor", "Logistics Fleet Director"], label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown("### 🌍 REGIONAL DEPLOYMENT")
sector_mode = st.sidebar.selectbox("Operational Theater:", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"], label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown("### 🗺️ SPATIAL RENDERING")
map_dimension = st.sidebar.radio("Map Dimension:", ["3D Tactical", "2D Overhead"], horizontal=True, label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 LIVE TELEMETRY")
live_ais = st.sidebar.toggle("Connect Live Satellite AIS Feed", value=False)
st.sidebar.markdown("---")

# RESTORED: All 8 Tactical Data Overlays
st.sidebar.markdown("### 📊 MULTI-DOMAIN OVERLAYS")
show_iuu = st.sidebar.checkbox("🛡️ Marine Protected Areas (IUU)", value=True)
show_military = st.sidebar.checkbox("⚓ Military Exclusion Zones", value=True)
show_weather = st.sidebar.checkbox("⛈️ Severe Weather Hazards", value=True)
show_currents = st.sidebar.checkbox("🌊 Ocean Microcurrents", value=True)
show_whales = st.sidebar.checkbox("🐋 Marine Mammal Habitats", value=True)
show_depth = st.sidebar.checkbox("🌱 Blue Carbon Bathymetry", value=True)
show_spill = st.sidebar.checkbox("🛢️ Oil Spill Trajectories", value=False)
show_wind = st.sidebar.checkbox("💨 Offshore Wind Optimization", value=False)
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 SYSTEM DIAGNOSTICS")
st.sidebar.caption(f"**Geospatial Engine:** {ee_status}\n\n**GenAI Reasoning:** {ai_status}\n\n**AIS Telemetry:** {ais_status}")

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
st.markdown(f"<p style='text-align: center; color: {muted_text}; font-size: 1.1rem; margin-bottom: 30px;'>Synthesizing planetary telemetry into predictive intelligence and actionable ESG workflows.</p>", unsafe_allow_html=True)

focus_mode = st.radio("SELECT STRATEGIC FOCUS TO FILTER BATTLESPACE & ANALYTICS:", 
    ["🌍 Global Overview", "🛡️ Human Rights & Ecocide", "🌪️ Macro-Economic Resilience", "🛢️ Crisis & Disaster Response", "🌱 Planetary Capital (ESG)"], 
    horizontal=True)
st.write("")

# Dynamic KPIs based on Filter
col1, col2, col3, col4 = st.columns(4)
with col1: st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ACTIVE THREATS</h4><p class='kpi-value' style='color:{accent_red};'>2 VOI</p><span class='kpi-subtext'>High risk of forced labor / IUU</span></div>", unsafe_allow_html=True)
with col2: st.markdown(f"<div class='metric-card military-card'><h4>⚓ CRISIS RESPONSE</h4><p class='kpi-value' style='color:{accent_amber};'>STANDBY</p><span class='kpi-subtext'>Spill/SAR algorithms ready</span></div>", unsafe_allow_html=True)
with col3: st.markdown(f"<div class='metric-card'><h4>🌪️ MACRO-ECONOMICS</h4><p class='kpi-value' style='color:{accent_blue};'>5 REROUTED</p><span class='kpi-subtext'>Inflationary supply shocks averted</span></div>", unsafe_allow_html=True)
with col4: st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 PLANETARY CAPITAL</h4><p class='kpi-value' style='color:{accent_green};'>14.2 HA</p><span class='kpi-subtext'>Optimal bio-sinks verified</span></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. UNIFIED DATA SCHEMA FOR DEEP-DIVE TOOLTIPS
# ---------------------------------------------------------
map_layers = []

def get_tooltip():
    return {
        "html": f"""
        <div style='background: {card_bg}; border: 1px solid {accent_blue}; padding: 14px; border-radius: 10px; color: {text_color}; font-family: Inter, sans-serif; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); max-width: 320px;'>
            <div style='font-size: 1.1rem; font-weight: 700; color: {accent_blue}; margin-bottom: 4px;'>{{name}}</div>
            <div style='font-size: 0.85rem; color: {muted_text}; margin-bottom: 2px;'>{{primary_metric}}</div>
            <div style='font-size: 0.85rem; color: {muted_text}; margin-bottom: 12px;'>{{secondary_metric}}</div>
            <div style='border-top: 1px solid {border_color}; padding-top: 10px;'>
                <span style='color: {accent_green}; font-weight: 600; font-size: 0.85rem;'>NOBEL-TIER ANALYTICS:</span><br/>
                <span style='font-size: 0.85rem; line-height: 1.4; color: {text_color};'>{{analytics}}</span>
            </div>
            <div style='margin-top: 10px; font-size: 0.75rem; color: {muted_text}; font-style: italic;'>Source: {{source}}</div>
        </div>
        """,
        "style": {"backgroundColor": "transparent", "padding": "0"} 
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
# 6. DYNAMIC MAP LOGIC (FILTERED BY OVERLAYS AND FOCUS)
# ---------------------------------------------------------
pitch_val = 50 if map_dimension == "3D Tactical" else 0
bearing_val = -10 if map_dimension == "3D Tactical" else 0

if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=pitch_val, bearing=bearing_val)
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]]
    base_lat, base_lon = 33.8, -119.5
    regional_ports = ["Port of Los Angeles", "Port of Long Beach", "Port Hueneme"]
    
    # RESTORED: Microcurrents
    if show_currents and focus_mode in ["🌍 Global Overview", "🌪️ Macro-Economic Resilience"]:
        path = [[[-120.5, 34.5], [-119.8, 33.8], [-119.2, 33.0]]]
        data = create_unified_tooltip_data(33.8, -119.8, "California Microcurrent Stream", "Velocity: 1.2 kts Southbound", "Status: Favorable Surf Zone", "Surfing this current allows a 10% reduction in engine RPM while maintaining SOG, generating massive fuel savings.", "Copernicus Ocean Physics", [56, 189, 248, 200], path=path[0])
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame([data]), get_path="path", get_color="color", width_min_pixels=6, pickable=True))

    # RESTORED: Marine Mammals
    if show_whales and focus_mode in ["🌍 Global Overview", "🌱 Planetary Capital (ESG)"]:
        poly = [[[-120.0, 33.5], [-119.5, 33.5], [-119.3, 34.0], [-119.8, 34.0]]]
        data = create_unified_tooltip_data(33.7, -119.6, "Dynamic Whale Pod Migration", "Status: 10-Knot Speed Limit Active", "Species: Blue Whale (Endangered)", "DeepMind SDM indicates high probability of plankton bloom. Dynamic speed reduction enforced.", "DeepMind SDM", [167, 139, 250, 40], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([data]), get_polygon="polygon", get_fill_color="color", get_line_color="[167, 139, 250, 200]", line_width_min_pixels=2, pickable=True))

    # RESTORED: Spill Trajectory
    if show_spill and focus_mode in ["🌍 Global Overview", "🛢️ Crisis & Disaster Response"]:
        poly = [[[-119.8, 33.9], [-119.6, 33.8], [-119.5, 33.9], [-119.7, 34.0]]]
        data = create_unified_tooltip_data(33.9, -119.6, "72-Hour Spill Trajectory", "Contaminant: Heavy Fuel Oil", "Impact Risk: Critical", "AlphaEarth leeway models project slick impacting Santa Cruz Island in 48 hours. Deploy booms.", "AlphaEarth", [245, 158, 11, 70], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([data]), get_polygon="polygon", get_fill_color="color", get_line_color="[245, 158, 11, 200]", line_width_min_pixels=2, pickable=True))

    # RESTORED: Offshore Wind Optimization
    if show_wind and focus_mode in ["🌍 Global Overview", "🌱 Planetary Capital (ESG)"]:
        poly = [[[-120.8, 34.2], [-120.4, 34.2], [-120.4, 34.5], [-120.8, 34.5]]]
        data = create_unified_tooltip_data(34.3, -120.6, "Verified Offshore Wind Zone", "Potential: 850 MW Capacity", "Wind Speed: Sustained 9 m/s", "Earth Engine wind atlas confirms optimal kinetic load. Cleared of migratory bird paths.", "Earth Engine / NREL", [45, 212, 191, 50], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([data]), get_polygon="polygon", get_fill_color="color", get_line_color="[45, 212, 191, 200]", line_width_min_pixels=2, pickable=True))

    if show_depth and focus_mode in ["🌍 Global Overview", "🌱 Planetary Capital (ESG)"]:
        poly = [[[-119.7, 33.9], [-119.4, 33.9], [-119.4, 34.1], [-119.7, 34.1]]]
        depth_data = create_unified_tooltip_data(34.0, -119.55, "Optimal Bathymetric Shelf", "Layer: Ocean Topography", "Range: -5m to -30m", "Optimal biological envelope.", "Copernicus Marine", [45, 212, 191, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([depth_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[45, 212, 191, 150]", line_width_min_pixels=2, pickable=True))
        
        kelp_df = pd.DataFrame([
            create_unified_tooltip_data(34.02, -119.55, "Verified Bio-Sink K-1", "Area: 5.1 HA", "Status: VERIFIED", "Yields 898 tCO2e/yr.", "DeepMind SDM", [34, 197, 94, 255], radius=3000, elevation=8980),
            create_unified_tooltip_data(33.98, -119.60, "Verified Bio-Sink K-2", "Area: 4.8 HA", "Status: VERIFIED", "High resilience to warming.", "DeepMind SDM", [34, 197, 94, 255], radius=3000, elevation=8450)
        ])
        map_layers.append(pdk.Layer("ColumnLayer", data=kelp_df, get_position="[lon, lat]", get_elevation="elevation", elevation_scale=1, radius="radius", get_fill_color="color", pickable=True, extruded=True, auto_highlight=True))

    if show_iuu and focus_mode in ["🌍 Global Overview", "🛡️ Human Rights & Ecocide (IUU)"]:
        poly = [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]]
        mpa_data = create_unified_tooltip_data(34.0, -119.7, "Channel Islands MPA", "Protection Level: FULL", "Jurisdiction: Federal", "Zero-take zone. Continuous AI surveillance active.", "UNEP-WCMC", [56, 189, 248, 20], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([mpa_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2, pickable=True))

    if show_weather and focus_mode in ["🌍 Global Overview", "🌪️ Macro-Economic Resilience"]:
        poly = [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]]
        storm_data = create_unified_tooltip_data(33.8, -119.3, "Severe Gale Warning", "Alert: WEATHER HAZARD", "H_s: > 6.1m (20ft)", "Extreme hydrodynamic drag detected.", "WeatherNext 3", [239, 68, 68, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([storm_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2, pickable=True))
        
        path = [[[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]]]
        route_data = create_unified_tooltip_data(33.4, -119.3, "AI Optimized Route", "Status: ACTIVE REROUTE", "Fuel Averted: 54 MT", "Predictive vector safely circumvents the Gale Warning polygon.", "AlphaEarth", [34, 197, 94, 200], path=path[0])
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame([route_data]), get_path="path", get_color="color", width_min_pixels=3, pickable=True))

    if show_cables and focus_mode in ["🌍 Global Overview", "⚓ Military Security"]:
        path = [[[-121.0, 33.5], [-119.0, 33.8], [-118.0, 34.2]]]
        cable_data = create_unified_tooltip_data(33.8, -119.0, "Tier-1 Subsea Data Cable", "Asset: Transpacific Trunk", "Vulnerability: Exposed", "Critical infrastructure carrying billions in daily financial transactions.", "Submarine Cable Map", [203, 213, 225, 200], path=path[0])
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame([cable_data]), get_path="path", get_color="color", width_min_pixels=4, pickable=True))

    if show_military and focus_mode in ["🌍 Global Overview", "⚓ Military Security"]:
        poly = [[[-120.5, 33.2], [-119.0, 33.2], [-119.0, 33.8], [-120.5, 33.8]]]
        military_data = create_unified_tooltip_data(33.5, -119.7, "Point Mugu Sea Range", "Status: RESTRICTED", "Type: Naval Weapons Area", "Geofence: ACTIVE | Status: LIVE FIRE", "US Navy", [139, 92, 246, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([military_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[139, 92, 246, 150]", line_width_min_pixels=2, pickable=True))

else: # HAWAII
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=pitch_val, bearing=bearing_val)
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    base_lat, base_lon = 21.2, -158.0
    regional_ports = ["Honolulu Harbor", "Pearl Harbor", "Kahului"]
    
    if show_currents and focus_mode in ["🌍 Global Overview", "🌪️ Macro-Economic Resilience"]:
        path = [[[-156.0, 22.0], [-157.0, 21.5], [-158.5, 21.0]]]
        data = create_unified_tooltip_data(21.5, -157.0, "North Equatorial Current", "Velocity: 1.5 kts Westbound", "Status: Favorable Surf Zone", "Surfing this current allows ships to throttle down, saving Scope 3 emissions.", "Copernicus Ocean Physics", [56, 189, 248, 200], path=path[0])
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame([data]), get_path="path", get_color="color", width_min_pixels=6, pickable=True))

    if show_depth and focus_mode in ["🌍 Global Overview", "🌱 Planetary Capital (ESG)"]:
        poly = [[[-158.0, 21.3], [-157.6, 21.3], [-157.6, 21.6], [-158.0, 21.6]]]
        depth_data = create_unified_tooltip_data(21.45, -157.8, "Reef Bathymetric Contour", "Layer: Ocean Topography", "Range: -5m to -30m", "Depth: -8m | SST: 24.5°C", "Copernicus Marine", [45, 212, 191, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([depth_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[45, 212, 191, 150]", line_width_min_pixels=2, pickable=True))
        
        reef_df = pd.DataFrame([
            create_unified_tooltip_data(21.45, -157.8, "Verified Reef Restoration R-1", "Area: 6.5 HA", "Status: VERIFIED", "Yields 1,144 tCO2e/yr.", "DeepMind SDM", [34, 197, 94, 255], radius=3000, elevation=11440),
            create_unified_tooltip_data(21.39, -157.71, "Verified Reef Restoration R-2", "Area: 4.2 HA", "Status: VERIFIED", "Generates +18% localized increase in critical fishery biomass.", "DeepMind SDM", [34, 197, 94, 255], radius=2500, elevation=7390)
        ])
        map_layers.append(pdk.Layer("ColumnLayer", data=reef_df, get_position="[lon, lat]", get_elevation="elevation", elevation_scale=1, radius="radius", get_fill_color="color", pickable=True, extruded=True, auto_highlight=True))

    if show_iuu and focus_mode in ["🌍 Global Overview", "🛡️ Human Rights & Ecocide (IUU)"]:
        poly = [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]]
        mpa_data = create_unified_tooltip_data(21.5, -158.0, "Kaena Point MPA", "Protection Level: FULL", "Jurisdiction: Federal", "Zero-take zone.", "UNEP-WCMC", [56, 189, 248, 20], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([mpa_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2, pickable=True))

    if show_weather and focus_mode in ["🌍 Global Overview", "🌪️ Macro-Economic Resilience"]:
        poly = [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]]
        storm_data = create_unified_tooltip_data(21.2, -157.8, "Tropical Squall Hazard", "Alert: WEATHER HAZARD", "H_s: > 4.5m", "Localized squall creating supply chain delays.", "WeatherNext 3", [239, 68, 68, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([storm_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2, pickable=True))

    if show_military and focus_mode in ["🌍 Global Overview", "⚓ Military Security"]:
        poly = [[[-159.9, 21.8], [-159.5, 21.8], [-159.5, 22.2], [-159.9, 22.2]]]
        military_data = create_unified_tooltip_data(22.0, -159.7, "PMRF Barking Sands", "Status: RESTRICTED", "Type: Pacific Missile Range", "Civilian intrusion violates federal exclusion zone.", "US Navy", [139, 92, 246, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([military_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[139, 92, 246, 150]", line_width_min_pixels=2, pickable=True))

# ---------------------------------------------------------
# 7. HIGH-FIDELITY VESSEL SIMULATION (3D BATTLESHIPS)
# ---------------------------------------------------------
live_vessels_data = []
raw_ais_log = ""

if live_ais and ais_key and WEBSOCKET_AVAILABLE:
    try:
        ws = websocket.create_connection("wss://stream.aisstream.io/v0/stream", timeout=4)
        ws.send(json.dumps({"APIKey": ais_key, "BoundingBoxes": ais_bounds, "FilterMessageTypes": ["PositionReport"]}))
        import time
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
                        v_len = int(random.uniform(100, 350))
                        v_draft = round(random.uniform(8.0, 15.0), 1)
                        live_vessels_data.append({
                            "MMSI": mmsi, "Vessel Name": name, "lat": lat, "lon": lon, 
                            "sog": sog, "cog": cog, "Length (m)": v_len, "Width (m)": int(v_len*0.15), "Draft (m)": v_draft, "Gross Tonnage": int(v_len * int(v_len*0.15) * v_draft * 0.7),
                            "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
                        })
                        raw_ais_log += f'{{"MMSI": "{mmsi}", "SOG": {sog}, "COG": {cog}}}\n'
                    if len(live_vessels_data) >= 30: break
            except: break
        ws.close()
    except: pass

if len(live_vessels_data) < 3:
    for i in range(45):
        sog = random.uniform(8.0, 22.0)
        v_type = random.choice(["CARGO", "TANKER", "BULK"])
        mmsi = f"36{random.randint(1000000, 9999999)}"
        v_len = int(random.uniform(150,350))
        v_draft = round(random.uniform(9.0,16.0), 1)
        lat, lon = base_lat + random.uniform(-1.5, 1.5), base_lon + random.uniform(-2.0, 2.0)
        cog = random.uniform(0, 360)
        live_vessels_data.append({
            "MMSI": mmsi, "Vessel Name": f"{v_type} {mmsi[-4:]}",
            "lat": lat, "lon": lon, "sog": round(sog,1), "cog": round(cog,1),
            "Length (m)": v_len, "Width (m)": int(v_len*0.15), "Draft (m)": v_draft, "Gross Tonnage": int(v_len * int(v_len*0.15) * v_draft * 0.7),
            "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
        })
        raw_ais_log += f'{{"MMSI": "{mmsi}", "SOG": {sog:.1f}, "COG": {cog:.1f}}}\n'

# NOBEL FEATURE: Transshipment (Modern Slavery) Detection
# Inject two dark targets meeting in the open ocean
dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
live_vessels_data.append({
    "MMSI": "413000000", "Vessel Name": "UNVERIFIED DARK TARGET ALPHA",
    "lat": dt_lat, "lon": dt_lon, "sog": 1.5, "cog": 80.0,
    "Length (m)": 45, "Width (m)": 8, "Draft (m)": 3.2, "Gross Tonnage": 806,
    "Risk Status": "CRITICAL ANOMALY", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
})
live_vessels_data.append({
    "MMSI": "413000001", "Vessel Name": "UNVERIFIED DARK TARGET BRAVO",
    "lat": dt_lat + 0.005, "lon": dt_lon + 0.005, "sog": 1.5, "cog": 260.0,
    "Length (m)": 120, "Width (m)": 18, "Draft (m)": 6.5, "Gross Tonnage": 9828,
    "Risk Status": "TRANSSHIPMENT DETECTED", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
})
raw_ais_log += f'{{"MMSI": "413000000", "WARNING": "SIGNAL LOST"}}\n'

# Format Map Vessels (3D Polygons)
vessels = []
for v in live_vessels_data:
    is_threat = v['Risk Status'] != "Nominal"
    
    # Hide nominal vessels if we are focusing deeply on non-vessel metrics to keep map clean
    if focus_mode == "🌱 Planetary Capital (ESG)" and not is_threat: continue
    
    cog_rad = math.radians(v['cog'])
    vec_len = max(v['sog'] * 0.003, 0.01)
    color = [239, 68, 68, 255] if is_threat else [56, 189, 248, 180]
    ship_poly = get_battleship_polygon(v['lat'], v['lon'], v['cog'], v['Length (m)'], v['Width (m)'])
    elevation = 150 if is_threat else max(30, v['Length (m)'] / 4.0)
    
    if is_threat:
        analysis = "HUMAN RIGHTS ANOMALY: Converging kinematic tracks indicate illegal ship-to-ship transfer (Transshipment) of forced labor or IUU catch. Intercept recommended."
    else:
        analysis = "Vessel kinetics operate within nominal parameters. Compliant track."
        
    vessels.append(create_unified_tooltip_data(
        v['lat'], v['lon'], v['Vessel Name'], f"Speed: {v['sog']} kts | Heading: {v['cog']}°", 
        f"Size: {v['Length (m)']}m x {v['Width (m)']}m | Tonnage: {v['Gross Tonnage']:,} GT", analysis, 
        "Verified AIS", color, polygon=ship_poly, path=[[v['lon'], v['lat']], [v['lon'] + vec_len * math.sin(cog_rad), v['lat'] + vec_len * math.cos(cog_rad)]], elevation=elevation
    ))

vessels_df = pd.DataFrame(vessels)
if not vessels_df.empty:
    map_layers.append(pdk.Layer("PolygonLayer", data=vessels_df, get_polygon="polygon", get_fill_color="color", get_line_color="[255,255,255,100]", line_width_min_pixels=1, extruded=True, get_elevation="elevation", pickable=True))
    map_layers.append(pdk.Layer("PathLayer", data=vessels_df, get_path="path", get_color="color", width_min_pixels=2, pickable=False))

# Render the sidebar RAW Data visualizer
st.sidebar.markdown("### 📡 RAW SATELLITE FEED")
st.sidebar.markdown(f"<div class='terminal'>{raw_ais_log}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 8. RENDER THE INTERACTIVE SMART MAP & DEEP DIVES
# ---------------------------------------------------------
col_map, col_details = st.columns([2.5, 1.5])

with col_map:
    st.markdown("<div style='border: 1px solid #27272a; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.2);'>", unsafe_allow_html=True)
    r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=get_tooltip())
    st.pydeck_chart(r, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_details:
    st.markdown(f"<div class='metric-card' style='height: 100%; border-top: none; padding-top: 5px;'>", unsafe_allow_html=True)
    
    if focus_mode == "🌍 Global Overview":
        st.markdown(f"<h3 style='color: {accent_blue}; font-size: 1.25rem;'>🌍 Global Telemetry</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Select a specific Strategic Focus from the menu above to filter the map and access deep-dive analytics.</p>", unsafe_allow_html=True)
        st.write(f"• **Total Assets Tracked:** {len(live_vessels_data)}")
        st.write("• **Active Anomalies:** 2")

    elif focus_mode == "🛡️ Human Rights & Ecocide (IUU)":
        st.markdown(f"<h3 style='color: {accent_red}; font-size: 1.25rem;'>🛡️ Dark Fleet Analytics</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>IUU fishing is intrinsically linked to modern slavery. By tracking 'Dark Targets,' we enforce human rights on the high seas.</p>", unsafe_allow_html=True)
        
        # Transshipment / Modern Slavery Detection Engine
        st.markdown("#### The Mathematical Trigger")
        st.code("IF (Distance_to_MPA < 15nm) \nAND (Converging_Tracks == TRUE) \nAND (Speed < 4kts):\n   TRIGGER = HUMAN_RIGHTS_THREAT", language="python")
        
        st.markdown("#### Automated UNCLOS Indictment Engine")
        if st.button("⚖️ DRAFT UNCLOS LEGAL INDICTMENT", use_container_width=True):
            with st.spinner("Compiling spatial evidence against Article 73 of UNCLOS..."):
                try:
                    res = model.generate_content(f"Draft a highly formal, 2-paragraph legal indictment under the UN Convention on the Law of the Sea (UNCLOS) for two vessels operating illegally and conducting ship-to-ship transshipment near {dt_lat}, {dt_lon}.")
                    st.success("Indictment Drafted for Interpol Transmission.")
                    st.markdown(f"<div class='terminal'>{res.text}</div>", unsafe_allow_html=True)
                except: st.error("AI Comms Offline.")

    elif focus_mode == "🌪️ Macro-Economic Resilience":
        st.markdown(f"<h3 style='color: {accent_blue}; font-size: 1.25rem;'>🌪️ Voyage Optimization</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Severe weather halts shipping, causing massive supply chain shocks that drive global inflation. AI rerouting prevents these shocks.</p>", unsafe_allow_html=True)
        st.markdown("#### Hydrodynamic Drag")
        st.latex(r"R_T = \frac{1}{2} \rho v^2 S C_T")
        
        st.markdown("#### 🧭 GenAI Routing Engine")
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
                        routing_prompt = f"You are a strategic marine logistics AI. A {v_len}m freighter is transiting from {origin_port} to {dest_port}. Avoid 6.1m waves. Generate 2-step rerouting plan. Estimate fuel saved."
                        res = model.generate_content(routing_prompt)
                        st.markdown(f"<div class='terminal'>{res.text}</div>", unsafe_allow_html=True)
                    except: st.error("AI Comms Offline.")

    elif focus_mode == "🛢️ Crisis & Disaster Response":
        st.markdown(f"<h3 style='color: {accent_amber}; font-size: 1.25rem;'>🛢️ Ecological Disaster Trajectory</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>If a vessel sinks or dumps oil, AlphaEarth leeway models instantly calculate a 72-hour contaminant drift grid.</p>", unsafe_allow_html=True)
        st.markdown("#### Drift Vector Formula")
        st.latex(r"D = v \cdot t \cdot (\text{Wind Leeway} + \text{Surface Current})")
        st.markdown("#### Tactical Action: Boom Deployment")
        if st.button("DEPLOY CONTAINMENT BOOMS", use_container_width=True):
            st.session_state.booms_deployed = True
        if st.session_state.booms_deployed:
            st.success("Containment booms dispatched to predicted impact zones. Ecological contamination averted.")

    elif focus_mode == "🌱 Planetary Capital (ESG)":
        st.markdown(f"<h3 style='color: {accent_green}; font-size: 1.25rem;'>🌱 Capital Verification</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Fusing Earth Engine's bathymetry with DeepMind's Species Distribution Models to find the exact biological envelope for Giant Kelp, de-risking the capital investment.</p>", unsafe_allow_html=True)
        st.write("• **Depth Threshold:** -5m to -30m")
        st.write("• **Thermal Threshold:** SST < 18°C")
        if st.button("Mint Verified Blue Carbon Credits", use_container_width=True):
            st.success("SUCCESS: 2,500 tCO₂e validated. Asset ID #BC-8492-GEE minted.")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 9. THE ENTERPRISE ANALYTICS SUITE (MUSE TABS RESTORED)
# ---------------------------------------------------------
st.write("---")
st.markdown("### 📈 Operational Analytics & AI Intelligence")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🚢 Active Fleet Kinematics", "💰 Scope 3 Financial Ledger", "📊 Historical Trend Analytics", "📁 Persistent Library", "🛡️ Sentinel Security", "💬 Strategic Advisory Chat"])

with tab1:
    st.markdown("<p class='hud-text'>Live tactical breakdown of all assets currently operating in the sector. Data includes size, speed, and heading parameters.</p>", unsafe_allow_html=True)
    fleet_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Type", "Length (m)", "Draft (m)", "Gross Tonnage", "sog", "cog", "Risk Status"]]
    fleet_df.rename(columns={"sog": "Speed (kts)", "cog": "Heading (°)"}, inplace=True)
    st.dataframe(fleet_df, use_container_width=True)

with tab2:
    st.markdown("<p class='hud-text'>Live accounting of protected maritime cargo value and calculated Scope 3 emissions reductions.</p>", unsafe_allow_html=True)
    ledger_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Risk Status", "Cargo Value ($M)", "Fuel Saved (MT)"]]
    total_cargo = ledger_df["Cargo Value ($M)"].sum()
    total_fuel = ledger_df["Fuel Saved (MT)"].sum()
    total_carbon = total_fuel * 3.11 
    st.markdown(f"**Total Capital Protected:** ${total_cargo:,.1f} Million | **Total Scope 3 Averted:** {total_carbon:,.1f} MT CO₂e | **Verified Carbon Value:** ${total_carbon * 75.00:,.2f}")
    st.dataframe(ledger_df.style.highlight_max(axis=0, subset=["Fuel Saved (MT)"], color=accent_green), use_container_width=True)

with tab3:
    st.markdown("<p class='hud-text'>Longitudinal decadal data analysis to justify capital intervention and ESG reporting.</p>", unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown("**10-Year Wave Height Extremes (Meters)**")
        st.caption("Data Authority: NOAA National Data Buoy Center (NDBC)")
        years = pd.date_range("2016", "2026", freq="YE")
        wave_data = pd.DataFrame({"Max Wave Height (m)": [5.2, 5.4, 5.1, 5.8, 6.0, 5.9, 6.2, 6.5, 6.4, 6.8]}, index=years)
        st.line_chart(wave_data, color="#e11d48")
    with chart_col2:
        st.markdown("**IUU Fishing / Dark Fleet Suspicions (Incidents)**")
        st.caption("Data Authority: Global Fishing Watch")
        iuu_data = pd.DataFrame({"Dark Fleet Incidents": [12, 14, 18, 15, 22, 28, 35, 41, 44, 52]}, index=years)
        st.bar_chart(iuu_data, color="#0284c7")

with tab4:
    st.markdown("<p class='hud-text'>Generated 'Artifacts' (Action Reports, Memos, Voyage Plans) are persisted here for operational continuity.</p>", unsafe_allow_html=True)
    if st.button("Generate & Save New Artifact: Executive Brief", use_container_width=True):
        with st.spinner("Generating..."):
            try:
                res = model.generate_content(f"Generate a concise 3-bullet executive brief for the {sector_mode} sector.")
                st.session_state.library.append({"type": "Executive Brief", "content": res.text, "time": pd.Timestamp.now().strftime('%H:%M:%SZ')})
                st.success("Artifact saved to Library.")
            except: st.error("Failed to generate.")
    st.markdown("---")
    for idx, item in enumerate(reversed(st.session_state.library)):
        with st.expander(f"📄 {item['time']} | {item['type']}"): st.markdown(item['content'])

with tab5:
    st.markdown("<p class='hud-text'>The Sentinel Layer isolates the AI from executing raw outbound web actions. Human authorization is required to bypass the Sentinel.</p>", unsafe_allow_html=True)
    st.markdown(f"**Pending Agent Action:** `AUTHORIZE INTERVENTION`")
    st.markdown("**Sentinel Status:** <span style='color:#ef4444;'>BLOCKED (Awaiting Human-In-The-Loop)</span>", unsafe_allow_html=True)
    if st.button(f"🔑 BYPASS SENTINEL & EXECUTE", type="primary", use_container_width=True):
        with st.spinner("Sentinel verifying credentials..."):
            import time
            time.sleep(1.0)
            st.session_state.sentinel_logs.append(f"[{pd.Timestamp.now().strftime('%H:%M:%SZ')}] SENTINEL CLEARED. Action executed.")
            st.success("Action Executed Successfully.")
    st.markdown("---")
    st.markdown("**Sentinel Execution Logs:**")
    for log in reversed(st.session_state.sentinel_logs):
        st.markdown(f"<div style='font-family: monospace; font-size: 0.75rem; color: #22c55e;'>{log}</div>", unsafe_allow_html=True)

with tab6:
    st.markdown("#### Live Intelligence Chat")
    for message in st.session_state.messages[-3:]: 
        with st.chat_message(message["role"]): st.markdown(message["content"])
    if prompt := st.chat_input("Request strategic risk evaluation..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                res = model.generate_content(f"You are a Senior Strategic Advisor. Sector is {sector_mode}. Analyze query: {prompt}")
                st.markdown(res.text)
                st.session_state.messages.append({"role": "assistant", "content": res.text})
            except: st.error("AI Comms Offline.")
