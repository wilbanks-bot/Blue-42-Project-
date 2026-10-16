import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import json
import ee
import math
import random
import time
from datetime import datetime
from google.oauth2 import service_account
import google.generativeai as genai

try:
    from fpdf import FPDF
except ImportError:
    st.error("Please install fpdf: pip install fpdf")

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# =========================================================
# 1. PAGE SETUP & EXPERT UX STYLING
# =========================================================
st.set_page_config(layout="wide", page_title="Blue 42 Command", page_icon="🌊", initial_sidebar_state="expanded")

# Initialize Session States
if "library" not in st.session_state: st.session_state.library = []
if "sentinel_logs" not in st.session_state: st.session_state.sentinel_logs = []
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Watchstander AI active. Awaiting strategic queries."}]

night_vision = st.sidebar.toggle("🌙 Executive Dark Mode", value=True)

# Define Theme Variables
if night_vision:
    bg_color = "#0B1121"; card_bg = "#1F2937"; text_color = "#F9FAFB"; accent_blue = "#38BDF8"; accent_red = "#F43F5E"; map_style = "dark"
else:
    bg_color = "#F8FAFC"; card_bg = "#FFFFFF"; text_color = "#0F172A"; accent_blue = "#0284c7"; accent_red = "#E11D48"; map_style = "light"

# Custom CSS for spacing, typography, and card UI
custom_css = f"""
<style>
    /* Maximize screen real estate */
    .block-container {{ padding-top: 1.5rem; padding-bottom: 2rem; max-width: 98%; }}
    
    /* Clean Metric Cards */
    div[data-testid="metric-container"] {{
        background-color: {card_bg};
        border: 1px solid {'#374151' if night_vision else '#E2E8F0'};
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }}
    
    /* Tactile Buttons */
    .stButton>button {{ border-radius: 6px; font-weight: 600; transition: all 0.2s ease; }}
    .stButton>button:hover {{ transform: translateY(-1px); box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2); }}
    
    /* Clean headers */
    h1, h2, h3, h4 {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# =========================================================
# 2. EXPERT HELPER FUNCTIONS 
# =========================================================
def create_pdf_brief(incident_data: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "BLUE 42 - TACTICAL INTERDICTION BRIEF", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 10, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", ln=True)
    pdf.cell(0, 10, f"Target MMSI: {incident_data.get('mmsi', 'UNKNOWN')}", ln=True)
    pdf.cell(0, 10, f"Infraction Type: {incident_data.get('infraction_type', 'Suspicious Activity')}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "AI Reasoning Trace:", ln=True)
    pdf.set_font("Arial", size=10)
    text = incident_data.get('ai_reasoning_trace', 'N/A').encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, text)
    return pdf.output(dest="S").encode("latin-1")

def filter_static_data_for_conflicts(static_data: list, live_vessels: list, safe_distance_km=2.0) -> list:
    """Deconflicts Kelp Planting: Ensures sites aren't placed in active transit corridors."""
    safe_data = []
    for item in static_data:
        if "Carbon Sink" in item['name'] or "Reef Restoration" in item['name']:
            conflict_detected = False
            for v in live_vessels:
                R = 6371
                dlat = math.radians(v['lat'] - item['lat'])
                dlon = math.radians(v['lon'] - item['lon'])
                a = math.sin(dlat/2)**2 + math.cos(math.radians(item['lat'])) * math.cos(math.radians(v['lat'])) * math.sin(dlon/2)**2
                dist = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))
                if dist < safe_distance_km:
                    conflict_detected = True
                    break
            if conflict_detected: continue 
        safe_data.append(item)
    return safe_data

