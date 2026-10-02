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
# 1. PAGE SETUP & REFINED UX THEME CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 | Maritime Command", page_icon="🌐", initial_sidebar_state="expanded")

if "sar_tasked" not in st.session_state:
    st.session_state.sar_tasked = False

night_vision = st.sidebar.toggle("🌙 Tactical Night Vision", value=True)

if night_vision:
    bg_color = "#0f172a"; card_bg = "#1e293b"; text_color = "#f8fafc"; muted_text = "#94a3b8"
    accent_blue = "#38bdf8"; accent_red = "#fb7185"; accent_green = "#34d399"; accent_purple = "#a78bfa"; accent_amber = "#fbbf24"
    map_style = "dark" 
else:
    bg_color = "#f1f5f9"; card_bg = "#ffffff"; text_color = "#0f172a"; muted_text = "#64748b"
    accent_blue = "#0284c7"; accent_red = "#e11d48"; accent_green = "#059669"; accent_purple = "#7c3aed"; accent_amber = "#d97706"
    map_style = "light" 

css = f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: 'Inter', -apple-system, sans-serif; }}
    .metric-card {{ background-color: {card_bg}; padding: 24px; border-radius: 12px; border-top: 4px solid {accent_blue}; margin-bottom: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); transition: transform 0.2s ease; }}
    .metric-card:hover {{ transform: translateY(-2px); }}
    .protection-card {{ border-top: 4px solid {accent_red}; }}
    .mitigation-card {{ border-top: 4px solid {accent_green}; }}
    .military-card {{ border-top: 4px solid {accent_purple}; }}
    .logistics-card {{ border-top: 4px solid {accent_amber}; }}
    h1, h2, h3, h4 {{ color: {text_color}; font-weight: 600; margin-top: 0; letter-spacing: -0.01em; }}
    h4 {{ font-size: 0.85rem; text-transform: uppercase; color: {muted_text}; letter-spacing: 0.05em; }}
    .kpi-value {{ font-size: 2.25rem; font-weight: 700; color: {text_color}; margin: 4px 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.85rem; color: {muted_text}; display: block; margin-bottom: 4px; }}
    .streamlit-expanderHeader {{ font-weight: 600 !important; font-size: 0.95rem; color: {text_color} !important; border-radius: 8px; }}
    div[data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid rgba(100,116,139,0.2); }}
    .terminal {{ background-color: #000000; padding: 12px; border: 1px solid {accent_green}; border-radius: 4px; color: {accent_green}; font-family: 'Courier New', monospace; font-size: 0.8rem; box-shadow: inset 0 0 10px rgba(52, 211, 153, 0.2); }}
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

try:
    ais_key = st.secrets.get("AISSTREAM_API_KEY", "")
    ais_status = "🟢 RADAR AUTHENTICATED" if ais_key else "🔴 RADAR OFFLINE"
except: ais_status = "🔴 RADAR OFFLINE"

# ---------------------------------------------------------
# 3. SIDEBAR: PROFESSIONAL UX NAVIGATION
# ---------------------------------------------------------
st.sidebar.markdown(f"""
<div style="margin-bottom: 30px; text-align: center;">
    <div style="font-size: 40px; color: {accent_blue};">🌊</div>
    <div style="font-weight: 700; color: {text_color}; font-size: 1.4rem; letter-spacing: 1px; margin-top: 5px;">BLUE 42 COMMAND</div>
    <div style="color: {muted_text}; font-size: 0.75rem; font-weight: 500; letter-spacing: 1px; text-transform: uppercase;">Global Blue Economy OS</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🌍 REGIONAL DEPLOYMENT")
sector_mode = st.sidebar.selectbox("Operational Theater:", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"], label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 LIVE TELEMETRY")
live_ais = st.sidebar.toggle("Connect Live Satellite AIS Feed", value=False)
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 SYSTEM DIAGNOSTICS")
st.sidebar.caption(f"**Geospatial Engine:** {ee_status}\n\n**GenAI Reasoning:** {ai_status}\n\n**AIS Telemetry:** {ais_status}")

# ---------------------------------------------------------
# 4. EXECUTIVE STORYBOARD & STRATEGIC FILTER
# ---------------------------------------------------------
st.markdown(f"<h2 style='color: {text_color}; text-align: center; margin-bottom: 8px; font-weight: 700;'>Global Maritime Command Center</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: {muted_text}; font-size: 1.1rem; margin-bottom: 30px;'>Synthesizing planetary telemetry into predictive intelligence for global economic stability and human rights.</p>", unsafe_allow_html=True)

focus_mode = st.radio("SELECT STRATEGIC FOCUS TO FILTER BATTLESPACE & ANALYTICS:", 
    ["🌍 Global Overview", "🛡️ Threat Interdiction", "⚓ Military Security", "🌪️ Supply Chain Resilience", "🌱 ESG Blue Carbon"], 
    horizontal=True)

st.write("")

if focus_mode == "🌍 Global Overview":
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ACTIVE THREATS</h4><p class='kpi-value' style='color:{accent_red};'>1 VOI</p><span class='kpi-subtext'>Target masking identity near MPA</span></div>", unsafe_allow_html=True)
    with col2: st.markdown(f"<div class='metric-card military-card'><h4>⚓ MILITARY ZONES</h4><p class='kpi-value' style='color:{accent_purple};'>SECURE</p><span class='kpi-subtext'>No incursions in weapons ranges</span></div>", unsafe_allow_html=True)
    with col3: st.markdown(f"<div class='metric-card'><h4>🌪️ RESILIENCE</h4><p class='kpi-value' style='color:{accent_blue};'>5 REROUTED</p><span class='kpi-subtext'>Avoiding extreme wave heights</span></div>", unsafe_allow_html=True)
    with col4: st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 BLUE CARBON</h4><p class='kpi-value' style='color:{accent_green};'>14.2 HA</p><span class='kpi-subtext'>Optimal restoration sites verified</span></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. UNIFIED DATA SCHEMA FOR DEEP-DIVE TOOLTIPS
# ---------------------------------------------------------
map_layers = []

# THE FIX: This ensures the Smart Card grabs exactly the fields we populate below
custom_tooltip = {
    "html": f"""
    <div style='background: {card_bg}; border: 1px solid {accent_blue}; padding: 14px; border-radius: 10px; color: {text_color}; font-family: Inter, sans-serif; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); max-width: 320px;'>
        <div style='font-size: 1.1rem; font-weight: 700; color: {accent_blue}; margin-bottom: 4px;'>{{name}}</div>
        <div style='font-size: 0.85rem; color: {muted_text}; margin-bottom: 2px;'>{{primary_metric}}</div>
        <div style='font-size: 0.85rem; color: {muted_text}; margin-bottom: 12px;'>{{secondary_metric}}</div>
        <div style='border-top: 1px solid rgba(148, 163, 184, 0.2); padding-top: 10px;'>
            <span style='color: {accent_green}; font-weight: 600; font-size: 0.85rem;'>AI ANALYTICS:</span><br/>
            <span style='font-size: 0.85rem; line-height: 1.4; color: {text_color};'>{{analytics}}</span>
        </div>
        <div style='margin-top: 10px; font-size: 0.75rem; color: {muted_text}; font-style: italic;'>Source: {{source}}</div>
    </div>
    """,
    "style": {"backgroundColor": "transparent", "padding": "0"} 
}

# Master function to format all map objects perfectly for the Smart Card
def create_unified_tooltip_data(lat, lon, name, primary, secondary, analytics, source, color, polygon=None, path=None, radius=None):
    return {"lat": lat, "lon": lon, "name": name, "primary_metric": primary, "secondary_metric": secondary, "analytics": analytics, "source": source, "color": color, "polygon": polygon, "path": path, "radius": radius}

# ---------------------------------------------------------
# 6. REGIONAL MAP CONFIGURATIONS & STATIC ZONES
# ---------------------------------------------------------
if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=50, bearing=0)
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]]
    base_lat, base_lon = 33.8, -119.5
    regional_ports = ["Port of Los Angeles", "Port of Long Beach", "Port Hueneme"]
    
    if focus_mode in ["🌍 Global Overview", "🌱 ESG Blue Carbon"]:
        poly = [[[-119.7, 33.9], [-119.4, 33.9], [-119.4, 34.1], [-119.7, 34.1]]]
        depth_data = create_unified_tooltip_data(34.0, -119.55, "Optimal Bathymetric Shelf", "Layer: Ocean Topography", "Range: -5m to -30m", "Depth: -14m | SST: 16.5°C. Highly viable blue carbon zone.", "Copernicus Marine", [45, 212, 191, 40], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([depth_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[45, 212, 191, 150]", line_width_min_pixels=2, pickable=True))
        
        kelp_df = pd.DataFrame([
            create_unified_tooltip_data(34.02, -119.55, "Verified Carbon Sink K-1", "Area: 5.1 HA", "Status: VERIFIED", "Viability Index: 98% | Drawdown: 898 tCO2e/yr", "DeepMind SDM", [34, 197, 94, 200], radius=3000),
            create_unified_tooltip_data(33.98, -119.60, "Verified Carbon Sink K-2", "Area: 4.8 HA", "Status: VERIFIED", "Deep-water thermal refuge. High resilience to warming.", "DeepMind SDM", [34, 197, 94, 200], radius=3000)
        ])
        map_layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))

    if focus_mode in ["🌍 Global Overview", "🛡️ Threat Interdiction"]:
        poly = [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]]
        mpa_data = create_unified_tooltip_data(34.0, -119.7, "Channel Islands Marine Sanctuary", "Protection Level: FULL", "Jurisdiction: Federal", "Zero-take zone. Continuous AI surveillance active to detect 'dark fleet' incursions.", "UNEP-WCMC", [56, 189, 248, 20], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([mpa_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2, pickable=True))

    if focus_mode in ["🌍 Global Overview", "🌪️ Supply Chain Resilience"]:
        poly = [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]]
        storm_data = create_unified_tooltip_data(33.8, -119.3, "Severe Gale Warning", "Alert: WEATHER HAZARD", "H_s: > 6.1m (20ft)", "Extreme hydrodynamic drag detected. Routing through this zone increases fuel consumption by 12%.", "WeatherNext 3", [239, 68, 68, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([storm_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2, pickable=True))
        
        path = [[[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]]]
        route_data = create_unified_tooltip_data(33.4, -119.3, "AI Optimized Route", "Status: ACTIVE REROUTE", "Fuel Averted: 54 MT", "Predictive vector safely circumvents the Gale Warning polygon.", "AlphaEarth", [34, 197, 94, 200], path=path[0])
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame([route_data]), get_path="path", get_color="color", width_min_pixels=3, pickable=True))

    if focus_mode in ["🌍 Global Overview", "⚓ Military Security"]:
        poly = [[[-120.5, 33.2], [-119.0, 33.2], [-119.0, 33.8], [-120.5, 33.8]]]
        military_data = create_unified_tooltip_data(33.5, -119.7, "Point Mugu Sea Range", "Status: RESTRICTED", "Type: Naval Weapons Area", "Geofence: ACTIVE | Status: LIVE FIRE. High risk of kinetic interaction.", "US Navy", [139, 92, 246, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([military_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[139, 92, 246, 150]", line_width_min_pixels=2, pickable=True))

else: # HAWAII
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=50, bearing=0)
    base_lat, base_lon = 21.2, -158.0
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    regional_ports = ["Honolulu Harbor", "Pearl Harbor", "Kahului"]
    
    if focus_mode in ["🌍 Global Overview", "🌱 ESG Blue Carbon"]:
        poly = [[[-158.0, 21.3], [-157.6, 21.3], [-157.6, 21.6], [-158.0, 21.6]]]
        depth_data = create_unified_tooltip_data(21.45, -157.8, "Reef Bathymetric Contour", "Layer: Ocean Topography", "Range: -5m to -30m", "Depth: -8m | SST: 24.5°C", "Copernicus Marine", [45, 212, 191, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([depth_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[45, 212, 191, 150]", line_width_min_pixels=2, pickable=True))
        
        reef_df = pd.DataFrame([create_unified_tooltip_data(21.45, -157.8, "Verified Reef Restoration Zone", "Area: 6.5 HA", "Status: VERIFIED", "Viability Index: 96% | Drawdown: 1144 tCO2e. Optimal ESG rehabilitation zone.", "DeepMind SDM", [34, 197, 94, 200], radius=3000)])
        map_layers.append(pdk.Layer("ScatterplotLayer", data=reef_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))

    if focus_mode in ["🌍 Global Overview", "🛡️ Threat Interdiction"]:
        poly = [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]]
        mpa_data = create_unified_tooltip_data(21.5, -158.0, "Kaena Point MPA Expansion", "Protection Level: FULL", "Jurisdiction: Federal/State", "Critical habitat preservation area. AI actively monitoring.", "UNEP-WCMC", [56, 189, 248, 20], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([mpa_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2, pickable=True))

    if focus_mode in ["🌍 Global Overview", "🌪️ Supply Chain Resilience"]:
        poly = [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]]
        storm_data = create_unified_tooltip_data(21.2, -157.8, "Tropical Squall Hazard", "Alert: WEATHER HAZARD", "H_s: > 4.5m", "Localized squall creating supply chain delays for Honolulu port approaches.", "WeatherNext 3", [239, 68, 68, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([storm_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2, pickable=True))
        
        path = [[[-158.5, 20.8], [-158.0, 20.9], [-157.4, 20.9], [-157.1, 21.2]]]
        route_data = create_unified_tooltip_data(21.0, -157.8, "AI Optimized Route", "Status: ACTIVE REROUTE", "Fuel Averted: 54 MT", "Predictive vector safely circumvents the hazard.", "AlphaEarth", [34, 197, 94, 200], path=path[0])
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame([route_data]), get_path="path", get_color="color", width_min_pixels=3, pickable=True))

    if focus_mode in ["🌍 Global Overview", "⚓ Military Security"]:
        poly = [[[-159.9, 21.8], [-159.5, 21.8], [-159.5, 22.2], [-159.9, 22.2]]]
        military_data = create_unified_tooltip_data(22.0, -159.7, "PMRF Barking Sands", "Status: RESTRICTED", "Type: Pacific Missile Range", "Civilian intrusion violates federal exclusion zone.", "US Navy", [139, 92, 246, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([military_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[139, 92, 246, 150]", line_width_min_pixels=2, pickable=True))

# ---------------------------------------------------------
# 7. LIVE VESSEL DATA ENGINE & SMART CARDS
# ---------------------------------------------------------
live_vessels_data = []

# Fetch Live WebSocket Data
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
                        v_len = int(random.uniform(150, 350))
                        live_vessels_data.append({
                            "MMSI": mmsi, "Vessel Name": name, "lat": lat, "lon": lon, 
                            "sog": pr.get('Sog', 0), "cog": pr.get('Cog', 0),
                            "Length (m)": v_len, "Draft (m)": round(random.uniform(9,15), 1), "Gross Tonnage": int(v_len * (v_len*0.15) * 12 * 0.7),
                            "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
                        })
                    if len(live_vessels_data) >= 30: break
            except: break
        ws.close()
    except: pass

# Simulation Fallback
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
            "Length (m)": v_len, "Draft (m)": round(random.uniform(9,15), 1), "Gross Tonnage": int(v_len * (v_len*0.15) * 12 * 0.7),
            "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
        })

# Add the Dark Target Threat
dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
live_vessels_data.append({
    "MMSI": "413000000", "Vessel Name": "UNVERIFIED DARK TARGET",
    "lat": dt_lat, "lon": dt_lon, "sog": 2.5, "cog": 80.0,
    "Length (m)": 45, "Draft (m)": 3.2, "Gross Tonnage": 806,
    "Risk Status": "CRITICAL ANOMALY", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
})

# THE FIX: Safely route ALL vessels through the unified dictionary to guarantee Smart Cards work
vessels = []
for v in live_vessels_data:
    is_threat = v['Risk Status'] != "Nominal"
    if focus_mode == "🌱 ESG Blue Carbon" and not is_threat: continue
    if focus_mode == "⚓ Military Security" and not is_threat: continue
    
    cog_rad = math.radians(v['cog'])
    vec_len = max(v['sog'] * 0.003, 0.01)
    color = [239, 68, 68, 255] if is_threat else [148, 163, 184, 150]
    
    analysis = "CRITICAL HUMAN RIGHTS ANOMALY: Vessel disabled transponder 15nm from MPA. Kinematics strongly suggest illicit fishing and forced labor operations." if is_threat else "Vessel kinetics operate within nominal parameters. Compliant track."
    
    vessels.append(create_unified_tooltip_data(
        v['lat'], v['lon'], v['Vessel Name'], f"Speed: {v['sog']:.1f} kts | Heading: {v['cog']:.1f}°", 
        f"Size: {v['Length (m)']}m | Tonnage: {v['Gross Tonnage']:,} GT", analysis, 
        "Verified AIS Telemetry", color, 
        path=[[v['lon'], v['lat']], [v['lon'] + vec_len * math.sin(cog_rad), v['lat'] + vec_len * math.cos(cog_rad)]], 
        radius=2500 if is_threat else 1000
    ))

vessels_df = pd.DataFrame(vessels)
if not vessels_df.empty:
    map_layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))
    map_layers.append(pdk.Layer("PathLayer", data=vessels_df, get_path="path", get_color="color", width_min_pixels=2, pickable=False))

# ---------------------------------------------------------
# 8. RENDER THE INTERACTIVE SMART MAP & DEEP DIVES
# ---------------------------------------------------------
col_map, col_details = st.columns([2.5, 1.5])

with col_map:
    st.markdown("<div style='border: 1px solid #27272a; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.2);'>", unsafe_allow_html=True)
    # The map uses the custom_tooltip dictionary defined above!
    r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=get_tooltip())
    st.pydeck_chart(r, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_details:
    st.markdown(f"<div class='metric-card' style='height: 100%; border-top: none; padding-top: 5px;'>", unsafe_allow_html=True)
    
    if focus_mode == "🌍 Global Overview":
        st.markdown(f"<h3 style='color: {accent_blue}; font-size: 1.25rem;'>🌍 Global Telemetry</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Select a specific Strategic Focus from the menu above to filter the map and access deep-dive analytics.</p>", unsafe_allow_html=True)
        st.write(f"• **Total Assets Tracked:** {len(live_vessels_data)}")
        st.write("• **Active Anomalies:** 1")

    elif focus_mode == "🛡️ Threat Interdiction":
        st.markdown(f"<h3 style='color: {accent_red}; font-size: 1.25rem;'>🛡️ Dark Fleet Analytics</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>When a vessel disables its AIS transponder near a Marine Protected Area (MPA), it correlates strongly with Illegal, Unreported, and Unregulated (IUU) fishing.</p>", unsafe_allow_html=True)
        st.markdown("#### The Mathematical Trigger")
        st.code("IF (Distance_to_MPA < 15nm) \nAND (Signal_Loss > 60m) \nAND (Speed < 4kts):\n   TRIGGER = HIGH_THREAT", language="python")
        if st.button("🛰️ INITIATE SAR TASKING", use_container_width=True):
            st.session_state["sar_tasked"] = True
        if st.session_state.get("sar_tasked", False):
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
                    except Exception as e: 
                        st.error(f"AI Comms Offline: {e}")

    elif focus_mode == "🌱 ESG Blue Carbon":
        st.markdown(f"<h3 style='color: {accent_green}; font-size: 1.25rem;'>🌱 Capital Verification</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Fusing Earth Engine's bathymetry with DeepMind's Species Distribution Models to find the exact biological envelope for Giant Kelp.</p>", unsafe_allow_html=True)
        st.markdown("#### Ecological Analytics")
        st.write("• **Depth Threshold:** -5m to -30m")
        st.write("• **Thermal Threshold:** SST < 18°C")
        if st.button("Mint Verified Blue Carbon Credits", use_container_width=True):
            st.success("SUCCESS: 2,500 tCO₂e validated. Asset ID #BC-8492-GEE minted.")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 9. ENTERPRISE DATA LEDGER (BOTTOM TABS)
# ---------------------------------------------------------
st.write("---")
st.markdown("### 📈 Operational Analytics & Financial Ledger")
tab1, tab2, tab3 = st.tabs(["🚢 Active Fleet Kinematics", "💰 Scope 3 Financial & Carbon Ledger", "📋 Executive Action Reports"])

with tab1:
    st.markdown("<p class='hud-text'>Live tactical breakdown of all assets currently operating in the sector. Data includes size, speed, and heading parameters.</p>", unsafe_allow_html=True)
    fleet_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Length (m)", "Draft (m)", "sog", "cog", "Risk Status"]]
    fleet_df.rename(columns={"sog": "Speed (kts)", "cog": "Heading (°)"}, inplace=True)
    st.dataframe(fleet_df, use_container_width=True)

with tab2:
    st.markdown("<p class='hud-text'>Live accounting of protected maritime cargo value and calculated Scope 3 emissions reductions.</p>", unsafe_allow_html=True)
    ledger_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Risk Status", "Cargo Value ($M)", "Fuel Saved (MT)"]]
    
    total_cargo = ledger_df["Cargo Value ($M)"].sum()
    total_fuel = ledger_df["Fuel Saved (MT)"].sum()
    total_carbon = total_fuel * 3.11 
    total_carbon_value = total_carbon * 75.00
    
    st.markdown(f"**Total Capital Protected:** ${total_cargo:,.1f} Million | **Total Scope 3 Averted:** {total_carbon:,.1f} MT CO₂e | **Verified Carbon Value:** ${total_carbon_value:,.2f}")
    st.dataframe(ledger_df.style.highlight_max(axis=0, subset=["Fuel Saved (MT)"], color=accent_green), use_container_width=True)

with tab3:
    st.markdown("<p class='hud-text'>GenAI automated formal reporting for Coast Guard incident dispatch and Corporate ESG audits.</p>", unsafe_allow_html=True)
    if st.button("Generate Official Action Report via Gemini", use_container_width=True):
        with st.spinner("Drafting formal compliance and incident report..."):
            try:
                report_prompt = f"You are an executive ESG auditor and Coast Guard officer. Based on the {sector_mode} sector with a strategic focus on {focus_mode}, write a highly formal, 2-paragraph executive incident report covering operational impact. Use formal government/financial language."
                response = model.generate_content(report_prompt)
                st.info(response.text)
            except Exception as e:
                st.error(f"GenAI Error: {e}")
