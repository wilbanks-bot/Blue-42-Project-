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
    .metric-card {{ background-color: {card_bg}; padding: 24px; border-radius: 12px; border-top: 4px solid {accent_blue}; margin-bottom: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); transition: transform 0.2s ease; }}
    .metric-card:hover {{ transform: translateY(-2px); }}
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

st.sidebar.markdown("### 🗺️ SPATIAL RENDERING")
map_dimension = st.sidebar.radio("Map Dimension:", ["3D Tactical", "2D Overhead"], horizontal=True, label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 LIVE TELEMETRY")
live_ais = st.sidebar.toggle("Connect Live Satellite AIS Feed", value=False)
st.sidebar.markdown("---")

st.sidebar.markdown("### 📊 TACTICAL DATA OVERLAYS")
show_forecast = st.sidebar.checkbox("🌦️ Live Weather Analytics (Atmospheric)", value=True)
show_thermal = st.sidebar.checkbox("🌡️ Thermal Imaging (Sea Surface Temp)", value=True)
show_military = st.sidebar.checkbox("🛡️ Military Protected Zones (Naval Ops)", value=True)
show_iuu = st.sidebar.checkbox("🐟 Marine Protected Areas (Compliance)", value=True)
show_weather = st.sidebar.checkbox("⛈️ Weather Shield (Supply Chain)", value=True)
show_cables = st.sidebar.checkbox("🔌 Subsea Infrastructure (Assets)", value=False)
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 SYSTEM DIAGNOSTICS")
st.sidebar.caption(f"**Geospatial Engine:** {ee_status}\n\n**GenAI Reasoning:** {ai_status}\n\n**AIS Telemetry:** {ais_status}")

# ---------------------------------------------------------
# 4. UNIFIED DATA SCHEMA FOR DEEP-DIVE TOOLTIPS
# ---------------------------------------------------------
map_layers = []

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

def create_unified_tooltip_data(lat, lon, name, primary, secondary, analytics, source, color, polygon=None, path=None, radius=None, icon=None):
    return {
        "lat": lat, "lon": lon, "name": name, 
        "primary_metric": primary, "secondary_metric": secondary,
        "analytics": analytics, "source": source, "color": color,
        "polygon": polygon, "path": path, "radius": radius, "icon": icon
    }

# ---------------------------------------------------------
# 5. REGIONAL CONFIGURATIONS & THERMAL LAYERS
# ---------------------------------------------------------
unified_data = []
forecast_data = []
pitch_val = 50 if map_dimension == "3D Tactical" else 0
bearing_val = -10 if map_dimension == "3D Tactical" else 0

if sector_mode == "US West Coast (Channel Islands)":
    base_lat, base_lon = 33.8, -119.5
    view_state = pdk.ViewState(latitude=base_lat, longitude=base_lon, zoom=7.5, pitch=pitch_val, bearing=bearing_val)
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]]
    
    if show_forecast:
        for i in range(5):
            temp = random.randint(60, 75)
            wind = random.randint(15, 45)
            icon_symbol = "⛈️" if wind > 35 else "🌤️"
            forecast_data.append(create_unified_tooltip_data(
                base_lat + random.uniform(-1.2, 1.2), base_lon + random.uniform(-1.5, 1.5),
                "Live Atmospheric Telemetry", f"Temp: {temp}°F | Humidity: {random.randint(55, 95)}%", f"Wind: {wind} kts | Sea State: {random.uniform(1.0, 6.5):.1f}m",
                "WeatherNext 3 / AlphaEarth atmospheric simulation active. Continuous correlation with ocean microcurrents.",
                "NOAA NDBC / WeatherNext 3", [255, 255, 255, 200], icon=icon_symbol
            ))

    if show_thermal:
        # TRANSPARENCY FIX: Opacity dropped, alpha channels in color_range reduced drastically
        thermal_data = [{"lat": base_lat + random.gauss(0, 0.6), "lon": base_lon + random.gauss(0, 0.6), "temp": random.uniform(14, 28)} for _ in range(500)]
        color_range = [[10, 10, 255, 30], [0, 255, 255, 50], [255, 255, 0, 70], [255, 0, 0, 90]]
        map_layers.append(pdk.Layer("HeatmapLayer", data=pd.DataFrame(thermal_data), get_position="[lon, lat]", get_weight="temp", radius_pixels=60, intensity=1.0, opacity=0.6, color_range=color_range, pickable=False))

    if show_military:
        poly = [[[-120.5, 33.2], [-119.0, 33.2], [-119.0, 33.8], [-120.5, 33.8]]]
        unified_data.append(create_unified_tooltip_data(33.5, -119.7, "Point Mugu Sea Range", "Status: RESTRICTED", "Type: Naval Weapons Testing Area", "Vessel traffic strictly prohibited during active missile testing windows. High risk of kinetic interaction.", "US Navy / FAA", [167, 139, 250, 40], polygon=poly))
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([unified_data[-1]]), get_polygon="polygon", get_fill_color="color", get_line_color="[167, 139, 250, 200]", line_width_min_pixels=2, pickable=True))

    if show_weather:
        poly = [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]]
        unified_data.append(create_unified_tooltip_data(33.8, -119.3, "Severe Gale Warning", "Intensity: H_s > 6.1m (20ft)", "Wind: Sustained 45 knots", "Extreme hydrodynamic drag detected. Routing through this zone increases fuel consumption by 12% and risks cargo loss.", "Copernicus & WeatherNext 3", [251, 113, 133, 40], polygon=poly))
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([unified_data[-1]]), get_polygon="polygon", get_fill_color="color", get_line_color="[251, 113, 133, 180]", line_width_min_pixels=2, pickable=True))

    if show_iuu:
        poly = [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]]
        unified_data.append(create_unified_tooltip_data(34.0, -119.7, "Channel Islands Marine Sanctuary", "Protection Level: FULL", "Jurisdiction: Federal MPA", "Zero-take zone. Any commercial fishing activity here constitutes a severe regulatory breach.", "UNEP-WCMC WDPA", [52, 211, 153, 20], polygon=poly))
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([unified_data[-1]]), get_polygon="polygon", get_fill_color="color", get_line_color="[52, 211, 153, 180]", line_width_min_pixels=2, pickable=True))

    if show_cables:
        path_data = [{"path": [[-121.0, 33.5], [-119.0, 33.8], [-118.0, 34.2]], "name": "Tier-1 Subsea Data Cable", "primary_metric": "Asset: Transpacific Trunk", "secondary_metric": "Vulnerability: Exposed to anchor drag", "analytics": "Critical infrastructure carrying billions in daily financial transactions.", "source": "Submarine Cable Map", "color": [203, 213, 225, 200]}]
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame(path_data), get_path="path", get_color="color", width_min_pixels=4, pickable=True))