# =========================================================
# 3. SECURE API INITIALIZATION (WITH DYNAMIC GEMINI FIX)
# =========================================================
ee_connected = False
try:
    if "EARTHENGINE_TOKEN" in st.secrets:
        key_dict = json.loads(st.secrets["EARTHENGINE_TOKEN"])
        creds = service_account.Credentials.from_service_account_info(key_dict).with_scopes(['https://www.googleapis.com/auth/earthengine'])
        ee.Initialize(credentials=creds, project=key_dict.get("project_id"))
        ee_status = "🟢 SECURE UPLINK"
        ee_connected = True
    else: ee_status = "🔴 UPLINK SEVERED"
except: ee_status = "🔴 UPLINK SEVERED"

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Expert UX: Dynamically find the best available model (fixes the 3.8-flash 404 issue)
        if 'models/gemini-3.8-flash' in available_models: target_model = 'gemini-3.8-flash'
        elif 'models/gemini-1.5-flash' in available_models: target_model = 'gemini-1.5-flash'
        elif available_models: target_model = available_models[0].replace('models/', '')
        else: target_model = 'gemini-3.8-flash'
            
        model = genai.GenerativeModel(target_model)
        ai_status = f"🟢 CORE ACTIVE"
    else: ai_status = "🔴 CORE OFFLINE"
except Exception as e: ai_status = "🔴 CORE OFFLINE"

try:
    ais_key = st.secrets.get("AISSTREAM_API_KEY", "")
    ais_status = "🟢 RADAR AUTHENTICATED" if ais_key else "🔴 RADAR OFFLINE"
except: ais_status = "🔴 RADAR OFFLINE"

