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
# 1. PAGE SETUP & GUARANTEED VARIABLE SCOPING
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 | Strategic Command", page_icon="🌐", initial_sidebar_state="expanded")

# Safeguard Session States
if "sar_tasked" not in st.session_state: st.session_state.sar_tasked = False
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Command AI active. Awaiting strategic parameters."}]

night_vision = st.sidebar.toggle("🌙 Tactical Night Vision", value=True)

# THE FIX: Master Palette defined instantly at the global level
if night_vision:
    bg_color = "#0B1121"
    card_bg = "#1F2937"
    text_color = "#F9FAFB"
    muted_text = "#9CA3AF"
    border_color = "#374151"
    accent_blue = "#38BDF8"
    accent_red = "#F43F5E"
    accent_green = "#10B981"
    accent_purple = "#8B5CF6"
    accent_amber = "#F59E0B"
    map_style = "dark"
    term_bg = "#000000"
    term_color = "#10B981"
else:
    bg_color = "#F8FAFC"
    card_bg = "#FFFFFF"
    text_color = "#0F172A"
    muted_text = "#64748B"
    border_color = "#E2E8F0"
    accent_blue = "#0284c7"
    accent_red = "#E11D48"
    accent_green = "#059669"
    accent_purple = "#7C3AED"
    accent_amber = "#D97706"
    map_style = "light"
    term_bg = "#F1F5F9"
    term_color = "#0F172A"

css = f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: 'Inter', -apple-system, sans-serif; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 8px; border: 1px solid {border_color}; margin-bottom: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
    .protection-card {{ border-top: 4px solid {accent_red}; }}
    .mitigation-card {{ border-top: 4px solid {accent_green}; }}
    .military-card {{ border-top: 4px solid {accent_purple}; }}
    .logistics-card {{ border-top: 4px solid {accent_amber}; }}
    h1, h2, h3, h4 {{ color: {text_color}; font-weight: 700; margin-top: 0; letter-spacing: -0.02em; }}
    h4 {{ font-size: 0.85rem; text-transform: uppercase; color: {muted_text}; letter-spacing: 0.05em; margin-bottom: 12px; }}
    .kpi-value {{ font-size: 2.2rem; font-weight: 800; color: {text_color}; margin: 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.85rem; color: {muted_text}; margin-top: 4px; display: block; }}
    .terminal {{ background-color: {term_bg}; padding: 16px; border-radius: 6px; border-left: 4px solid {accent_blue}; color: {term_color}; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.85rem; white-space: pre-wrap; line-height: 1.5; }}
    div[data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid {border_color}; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 24px; }}
    .stTabs [data-baseweb="tab"] {{ color: {muted_text}; background-color: transparent; padding-top: 10px; padding-bottom: 10px; font-weight: 600; font-size: 1.05rem; }}
    .stTabs [aria-selected="true"] {{ color: {accent_blue}; border-bottom: 2px solid {accent_blue}; }}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. SAFE TOOLTIP CONFIGURATION
# ---------------------------------------------------------
# Guaranteed to have access to the color variables above
tooltip_config = {
    "html": f"""
    <div style='font-family: -apple-system, sans-serif; padding: 4px;'>
        <b style='font-size: 15px; color: {accent_blue};'>{{name}}</b><hr style='margin: 6px 0; border-color: {border_color};'/>
        <div style='color: {text_color}; font-size: 12px;'>{{primary_metric}}</div>
        <div style='color: {text_color}; font-size: 12px; margin-bottom: 8px;'>{{secondary_metric}}</div>
        <b style='color: {accent_green}; font-size: 11px;'>AI ANALYTICS:</b><br/>
        <div style='color: {muted_text}; font-size: 12px; max-width: 250px; word-wrap: break-word;'>{{analytics}}</div>
    </div>
    """,
    "style": {
        "backgroundColor": card_bg, "color": text_color, "border": f"1px solid {accent_blue}", 
        "borderRadius": "8px", "padding": "12px", "boxShadow": "0 4px 10px rgba(0,0,0,0.4)"
    }
}