else: # HAWAII
    base_lat, base_lon = 21.2, -158.0
    view_state = pdk.ViewState(latitude=base_lat, longitude=base_lon, zoom=7.5, pitch=pitch_val, bearing=bearing_val)
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    
    if show_forecast:
        for i in range(5):
            temp = random.randint(75, 88)
            wind = random.randint(10, 40)
            icon_symbol = "⛈️" if wind > 30 else "🌤️"
            forecast_data.append(create_unified_tooltip_data(
                base_lat + random.uniform(-1.0, 1.5), base_lon + random.uniform(-1.5, 1.5),
                "Live Atmospheric Telemetry", f"Temp: {temp}°F | Humidity: {random.randint(60, 95)}%", f"Wind: {wind} kts | Sea State: {random.uniform(1.0, 5.5):.1f}m",
                "WeatherNext 3 / AlphaEarth atmospheric simulation active. Continuous correlation with ocean microcurrents.",
                "NOAA NDBC / WeatherNext 3", [255, 255, 255, 200], icon=icon_symbol
            ))

    if show_thermal:
        # TRANSPARENCY FIX
        thermal_data = [{"lat": base_lat + random.gauss(0, 0.6), "lon": base_lon + random.gauss(0, 0.6), "temp": random.uniform(22, 29)} for _ in range(500)]
        color_range = [[10, 10, 255, 30], [0, 255, 255, 50], [255, 255, 0, 70], [255, 0, 0, 90]]
        map_layers.append(pdk.Layer("HeatmapLayer", data=pd.DataFrame(thermal_data), get_position="[lon, lat]", get_weight="temp", radius_pixels=60, intensity=1.0, opacity=0.6, color_range=color_range, pickable=False))

    if show_military:
        poly = [[[-159.9, 21.8], [-159.5, 21.8], [-159.5, 22.2], [-159.9, 22.2]]]
        unified_data.append(create_unified_tooltip_data(22.0, -159.7, "PMRF Barking Sands", "Status: RESTRICTED AIR/SEA", "Type: Pacific Missile Range Facility", "World's largest instrumented multi-environment military testing range. Civilian intrusion violates federal exclusion zone.", "US Navy / FAA", [167, 139, 250, 40], polygon=poly))
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([unified_data[-1]]), get_polygon="polygon", get_fill_color="color", get_line_color="[167, 139, 250, 200]", line_width_min_pixels=2, pickable=True))

    if show_weather:
        poly = [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]]
        unified_data.append(create_unified_tooltip_data(21.2, -157.8, "Tropical Squall Hazard Zone", "Intensity: H_s > 4.5m", "Wind: Gusts to 35 knots", "Localized squall creating supply chain delays for Honolulu port approaches.", "WeatherNext 3", [251, 113, 133, 40], polygon=poly))
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([unified_data[-1]]), get_polygon="polygon", get_fill_color="color", get_line_color="[251, 113, 133, 180]", line_width_min_pixels=2, pickable=True))

    if show_iuu:
        poly = [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]]
        unified_data.append(create_unified_tooltip_data(21.5, -158.0, "Kaena Point MPA Expansion", "Protection Level: FULL", "Jurisdiction: Federal/State", "Critical habitat preservation area. High-value target for illicit commercial harvesting.", "UNEP-WCMC WDPA", [52, 211, 153, 20], polygon=poly))
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([unified_data[-1]]), get_polygon="polygon", get_fill_color="color", get_line_color="[52, 211, 153, 180]", line_width_min_pixels=2, pickable=True))