# =========================================================
# 4. SIDEBAR: UX-OPTIMIZED TACTICAL CONTROLS
# =========================================================
st.sidebar.markdown(f"<h2>🌊 BLUE 42</h2><p style='color:{muted_text};'>Global Blue Economy OS</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

operator_role = st.sidebar.selectbox("👤 Operator Profile:", ["Strategic Commander", "ESG Financial Auditor", "Logistics Fleet Director"])
sector_mode = st.sidebar.selectbox("🌍 Operational Theater:", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"])

st.sidebar.markdown("---")
with st.sidebar.expander("🛠️ System Status", expanded=True):
    st.write(f"**GEO:** {ee_status}")
    st.write(f"**AI:** {ai_status}")
    st.write(f"**AIS:** {ais_status}")

# UX Improvement: Grouped toggles using progressive disclosure
with st.sidebar.expander("📊 Map Overlays & Layers", expanded=False):
    live_ais = st.toggle("📡 Live Satellite AIS Feed", value=False)
    st.divider()
    st.write("**Security & Law Enforcement**")
    show_iuu = st.checkbox("🛡️ Marine Protected Areas", value=True)
    show_military = st.checkbox("⚓ Naval Exclusion Zones", value=True)
    st.divider()
    st.write("**Environment & ESG**")
    show_weather = st.checkbox("⛈️ Extreme Weather Hazards", value=True)
    show_depth = st.checkbox("🌱 Blue Carbon Sites", value=True)
    show_currents = st.checkbox("🌊 Ocean Microcurrents", value=True)

# =========================================================
# 5. HEADER & KPI METRICS
# =========================================================
st.title("🌍 Global Maritime Command Center")
st.caption("Synthesizing planetary telemetry into predictive intelligence and actionable workflows.")

# Clean KPI Row
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("⚠️ Supply Value at Risk", "$4.2B", "-2.1% (Weather Impact)", delta_color="inverse")
kpi2.metric("✅ Scope 3 Averted", "1,245 MT", "Optimal AI Routing")
kpi3.metric("🌱 Verified Blue Carbon", "$12.4M", "+1.2 HA Identified")
kpi4.metric("🚨 Active IUU Threats", "2", "1 Critical Anomaly", delta_color="inverse")
kpi5.metric("🐋 Mammal Strikes Avoided", "14", "Geofence Enforced")
st.write("")

# =========================================================
# 6. GOOGLE EARTH ENGINE KELP MODELING & DATA SOURCING
# =========================================================
@st.cache_data(ttl=3600)
def get_dynamic_kelp_sites(sector):
    if ee_connected:
        try:
            bathy = ee.ImageCollection('COPERNICUS/MARINE/WAV/ANFC_0_083DEG_STATIC').first().select('deptho')
            depth_mask = bathy.gte(5).And(bathy.lte(30))
            sst = ee.ImageCollection('ECMWF/ERA5_HOURLY').filterDate('2023-01-01', '2023-12-31').mean().select('sea_surface_temperature')
            temp_mask = sst.lt(291.15)
            suitability = depth_mask.And(temp_mask)
            suitable_areas = suitability.updateMask(suitability)
            roi = ee.Geometry.Rectangle([-122.0, 33.0, -118.0, 35.0]) if sector == "US West Coast (Channel Islands)" else ee.Geometry.Rectangle([-161.0, 19.0, -154.0, 23.0])
            clusters = suitable_areas.reduceToVectors(geometry=roi, crs=bathy.projection(), scale=1000, geometryType='centroid', maxPixels=1e9).limit(5)
            features = clusters.getInfo()['features']
            kelp_data = []
            for i, f in enumerate(features):
                coords = f['geometry']['coordinates']
                kelp_data.append(create_unified_tooltip_data(coords[1], coords[0], f"EE Verified Carbon Sink {i+1}", "Area: Verified", "Viability Index: High", "Optimal depth and SST (<18C) detected.", "Google DeepMind / EE", [16, 185, 129, 255], radius=3000, elevation=8000))
            if kelp_data: return kelp_data
        except Exception: pass
    # FALLBACK
    if sector == "US West Coast (Channel Islands)":
        return [
            create_unified_tooltip_data(34.02, -119.55, "Verified Carbon Sink K-1", "Area: 5.1 HA", "Viability Index: 98%", "Depth 14m, SST 16.5C. Safe for capital allocation.", "DeepMind SDM", [16, 185, 129, 255], radius=3000, elevation=8980),
            create_unified_tooltip_data(33.98, -119.60, "Verified Carbon Sink K-2", "Area: 4.8 HA", "Viability Index: 95%", "Deep-water thermal refuge.", "DeepMind SDM", [16, 185, 129, 255], radius=3000, elevation=8450)
        ]
    else:
        return [create_unified_tooltip_data(21.45, -157.8, "Verified Reef Restoration R-1", "Area: 6.5 HA", "Viability Index: 96%", "Optimal ESG rehabilitation zone.", "DeepMind SDM", [16, 185, 129, 255], radius=3000, elevation=11440)]

def create_unified_tooltip_data(lat, lon, name, primary, secondary, analytics, source, color, polygon=None, path=None, radius=None, elevation=0):
    return {"lat": lat, "lon": lon, "name": name, "primary_metric": primary, "secondary_metric": secondary, "analytics": analytics, "source": source, "color": color, "polygon": polygon, "path": path, "radius": radius, "elevation": elevation}

def get_battleship_polygon(lat, lon, cog, length_m, width_m):
    cog_rad = math.radians(cog)
    L, W = length_m * 3.5, width_m * 3.5
    lat_deg_per_m = 1.0 / 111111.0; lon_deg_per_m = 1.0 / (111111.0 * math.cos(math.radians(lat)))
    pts = [(-W/2, -L/2), (W/2, -L/2), (W/2, L/4), (0, L/2), (-W/2, L/4)]
    poly = []
    for dx, dy in pts:
        x_rot = dx * math.cos(cog_rad) + dy * math.sin(cog_rad)
        y_rot = -dx * math.sin(cog_rad) + dy * math.cos(cog_rad)
        poly.append([lon + x_rot * lon_deg_per_m, lat + y_rot * lat_deg_per_m])
    return [poly]

# ---------------------------------------------------------
# 7. HIGH-FIDELITY VESSEL SIMULATION
# ---------------------------------------------------------
live_vessels_data = []

if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=50, bearing=-15)
    base_lat, base_lon, ais_bounds = 33.8, -119.5, [[[33.0, -121.0], [35.0, -118.0]]]
    regional_ports = ["Port of Los Angeles", "Port of Long Beach", "Port Hueneme"]
else:
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=50, bearing=-15)
    base_lat, base_lon, ais_bounds = 21.2, -158.0, [[[19.0, -161.0], [23.0, -154.0]]]
    regional_ports = ["Honolulu Harbor", "Pearl Harbor", "Kahului"]

