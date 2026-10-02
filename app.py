import streamlit as st
import pydeck as pdk
import pandas as pd
import json
import ee
import math
import asyncio
import websockets
from google.oauth2 import service_account
import google.generativeai as genai

# ---------------------------------------------------------
# 1. PAGE SETUP & THEME CONFIGURATION
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
    map_style = "satellite"; term_bg = "#F1F5F9"; term_color = "#0F172A"

css = f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    .metric-card {{ background-color: {card_bg}; padding: 24px; border-radius: 8px; border-top: 4px solid {accent_blue}; margin-bottom: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
    .protection-card {{ border-top: 4px solid {accent_red}; }}
    .mitigation-card {{ border-top: 4px solid {accent_green}; }}
    .alert-card {{ border: 1px solid {accent_red}; background-color: rgba(225, 29, 72, 0.05); border-left: 6px solid {accent_red}; animation: pulse-border 2s infinite; }}
    h2, h3, h4 {{ color: {text_color}; font-weight: 600; letter-spacing: -0.025em; margin-top: 0; }}
    h4 {{ font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748B; }}
    .kpi-value {{ font-size: 2.25rem; font-weight: 700; color: {text_color}; margin: 8px 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.875rem; color: #64748B; font-weight: 500; display: block; }}
    .kpi-impact {{ font-size: 0.875rem; color: {accent_green}; font-weight: 600; margin-top: 4px; display: block; }}
    .hud-text {{ color: #64748B; font-size: 0.875rem; line-height: 1.5; }}
    .terminal {{ background-color: {term_bg}; padding: 16px; border-radius: 6px; border-left: 4px solid {accent_blue}; color: {term_color}; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.85rem; white-space: pre-wrap; }}
    @keyframes pulse-border {{ 0% {{ box-shadow: 0 0 0 0 rgba(225, 29, 72, 0.4); }} 70% {{ box-shadow: 0 0 0 10px rgba(225, 29, 72, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(225, 29, 72, 0); }} }}
    .streamlit-expanderHeader {{ font-weight: 600 !important; font-size: 0.95rem; color: {text_color} !important; }}
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
# 3. SIDEBAR: ENTERPRISE LOGO & OVERLAYS
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
show_weather = st.sidebar.checkbox("⛈️ Supply Chain Resilience (Weather)", value=True)
show_iuu = st.sidebar.checkbox("🐟 Regulatory Compliance (IUU / MPAs)", value=True)
show_sar = st.sidebar.checkbox("🚁 Crisis Response (Predictive SAR)", value=False)
st.sidebar.markdown("---")

# ---------------------------------------------------------
# 4. DATA LOGIC & LIVE WEBSOCKET TRACKING
# ---------------------------------------------------------
layers = []
active_alerts = []
risk_level = "GREEN (Nominal Operational Risk)"

if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=50, bearing=-15)
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]] # Required AIS format: [Lat, Lon]
    
    # Baseline Boats (Used if Live Feed is OFF)
    vessels_data = [
        {"lat": 34.12, "lon": -119.85, "name": "COMMERCIAL FREIGHTER", "color": [37, 99, 235, 255], "sog": 12.4, "cog": 135, "analytics": "Vector normal.", "source": "Verified AIS"},
        {"lat": 33.95, "lon": -120.15, "name": "UNVERIFIED ASSET", "color": [225, 29, 72, 255], "sog": 9.1, "cog": 80, "analytics": "COMPLIANCE BREACH: Transponder disabled.", "source": "Anomaly Detection"}
    ]
    
    if show_weather:
        storm_data = pd.DataFrame([{"polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]], "name": "Severe Gale Warning", "analytics": "H_s > 6.1m detected.", "source": "WeatherNext 3", "sog": "N/A", "cog": "N/A"}])
        layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[225, 29, 72, 40]", get_line_color="[225, 29, 72, 150]", line_width_min_pixels=2, pickable=True))
        active_alerts.append("Supply chain weather risk identified.")

    if show_iuu:
        kelp_df = pd.DataFrame([{"lat": 34.02, "lon": -119.55, "name": "Verified Carbon Sink", "analytics": "Depth 14m, SST 16.5°C.", "source": "Copernicus/GDM", "color": [16, 185, 129, 255], "sog": "N/A", "cog": "N/A"}])
        layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_fill_color="color", get_radius=4000, pickable=True))
        active_alerts.append("Regulatory breach in protected biosphere.")
        risk_level = "RED (High Compliance Risk)"

    if show_sar:
        sar_data = pd.DataFrame([{"polygon": [[[-120.5, 33.7], [-119.8, 33.7], [-119.6, 34.2], [-120.3, 34.2]]], "name": "Predictive Drift Zone", "analytics": "AlphaEarth leeway grid.", "source": "WeatherNext 3", "sog": "N/A", "cog": "N/A"}])
        layers.append(pdk.Layer("PolygonLayer", data=sar_data, get_polygon="polygon", get_fill_color="[245, 158, 11, 80]", get_line_color="[245, 158, 11, 255]", line_width_min_pixels=3, pickable=True))
        active_alerts.append("Humanitarian exposure. Drift vector calculating.")
        if risk_level == "GREEN": risk_level = "AMBER (Elevated Operational Risk)"

else:
    # PACIFIC (HAWAII) REGION
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=50, bearing=-15)
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    
    vessels_data = [
        {"lat": 21.1, "lon": -157.9, "name": "PACIFIC FREIGHT", "color": [37, 99, 235, 255], "sog": 14.2, "cog": 310, "analytics": "Approaching Honolulu Port.", "source": "Verified AIS"},
        {"lat": 21.6, "lon": -158.3, "name": "UNVERIFIED ASSET", "color": [225, 29, 72, 255], "sog": 5.4, "cog": 45, "analytics": "COMPLIANCE BREACH.", "source": "Anomaly Detection"}
    ]

# ---------------------------------------------------------
# 5. FETCH LIVE SHIPS VIA SATELLITE (IF TOGGLED)
# ---------------------------------------------------------
if live_ais and ais_key:
    with st.sidebar.status("📡 Establishing WebSocket Uplink...", expanded=True) as status:
        try:
            def fetch_live_data():
                async def get_live_ships():
                    sub_msg = {"APIKey": ais_key, "BoundingBoxes": ais_bounds, "FilterMessageTypes": ["PositionReport"]}
                    live_ships = []
                    async with websockets.connect("wss://stream.aisstream.io/v0/stream") as ws:
                        await ws.send(json.dumps(sub_msg))
                        end_time = asyncio.get_event_loop().time() + 4.0
                        while asyncio.get_event_loop().time() < end_time:
                            try:
                                msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                                data = json.loads(msg)
                                if data.get("MessageType") == "PositionReport":
                                    pr = data["Message"]["PositionReport"]
                                    meta = data.get("MetaData", {})
                                    mmsi = str(meta.get("MMSI", "UNKNOWN"))
                                    name = meta.get("ShipName", "").strip()
                                    if not name: name = f"MMSI: {mmsi}"
                                    
                                    lat = pr.get('Latitude', 0)
                                    lon = pr.get('Longitude', 0)
                                    if lat == 0 and lon == 0: continue
                                    
                                    live_ships.append({
                                        "lat": lat, "lon": lon, 
                                        "name": name,
                                        "color": [37, 99, 235, 255],
                                        "analytics": "Live Tracking Active.",
                                        "source": "AISStream Live Satellite",
                                        "sog": pr.get('Sog', 0), "cog": pr.get('Cog', 0)
                                    })
                                    if len(live_ships) >= 40: break
                            except asyncio.TimeoutError: continue
                    return live_ships

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(get_live_ships())

            live_vessels_data = fetch_live_data()
            if live_vessels_data:
                vessels_data = live_vessels_data # Override baseline with LIVE data!
                status.update(label=f"Tracking {len(vessels_data)} live vessels in sector.", state="complete")
            else:
                status.update(label="No vessels broadcasting in sector right now. Using baseline.", state="error")
        except Exception as e:
            status.update(label=f"Uplink failed: {e}", state="error")

# ---------------------------------------------------------
# 6. ARPA RADAR VECTORS (CALCULATE SHIP HEADING & SPEED)
# ---------------------------------------------------------
# This converts Speed (SOG) and Direction (COG) into a physical line pointing on the map
for v in vessels_data:
    cog_rad = math.radians(v['cog'])
    length = max(v['sog'] * 0.003, 0.01) # Faster ships have longer lines
    v['heading_path'] = [[v['lon'], v['lat']], [v['lon'] + length * math.sin(cog_rad), v['lat'] + length * math.cos(cog_rad)]]

vessels_df = pd.DataFrame(vessels_data)

# Layer A: The Ship Dot
layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_fill_color="color", get_line_color="[255,255,255,200]", stroked=True, line_width_min_pixels=2, get_radius=1500, pickable=True))
# Layer B: The Heading Vector (The Line pointing direction)
layers.append(pdk.Layer("PathLayer", data=vessels_df, get_path="heading_path", get_color="color", width_min_pixels=3, pickable=False))
# Layer C: The Floating Text Name
layers.append(pdk.Layer("TextLayer", data=vessels_df, get_position="[lon, lat]", get_text="name", get_color="[255, 255, 255, 255]", get_size=13, get_alignment_baseline="'bottom'", get_pixel_offset="[0, -15]", pickable=False))

# ---------------------------------------------------------
# 7. MAIN DASHBOARD: THE EXECUTIVE HUD 
# ---------------------------------------------------------
if not active_alerts: active_alerts.append("All assets operating within nominal parameters.")
ai_summary_text = " | ".join(active_alerts)

st.markdown(f"<h2 style='color: {accent_blue};'>PROJECT BLUE 42: STRATEGIC INSIGHTS</h2>", unsafe_allow_html=True)
st.markdown("<p class='hud-text' style='margin-bottom: 20px;'>Transforming Planetary Telemetry into Auditable Business Value.</p>", unsafe_allow_html=True)

alert_class = "alert-card" if "RED" in risk_level else ""
st.markdown(f"""
<div class='metric-card {alert_class}'>
    <h4>⚠️ GENAI STRATEGIC RISK ASSESSMENT</h4>
    <p style='color: {text_color}; font-size: 1.1rem;'><b>ENTERPRISE THREAT LEVEL: <span style='color: {accent_red};'>{risk_level}</span></b></p>
    <p class='hud-text'>{ai_summary_text}</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ASSET PROTECTION</h4><p class='kpi-value' style='color:{accent_red};'>1 CRITICAL</p><span class='kpi-subtext'>10M Hectares Surveilled</span></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='metric-card'><h4>🌪️ RESILIENCE</h4><p class='kpi-value'>5 SHIPS</p><span class='kpi-subtext'>Dynamic Rerouting Active</span></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 MITIGATION</h4><p class='kpi-value'>14 HA</p><span class='kpi-subtext'>Blue Carbon Sites Verified</span></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 8. ASSEMBLE MAP & TOOLTIPS
# ---------------------------------------------------------
custom_tooltip = {
    "html": f"""
    <div style='font-family: -apple-system, sans-serif; padding: 10px; line-height: 1.4;'>
        <b style='color: {accent_blue}; font-size: 1.1em;'>{{name}}</b><br/>
        <span style='color: #E0E0E0; font-size: 0.9em;'>Speed: {{sog}} kts | Heading: {{cog}}&deg;</span>
        <hr style='border-color: #333; margin: 8px 0;'/>
        <b style='color: {accent_green};'>AI Insight:</b> <span style='color: #ccc;'>{{analytics}}</span><br/>
        <b style='color: #888;'>Source:</b> <span style='color: #ccc;'>{{source}}</span>
    </div>
    """,
    "style": {"backgroundColor": "#1E293B", "border": f"1px solid {accent_blue}", "color": "#F8FAFC", "borderRadius": "8px", "boxShadow": "0 10px 15px -3px rgba(0, 0, 0, 0.5)"}
}

r = pdk.Deck(layers=layers, initial_view_state=view_state, map_style=map_style, tooltip=custom_tooltip)
st.pydeck_chart(r, use_container_width=True)

# ---------------------------------------------------------
# 9. SIDEBAR: GENAI VOYAGE ROUTING ENGINE 
# ---------------------------------------------------------
st.sidebar.markdown("### 🧭 GENAI ROUTING ENGINE")
if st.sidebar.button("Generate Voyage Plan Override"):
    with st.sidebar.status("GenAI calculating hydrodynamic drag...", expanded=True):
        try:
            routing_prompt = f"You are a strategic marine logistics AI. The sector is {sector_mode}. A weather hazard with significant wave heights (H_s) > 6.1m is detected. Generate a brief, highly technical 3-step voyage rerouting plan to minimize drag. Estimate bunker fuel saved. Use bullet points."
            route_response = model.generate_content(routing_prompt)
            st.success("Routing Plan Generated")
            st.markdown(f"<div class='terminal'>{route_response.text}</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error("Comms failure with GenAI Engine.")
