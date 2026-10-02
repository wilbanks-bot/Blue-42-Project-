import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import json
import ee
import math
import random
from google.oauth2 import service_account
import google.generativeai as genai

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# ---------------------------------------------------------
# 1. PAGE SETUP & MATTE ENTERPRISE THEME
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 | Strategic Command", page_icon="🌐", initial_sidebar_state="expanded")

if "sar_tasked" not in st.session_state:
    st.session_state.sar_tasked = False

night_vision = st.sidebar.toggle("🌙 Executive Dark Mode", value=True)

if night_vision:
    bg_color = "#09090b"; card_bg = "#18181b"; text_color = "#f4f4f5"
    accent_blue = "#0ea5e9"; accent_red = "#ef4444"; accent_green = "#22c55e"; accent_purple = "#8b5cf6"; accent_amber = "#f59e0b"
    map_style = "dark"; term_bg = "#000000"; term_color = "#10b981"
else:
    bg_color = "#f8fafc"; card_bg = "#ffffff"; text_color = "#0f172a"
    accent_blue = "#0284c7"; accent_red = "#e11d48"; accent_green = "#059669"; accent_purple = "#7c3aed"; accent_amber = "#d97706"
    map_style = "satellite"; term_bg = "#f1f5f9"; term_color = "#0f172a"