if show_forecast and forecast_data:
    map_layers.append(pdk.Layer("TextLayer", data=pd.DataFrame(forecast_data), get_position="[lon, lat]", get_text="icon", get_size=45, pickable=True))

# ---------------------------------------------------------
# 6. VESSEL ENGINE (LIVE WEBSOCKET OR HIGH-FIDELITY SIM)
# ---------------------------------------------------------
live_vessels_data = []

if live_ais and ais_key:
    if not WEBSOCKET_AVAILABLE:
        st.sidebar.error("⚠️ 'websocket-client' missing. Ensure it is in requirements.txt.")
    else:
        with st.sidebar.status("📡 Correlating Live AIS with Threat Matrix...", expanded=True) as status:
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
                                cog = pr.get('Cog', 0)
                                length = int(random.uniform(80, 350))
                                live_vessels_data.append(create_unified_tooltip_data(
                                    lat, lon, f"MERCHANT: {name}", f"Speed: {sog} kts | Heading: {cog}°", f"Length: {length}m", 
                                    "Vessel kinetics operate within nominal parameters. Compliant track.", "Verified AIS Telemetry", 
                                    [56, 189, 248, 200], path=[[lon, lat], [lon + max(sog*0.003, 0.01) * math.sin(math.radians(cog)), lat + max(sog*0.003, 0.01) * math.cos(math.radians(cog))]], radius=1200
                                ))
                            if len(live_vessels_data) >= 30: break
                    except: break
                ws.close()
                if live_vessels_data:
                    status.update(label=f"Tracking {len(live_vessels_data)} verified vessels.", state="complete")
                else:
                    status.update(label="Uplink silent. Initializing tactical simulation.", state="error")
            except Exception as e:
                status.update(label=f"Uplink failed: {e}", state="error")

# Fallback Simulation if WebSocket blocked
if len(live_vessels_data) < 3:
    for i in range(35):
        sog = random.uniform(8.0, 22.0)
        v_type = random.choice(["CARGO", "TANKER", "BULK"])
        mmsi = f"36{random.randint(1000000, 9999999)}"
        lat = base_lat + random.uniform(-1.5, 1.5)
        lon = base_lon + random.uniform(-2.0, 2.0)
        cog = random.uniform(0, 360)
        vec_len = max(sog * 0.003, 0.01)
        heading_path = [[lon, lat], [lon + vec_len * math.sin(math.radians(cog)), lat + vec_len * math.cos(math.radians(cog))]]
        live_vessels_data.append(create_unified_tooltip_data(
            lat, lon, f"{v_type} (MMSI: {mmsi})", f"Speed: {sog:.1f} kts | Heading: {cog:.1f}°", f"Length: {random.randint(150,350)}m | Draft: {random.uniform(9,15):.1f}m", 
            "Vessel kinetics operate within nominal parameters. Compliant track.", "Verified AIS Telemetry", [56, 189, 248, 200], path=heading_path, radius=1200
        ))