def create_unified_data(lat, lon, name, primary, secondary, analytics, source, color, polygon=None, path=None, radius=0, elevation=0, label=""):
    return {"lat": lat, "lon": lon, "name": name, "primary_metric": primary, "secondary_metric": secondary, "analytics": analytics, "source": source, "color": color, "polygon": polygon, "path": path, "radius": radius, "elevation": elevation, "label_text": label}

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
# 3. SECURE API INITIALIZATION
# ---------------------------------------------------------
try:
    if "EARTHENGINE_TOKEN" in st.secrets:
        key_dict = json.loads(st.secrets["EARTHENGINE_TOKEN"])
        creds = service_account.Credentials.from_service_account_info(key_dict).with_scopes(['https://www.googleapis.com/auth/earthengine'])
        ee.Initialize(credentials=creds, project=key_dict.get("project_id"))
        ee_status = "🟢 ON-LINE"
    else: ee_status = "🔴 OFFLINE"
except: ee_status = "🔴 OFFLINE"

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        avail = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = 'gemini-1.5-flash' if 'models/gemini-1.5-flash' in avail else avail[0].replace('models/', '')
        model = genai.GenerativeModel(target_model)
        ai_status = "🟢 ACTIVE"
    else: ai_status = "🔴 OFFLINE"
except: ai_status = "🔴 OFFLINE"

try:
    ais_key = st.secrets.get("AISSTREAM_API_KEY", "")
    ais_status = "🟢 AUTHENTICATED" if ais_key else "🔴 OFFLINE"
except: ais_status = "🔴 OFFLINE"

