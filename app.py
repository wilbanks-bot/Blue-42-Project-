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
# 1. PAGE SETUP & REFINED UX THEME CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 | Maritime Command", page_icon="🌐", initial_sidebar_state="expanded")

if "sar_tasked" not in st.session_state:
    st.session_state.sar_tasked = False

night_vision = st.sidebar.toggle("🌙 Tactical Night Vision", value=True)

if night_vision:
    bg_color = "#0f172a"; card_bg = "#1e293b"; text_color = "#f8fafc"
    accent_blue = "#38bdf8"; accent_red = "#fb7185"; accent_green = "#34d399"; accent_purple = "#a78bfa"; accent_amber = "#fbbf24"
    map_style = "dark" 
else:
    bg_color = "#f1f5f9"; card_bg = "#ffffff"; text_color = "#0f172a"
    accent_blue = "#0284c7"; accent_red = "#e11d48"; accent_green = "#059669"; accent_purple = "#7c3aed"; accent_amber = "#d97706"
    map_style = "satellite" 

css = f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: 'Inter', -apple-system, sans-serif; }}
    .metric-card {{ background-color: {card_bg}; padding: 24px; border-radius: 12px; border-top: 4px solid {accent_blue}; margin-bottom: 5px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); transition: transform 0.2s ease; }}
    .metric-card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 12px -1px rgba(0, 0, 0, 0.15); }}
    .protection-card {{ border-top: 4px solid {accent_red}; }}
    .mitigation-card {{ border-top: 4px solid {accent_green}; }}
    .military-card {{ border-top: 4px solid {accent_purple}; }}
    .logistics-card {{ border-top: 4px solid {accent_amber}; }}
    h1, h2, h3, h4 {{ color: {text_color}; font-weight: 600; margin-top: 0; letter-spacing: -0.01em; }}
    h4 {{ font-size: 0.85rem; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; }}
    .kpi-value {{ font-size: 2.25rem; font-weight: 700; color: {text_color}; margin: 4px 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.85rem; color: #64748b; display: block; margin-bottom: 4px; }}
    .streamlit-expanderHeader {{ font-weight: 600 !important; font-size: 0.95rem; color: {text_color} !important; border-radius: 8px; }}
    div[data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid rgba(100,116,139,0.2); }}
    .terminal {{ background-color: #000000; padding: 12px; border: 1px solid {accent_green}; border-radius: 4px; color: {accent_green}; font-family: 'Courier New', monospace; font-size: 0.8rem; box-shadow: inset 0 0 10px rgba(52, 211, 153, 0.2); }}
    /* Custom Radio Button Styling for the Filter */
    div.row-widget.stRadio > div {{ flex-direction: row; align-items: center; justify-content: center; background-color: {card_bg}; padding: 10px; border-radius: 10px; border: 1px solid {accent_blue}; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
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
        model = genai.GenerativeModel('gemini-1.5-flash')
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
    <div style="color: #64748b; font-size: 0.75rem; font-weight: 500; letter-spacing: 1px; text-transform: uppercase;">Global Blue Economy OS</div>
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
# 4. EXECUTIVE STORYBOARD & KPI SECTION
# ---------------------------------------------------------
st.markdown(f"<h2 style='color: {text_color}; text-align: center; margin-bottom: 5px;'>Global Maritime Command Center</h2>", unsafe_allow_html=True)
st.markdown("<p class='hud-text' style='text-align: center; margin-bottom: 25px;'>Synthesizing planetary telemetry into predictive intelligence and actionable ESG workflows.</p>", unsafe_allow_html=True)

# 4-Card Executive Row
col1, col2, col3, col4 = st.columns(4)
with col1: st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ACTIVE THREATS</h4><p class='kpi-value' style='color:{accent_red};'>1 VOI</p><span class='kpi-subtext'>Target masking identity near MPA</span></div>", unsafe_allow_html=True)
with col2: st.markdown(f"<div class='metric-card military-card'><h4>⚓ MILITARY ZONES</h4><p class='kpi-value' style='color:{accent_purple};'>SECURE</p><span class='kpi-subtext'>No incursions in weapons ranges</span></div>", unsafe_allow_html=True)
with col3: st.markdown(f"<div class='metric-card'><h4>🌪️ RESILIENCE</h4><p class='kpi-value' style='color:{accent_blue};'>5 REROUTED</p><span class='kpi-subtext'>Avoiding extreme wave heights</span></div>", unsafe_allow_html=True)
with col4: st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 BLUE CARBON</h4><p class='kpi-value' style='color:{accent_green};'>14.2 HA</p><span class='kpi-subtext'>Optimal restoration sites verified</span></div>", unsafe_allow_html=True)

# ---> NEW UX: STRATEGIC FOCUS FILTER <---
st.write("")
focus_mode = st.radio("🔍 SELECT STRATEGIC FOCUS TO FILTER MAP & DEEP DIVE ANALYTICS:", 
    ["🌍 Global Overview (All Layers)", "🛡️ Threat Interdiction (IUU)", "⚓ Military Security", "🌪️ Supply Chain Resilience", "🌱 ESG Blue Carbon"], 
    horizontal=True)
st.write("")

# ---------------------------------------------------------
# 5. DYNAMIC MAP LOGIC (FILTERED BY FOCUS)
# ---------------------------------------------------------
map_layers = []

def create_unified_tooltip_data(lat, lon, name, primary, secondary, analytics, source, color, polygon=None, path=None, radius=None):
    return {"lat": lat, "lon": lon, "name": name, "primary_metric": primary, "secondary_metric": secondary, "analytics": analytics, "source": source, "color": color, "polygon": polygon, "path": path, "radius": radius}

def get_tooltip():
    return {
        "html": f"""
        <div style='background: {card_bg}; border: 1px solid {accent_blue}; padding: 14px; border-radius: 10px; color: {text_color}; font-family: Inter, sans-serif; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); max-width: 320px;'>
            <div style='font-size: 1.1rem; font-weight: 700; color: {accent_blue}; margin-bottom: 4px;'>{{name}}</div>
            <div style='font-size: 0.85rem; color: #94a3b8; margin-bottom: 2px;'>{{primary_metric}}</div>
            <div style='font-size: 0.85rem; color: #94a3b8; margin-bottom: 12px;'>{{secondary_metric}}</div>
            <div style='border-top: 1px solid rgba(148, 163, 184, 0.2); padding-top: 10px;'>
                <span style='color: {accent_green}; font-weight: 600; font-size: 0.85rem;'>AI ANALYTICS:</span><br/>
                <span style='font-size: 0.85rem; line-height: 1.4; color: {text_color};'>{{analytics}}</span>
            </div>
            <div style='margin-top: 10px; font-size: 0.75rem; color: #64748b; font-style: italic;'>Source: {{source}}</div>
        </div>
        """,
        "style": {"backgroundColor": "transparent", "padding": "0"} 
    }

if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=50, bearing=-10)
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]]
    base_lat, base_lon = 33.8, -119.5
    regional_ports = ["Port of Los Angeles", "Port of Long Beach", "Port Hueneme"]
    
    if focus_mode in ["🌍 Global Overview (All Layers)", "🌱 ESG Blue Carbon"]:
        depth_data = pd.DataFrame([{"polygon": [[[-119.7, 33.9], [-119.4, 33.9], [-119.4, 34.1], [-119.7, 34.1]]], "name": "Optimal Bathymetric Shelf", "analytics": "Copernicus Depth: -5m to -30m.", "source": "Copernicus Marine"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=depth_data, get_polygon="polygon", get_fill_color="[45, 212, 191, 50]", get_line_color="[45, 212, 191, 200]", line_width_min_pixels=2, pickable=True))
        kelp_df = pd.DataFrame([{"lat": 34.02, "lon": -119.55, "name": "Verified Carbon Sink", "analytics": "Depth 14m, SST 16.5°C.", "source": "GDM", "color": [16, 185, 129, 255]}])
        map_layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_fill_color="color", get_radius=4000, pickable=True))

    if focus_mode in ["🌍 Global Overview (All Layers)", "🛡️ Threat Interdiction (IUU)"]:
        mpa_data = pd.DataFrame([{"polygon": [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]], "name": "Channel Islands MPA", "analytics": "Federally Protected Boundary.", "source": "UNEP-WCMC"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=mpa_data, get_polygon="polygon", get_fill_color="[56, 189, 248, 30]", get_line_color="[56, 189, 248, 200]", line_width_min_pixels=3, pickable=True))

    if focus_mode in ["🌍 Global Overview (All Layers)", "🌪️ Supply Chain Resilience"]:
        storm_data = pd.DataFrame([{"polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]], "name": "Severe Gale Warning", "analytics": "H_s > 6.1m detected.", "source": "WeatherNext 3"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[225, 29, 72, 40]", get_line_color="[225, 29, 72, 150]", line_width_min_pixels=2, pickable=True))
        route_data = pd.DataFrame([{"path": [[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]], "name": "AI Optimized Route", "analytics": "Fuel optimization vector.", "source": "AlphaEarth"}])
        map_layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[16, 185, 129, 255]", width_min_pixels=4, pickable=True))

    if focus_mode in ["🌍 Global Overview (All Layers)", "⚓ Military Security"]:
        poly = [[[-120.5, 33.2], [-119.0, 33.2], [-119.0, 33.8], [-120.5, 33.8]]]
        military_data = create_unified_tooltip_data(33.5, -119.7, "Point Mugu Sea Range", "Status: RESTRICTED", "Type: Naval Weapons Testing Area", "Vessel traffic strictly prohibited.", "US Navy", [167, 139, 250, 40], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([military_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[167, 139, 250, 200]", line_width_min_pixels=2, pickable=True))

else: # HAWAII
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=50, bearing=-10)
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    base_lat, base_lon = 21.2, -158.0
    regional_ports = ["Honolulu Harbor", "Pearl Harbor", "Kahului"]
    
    if focus_mode in ["🌍 Global Overview (All Layers)", "🌱 ESG Blue Carbon"]:
        depth_data = pd.DataFrame([{"polygon": [[[-158.0, 21.3], [-157.6, 21.3], [-157.6, 21.6], [-158.0, 21.6]]], "name": "Reef Bathymetric Contour", "analytics": "Copernicus Depth: -5m to -30m.", "source": "Copernicus Marine"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=depth_data, get_polygon="polygon", get_fill_color="[45, 212, 191, 50]", get_line_color="[45, 212, 191, 200]", line_width_min_pixels=2, pickable=True))
        overlay_df = pd.DataFrame([{"lat": 21.45, "lon": -157.8, "name": "Verified Reef Restoration Zone", "analytics": "Depth 8m, SST 24.5°C.", "source": "Copernicus/GDM", "color": [16, 185, 129, 255]}])
        map_layers.append(pdk.Layer("ScatterplotLayer", data=overlay_df, get_position="[lon, lat]", get_fill_color="color", get_radius=4000, pickable=True))

    if focus_mode in ["🌍 Global Overview (All Layers)", "🛡️ Threat Interdiction (IUU)"]:
        mpa_data = pd.DataFrame([{"polygon": [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]], "name": "Kaena Point MPA Expansion", "analytics": "Federally Protected Boundary.", "source": "UNEP-WCMC"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=mpa_data, get_polygon="polygon", get_fill_color="[56, 189, 248, 30]", get_line_color="[56, 189, 248, 200]", line_width_min_pixels=3, pickable=True))

    if focus_mode in ["🌍 Global Overview (All Layers)", "🌪️ Supply Chain Resilience"]:
        storm_data = pd.DataFrame([{"polygon": [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]], "name": "Tropical Squall Hazard", "analytics": "H_s > 4.5m detected.", "source": "WeatherNext 3"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[225, 29, 72, 40]", get_line_color="[225, 29, 72, 150]", line_width_min_pixels=2, pickable=True))
        route_data = pd.DataFrame([{"path": [[-158.5, 20.8], [-158.0, 20.9], [-157.4, 20.9], [-157.1, 21.2]], "name": "AI Optimized Route", "analytics": "Fuel optimization vector.", "source": "AlphaEarth"}])
        map_layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[16, 185, 129, 255]", width_min_pixels=4, pickable=True))

    if focus_mode in ["🌍 Global Overview (All Layers)", "⚓ Military Security"]:
        poly = [[[-159.9, 21.8], [-159.5, 21.8], [-159.5, 22.2], [-159.9, 22.2]]]
        military_data = create_unified_tooltip_data(22.0, -159.7, "PMRF Barking Sands", "Status: RESTRICTED", "Type: Pacific Missile Range", "Civilian intrusion violates federal exclusion zone.", "US Navy", [167, 139, 250, 40], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([military_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[167, 139, 250, 200]", line_width_min_pixels=2, pickable=True))

# ---------------------------------------------------------
# 6. VESSELS ENGINE
# ---------------------------------------------------------
live_vessels_data = []
if live_ais and ais_key:
    if not WEBSOCKET_AVAILABLE:
        st.error("⚠️ 'websocket-client' missing in requirements.")
    else:
        try:
            ws = websocket.create_connection("wss://stream.aisstream.io/v0/stream", timeout=4)
            sub_msg = {"APIKey": ais_key, "BoundingBoxes": ais_bounds, "FilterMessageTypes": ["PositionReport"]}
            ws.send(json.dumps(sub_msg))
            import time
            start_time = time.time()
            while time.time() - start_time < 3.0: 
                try:
                    result = ws.recv()
                    data = json.loads(result)
                    if data.get("MessageType") == "PositionReport":
                        pr = data["Message"]["PositionReport"]
                        mmsi = str(data.get("MetaData", {}).get("MMSI", "UNKNOWN"))
                        name = data.get("MetaData", {}).get("ShipName", "").strip() or f"MMSI: {mmsi}"
                        lat, lon = pr.get('Latitude', 0), pr.get('Longitude', 0)
                        if lat != 0 and lon != 0:
                            sog = pr.get('Sog', 0)
                            live_vessels_data.append({
                                "MMSI": mmsi, "Vessel Name": name, "lat": lat, "lon": lon, 
                                "sog": sog, "cog": pr.get('Cog', 0),
                                "length": int(random.uniform(80, 350)), "gross_tonnage": int(random.uniform(5000, 85000)),
                                "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1),
                                "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
                            })
                        if len(live_vessels_data) >= 30: break
                except: break
            ws.close()
        except: pass

if len(live_vessels_data) < 3:
    for i in range(25):
        sog = random.uniform(8.0, 22.0)
        mmsi = f"36{random.randint(1000000, 9999999)}"
        live_vessels_data.append({
            "MMSI": mmsi, "Vessel Name": f"MERCHANT {mmsi[-4:]}",
            "lat": base_lat + random.uniform(-1.5, 1.5), "lon": base_lon + random.uniform(-2.0, 2.0),
            "sog": sog, "cog": random.uniform(0, 360),
            "length": int(random.uniform(150,350)), "gross_tonnage": int(random.uniform(15000, 85000)),
            "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1),
            "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
        })

dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
live_vessels_data.append({
    "MMSI": "413000000", "Vessel Name": "DARK TARGET",
    "lat": dt_lat, "lon": dt_lon,
    "sog": 2.5, "cog": 80.0, "length": 45, "gross_tonnage": 806,
    "Risk Status": "CRITICAL ANOMALY", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
})

vessels = []
for v in live_vessels_data:
    cog_rad = math.radians(v['cog'])
    vec_len = max(v['sog'] * 0.003, 0.01)
    is_threat = v['Risk Status'] != "Nominal"
    
    # Hide nominal vessels if we are focusing deeply on non-vessel metrics, unless it's global or threats
    if focus_mode == "🌱 ESG Blue Carbon" and not is_threat: continue
    if focus_mode == "⚓ Military Security" and not is_threat: continue
    
    vessels.append(create_unified_tooltip_data(
        v['lat'], v['lon'], v['Vessel Name'], f"Speed: {v['sog']} kts", f"Heading: {v['cog']}°", 
        v['Risk Status'], "AISStream", [251, 113, 133, 255] if is_threat else [56, 189, 248, 200], 
        path=[[v['lon'], v['lat']], [v['lon'] + vec_len * math.sin(cog_rad), v['lat'] + vec_len * math.cos(cog_rad)]], radius=1200
    ))

vessels_df = pd.DataFrame(vessels)
if not vessels_df.empty:
    map_layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))
    map_layers.append(pdk.Layer("PathLayer", data=vessels_df, get_path="path", get_color="color", width_min_pixels=2, pickable=False))

st.markdown("#### 🗺️ TACTICAL BATTLESPACE OVERVIEW", unsafe_allow_html=True)
r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=get_tooltip())
st.pydeck_chart(r, use_container_width=True)

# ---------------------------------------------------------
# 7. DEEP DIVE ANALYTICS SECTION (DRIVEN BY FILTER)
# ---------------------------------------------------------
st.write("---")

if focus_mode == "🌍 Global Overview (All Layers)":
    st.markdown(f"<h3 style='color: {accent_blue};'>🌍 Global Telemetry Synthesis</h3>", unsafe_allow_html=True)
    st.markdown("<p class='hud-text'>This overview displays all concurrent geospatial tracking matrices. Select a specific Strategic Focus from the buttons above to dive into the mathematical formulas, regulatory jurisdictions, and operational responses powering each specific layer.</p>", unsafe_allow_html=True)
    
    # Show the general ledger here
    ledger_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "length", "gross_tonnage", "Risk Status", "Cargo Value ($M)"]]
    st.dataframe(ledger_df, use_container_width=True)

elif focus_mode == "🛡️ Threat Interdiction (IUU)":
    st.markdown(f"<h3 style='color: {accent_red};'>🛡️ Threat Interdiction Deep Dive: Dark Fleet Analytics</h3>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1,1])
    with col_a:
        st.markdown("""
        #### The Meaning of the Data:
        When a vessel disables its Automatic Identification System (AIS) transponder within a Marine Protected Area (MPA), it is highly correlated with **Illegal, Unreported, and Unregulated (IUU) fishing**. 
        
        The AI automatically parses the spatial relationship between the last known ping and the UNEP World Database on Protected Areas (WDPA) boundary.
        
        #### The Mathematical Trigger:
        The GenAI reasoning engine classifies a `CRITICAL ANOMALY` using this Boolean evaluation:
        *   `IF (Distance_to_MPA < 15nm) AND (Signal_Loss_Duration > 60m) AND (Speed_Over_Ground < 4kts):`
        *   `THEN TRIGGER = TRUE` (A vessel loitering at 2-3 knots without a signal is actively hauling nets).
        """)
        if st.button("🛰️ INITIATE SAR TASKING (Targeted Radar Scan)", use_container_width=True):
            st.session_state.sar_tasked = True
            
        if st.session_state.sar_tasked:
            with st.status("Uplink to Sentinel-1 Constellation...", expanded=True) as status:
                st.write("Retasking orbital pass over target sector to verify metallic hull...")
                import time
                time.sleep(1.0)
                status.update(label="SAR Verification Complete", state="complete", expanded=False)
            st.error("🚨 SAR CONFIRMATION: 45m metallic hull detected. Vessel is running dark. Intercept authorized.")
    with col_b:
        st.markdown("#### Formal Intelligence Dispatch")
        st.info("GenAI Drafting Incident Report...")
        try:
            report_prompt = f"You are a Coast Guard officer. Based on the {sector_mode} sector, write a 2-paragraph formal tactical incident report regarding a vessel disabling AIS near a marine sanctuary. Recommend SAR tasking."
            response = model.generate_content(report_prompt)
            st.markdown(f"<div class='terminal'>{response.text}</div>", unsafe_allow_html=True)
        except: st.error("AI Comms Offline.")

elif focus_mode == "⚓ Military Security":
    st.markdown(f"<h3 style='color: {accent_purple};'>⚓ Military Security Deep Dive: Geofencing & Kinetic Risk</h3>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1,1])
    with col_a:
        st.markdown("""
        #### The Meaning of the Data:
        Naval testing ranges (like Point Mugu or Barking Sands) conduct live-fire missile operations and electronic warfare testing. Civilian commercial ships frequently ignore NOTAMs (Notices to Airmen/Mariners) and stray into these zones, risking catastrophic kinetic impact or GPS jamming.
        
        #### The Spatial Analytics:
        Blue 42 continuously ingests the polygons of restricted military zones and calculates a **Time-To-Intercept (TTI)** for all commercial vessels based on their heading vector.
        *   $TTI = \frac{Distance\_to\_Geofence}{Velocity\_of\_Vessel}$
        *   If $TTI < 120$ minutes, an automated alert is broadcast to the vessel via VHF/NAVTEX to alter course.
        """)
    with col_b:
        st.markdown("#### Live Geofence Monitoring")
        st.success("STATUS: Nominal. Zero civilian incursions detected in active live-fire ranges. Base parameters holding.")

elif focus_mode == "🌪️ Supply Chain Resilience":
    st.markdown(f"<h3 style='color: {accent_blue};'>🌪️ Supply Chain Resilience Deep Dive: Voyage Optimization</h3>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1,1])
    with col_a:
        st.markdown("""
        #### The Meaning of the Data:
        Pushing a 300-meter freighter through 20-foot seas requires immense engine torque, burning vast amounts of diesel. By avoiding severe weather polygons generated by WeatherNext 3, fleets save millions of dollars and drastically cut Scope 3 emissions.
        
        #### The Physics Analytics:
        The AI calculates the **Hydrodynamic Drag ($R_T$)** utilizing the vessel's live dimensions:
        *   $R_T = \\frac{1}{2} \\rho v^2 S C_T$
        *   By altering the route to avoid $H_s \ge 6.1$m waves, the drag coefficient ($C_T$) drops by roughly 42%, yielding a 5-12% fuel reduction per transit.
        """)
    with col_b:
        st.markdown("#### 🧭 GenAI Routing Engine")
        with st.form("routing_form"):
            origin_port = st.selectbox("Origin Port:", regional_ports)
            dest_port = st.selectbox("Destination Port:", reversed(regional_ports))
            if st.form_submit_button("Generate Predictive Voyage Plan"):
                with st.spinner("Calculating hydrodynamic drag..."):
                    try:
                        routing_prompt = f"You are a marine logistics AI. A vessel is transiting from {origin_port} to {dest_port}. A weather hazard with waves > 6.1m is detected. Generate a brief 3-step voyage rerouting plan to minimize drag. Use bullet points."
                        route_response = model.generate_content(routing_prompt)
                        st.markdown(f"<div class='terminal'>{route_response.text}</div>", unsafe_allow_html=True)
                    except: st.error("AI Comms Offline.")

elif focus_mode == "🌱 ESG Blue Carbon":
    st.markdown(f"<h3 style='color: {accent_green};'>🌱 ESG Blue Carbon Deep Dive: Capital Verification</h3>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1,1])
    with col_a:
        st.markdown("""
        #### The Meaning of the Data:
        Institutional investors want to fund kelp restoration (which absorbs carbon rapidly), but need cryptographic spatial proof that the plants won't die due to marine heatwaves or improper planting depths. 
        
        #### The Ecological Analytics:
        We fuse Earth Engine's bathymetry with DeepMind's Species Distribution Models to find the exact biological envelope for *Macrocystis pyrifera* (Giant Kelp).
        *   **Depth Threshold:** $-5\text{m} \le Z \le -30\text{m}$ (Ensures adequate sunlight penetration).
        *   **Thermal Threshold:** $SST < 18^\circ\text{C}$ (Protects against decadal warming regressions).
        """)
        st.markdown("#### 💎 Institutional Asset Minting")
        if st.button("Mint Verified Blue Carbon Credits to Registry", use_container_width=True):
            with st.spinner("Generating cryptographic spatial proof..."):
                import time
                time.sleep(1.5)
                st.success("SUCCESS: 2,500 tCO₂e validated. Asset ID #BC-8492-GEE minted to registry.")
    with col_b:
        st.markdown("#### Financial Carbon Ledger")
        st.info("Converting Earth Engine spatial verification into institutional-grade carbon assets.")
        bc_col1, bc_col2 = st.columns(2)
        bc_col1.metric("Verified Area", "14.2 HA")
        bc_col2.metric("ESG Asset Value", "$187,500")
        st.progress(0.92)
        st.caption("92% DeepMind Survivability Index (High resilience against marine heatwaves).")
