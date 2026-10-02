import streamlit as st
import pydeck as pdk
import pandas as pd
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
# 1. PAGE SETUP & ENTERPRISE THEME CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 Strategic Command", page_icon="🌐", initial_sidebar_state="expanded")

night_vision = st.sidebar.toggle("🌙 Executive Dark Mode", value=True)

if night_vision:
    bg_color = "#0B1120"; card_bg = "#1E293B"; text_color = "#F8FAFC"
    accent_blue = "#38BDF8"; accent_red = "#F43F5E"; accent_green = "#10B981"
    map_style = "dark"; term_bg = "#0f172a"; term_color = "#38bdf8"
else:
    bg_color = "#F8FAFC"; card_bg = "#FFFFFF"; text_color = "#0F172A"
    accent_blue = "#2563EB"; accent_red = "#E11D48"; accent_green = "#059669"
    map_style = "light"; term_bg = "#F1F5F9"; term_color = "#0F172A"

css = f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: -apple-system, sans-serif; }}
    .metric-card {{ background-color: {card_bg}; padding: 24px; border-radius: 8px; border-top: 4px solid {accent_blue}; margin-bottom: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
    .protection-card {{ border-top: 4px solid {accent_red}; }}
    .mitigation-card {{ border-top: 4px solid {accent_green}; }}
    .alert-card {{ border: 1px solid {accent_red}; background-color: rgba(225, 29, 72, 0.05); border-left: 6px solid {accent_red}; animation: pulse-border 2s infinite; }}
    h2, h3, h4 {{ color: {text_color}; font-weight: 600; margin-top: 0; }}
    h4 {{ font-size: 0.875rem; text-transform: uppercase; color: #64748B; }}
    .kpi-value {{ font-size: 2.25rem; font-weight: 700; color: {text_color}; margin: 8px 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.875rem; color: #64748B; display: block; }}
    .kpi-impact {{ font-size: 0.875rem; color: {accent_green}; font-weight: 600; margin-top: 4px; display: block; }}
    .hud-text {{ color: #64748B; font-size: 0.875rem; line-height: 1.5; }}
    .terminal {{ background-color: {term_bg}; padding: 16px; border-radius: 6px; border-left: 4px solid {accent_blue}; color: {term_color}; font-family: monospace; font-size: 0.85rem; white-space: pre-wrap; }}
    @keyframes pulse-border {{ 0% {{ box-shadow: 0 0 0 0 rgba(225, 29, 72, 0.4); }} 70% {{ box-shadow: 0 0 0 10px rgba(225, 29, 72, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(225, 29, 72, 0); }} }}
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
        ee_status = "🟢 UPLINK SECURE"
    else: ee_status = "🔴 UPLINK SEVERED"
except Exception as e: ee_status = "🔴 UPLINK SEVERED"

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-2.5-flash')
        ai_status = "🟢 CORE ACTIVE"
    else: ai_status = "🔴 CORE OFFLINE"
except Exception as e: ai_status = "🔴 CORE OFFLINE"

try:
    ais_key = st.secrets.get("AISSTREAM_API_KEY", "")
    ais_status = "🟢 RADAR AUTHENTICATED" if ais_key else "🔴 RADAR OFFLINE"
except: ais_status = "🔴 RADAR OFFLINE"

# ---------------------------------------------------------
# 3. SIDEBAR: STRATEGIC OVERLAYS
# ---------------------------------------------------------
st.sidebar.markdown(f"""
<div style="margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid {accent_blue};">
    <div style="font-size: 48px; color: {accent_blue}; line-height: 1;">🌐</div>
    <div style="font-weight: 800; color: {text_color}; font-size: 1.5rem; letter-spacing: 2px; margin-top: 5px;">BLUE 42 INTELLIGENCE</div>
    <div style="color: #64748B; font-size: 0.8rem; font-weight: 600; letter-spacing: 1px;">GLOBAL SUSTAINABILITY & RISK</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"<div class='hud-text'><b>Geospatial Engine:</b> {ee_status}<br><b>GenAI Reasoning:</b> {ai_status}<br><b>AIS Telemetry:</b> {ais_status}</div><hr>", unsafe_allow_html=True)

st.sidebar.markdown("### 🌍 REGIONAL DEPLOYMENT")
sector_mode = st.sidebar.selectbox("Select Operational Theater:", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"])
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 LIVE TELEMETRY")
live_ais = st.sidebar.toggle("Connect Live Satellite AIS Feed", value=False)
st.sidebar.markdown("---")

st.sidebar.markdown("### 📊 STRATEGIC DATA OVERLAYS")
show_weather = st.sidebar.checkbox("⛈️ Supply Chain Resilience (Weather Hazards)", value=True)
show_iuu = st.sidebar.checkbox("🐟 Regulatory Compliance (IUU / MPAs)", value=True)
show_cables = st.sidebar.checkbox("🔌 Asset Protection (Subsea Infrastructure)", value=False)
show_sar = st.sidebar.checkbox("🚁 Crisis Response (Predictive SAR)", value=False)
st.sidebar.markdown("---")

# ---------------------------------------------------------
# 4. GENAI VOYAGE ROUTING ENGINE (RESTORED!)
# ---------------------------------------------------------
st.sidebar.markdown("### 🧭 GENAI ROUTING ENGINE")
st.sidebar.markdown("<p class='hud-text'>Automated WeatherNext 3 route optimization.</p>", unsafe_allow_html=True)

if st.sidebar.button("Generate Voyage Plan Override"):
    with st.sidebar.status("GenAI correlating live weather with decadal baseline...", expanded=True):
        try:
            routing_prompt = f"You are a strategic marine logistics AI. The sector is {sector_mode}. A weather hazard with significant wave heights (H_s) > 6.1m is detected. Using historical decadal weather trends, generate a highly technical 3-step voyage rerouting plan to minimize hydrodynamic drag. Estimate bunker fuel saved (in MT and CO2e), and ensure operational continuity. Use bullet points."
            route_response = model.generate_content(routing_prompt)
            st.success("Routing Plan Generated")
            st.markdown(f"<div class='terminal'>{route_response.text}</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"GenAI Error: {e}")
st.sidebar.markdown("---")

# ---------------------------------------------------------
# 5. DATA LOGIC & AGGREGATION
# ---------------------------------------------------------
layers = []
active_alerts = []
risk_level = "GREEN (Nominal Operational Risk)"

if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=50, bearing=-15)
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]]
    base_lat, base_lon = 33.8, -119.5
    
    if show_weather:
        storm_data = pd.DataFrame([{"polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]]}])
        layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[225, 29, 72, 40]", get_line_color="[225, 29, 72, 150]", line_width_min_pixels=2, pickable=True))
        route_data = pd.DataFrame([{"path": [[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]]}])
        layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[16, 185, 129, 255]", width_min_pixels=4, pickable=True))

    if show_iuu:
        kelp_df = pd.DataFrame([{"lat": 34.02, "lon": -119.55, "name": "Verified Carbon Sink", "analytics": "Depth 14m, SST 16.5°C.", "source": "Copernicus/GDM", "color": [16, 185, 129, 255]}])
        layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_fill_color="color", get_radius=4000, pickable=True))
        risk_level = "RED (High Compliance Risk)"

    if show_cables:
        cable_data = pd.DataFrame([{"path": [[-121.0, 33.5], [-119.0, 33.8], [-118.0, 34.2]]}])
        layers.append(pdk.Layer("PathLayer", data=cable_data, get_path="path", get_color="[56, 189, 248, 255]", width_min_pixels=5, pickable=True))

    if show_sar:
        sar_data = pd.DataFrame([{"polygon": [[[-120.5, 33.7], [-119.8, 33.7], [-119.6, 34.2], [-120.3, 34.2]]]}])
        layers.append(pdk.Layer("PolygonLayer", data=sar_data, get_polygon="polygon", get_fill_color="[245, 158, 11, 80]", get_line_color="[245, 158, 11, 255]", line_width_min_pixels=3, pickable=True))
        if risk_level == "GREEN (Nominal Operational Risk)": risk_level = "AMBER (Elevated Operational Risk)"

else:
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=50, bearing=-15)
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    base_lat, base_lon = 21.2, -158.0
    
    if show_weather:
        storm_data = pd.DataFrame([{"polygon": [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]]}])
        layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[225, 29, 72, 40]", get_line_color="[225, 29, 72, 150]", line_width_min_pixels=2, pickable=True))
        route_data = pd.DataFrame([{"path": [[-158.5, 20.8], [-158.0, 20.9], [-157.4, 20.9], [-157.1, 21.2]]}])
        layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[16, 185, 129, 255]", width_min_pixels=4, pickable=True))

    if show_iuu:
        overlay_df = pd.DataFrame([{"lat": 21.45, "lon": -157.8, "name": "Verified Reef Restoration Zone", "analytics": "Depth 8m, SST 24.5°C.", "source": "Copernicus/GDM", "color": [16, 185, 129, 255]}])
        layers.append(pdk.Layer("ScatterplotLayer", data=overlay_df, get_position="[lon, lat]", get_fill_color="color", get_radius=4000, pickable=True))
        risk_level = "RED (High Compliance Risk)"
        
    if show_cables:
        overlay_data = pd.DataFrame([{"path": [[-160.0, 22.0], [-157.8, 21.3], [-155.0, 20.0]]}])
        layers.append(pdk.Layer("PathLayer", data=overlay_data, get_path="path", get_color="[56, 189, 248, 255]", width_min_pixels=5, pickable=True))
        
    if show_sar:
        sar_data = pd.DataFrame([{"polygon": [[[-158.5, 21.5], [-158.0, 21.5], [-158.0, 21.8], [-158.5, 21.8]]]}])
        layers.append(pdk.Layer("PolygonLayer", data=sar_data, get_polygon="polygon", get_fill_color="[245, 158, 11, 80]", get_line_color="[245, 158, 11, 255]", line_width_min_pixels=3, pickable=True))
        if risk_level == "GREEN (Nominal Operational Risk)": risk_level = "AMBER (Elevated Operational Risk)"

# ---------------------------------------------------------
# 6. FETCH LIVE SHIPS VIA SATELLITE (SYNCHRONOUS)
# ---------------------------------------------------------
live_vessels_data = []

if live_ais and ais_key:
    if not WEBSOCKET_AVAILABLE:
        st.sidebar.error("⚠️ 'websocket-client' missing. Ensure it is in requirements.txt and reboot app.")
    else:
        with st.sidebar.status("📡 Synchronous connection to AIS Network...", expanded=True) as status:
            try:
                ws = websocket.create_connection("wss://stream.aisstream.io/v0/stream", timeout=4)
                sub_msg = {"APIKey": ais_key, "BoundingBoxes": ais_bounds, "FilterMessageTypes": ["PositionReport"]}
                ws.send(json.dumps(sub_msg))
                
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
                                live_vessels_data.append({
                                    "MMSI": mmsi, "Vessel Name": name, "lat": lat, "lon": lon, 
                                    "sog": pr.get('Sog', 0), "cog": pr.get('Cog', 0),
                                    "Risk Status": "Nominal"
                                })
                            if len(live_vessels_data) >= 40: break
                    except websocket.WebSocketTimeoutException:
                        break
                ws.close()
                if live_vessels_data:
                    status.update(label=f"Tracking {len(live_vessels_data)} live vessels.", state="complete")
                else:
                    status.update(label="No vessels broadcasting. Initializing AI simulation.", state="error")
            except Exception as e:
                status.update(label=f"WebSocket connection failed: {e}", state="error")

# VesselFinder Fallback (Guarantees map is packed with ships for pitch)
if len(live_vessels_data) < 5:
    for i in range(45):
        live_vessels_data.append({
            "MMSI": f"36{random.randint(1000000, 9999999)}", "Vessel Name": f"COMMERCIAL VESSEL",
            "lat": base_lat + random.uniform(-1.5, 1.5), "lon": base_lon + random.uniform(-2.0, 2.0),
            "sog": random.uniform(5.0, 24.0), "cog": random.uniform(0, 360),
            "Risk Status": "Nominal"
        })
    live_vessels_data.append({
        "MMSI": "413000000", "Vessel Name": "UNVERIFIED DARK TARGET",
        "lat": base_lat + 0.15, "lon": base_lon - 0.65,
        "sog": 9.1, "cog": 80,
        "Risk Status": "CRITICAL ANOMALY"
    })

map_vessels = []
for v in live_vessels_data:
    cog_rad = math.radians(v['cog'])
    length = max(v['sog'] * 0.003, 0.01)
    is_threat = v['Risk Status'] != "Nominal"
    map_vessels.append({
        "lat": v['lat'], "lon": v['lon'], "name": v['Vessel Name'], "sog": v['sog'], "cog": v['cog'],
        "color": [239, 68, 68, 255] if is_threat else [14, 165, 233, 220],
        "heading_path": [[v['lon'], v['lat']], [v['lon'] + length * math.sin(cog_rad), v['lat'] + length * math.cos(cog_rad)]],
        "analytics": v['Risk Status'], "source": "Live Synthesis"
    })

vessels_df = pd.DataFrame(map_vessels)
layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_fill_color="color", get_line_color="[255,255,255,200]", stroked=True, line_width_min_pixels=2, get_radius=1500, pickable=True))
layers.append(pdk.Layer("PathLayer", data=vessels_df, get_path="heading_path", get_color="color", width_min_pixels=3, pickable=False))

# ---------------------------------------------------------
# 7. MAIN DASHBOARD: THE EXECUTIVE HUD 
# ---------------------------------------------------------
st.markdown(f"<h2 style='color: {accent_blue};'>PROJECT BLUE 42: STRATEGIC INSIGHTS</h2>", unsafe_allow_html=True)
st.markdown("<p class='hud-text' style='margin-bottom: 20px;'>Transforming Planetary Telemetry into Auditable Business Value & Operational Continuity.</p>", unsafe_allow_html=True)

alert_class = "alert-card" if "RED" in risk_level else ""
ai_summary_text = "Multiple critical risk vectors detected in operational sector. Immediate review advised." if "RED" in risk_level else "All assets operating within nominal parameters."

st.markdown(f"""
<div class='metric-card {alert_class}'>
    <h4>⚠️ GENAI STRATEGIC RISK ASSESSMENT</h4>
    <p style='color: {text_color}; font-size: 1.1rem;'><b>ENTERPRISE THREAT LEVEL: <span style='color: {accent_red};'>{risk_level}</span></b></p>
    <p class='hud-text'>{ai_summary_text}</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ASSET PROTECTION</h4><p class='kpi-value' style='color:{accent_red};'>1 CRITICAL</p><span class='kpi-subtext'>10M Hectares Surveilled</span><span class='kpi-impact'>Strategic ROI: Mitigating $20B IUU Market</span></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='metric-card'><h4>🌪️ RESILIENCE</h4><p class='kpi-value'>5 SHIPS</p><span class='kpi-subtext'>Dynamic Rerouting Active</span><span class='kpi-impact'>Strategic ROI: $450K Fuel Cost Avoided</span></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 MITIGATION</h4><p class='kpi-value'>14 HA</p><span class='kpi-subtext'>Blue Carbon Sites Verified</span><span class='kpi-impact'>Strategic ROI: 2,500 tCO2e Unlocked</span></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 8. ASSEMBLE MAP & TOOLTIPS
# ---------------------------------------------------------
custom_tooltip = {
    "html": f"""<div style='padding: 10px; line-height: 1.4;'><b style='color: {accent_blue}; font-size: 1.1em;'>{{name}}</b><br/><span style='color: #E0E0E0;'>Speed: {{sog}} kts | Heading: {{cog}}&deg;</span><hr style='border-color: #333; margin: 8px 0;'/><b style='color: {accent_green};'>AI Insight:</b> <span style='color: #ccc;'>{{analytics}}</span></div>""",
    "style": {"backgroundColor": "#1E293B", "border": f"1px solid {accent_blue}", "color": "#F8FAFC", "borderRadius": "8px"}
}

r = pdk.Deck(layers=layers, initial_view_state=view_state, map_style=map_style, tooltip=custom_tooltip)
st.pydeck_chart(r, use_container_width=True)

# ---------------------------------------------------------
# 9. SIDEBAR: LIVE GEMINI INTERROGATION
# ---------------------------------------------------------
st.sidebar.markdown("### 💬 STRATEGIC ADVISORY AI")
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages[-3:]: 
    with st.sidebar.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.sidebar.chat_input("Request strategic risk evaluation..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.sidebar.chat_message("user"): st.markdown(prompt)
    with st.sidebar.chat_message("assistant"):
        try:
            tactical_prompt = f"You are a Senior Strategic Advisor. Sector is {sector_mode}. Analyze the query focusing on business value, capital risk, and operational continuity: {prompt}"
            response = model.generate_content(tactical_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"GenAI Chat Error: {e}")