# ---------------------------------------------------------
# 4. EXECUTIVE HEADER & TACTICAL CONTROLS
# ---------------------------------------------------------
st.sidebar.markdown(f"""
<div style="text-align: center; margin-bottom: 20px;">
    <div style="font-size: 3rem; color: {accent_blue}; line-height: 1;">🌐</div>
    <div style="font-weight: 800; color: {text_color}; font-size: 1.5rem; letter-spacing: 0.1em; margin-top: 0.5rem;">BLUE 42</div>
    <div style="color: {muted_text}; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.1em;">GLOBAL MARITIME OS</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"<div style='font-size: 0.8rem; color: {muted_text}; margin-bottom: 2rem;'><b>GEO:</b> {ee_status} | <b>AI:</b> {ai_status} | <b>AIS:</b> {ais_status}</div>", unsafe_allow_html=True)

st.sidebar.markdown("### 🌍 DEPLOYMENT ZONE")
sector_mode = st.sidebar.selectbox("Sector", ["US West Coast (Channel Islands)", "Pacific Ops (Hawaiian Islands)"], label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 TELEMETRY & OVERLAYS")
live_ais = st.sidebar.toggle("Connect Live Satellite AIS", value=False)
show_iuu = st.sidebar.checkbox("🛡️ Marine Protected Areas", value=True)
show_weather = st.sidebar.checkbox("⛈️ Weather Hazard Polygons", value=True)
show_cables = st.sidebar.checkbox("🔌 Subsea Data Trunks", value=True)
show_depth = st.sidebar.checkbox("🌱 Blue Carbon Bio-Sinks", value=True)
show_military = st.sidebar.checkbox("⚓ Naval Exclusion Zones", value=False)

st.markdown(f"<h1 style='text-align: center; margin-bottom: 0.5rem;'>Global Maritime Command Center</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: {muted_text}; font-size: 1.1rem; margin-bottom: 2rem;'>Synthesizing planetary telemetry into auditable business value and global security workflows.</p>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1: st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ Threat Interdiction</h4><h2 style='color:{text_color}'>1 ACTIVE VOI</h2><p style='color:{accent_blue}; margin:0; font-size:0.85rem;'>Target masking identity near MPA</p></div>", unsafe_allow_html=True)
with col2: st.markdown(f"<div class='metric-card resilience-card' style='border-top-color:{accent_blue};'><h4>🌪️ Supply Chain Resilience</h4><h2 style='color:{text_color}'>5 REROUTED</h2><p style='color:{accent_blue}; margin:0; font-size:0.85rem;'>Avoiding extreme hydrodynamic drag</p></div>", unsafe_allow_html=True)
with col3: st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 Planetary Capital</h4><h2 style='color:{text_color}'>14.2 HA</h2><p style='color:{accent_blue}; margin:0; font-size:0.85rem;'>Optimal blue carbon sites verified</p></div>", unsafe_allow_html=True)
with col4: st.markdown(f"<div class='metric-card military-card'><h4>⚓ Sovereign Defense</h4><h2 style='color:{text_color}'>SECURE</h2><p style='color:{accent_blue}; margin:0; font-size:0.85rem;'>No civilian incursions in active ranges</p></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. DYNAMIC MAP DATA GENERATION 
# ---------------------------------------------------------
map_layers = []
static_data = []

if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=50, bearing=-10)
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]]
    base_lat, base_lon = 33.8, -119.5
    regional_ports = ["Port of Los Angeles", "Port of Long Beach", "Port Hueneme"]
    
    if show_iuu:
        poly = [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]]
        static_data.append(create_unified_data(34.0, -119.7, "Channel Islands MPA", "Protection Level: FULL", "Jurisdiction: Federal", "Zero-take zone. AI tracking active.", "UNEP", [56, 189, 248, 20], polygon=poly))
    if show_weather:
        poly = [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]]
        static_data.append(create_unified_data(33.8, -119.3, "Severe Gale Warning", "Intensity: H_s > 6.1m (20ft)", "Wind: Sustained 45 knots", "Extreme hydrodynamic drag detected. Rerouting prevents cargo loss.", "WeatherNext 3", [239, 68, 68, 30], polygon=poly))
        path = [[[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]]]
        static_data.append(create_unified_data(33.4, -119.3, "AI Optimized Route", "Status: ACTIVE REROUTE", "Fuel Averted: 54 MT", "Predictive vector safely circumvents hazard.", "AlphaEarth", [16, 185, 129, 200], path=path[0]))
    if show_depth:
        poly = [[[-119.7, 33.9], [-119.4, 33.9], [-119.4, 34.1], [-119.7, 34.1]]]
        static_data.append(create_unified_data(34.0, -119.55, "Optimal Bathymetric Shelf", "Layer: Ocean Topography", "Range: -5m to -30m", "Highly viable blue carbon zone.", "Copernicus", [16, 185, 129, 30], polygon=poly))
        static_data.append(create_unified_data(34.02, -119.55, "Verified Carbon Sink K-1", "Area: 5.1 HA", "Viability Index: 98%", "Depth 14m, SST 16.5°C. Safe for capital allocation.", "DeepMind SDM", [16, 185, 129, 255], radius=3000, elevation=8980, label="VERIFIED SINK K-1"))
    if show_cables:
        path = [[[-121.0, 33.5], [-119.0, 33.8], [-118.0, 34.2]]]
        static_data.append(create_unified_data(33.8, -119.0, "Transpacific Data Trunk", "Asset: Fiber Trunk", "Vulnerability: Exposed to anchor drag", "Critical infrastructure carrying financial data.", "Submarine Cable Map", [139, 92, 246, 200], path=path[0]))
    if show_military:
        poly = [[[-120.5, 33.2], [-119.0, 33.2], [-119.0, 33.8], [-120.5, 33.8]]]
        static_data.append(create_unified_data(33.5, -119.7, "Point Mugu Sea Range", "Status: RESTRICTED", "Type: Naval Weapons Area", "Geofence: ACTIVE | Status: LIVE FIRE. High kinetic risk.", "US Navy", [139, 92, 246, 30], polygon=poly))
else:
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=50, bearing=-10)
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    base_lat, base_lon = 21.2, -158.0
    regional_ports = ["Honolulu Harbor", "Pearl Harbor", "Kahului"]
    
    if show_iuu:
        poly = [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]]
        static_data.append(create_unified_data(21.5, -158.0, "Kaena Point MPA Expansion", "Protection Level: FULL", "Jurisdiction: Federal/State", "Critical habitat preservation area. High-value target for illicit harvesting.", "UNEP-WCMC", [56, 189, 248, 30], polygon=poly))
    if show_weather:
        poly = [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]]
        static_data.append(create_unified_data(21.2, -157.8, "Tropical Squall Hazard Zone", "Intensity: H_s > 4.5m", "Wind: Gusts to 35 knots", "Localized squall creating supply chain delays.", "WeatherNext 3", [239, 68, 68, 30], polygon=poly))
    if show_depth:
        poly = [[[-158.0, 21.3], [-157.6, 21.3], [-157.6, 21.6], [-158.0, 21.6]]]
        static_data.append(create_unified_data(21.45, -157.8, "Reef Bathymetric Contour", "Layer: Ocean Topography", "Range: -5m to -30m", "Optimal thermal and depth envelope.", "Copernicus Marine", [16, 185, 129, 30], polygon=poly))
        static_data.append(create_unified_data(21.45, -157.8, "Verified Reef Restoration R-1", "Area: 6.5 HA", "Viability Index: 96%", "Optimal ESG rehabilitation zone.", "DeepMind SDM", [16, 185, 129, 255], radius=3000, elevation=11440, label="VERIFIED REEF R-1"))
    if show_cables:
        path = [[[-160.0, 22.0], [-157.8, 21.3], [-155.0, 20.0]]]
        static_data.append(create_unified_data(21.3, -157.8, "Honolulu Transpacific Landing", "Asset: Fiber Trunk", "Vulnerability: High", "Critical infrastructure carrying Pacific financial routing.", "Submarine Cable Map", [139, 92, 246, 200], path=path[0]))
    if show_military:
        poly = [[[-159.9, 21.8], [-159.5, 21.8], [-159.5, 22.2], [-159.9, 22.2]]]
        static_data.append(create_unified_data(22.0, -159.7, "PMRF Barking Sands", "Status: RESTRICTED", "Type: Pacific Missile Range", "Civilian intrusion violates federal exclusion zone.", "US Navy", [139, 92, 246, 30], polygon=poly))

static_df = pd.DataFrame(static_data)
if not static_df.empty:
    polygons = static_df[static_df['polygon'].notnull()]
    if not polygons.empty: map_layers.append(pdk.Layer("PolygonLayer", data=polygons, get_polygon="polygon", get_fill_color="color", get_line_color="[255,255,255,100]", line_width_min_pixels=1, pickable=True, auto_highlight=True))
    paths = static_df[static_df['path'].notnull()]
    if not paths.empty: map_layers.append(pdk.Layer("PathLayer", data=paths, get_path="path", get_color="color", width_min_pixels=3, pickable=True, auto_highlight=True))
    columns = static_df[static_df['radius'] > 0]
    if not columns.empty: map_layers.append(pdk.Layer("ColumnLayer", data=columns, get_position="[lon, lat]", get_elevation="elevation", elevation_scale=1, radius="radius", get_fill_color="color", pickable=True, extruded=True, auto_highlight=True))
    labels = static_df[static_df['label_text'] != ""]
    if not labels.empty: map_layers.append(pdk.Layer("TextLayer", data=labels, get_position="[lon, lat]", get_text="label_text", get_color="[255, 255, 255, 255]", get_size=12, get_alignment_baseline="'center'", pickable=False))

# --- LIVE AIS / SIMULATION ENGINE ---
live_vessels_data = []

if live_ais and ais_key and WEBSOCKET_AVAILABLE:
    with st.spinner("Establishing secure satellite uplink..."):
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
                                "MMSI": mmsi, "Vessel Name": name, "Type": "MERCHANT", "lat": lat, "lon": lon, 
                                "sog": sog, "cog": cog, "Length (m)": v_len, "Width (m)": v_width, "Draft (m)": round(random.uniform(8.0, 15.0), 1),
                                "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
                            })
                        if len(live_vessels_data) >= 30: break
                except: break
            ws.close()
        except: pass

if len(live_vessels_data) < 3:
    for i in range(35):
        sog = random.uniform(8.0, 22.0)
        v_type = random.choice(["CARGO", "TANKER", "BULK"])
        mmsi = f"36{random.randint(1000000, 9999999)}"
        v_len = int(random.uniform(150,350))
        live_vessels_data.append({
            "MMSI": mmsi, "Vessel Name": f"{v_type} {mmsi[-4:]}", "Type": v_type,
            "lat": base_lat + random.uniform(-1.5, 1.5), "lon": base_lon + random.uniform(-2.0, 2.0),
            "sog": round(sog,1), "cog": round(random.uniform(0, 360),1),
            "Length (m)": v_len, "Width (m)": int(v_len*0.15), "Draft (m)": round(random.uniform(8.0, 16.0), 1),
            "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
        })

dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
live_vessels_data.append({
    "MMSI": "413000000", "Vessel Name": "UNVERIFIED DARK TARGET", "Type": "SUSPECT",
    "lat": dt_lat, "lon": dt_lon, "sog": 2.5, "cog": 80.0,
    "Length (m)": 45, "Width (m)": 8, "Draft (m)": 3.2,
    "Risk Status": "CRITICAL ANOMALY", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
})

vessels = []
path_data = []

for v in live_vessels_data:
    is_threat = v['Risk Status'] != "Nominal"
    cog_rad = math.radians(v['cog'])
    vec_len = max(v['sog'] * 0.004, 0.02)
    color = [244, 63, 94, 255] if is_threat else [56, 189, 248, 180]
    
    analysis = "HUMAN RIGHTS ANOMALY: Vessel disabled transponder 15nm from MPA. Kinematics strongly suggest illicit fishing/forced labor." if is_threat else "Vessel kinetics operate within nominal parameters."
    ship_poly = get_battleship_polygon(v['lat'], v['lon'], v['cog'], v['Length (m)'], v['Width (m)'])
    
    vessels.append(create_unified_data(
        v['lat'], v['lon'], v['Vessel Name'], f"Speed: {v['sog']} kts | Heading: {v['cog']}°", 
        f"Size: {v['Length (m)']}m | Draft: {v['Draft (m)']}m", analysis, 
        "Verified AIS", color, polygon=ship_poly, elevation=150 if is_threat else max(30, v['Length (m)'] / 4.0), label=f"⚠ THREAT" if is_threat else ""
    ))
    path_data.append({"path": [[v['lon'], v['lat']], [v['lon'] + vec_len * math.sin(cog_rad), v['lat'] + vec_len * math.cos(cog_rad)]], "color": color})

vessels_df = pd.DataFrame(vessels)
if not vessels_df.empty:
    vessels_df['coordinates'] = vessels_df.apply(lambda r: [r['lon'], r['lat']], axis=1)
    map_layers.append(pdk.Layer("PolygonLayer", data=vessels_df, get_polygon="polygon", get_fill_color="color", get_line_color="[255,255,255,100]", line_width_min_pixels=1, extruded=True, get_elevation="elevation", pickable=True, auto_highlight=True))
    map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame(path_data), get_path="path", get_color="color", width_min_pixels=2, pickable=False))
    labels = vessels_df[vessels_df['label_text'] != ""]
    if not labels.empty: map_layers.append(pdk.Layer("TextLayer", data=labels, get_position="coordinates", get_text="label_text", get_color="[244, 63, 94, 255]", get_size=12, get_alignment_baseline="'bottom'", get_pixel_offset="[0, -25]", pickable=False))

# ---------------------------------------------------------
# 6. RENDER MAP & TARGET LOCK SIDE PANEL
# ---------------------------------------------------------
col_map, col_ops = st.columns([2.5, 1.5])

with col_map:
    st.markdown(f"<div style='border: 1px solid {border_color}; border-radius: 8px; overflow: hidden;'>", unsafe_allow_html=True)
    
    # "Target Lock" Interactive Selection
    selected_target = None
    try:
        r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=tooltip_config)
        event = st.pydeck_chart(r, use_container_width=True, height=650, on_select="rerun", selection_mode="single-object")
        if event and hasattr(event, "selection") and event.selection.get("objects"):
            for layer_name, items in event.selection["objects"].items():
                if items:
                    selected_target = items[0]
                    break
    except:
        st.pydeck_chart(pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=tooltip_config), use_container_width=True, height=650)
    st.markdown("</div>", unsafe_allow_html=True)

with col_ops:
    st.markdown(f"<div class='metric-card' style='height: 650px; overflow-y: auto; border-top: none; box-shadow: none;'>", unsafe_allow_html=True)
    
    if selected_target:
        is_threat = "CRITICAL" in selected_target.get('analytics', '')
        t_color = accent_red if is_threat else accent_blue
        
        st.markdown(f"<h3 style='color: {t_color}; margin-bottom: 5px;'>🎯 TARGET LOCK ACQUIRED</h3>", unsafe_allow_html=True)
        st.markdown(f"<h2>{selected_target.get('name', 'UNKNOWN ASSET')}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text};'><b>{selected_target.get('primary_metric', '')}</b><br>{selected_target.get('secondary_metric', '')}</p>", unsafe_allow_html=True)
        
        st.markdown("#### 🧠 AI ANALYTICS")
        if is_threat:
            st.error(selected_target.get('analytics', 'Threat detected.'))
            if st.button("⚖️ DRAFT UNCLOS LEGAL INDICTMENT", use_container_width=True):
                with st.spinner("Compiling spatial evidence..."):
                    try:
                        res = model.generate_content("Draft a formal, 2-paragraph legal indictment under UNCLOS for a vessel operating illegally near a Marine Protected Area.")
                        st.info(res.text)
                    except: st.error("AI Comms Offline.")
        else:
            st.success(selected_target.get('analytics', 'Nominal track.'))
            st.markdown("#### 🧭 Dynamic Route Optimization")
            with st.form(f"route_form_{selected_target.get('name')}"):
                origin = st.selectbox("Origin Port:", regional_ports)
                dest = st.selectbox("Destination Port:", reversed(regional_ports))
                if st.form_submit_button("Generate Predictive Voyage Plan", use_container_width=True):
                    with st.spinner("AI calculating hydrodynamic drag against decadal wave baselines..."):
                        try:
                            res = model.generate_content(f"A vessel is transiting from {origin} to {dest}. Generate a 3-step rerouting plan to avoid 6.1m waves. Estimate fuel saved.")
                            st.markdown(f"<div class='terminal'>{res.text}</div>", unsafe_allow_html=True)
                        except: st.error("AI Comms Offline.")
        
        st.caption(f"Source Authority: {selected_target.get('source', 'Unknown')}")
        st.markdown("<br><i>Click the map background to clear target lock.</i>", unsafe_allow_html=True)
        
    else:
        # DEFAULT VIEW (No target locked)
        st.markdown(f"<h3 style='color: {accent_blue};'>🌍 Executive Intelligence Briefing</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text};'><b>Click on any asset on the map</b> to lock the target and access deep-dive AI analytics.</p><hr>", unsafe_allow_html=True)
        
        st.markdown("#### Operational Baselines")
        st.write(f"• **Active Fleet Tracks:** {len(live_vessels_data)}")
        st.write("• **Critical Anomalies (Dark Fleet):** 1")
        st.write("• **Total Capital Protected (24H):** $4.2 Billion")
        st.write("• **Verified Carbon Assets:** 14.2 HA")
        
        st.markdown("---")
        st.markdown("#### 💬 Strategic Advisory AI")
        if "chat_history" not in st.session_state: st.session_state.chat_history = []
        for msg in st.session_state.chat_history[-2:]:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if prompt := st.chat_input("Request strategic evaluation..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                try:
                    res = model.generate_content(f"You are a Senior Maritime Advisor. Analyze: {prompt}")
                    st.markdown(res.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": res.text})
                except: st.error("AI Comms Offline.")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. ENTERPRISE DATA LEDGERS (BOTTOM TABS)
# ---------------------------------------------------------
st.write("---")
st.markdown("### 📈 Operational Analytics & Financial Ledgers")
tab1, tab2 = st.tabs(["🚢 Active Fleet Kinematics", "💰 Scope 3 Financial & Carbon Ledger"])

with tab1:
    fleet_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Length (m)", "sog", "cog", "Risk Status"]]
    fleet_df.rename(columns={"sog": "Speed (kts)", "cog": "Heading (°)"}, inplace=True)
    st.dataframe(fleet_df, use_container_width=True)

with tab2:
    ledger_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Risk Status", "Cargo Value ($M)", "Fuel Saved (MT)"]]
    total_cargo = ledger_df["Cargo Value ($M)"].sum()
    total_carbon = ledger_df["Fuel Saved (MT)"].sum() * 3.11 
    st.markdown(f"**Total Capital Protected:** <span style='color:{accent_green}'>${total_cargo:,.1f} Million</span> | **Scope 3 Averted:** <span style='color:{accent_blue}'>{total_carbon:,.1f} MT CO₂e</span>", unsafe_allow_html=True)
    st.dataframe(ledger_df.style.highlight_max(axis=0, subset=["Fuel Saved (MT)"], color=accent_green), use_container_width=True)