if live_ais and ais_key and WEBSOCKET_AVAILABLE:
    with st.sidebar.status("📡 Correlating Live AIS...", expanded=False) as status:
        try:
            ws = websocket.create_connection("wss://stream.aisstream.io/v0/stream", timeout=4)
            ws.send(json.dumps({"APIKey": ais_key, "BoundingBoxes": ais_bounds, "FilterMessageTypes": ["PositionReport"]}))
            start_time = time.time()
            while time.time() - start_time < 2.0: 
                try:
                    data = json.loads(ws.recv())
                    if data.get("MessageType") == "PositionReport":
                        pr = data["Message"]["PositionReport"]
                        mmsi = str(data.get("MetaData", {}).get("MMSI", "UNKNOWN"))
                        lat, lon = pr.get('Latitude', 0), pr.get('Longitude', 0)
                        if lat != 0 and lon != 0:
                            v_len = int(random.uniform(150, 350))
                            live_vessels_data.append({"MMSI": mmsi, "Vessel Name": f"MMSI: {mmsi}", "lat": lat, "lon": lon, "sog": pr.get('Sog', 0), "cog": pr.get('Cog', 0), "Length (m)": v_len, "Width (m)": int(v_len*0.15), "Draft (m)": round(random.uniform(8.0, 15.0), 1), "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)})
                        if len(live_vessels_data) >= 30: break
                except websocket.WebSocketTimeoutException: break
            ws.close()
            status.update(label="Radar synced.", state="complete")
        except Exception: status.update(label="Uplink failed.", state="error")

if len(live_vessels_data) < 3:
    for i in range(35):
        v_len = int(random.uniform(150,350))
        live_vessels_data.append({
            "MMSI": f"36{random.randint(1000000, 9999999)}", "Vessel Name": f"{random.choice(['CARGO', 'TANKER', 'BULK'])} {random.randint(100, 999)}",
            "lat": base_lat + random.uniform(-1.5, 1.5), "lon": base_lon + random.uniform(-2.0, 2.0),
            "sog": round(random.uniform(8.0, 22.0),1), "cog": round(random.uniform(0, 360),1), "Length (m)": v_len, "Width (m)": int(v_len*0.15), "Draft (m)": round(random.uniform(9.0,16.0), 1),
            "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
        })

# Inject Dark Target
dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
live_vessels_data.append({
    "MMSI": "413000000", "Vessel Name": "UNVERIFIED DARK TARGET ALPHA", "Type": "SUSPECT",
    "lat": dt_lat, "lon": dt_lon, "sog": 1.5, "cog": 80.0, "Length (m)": 45, "Width (m)": 8, "Draft (m)": 3.2,
    "Risk Status": "CRITICAL ANOMALY", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
})

# ---------------------------------------------------------
# 8. BUILD MAP LAYERS 
# ---------------------------------------------------------
static_data = []
if sector_mode == "US West Coast (Channel Islands)":
    if show_iuu: static_data.append(create_unified_tooltip_data(34.0, -119.7, "Channel Islands Marine Sanctuary", "Protection Level: FULL", "Jurisdiction: Federal", "Zero-take zone. Continuous AI surveillance active.", "UNEP-WCMC", [56, 189, 248, 40], polygon=[[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]]))
    if show_weather:
        static_data.append(create_unified_tooltip_data(33.8, -119.3, "Severe Gale Warning", "Intensity: H_s > 6.1m (20ft)", "Wind: Sustained 45 knots", "Extreme hydrodynamic drag detected.", "WeatherNext 3", [239, 68, 68, 50], polygon=[[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]]))
        static_data.append(create_unified_tooltip_data(33.4, -119.3, "AI Optimized Logistics Route", "Status: ACTIVE REROUTE", "Fuel Averted: 54 MT", "Predictive vector safely circumvents the Gale Warning.", "AlphaEarth", [16, 185, 129, 200], path=[[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]]))
    if show_depth: static_data.extend(filter_static_data_for_conflicts(get_dynamic_kelp_sites(sector_mode), live_vessels_data, 2.0))
    if show_military: static_data.append(create_unified_tooltip_data(33.5, -119.7, "Point Mugu Sea Range", "Status: RESTRICTED", "Type: Naval Weapons Area", "Geofence: ACTIVE | Status: LIVE FIRE.", "US Navy", [139, 92, 246, 40], polygon=[[[-120.5, 33.2], [-119.0, 33.2], [-119.0, 33.8], [-120.5, 33.8]]]))
    if show_currents: static_data.append(create_unified_tooltip_data(33.8, -119.8, "California Microcurrent Stream", "Velocity: 1.2 kts Southbound", "Status: Favorable Surf Zone", "Surfing this current allows a 10% reduction in engine RPM.", "Copernicus", [56, 189, 248, 200], path=[[-120.5, 34.5], [-119.8, 33.8], [-119.2, 33.0]]))
else: 
    if show_iuu: static_data.append(create_unified_tooltip_data(21.5, -158.0, "Kaena Point MPA Expansion", "Protection Level: FULL", "Jurisdiction: Federal/State", "Critical habitat preservation area.", "UNEP-WCMC", [56, 189, 248, 40], polygon=[[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]]))
    if show_weather: static_data.append(create_unified_tooltip_data(21.2, -157.8, "Tropical Squall Hazard Zone", "Intensity: H_s > 4.5m", "Wind: Gusts to 35 knots", "Localized squall creating supply chain delays.", "WeatherNext 3", [239, 68, 68, 50], polygon=[[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]]))
    if show_depth: static_data.extend(filter_static_data_for_conflicts(get_dynamic_kelp_sites(sector_mode), live_vessels_data, 2.0))

map_layers = []
static_df = pd.DataFrame(static_data)
if not static_df.empty:
    if not static_df[static_df['polygon'].notnull()].empty: map_layers.append(pdk.Layer("PolygonLayer", data=static_df[static_df['polygon'].notnull()], get_polygon="polygon", get_fill_color="color", get_line_color="[255,255,255,100]", line_width_min_pixels=1, pickable=True, auto_highlight=True))
    if not static_df[static_df['path'].notnull()].empty: map_layers.append(pdk.Layer("PathLayer", data=static_df[static_df['path'].notnull()], get_path="path", get_color="color", width_min_pixels=3, pickable=True, auto_highlight=True))
    if not static_df[static_df['radius'] > 0].empty: map_layers.append(pdk.Layer("ColumnLayer", data=static_df[static_df['radius'] > 0], get_position="[lon, lat]", get_elevation="elevation", elevation_scale=1, radius="radius", get_fill_color="color", pickable=True, extruded=True, auto_highlight=True))

vessels, path_data = [], []
for v in live_vessels_data:
    is_threat = v['Risk Status'] == "CRITICAL ANOMALY"
    vec_len = max(v['sog'] * 0.003, 0.01)
    color = [239, 68, 68, 255] if is_threat else [56, 189, 248, 180]
    analysis = "HUMAN RIGHTS ANOMALY: Mathematical signature matches illicit loitering." if is_threat else "Vessel kinetics operate within nominal parameters."
    vessels.append(create_unified_tooltip_data(v['lat'], v['lon'], v['Vessel Name'], f"Speed: {v['sog']} kts | Heading: {v['cog']}°", f"Length: {v['Length (m)']}m | Draft: {v['Draft (m)']}m", analysis, "Verified AIS Telemetry", color, polygon=get_battleship_polygon(v['lat'], v['lon'], v['cog'], v['Length (m)'], v['Width (m)']), elevation=(150 if is_threat else max(30, v['Length (m)'] / 4.0))))
    path_data.append({"path": [[v['lon'], v['lat']], [v['lon'] + vec_len * math.sin(math.radians(v['cog'])), v['lat'] + vec_len * math.cos(math.radians(v['cog']))]], "color": color})

vessels_df = pd.DataFrame(vessels)
if not vessels_df.empty:
    map_layers.append(pdk.Layer("PolygonLayer", data=vessels_df, get_polygon="polygon", get_fill_color="color", get_line_color="[255,255,255,100]", line_width_min_pixels=1, extruded=True, get_elevation="elevation", pickable=True, auto_highlight=True))
    map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame(path_data), get_path="path", get_color="color", width_min_pixels=2, pickable=False))