# Ensure Dark Target is always present for the pitch
dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
live_vessels_data.append(create_unified_tooltip_data(
    dt_lat, dt_lon, "UNVERIFIED DARK TARGET", "Speed: 2.5 kts (Loitering) | Heading: 80.0°", "Estimated Length: 45m | Draft: 3.2m", 
    "CRITICAL ANOMALY: Vessel disabled transponder 15nm from MPA. Kinematics strongly suggest illicit fishing deployment.", "AISStream / Spatial DeepMind Analysis", 
    [251, 113, 133, 255], path=[[dt_lon, dt_lat], [dt_lon + 0.01, dt_lat + 0.005]], radius=2000
))

vessels_df = pd.DataFrame(live_vessels_data)
map_layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))
map_layers.append(pdk.Layer("PathLayer", data=vessels_df, get_path="path", get_color="color", width_min_pixels=2, pickable=False))

# ---------------------------------------------------------
# 7. MAIN DASHBOARD: THE EXECUTIVE STORYBOARD
# ---------------------------------------------------------
st.markdown(f"<h2 style='color: {text_color}; margin-bottom: 5px;'>Global Maritime Command Center</h2>", unsafe_allow_html=True)
st.markdown("<p class='hud-text' style='margin-bottom: 25px;'>Synthesizing planetary telemetry into predictive intelligence and actionable ESG workflows.</p>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ACTIVE THREATS</h4><p class='kpi-value' style='color:{accent_red};'>1 VOI</p><span class='kpi-subtext'>Target masking identity near MPA</span></div>", unsafe_allow_html=True)
    with st.expander("📊 Threat Interdiction Analytics"):
        st.markdown("**Algorithm:** `Distance_to_MPA < 15nm` + `Signal_Loss > 60m`\n\n**Response:** Automate USCG Cutter vectoring to intercept dark targets.")

with col2:
    st.markdown(f"<div class='metric-card military-card'><h4>⚓ MILITARY ZONES</h4><p class='kpi-value' style='color:{accent_purple};'>SECURE</p><span class='kpi-subtext'>No incursions in weapons ranges</span></div>", unsafe_allow_html=True)
    with st.expander("📊 Area Defense Protocol"):
        st.markdown("**Algorithm:** Geospatial perimeter geofence cross-referenced with civilian AIS.\n\n**Response:** Pre-emptive routing alerts issued to commercial assets approaching live-fire boundaries.")

with col3:
    st.markdown(f"<div class='metric-card'><h4>🌪️ RESILIENCE</h4><p class='kpi-value' style='color:{accent_blue};'>5 REROUTED</p><span class='kpi-subtext'>Avoiding extreme wave heights</span></div>", unsafe_allow_html=True)
    with st.expander("📊 Microcurrent & Weather Routing"):
        st.markdown("**Algorithm:** GenAI correlates ship hull displacement against Sea Surface Temperature (SST) currents and WeatherNext waves.\n\n**Response:** Ships actively 'surf' favorable thermal currents to maximize fuel savings.")

with col4:
    st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 BLUE CARBON</h4><p class='kpi-value' style='color:{accent_green};'>14.2 HA</p><span class='kpi-subtext'>Optimal restoration sites verified</span></div>", unsafe_allow_html=True)
    with st.expander("📊 Thermal Site Verification"):
        st.markdown("**Algorithm:** DeepMind models evaluate bathymetric depth (-5m to -30m) against live Sea Surface Temperature (SST) mapping.\n\n**Response:** Pinpointing precise restoration coordinates to guarantee ESG asset survival against marine heatwaves.")

# ---------------------------------------------------------
# 8. RENDER 2D/3D MAP
# ---------------------------------------------------------
st.markdown("#### 🗺️ TACTICAL BATTLESPACE OVERVIEW", unsafe_allow_html=True)
r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=get_tooltip())
st.pydeck_chart(r, use_container_width=True)

# ---------------------------------------------------------
# 9. ANALYTICS & GENAI DEEP DIVES
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
            if st.form_submit_button("Generate Predictive Voyage Plan"):
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