css = f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: 'Inter', -apple-system, sans-serif; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px 24px; border-radius: 6px; border: 1px solid #27272a; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    .protection-card {{ border-left: 4px solid {accent_red}; }}
    .military-card {{ border-left: 4px solid {accent_purple}; }}
    .resilience-card {{ border-left: 4px solid {accent_blue}; }}
    .mitigation-card {{ border-left: 4px solid {accent_green}; }}
    h1, h2, h3, h4 {{ color: {text_color}; font-weight: 600; margin-top: 0; letter-spacing: -0.02em; }}
    h4 {{ font-size: 0.8rem; text-transform: uppercase; color: #a1a1aa; letter-spacing: 0.05em; margin-bottom: 8px; }}
    .kpi-value {{ font-size: 2rem; font-weight: 700; color: {text_color}; margin: 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.85rem; color: #a1a1aa; display: block; margin-top: 4px; }}
    .streamlit-expanderHeader {{ font-weight: 500 !important; font-size: 0.9rem; color: {text_color} !important; border-radius: 6px; }}
    div[data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid #27272a; }}
    div.row-widget.stRadio > div {{ flex-direction: row; align-items: center; justify-content: center; background-color: {card_bg}; padding: 12px; border-radius: 6px; border: 1px solid #27272a; }}
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
        model = genai.GenerativeModel('gemini-2.5-flash')
        ai_status = "🟢 CORE ACTIVE"
    else: ai_status = "🔴 CORE OFFLINE"
except: ai_status = "🔴 CORE OFFLINE"

# ---------------------------------------------------------
# 3. SIDEBAR: PROFESSIONAL UX NAVIGATION
# ---------------------------------------------------------
st.sidebar.markdown(f"""
<div style="margin-bottom: 30px; text-align: center;">
    <div style="font-size: 36px; color: {accent_blue}; line-height: 1;">🌐</div>
    <div style="font-weight: 700; color: {text_color}; font-size: 1.25rem; letter-spacing: 1.5px; margin-top: 8px;">BLUE 42 COMMAND</div>
    <div style="color: #a1a1aa; font-size: 0.75rem; font-weight: 500; letter-spacing: 1px; text-transform: uppercase; margin-top: 2px;">Global Blue Economy OS</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🌍 REGIONAL DEPLOYMENT")
sector_mode = st.sidebar.selectbox("Operational Theater:", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"], label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 SYSTEM DIAGNOSTICS")
st.sidebar.caption(f"**Geospatial Engine:** {ee_status}\n\n**GenAI Reasoning:** {ai_status}")

# ---------------------------------------------------------
# 4. EXECUTIVE STORYBOARD & STRATEGIC FILTER
# ---------------------------------------------------------
st.markdown(f"<h2 style='color: {text_color}; text-align: center; margin-bottom: 8px; font-weight: 700;'>Global Maritime Command Center</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: #a1a1aa; font-size: 1.1rem; margin-bottom: 30px;'>Synthesizing planetary telemetry into predictive intelligence and actionable ESG workflows.</p>", unsafe_allow_html=True)

focus_mode = st.radio("SELECT STRATEGIC FOCUS TO FILTER BATTLESPACE & ANALYTICS:", 
    ["🌍 Global Overview", "🛡️ Threat Interdiction", "⚓ Military Security", "🌪️ Supply Chain Resilience", "🌱 ESG Blue Carbon"], 
    horizontal=True)

st.write("")

if focus_mode == "🌍 Global Overview":
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ACTIVE THREATS</h4><p class='kpi-value' style='color:{accent_red};'>1 VOI</p><span class='kpi-subtext'>Target masking identity near MPA</span></div>", unsafe_allow_html=True)
    with col2: st.markdown(f"<div class='metric-card military-card'><h4>⚓ MILITARY ZONES</h4><p class='kpi-value' style='color:{accent_purple};'>SECURE</p><span class='kpi-subtext'>No incursions in weapons ranges</span></div>", unsafe_allow_html=True)
    with col3: st.markdown(f"<div class='metric-card resilience-card'><h4>🌪️ RESILIENCE</h4><p class='kpi-value' style='color:{accent_blue};'>5 REROUTED</p><span class='kpi-subtext'>Avoiding extreme wave heights</span></div>", unsafe_allow_html=True)
    with col4: st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 BLUE CARBON</h4><p class='kpi-value' style='color:{accent_green};'>14.2 HA</p><span class='kpi-subtext'>Optimal restoration sites verified</span></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. SMART CARD TOOLTIP ENGINE
# ---------------------------------------------------------
# The UX Upgrade: A beautiful, separated "Smart Card" that renders instantly on the map.
map_layers = []

def get_smart_card_tooltip():
    return {
        "html": f"""
        <div style='background: {card_bg}; border: 1px solid {accent_blue}; padding: 16px; border-radius: 8px; color: {text_color}; font-family: Inter, sans-serif; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); min-width: 300px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid #27272a; padding-bottom: 8px;'>
                <div style='font-size: 1.1rem; font-weight: 700; color: {accent_blue};'>{{name}}</div>
                <div style='font-size: 0.7rem; background: #27272a; padding: 2px 6px; border-radius: 4px; color: #a1a1aa; letter-spacing: 1px;'>SMART CARD</div>
            </div>
            <div style='margin-bottom: 12px;'>
                <div style='font-size: 0.85rem; color: #a1a1aa;'><b>Target ID:</b> {{primary_metric}}</div>
                <div style='font-size: 0.85rem; color: #a1a1aa;'><b>Vector:</b> {{secondary_metric}}</div>
            </div>
            <div style='background: rgba(14, 165, 233, 0.05); border-left: 3px solid {accent_blue}; padding: 8px; margin-bottom: 8px;'>
                <span style='color: {accent_blue}; font-weight: 600; font-size: 0.75rem; letter-spacing: 1px;'>DATA ANALYTIC</span><br/>
                <span style='font-size: 0.85rem; color: #f4f4f5; font-family: monospace;'>{{analytic_data}}</span>
            </div>
            <div style='background: rgba(34, 197, 94, 0.05); border-left: 3px solid {accent_green}; padding: 8px; margin-bottom: 12px;'>
                <span style='color: {accent_green}; font-weight: 600; font-size: 0.75rem; letter-spacing: 1px;'>AI ANALYSIS</span><br/>
                <span style='font-size: 0.85rem; color: #f4f4f5;'>{{analysis}}</span>
            </div>
            <div style='font-size: 0.75rem; color: #64748b; font-style: italic; text-align: right;'>Auth: {{source}}</div>
        </div>
        """,
        "style": {"backgroundColor": "transparent", "padding": "0"} 
    }

def create_smart_card_data(lat, lon, name, primary, secondary, analytic_data, analysis, source, color, polygon=None, path=None, radius=None):
    return {
        "lat": lat, "lon": lon, "name": name, 
        "primary_metric": primary, "secondary_metric": secondary,
        "analytic_data": analytic_data, "analysis": analysis, 
        "source": source, "color": color,
        "polygon": polygon, "path": path, "radius": radius
    }

# ---------------------------------------------------------
# 6. DYNAMIC MAP LOGIC WITH SMART CARD DATA
# ---------------------------------------------------------
if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=45, bearing=0)
    base_lat, base_lon = 33.8, -119.5
    
    if focus_mode in ["🌍 Global Overview", "🌱 ESG Blue Carbon"]:
        poly = [[[-119.7, 33.9], [-119.4, 33.9], [-119.4, 34.1], [-119.7, 34.1]]]
        depth_data = create_smart_card_data(34.0, -119.55, "Optimal Bathymetric Shelf", "Layer: Ocean Topography", "Range: -5m to -30m", "Depth: -14m | SST: 16.5°C | Current: 1.2kts", "Optimal bathymetric shelf. High-yield Blue Carbon sequestration zone verified for institutional minting.", "Copernicus Marine", [45, 212, 191, 40], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([depth_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[45, 212, 191, 150]", line_width_min_pixels=2, pickable=True))
        
        kelp_df = pd.DataFrame([create_smart_card_data(34.02, -119.55, "Verified Carbon Sink K-1", "Area: 5.1 HA", "Status: VERIFIED", "Viability Index: 98% | Drawdown: 898 tCO2e", "Site meets all DeepMind thermal survivability thresholds against decadal heatwaves. Safe for capital allocation.", "DeepMind SDM", [34, 197, 94, 200], radius=3000)])
        map_layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))

    if focus_mode in ["🌍 Global Overview", "🛡️ Threat Interdiction"]:
        poly = [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]]
        mpa_data = create_smart_card_data(34.0, -119.7, "Channel Islands MPA", "Protection Level: FULL", "Jurisdiction: Federal", "Designation: Sanctuary | Commercial Take: 0%", "Zero-take zone. Continuous AI surveillance active to detect 'dark fleet' incursions across perimeter.", "UNEP-WCMC WDPA", [56, 189, 248, 20], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([mpa_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2, pickable=True))

    if focus_mode in ["🌍 Global Overview", "🌪️ Supply Chain Resilience"]:
        poly = [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]]
        storm_data = create_smart_card_data(33.8, -119.3, "Severe Gale Warning", "Alert: WEATHER HAZARD", "Radius: 45nm", "H_s: > 6.1m (20ft) | Sustained Wind: 45 kts", "Extreme hydrodynamic resistance zone. Routing commercial traffic away saves 12% bunker fuel and prevents cargo loss.", "WeatherNext 3", [239, 68, 68, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([storm_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2, pickable=True))
        
        path = [[[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]]]
        route_data = create_smart_card_data(33.4, -119.3, "AI Optimized Route", "Status: ACTIVE REROUTE", "Vessels: 5 Commercial", "Drag Coeff (C_T) reduction: 42% | Fuel Averted: 54 MT", "Predictive vector safely circumvents the Gale Warning polygon, preserving operational continuity.", "AlphaEarth", [34, 197, 94, 200], path=path[0])
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame([route_data]), get_path="path", get_color="color", width_min_pixels=3, pickable=True))

    if focus_mode in ["🌍 Global Overview", "⚓ Military Security"]:
        poly = [[[-120.5, 33.2], [-119.0, 33.2], [-119.0, 33.8], [-120.5, 33.8]]]
        military_data = create_smart_card_data(33.5, -119.7, "Point Mugu Sea Range", "Status: RESTRICTED", "Type: Naval Weapons Area", "Geofence: ACTIVE | Status: LIVE FIRE", "High risk of kinetic interaction. TTI (Time-To-Intercept) algorithms actively repelling civilian AIS tracks.", "US Navy", [139, 92, 246, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([military_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[139, 92, 246, 150]", line_width_min_pixels=2, pickable=True))

else: # HAWAII
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=45, bearing=0)
    base_lat, base_lon = 21.2, -158.0
    
    if focus_mode in ["🌍 Global Overview", "🌱 ESG Blue Carbon"]:
        poly = [[[-158.0, 21.3], [-157.6, 21.3], [-157.6, 21.6], [-158.0, 21.6]]]
        depth_data = create_smart_card_data(21.45, -157.8, "Reef Bathymetric Contour", "Layer: Ocean Topography", "Range: -5m to -30m", "Depth: -8m | SST: 24.5°C", "Optimal bathymetric shelf. High-yield reef rehabilitation zone verified.", "Copernicus Marine", [45, 212, 191, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([depth_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[45, 212, 191, 150]", line_width_min_pixels=2, pickable=True))
        
        overlay_df = pd.DataFrame([create_smart_card_data(21.45, -157.8, "Verified Reef Restoration Zone", "Area: 6.5 HA", "Status: VERIFIED", "Viability Index: 96% | Drawdown: 1144 tCO2e", "Site meets all thermal survivability thresholds. Safe for capital allocation.", "DeepMind SDM", [34, 197, 94, 200], radius=3000)])
        map_layers.append(pdk.Layer("ScatterplotLayer", data=overlay_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))

    if focus_mode in ["🌍 Global Overview", "🛡️ Threat Interdiction"]:
        poly = [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]]
        mpa_data = create_smart_card_data(21.5, -158.0, "Kaena Point MPA Expansion", "Protection Level: FULL", "Jurisdiction: Federal/State", "Designation: Sanctuary | Commercial Take: 0%", "Critical habitat preservation area. AI actively monitoring for illicit commercial harvesting.", "UNEP-WCMC", [56, 189, 248, 20], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([mpa_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2, pickable=True))

    if focus_mode in ["🌍 Global Overview", "🌪️ Supply Chain Resilience"]:
        poly = [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]]
        storm_data = create_smart_card_data(21.2, -157.8, "Tropical Squall Hazard", "Alert: WEATHER HAZARD", "Radius: 30nm", "H_s: > 4.5m | Sustained Wind: 35 kts", "Localized squall creating supply chain delays for Honolulu port approaches. Fleets rerouting.", "WeatherNext 3", [239, 68, 68, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([storm_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2, pickable=True))

    if focus_mode in ["🌍 Global Overview", "⚓ Military Security"]:
        poly = [[[-159.9, 21.8], [-159.5, 21.8], [-159.5, 22.2], [-159.9, 22.2]]]
        military_data = create_smart_card_data(22.0, -159.7, "PMRF Barking Sands", "Status: RESTRICTED", "Type: Pacific Missile Range", "Geofence: ACTIVE | Status: LIVE FIRE", "World's largest instrumented military testing range. Civilian intrusion violates federal exclusion zone.", "US Navy", [139, 92, 246, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([military_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[139, 92, 246, 150]", line_width_min_pixels=2, pickable=True))

# ---------------------------------------------------------
# 7. VESSELS ENGINE (SMART CARDS ATTACHED)
# ---------------------------------------------------------
vessels = []

if focus_mode in ["🌍 Global Overview", "🌪️ Supply Chain Resilience"]:
    for i in range(15):
        sog = random.uniform(8.0, 22.0)
        v_type = random.choice(["CARGO", "TANKER", "BULK"])
        mmsi = f"36{random.randint(1000000, 9999999)}"
        lat = base_lat + random.uniform(-1.5, 1.5)
        lon = base_lon + random.uniform(-2.0, 2.0)
        vessels.append(create_smart_card_data(
            lat, lon, f"{v_type} (MMSI: {mmsi})", f"Class: COMMERCIAL", f"Length: {random.randint(150,350)}m", 
            f"SOG: {sog:.1f} kts | COG: {random.randint(0, 360)}° | AIS: ACTIVE", "Vessel kinetics operate within nominal parameters. Compliant track.", "Verified AIS", [148, 163, 184, 150], radius=1000
        ))

if focus_mode in ["🌍 Global Overview", "🛡️ Threat Interdiction"]:
    dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
    vessels.append(create_smart_card_data(
        dt_lat, dt_lon, "UNVERIFIED DARK TARGET", "Class: SUSPECT", "Est. Length: 45m", 
        "SOG: 2.5 kts | COG: 80.0° | AIS: LOST SIGNAL", "CRITICAL ANOMALY: Vessel disabled transponder 15nm from MPA. Kinematics strongly suggest illicit deployment. Intercept recommended.", "AIS/WDPA Fusion", [239, 68, 68, 255], radius=2500
    ))

vessels_df = pd.DataFrame(vessels)
if not vessels_df.empty:
    map_layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))

# ---------------------------------------------------------
# 8. RENDER THE INTERACTIVE SMART MAP & DEEP DIVES
# ---------------------------------------------------------
col_map, col_details = st.columns([2.5, 1.5])

with col_map:
    st.markdown("<div style='border: 1px solid #27272a; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.2);'>", unsafe_allow_html=True)
    r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=get_smart_card_tooltip())
    st.pydeck_chart(r, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_details:
    st.markdown(f"<div class='metric-card' style='height: 100%; border-top: none; padding-top: 5px;'>", unsafe_allow_html=True)
    
    if focus_mode == "🌍 Global Overview":
        st.markdown(f"<h3 style='color: {accent_blue}; font-size: 1.25rem;'>🌍 Intelligence Overview</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Interact with any element on the map to retrieve its Smart Card, or select a Strategic Focus filter above to drill down.</p>", unsafe_allow_html=True)
        st.markdown("#### System Baseline")
        st.write("• **Total Assets Tracked:** 16")
        st.write("• **Active Anomalies:** 1")
        st.write("• **Weather Advisories:** 1")

    elif focus_mode == "🛡️ Threat Interdiction":
        st.markdown(f"<h3 style='color: {accent_red}; font-size: 1.25rem;'>🛡️ Dark Fleet Analytics</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>When a vessel disables its AIS transponder near a Marine Protected Area (MPA), it correlates strongly with Illegal, Unreported, and Unregulated (IUU) fishing.</p>", unsafe_allow_html=True)
        st.markdown("#### The Mathematical Trigger")
        st.code("IF (Distance_to_MPA < 15nm) \nAND (Signal_Loss > 60m) \nAND (Speed < 4kts):\n   TRIGGER = HIGH_THREAT", language="python")
        st.markdown("#### Tactical Action")
        if st.button("🛰️ INITIATE SAR TASKING", use_container_width=True):
            st.session_state.sar_tasked = True
        if st.session_state.sar_tasked:
            st.success("SAR CONFIRMATION: 45m metallic hull detected. Intercept authorized.")

    elif focus_mode == "⚓ Military Security":
        st.markdown(f"<h3 style='color: {accent_purple}; font-size: 1.25rem;'>⚓ Geofencing & Kinetic Risk</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Blue 42 continuously ingests the polygons of restricted military zones to calculate Time-To-Intercept (TTI) for commercial vessels.</p>", unsafe_allow_html=True)
        st.markdown("#### Time-To-Intercept Formula")
        st.latex(r"TTI = \frac{Distance\_to\_Geofence}{Velocity\_of\_Vessel}")
        st.info("STATUS: Nominal. Zero civilian incursions detected in active live-fire ranges.")

    elif focus_mode == "🌪️ Supply Chain Resilience":
        st.markdown(f"<h3 style='color: {accent_blue}; font-size: 1.25rem;'>🌪️ Voyage Optimization</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>By avoiding severe weather polygons, fleets save millions of dollars and drastically cut Scope 3 emissions.</p>", unsafe_allow_html=True)
        st.markdown("#### Hydrodynamic Drag")
        st.latex(r"R_T = \frac{1}{2} \rho v^2 S C_T")
        st.markdown(f"<span style='color: {muted_text}; font-size: 0.85rem;'>Altering the route to avoid $H_s \ge 6.1$m waves drops the drag coefficient ($C_T$) by ~42%.</span>", unsafe_allow_html=True)

    elif focus_mode == "🌱 ESG Blue Carbon":
        st.markdown(f"<h3 style='color: {accent_green}; font-size: 1.25rem;'>🌱 Capital Verification</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Fusing Earth Engine's bathymetry with DeepMind's Species Distribution Models to find the exact biological envelope for Giant Kelp.</p>", unsafe_allow_html=True)
        st.markdown("#### Ecological Analytics")
        st.write("• **Depth Threshold:** -5m to -30m")
        st.write("• **Thermal Threshold:** SST < 18°C")
        st.markdown("#### Institutional Asset Minting")
        if st.button("Mint Verified Blue Carbon Credits", use_container_width=True):
            st.success("SUCCESS: 2,500 tCO₂e validated. Asset ID #BC-8492-GEE minted.")

    st.markdown("</div>", unsafe_allow_html=True)