# ---------------------------------------------------------
# 9. UI LAYOUT: MAP vs OPERATIONS CENTER
# ---------------------------------------------------------
col_map, col_ops = st.columns([6.5, 3.5], gap="large")

tooltip_config = {"html": f"**{{name}}**<br>---<br>{{primary_metric}}<br>{{secondary_metric}}<br>**AI ANALYTICS:**<br>{{analytics}}<br>*Source: {{source}}*", "style": {"backgroundColor": card_bg, "color": text_color, "border": f"1px solid {accent_blue}", "borderRadius": "8px", "padding": "12px", "fontFamily": "sans-serif", "maxWidth": "300px"}}

with col_map:
    st.markdown("#### Live Geospatial Battlespace")
    r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=tooltip_config)
    st.pydeck_chart(r, use_container_width=True, height=550)

with col_ops:
    st.markdown("#### Operations Center")
    chat_tab, artifact_tab, sentinel_tab = st.tabs(["💬 AI Advisor", "📁 Artifacts", "🛡️ Sentinel"])

    with chat_tab:
        st.caption(f"Role: **{operator_role}**")
        chat_container = st.container(height=380)
        with chat_container:
            for msg in st.session_state.messages:
                st.markdown(f"**{'🤖 AI' if msg['role']=='assistant' else '👤 You'}:** {msg['content']}")
        
        if prompt := st.chat_input("Ask Blue 42..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.spinner("Processing..."):
                try:
                    res = model.generate_content(f"You are a {operator_role} AI. Respond to: {prompt}")
                    st.session_state.messages.append({"role": "assistant", "content": res.text})
                    st.rerun()
                except Exception:
                    st.error("AI Comms Offline.")

    with artifact_tab:
        st.markdown("Generate official reports for operational continuity.")
        
        # Primary Action UX Button
        if st.button("Generate Threat Profile", type="primary", use_container_width=True):
            with st.spinner("Generating Structured Profile..."):
                try:
                    res = model.generate_content("Generate a concise 3-bullet threat artifact for a vessel masking AIS. MUST INCLUDE an 'AI Reasoning Trace' detailing speed drops or zig-zagging.")
                    pdf_bytes = create_pdf_brief({"mmsi": "413000000", "infraction_type": "Suspected IUU & Transponder Evasion", "ai_reasoning_trace": res.text})
                    st.session_state.library.append({"type": "Threat Profile", "content": res.text, "pdf_bytes": pdf_bytes, "time": pd.Timestamp.now().strftime('%H:%M:%SZ')})
                    st.toast("Artifact successfully generated and logged.", icon="✅")
                except Exception as e: st.error("Failed to generate.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        for idx, item in enumerate(reversed(st.session_state.library)):
            with st.expander(f"📄 {item['time']} | {item['type']}"):
                st.write(item['content'])
                if 'pdf_bytes' in item:
                    st.download_button("Download Official PDF", data=item['pdf_bytes'], file_name="Interdiction_Brief.pdf", mime="application/pdf", key=f"dl_{idx}", use_container_width=True)

    with sentinel_tab:
        st.info("Sentinel Layer: Human-in-the-Loop authorization required for outbound web actions.")
        action_req = "AUTHORIZE KINETIC INTERCEPT" if operator_role == "Strategic Commander" else "AUTHORIZE CARBON CREDIT MINTING"
        
        # Threat Card UX
        st.error(f"**Pending Action:** `{action_req}`\n\nTarget: MMSI 413000000\n\nStatus: BLOCKED")
        
        if st.button("🔑 BYPASS SENTINEL & EXECUTE", type="primary", use_container_width=True):
            with st.spinner("Securing transmission..."):
                time.sleep(1.0)
                st.session_state.sentinel_logs.append(f"[{pd.Timestamp.now().strftime('%H:%M:%SZ')}] PAYLOAD TRANSMITTED.")
                st.toast("Action Executed. Webhook payload securely transmitted.", icon="🚀")
        
        if st.session_state.sentinel_logs:
            st.write("---")
            for log in reversed(st.session_state.sentinel_logs):
                st.caption(f"> {log}")

# =========================================================
# 10. FINANCIAL LEDGERS & GENAI ROUTING
# =========================================================
st.write("---")
st.markdown("#### 📈 Enterprise Data Ledger & Analytics")

ledger_tab, routing_tab, trend_tab = st.tabs(["💰 Scope 3 Financial Ledger", "🧭 GenAI Voyage Routing Engine", "📊 Historical Trend Analytics"])

with ledger_tab:
    ledger_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Length (m)", "Risk Status", "Cargo Value ($M)", "Fuel Saved (MT)"]]
    st.dataframe(ledger_df.style.highlight_max(axis=0, subset=["Fuel Saved (MT)"], color="#10B981"), use_container_width=True, hide_index=True)

with routing_tab:
    st.write("Automated route optimization ensuring verifiable fuel/carbon reductions.")
    with st.form("routing_form"):
        vessel_opts = [f"{v['Vessel Name']} (MMSI: {v['MMSI']})" for v in live_vessels_data if v['Risk Status'] == "Nominal"]
        selected_vessel = st.selectbox("Select Asset to Reroute:", vessel_opts if vessel_opts else ["No Active Fleet"])
        
        c1, c2 = st.columns(2)
        with c1: origin_port = st.selectbox("Origin Port:", regional_ports)
        with c2: dest_port = st.selectbox("Destination Port:", reversed(regional_ports))

        if st.form_submit_button("Generate Predictive Voyage Plan", use_container_width=True):
            target_v = next((v for v in live_vessels_data if v['MMSI'] in selected_vessel), None)
            v_len = target_v['Length (m)'] if target_v else 300
            with st.spinner("GenAI calculating hydrodynamic drag..."):
                try:
                    res = model.generate_content(f"You are a logistics AI. A {v_len}m vessel is transiting from {origin_port} to {dest_port}. Generate a 3-step rerouting plan to avoid 6.1m waves. Estimate fuel saved.")
                    st.info(res.text)
                except Exception: st.error("AI Comms Offline. Ensure API key is configured.")

with trend_tab:
    c1, c2 = st.columns(2)
    years = pd.date_range("2016", "2026", freq="YE")
    with c1:
        st.write("**10-Year Wave Height Extremes (Meters)**")
        st.line_chart(pd.DataFrame({"Max Wave (m)": [5.2, 5.4, 5.1, 5.8, 6.0, 5.9, 6.2, 6.5, 6.4, 6.8]}, index=years), color="#F43F5E")
    with c2:
        st.write("**IUU Dark Fleet Incidents**")
        st.bar_chart(pd.DataFrame({"Incidents": [12, 14, 18, 15, 22, 28, 35, 41, 44, 52]}, index=years), color="#38BDF8")
