import streamlit as st
import pydeck as pdk
import pandas as pd
import json
import ee
import asyncio
import websockets
from google.oauth2 import service_account
import google.generativeai as genai

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
    .kpi-impact {{ font-size: 0.875rem; color: {accent_green}; margin-top: 4px; display: block; }}
    .hud-text {{ color: #64748B; font-size: 0.875rem; line-height: 1.5; }}
    .terminal {{ background-color: {term_bg}; padding: 16px; border-radius: 6px; border-left: 4px solid {accent_blue}; color: {term_color}; font-family: 'SFMono-Regular', monospace; font-size: 0.85rem; white-space: pre-wrap; }}
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
    else:
        ee_status = "🔴 UPLINK SEVERED"
except Exception as e:
    ee_status = "🔴 UPLINK SEVERED"

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-2.5-flash')
        ai_status = "🟢 CORE ACTIVE"
    else:
        ai_status = "🔴 CORE OFFLINE"
except Exception as e:
    ai_status = "🔴 CORE OFFLINE"

try:
    ais_key = st.secrets.get("AISSTREAM_API_KEY", "")
    ais_status = "🟢 AISSTREAM AUTHENTICATED" if ais_key else "🔴 AISSTREAM OFFLINE"
except:
    ais_key = ""
    ais_status = "🔴 AISSTREAM OFFLINE"

# ---------------------------------------------------------
# 3. SIDEBAR: ENTERPRISE LOGO & STRATEGIC OVERLAYS
# ---------------------------------------------------------
st.sidebar.markdown(f"""
<div style="margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid {accent_blue};">
    <div style="font-size: 48px; color: {accent_blue}; line-height: 1;">🌐</div>
    <div style="font-weight: 800; color: {text_color}; font-size: 1.5rem; letter-spacing: 2px; margin-top: 5px;">BLUE 42 INTELLIGENCE</div>
    <div style="color: #64748B; font-size: 0.8rem; font-weight: 600; letter-spacing: 1px;">GLOBAL SUSTAINABILITY & RISK</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"<div class='hud-text'><b>Geospatial Engine:</b> {ee_status}<br><b>GenAI Reasoning:</b> {ai_status}<br><b>Radar Telemetry:</b> {ais_status}</div><hr>", unsafe_allow_html=True)

st.sidebar.markdown("### 🌍 REGIONAL DEPLOYMENT")
sector_mode = st.sidebar.selectbox("Select Operational Theater:", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"])
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 LIVE TELEMETRY")
live_ais = st.sidebar.toggle("Connect to Live AIS Satellite Feed", value=False)
st.sidebar.markdown("---")

st.sidebar.markdown("### 📊 STRATEGIC DATA OVERLAYS")
show_weather = st.sidebar.checkbox("⛈️ Supply Chain Resilience (Weather)", value=True)
show_iuu = st.sidebar.checkbox("🐟 Regulatory Compliance (IUU / MPAs)", value=True)
show_cables = st.sidebar.checkbox("🔌 Asset Protection (Subsea Cables)", value=False)
show_sar = st.sidebar.checkbox("🚁 Crisis Response (Predictive SAR)", value=False)
st.sidebar.markdown("---")

# ---------------------------------------------------------
# 4. REGIONAL DATA & LAYER AGGREGATION
# ---------------------------------------------------------
layers = []
radio_feeds = []
active_alerts = []
risk_level = "GREEN (Nominal Operational Risk)"

if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=50, bearing=-15)
    ais_bounds = [[[-121.0, 33.0], [-118.0, 35.0]]] # SoCal Bounding Box
    vessels_data = [
        {"lat": 34.12, "lon": -119.85, "name": "COMMERCIAL FREIGHTER", "type": "COMMERCIAL", "color": [37, 99, 235, 200], "analytics": "Vector normal.", "source": "Baseline AIS"},
        {"lat": 33.95, "lon": -120.15, "name": "UNVERIFIED ASSET", "type": "UNVERIFIED", "color": [225, 29, 72, 255], "analytics": "COMPLIANCE BREACH: Transponder disabled.", "source": "Anomaly Detection"}
    ]
    
    if show_weather:
        storm_data = pd.DataFrame([{"polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]]}])
        layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[225, 29, 72, 40]", get_line_color="[225, 29, 72, 150]", line_width_min_pixels=2))
        route_data = pd.DataFrame([{"path": [[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]]}])
        layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[16, 185, 129, 255]", width_min_pixels=4))
        active_alerts.append("Supply chain weather risk identified. Automated rerouting protocols initiated.")

    if show_iuu:
        radio_feeds.append("[14:02Z PORT AUTHORITY] 'Unregistered commercial trawler detected hauling nets 3nm off Santa Cruz Is.'\n> AI CROSS-REFERENCE: MMSI 413000000.")
        kelp_df = pd.DataFrame([{"lat": 34.02, "lon": -119.55, "name": "Verified Carbon Sink", "type": "KELP", "analytics": "Depth 14m, SST 16.5°C.", "source": "Copernicus/GDM", "color": [16, 185, 129, 255]}])
        layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_fill_color="color", get_radius=4000))
        active_alerts.append("Regulatory breach in protected biosphere. Significant ecological capital at risk.")
        risk_level = "RED (High Compliance Risk)"
        
    if show_cables:
        radio_feeds.append("[14:15Z INFRASTRUCTURE ALERT] 'Hydroacoustic anomaly detected.'\n> ASSET MATCH: Transpacific Data Trunk.")
        cable_data = pd.DataFrame([{"path": [[-121.0, 33.5], [-119.0, 33.8], [-118.0, 34.2]]}])
        layers.append(pdk.Layer("PathLayer", data=cable_data, get_path="path", get_color="[56, 189, 248, 255]", width_min_pixels=5))
        active_alerts.append("Asset vulnerability detected over Tier-1 fiber optic trunk.")
        risk_level = "RED (Critical Asset Risk)"
        
    if show_sar:
        radio_feeds.append("[14:22Z DISTRESS SIGNAL] 'S/V Orion. Engine failure. Lat 33.7, Lon -119.8.'\n> INITIATING: Predictive SAR Drift Grid.")
        sar_data = pd.DataFrame([{"polygon": [[[-120.5, 33.7], [-119.8, 33.7], [-119.6, 34.2], [-120.3, 34.2]]]}])
        layers.append(pdk.Layer("PolygonLayer", data=sar_data, get_polygon="polygon", get_fill_color="[245, 158, 11, 80]", get_line_color="[245, 158, 11, 255]", line_width_min_pixels=3))
        active_alerts.append("Vessel adrift. Humanitarian exposure. Drift vector calculating.")
        if risk_level == "GREEN (Nominal Operational Risk)": risk_level = "AMBER (Elevated Operational Risk)"

else:
    # PACIFIC (HAWAII) REGION
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=50, bearing=-15)
    ais_bounds = [[[-161.0, 19.0], [-154.0, 23.0]]] # Hawaii Bounding Box
    vessels_data = [
        {"lat": 21.1, "lon": -157.9, "name": "PACIFIC FREIGHT", "type": "COMMERCIAL", "color": [37, 99, 235, 200], "analytics": "Approaching Honolulu Port.", "source": "Baseline AIS"},
        {"lat": 21.6, "lon": -158.3, "name": "UNVERIFIED ASSET", "type": "UNVERIFIED", "color": [225, 29, 72, 255], "analytics": "COMPLIANCE BREACH: Transponder disabled.", "source": "Anomaly Detection"}
    ]
    
    if show_weather:
        storm_data = pd.DataFrame([{"polygon": [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]]}])
        layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[225, 29, 72, 40]", get_line_color="[225, 29, 72, 150]", line_width_min_pixels=2))
        route_data = pd.DataFrame([{"path": [[-158.5, 20.8], [-158.0, 20.9], [-157.4, 20.9], [-157.1, 21.2]]}])
        layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[16, 185, 129, 255]", width_min_pixels=4))
        active_alerts.append("Tropical squall identified. Rerouting protocols active.")

    if show_iuu:
        radio_feeds.append("[08:15W PORT AUTHORITY] 'Unidentified vessel deploying gear off Kaena Point MPA.'\n> AI CROSS-REFERENCE: MMSI 412999000.")
        overlay_df = pd.DataFrame([{"lat": 21.45, "lon": -157.8, "name": "Verified Reef Restoration Zone", "type": "REEF", "analytics": "Depth 8m, SST 24.5°C.", "source": "Copernicus/GDM", "color": [16, 185, 129, 255]}])
        layers.append(pdk.Layer("ScatterplotLayer", data=overlay_df, get_position="[lon, lat]", get_fill_color="color", get_radius=4000))
        active_alerts.append("Regulatory breach near protected reef. ESG investments at risk.")
        risk_level = "RED (High Compliance Risk)"
        
    if show_cables:
        radio_feeds.append("[08:30W INFRASTRUCTURE ALERT] 'Hydroacoustic anomaly detected.'\n> ASSET MATCH: Pacific Fiber Trunk.")
        overlay_data = pd.DataFrame([{"path": [[-160.0, 22.0], [-157.8, 21.3], [-155.0, 20.0]]}])
        layers.append(pdk.Layer("PathLayer", data=overlay_data, get_path="path", get_color="[56, 189, 248, 255]", width_min_pixels=5))
        active_alerts.append("Asset vulnerability detected at Honolulu landing trunk.")
        risk_level = "RED (Critical Asset Risk)"
        
    if show_sar:
        radio_feeds.append("[08:45W DISTRESS SIGNAL] 'F/V Makai. Engine fire. Lat 21.6, Lon -158.2.'\n> INITIATING: SAR Drift Grid.")
        sar_data = pd.DataFrame([{"polygon": [[[-158.5, 21.5], [-158.0, 21.5], [-158.0, 21.8], [-158.5, 21.8]]]}])
        layers.append(pdk.Layer("PolygonLayer", data=sar_data, get_polygon="polygon", get_fill_color="[245, 158, 11, 80]", get_line_color="[245, 158, 11, 255]", line_width_min_pixels=3))
        active_alerts.append("Vessel adrift in Kauai Channel. Humanitarian protocols activated.")
        if risk_level == "GREEN (Nominal Operational Risk)": risk_level = "AMBER (Elevated Operational Risk)"

# ---------------------------------------------------------
# 5. LIVE WEBSOCKET DATA INGESTION
# ---------------------------------------------------------
if live_ais and ais_key:
    with st.sidebar.status("📡 Connecting to Live AIS Satellite Network...", expanded=True) as status:
        try:
            async def get_live_ships():
                sub_msg = {"APIKey": ais_key, "BoundingBoxes": ais_bounds, "FilterMessageTypes": ["PositionReport"]}
                live_ships = []
                # Connect to global maritime socket
                async with websockets.connect("wss://stream.aisstream.io/v0/stream") as ws:
                    await ws.send(json.dumps(sub_msg))
                    # Listen for 3 seconds to gather a live batch
                    end_time = asyncio.get_event_loop().time() + 3.0
                    while asyncio.get_event_loop().time() < end_time:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                            data = json.loads(msg)
                            if data["MessageType"] == "PositionReport":
                                pr = data["Message"]["PositionReport"]
                                mmsi = str(data["MetaData"]["MMSI"])
                                name = data["MetaData"]["ShipName"].strip() if data["MetaData"]["ShipName"] else f"UNKNOWN (MMSI: {mmsi})"
                                live_ships.append({
                                    "lat": pr["Latitude"], 
                                    "lon": pr["Longitude"], 
                                    "name": name,
                                    "type": "LIVE VESSEL",
                                    "color": [37, 99, 235, 255] if "UNKNOWN" not in name else [225, 29, 72, 255],
                                    "analytics": f"Live SOG: {pr.get('Sog', 0)} knots. COG: {pr.get('Cog', 0)}°.",
                                    "source": "AISStream Live WebSocket"
                                })
                                if len(live_ships) >= 30: break
                        except asyncio.TimeoutError:
                            continue
                return live_ships

            live_vessels_data = asyncio.run(get_live_ships())
            if live_vessels_data:
                vessels_data = live_vessels_data # Override baseline with live data!
                status.update(label=f"Tracking {len(vessels_data)} live vessels in sector.", state="complete")
            else:
                status.update(label="No vessels broadcasting in sector right now. Using baseline.", state="error")
        except Exception as e:
            status.update(label=f"Uplink failed: {e}", state="error")

# Append vessel data to map
layers.append(pdk.Layer("ScatterplotLayer", data=pd.DataFrame(vessels_data), get_position="[lon, lat]", get_fill_color="color", get_line_color="[255,255,255,200]", stroked=True, line_width_min_pixels=2, get_radius=1500, pickable=True))

if not radio_feeds: radio_feeds.append("[14:30Z] Data streams clear. No material anomalies detected.")
if not active_alerts: active_alerts.append("All assets and protected zones operating within nominal parameters.")

radio_text = "\n\n".join(radio_feeds)
ai_summary_text = " | ".join(active_alerts)

# ---------------------------------------------------------
# 6. MAIN DASHBOARD: THE EXECUTIVE HUD & ROI METRICS
# ---------------------------------------------------------
st.markdown(f"<h2 style='color: {accent_blue};'>PROJECT BLUE 42: STRATEGIC INSIGHTS</h2>", unsafe_allow_html=True)
st.markdown("<p class='hud-text' style='margin-bottom: 20px;'>Transforming Planetary Telemetry into Auditable Business Value & Operational Continuity.</p>", unsafe_allow_html=True)

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
    st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ASSET & INFRASTRUCTURE PROTECTION</h4><p class='kpi-value' style='color:{accent_red};'>1 CRITICAL ANOMALY</p><span class='kpi-subtext'>10M Hectares Under Automated Surveillance</span><span class='kpi-impact'>Strategic ROI: Mitigating Regulatory Fines & Combating $20B IUU Market</span></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='metric-card'><h4>🌪️ SUPPLY CHAIN RESILIENCE</h4><p class='kpi-value'>5 VECTORS OPTIMIZED</p><span class='kpi-subtext'>Dynamic Weather Rerouting Activated</span><span class='kpi-impact'>Strategic ROI: $450K Fuel Cost Avoided (54 MT Scope 3 CO2e)</span></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 ESG CAPITAL ALLOCATION</h4><p class='kpi-value'>14 HA VERIFIED</p><span class='kpi-subtext'>Optimal Blue Carbon Sites Mathematically Identified</span><span class='kpi-impact'>Strategic ROI: 2,500 tCO2e Sequestration Potential Unlocked</span></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. ASSEMBLE MAP & TOOLTIPS
# ---------------------------------------------------------
custom_tooltip = {
    "html": f"<div style='font-family: -apple-system, sans-serif; padding: 10px;'><b style='color: {accent_blue}; font-size: 1.1em;'>{{name}}</b><br/><hr style='border-color: #333; margin: 8px 0;'/><b style='color: {accent_green};'>AI Insight:</b> <span style='color: #ccc;'>{{analytics}}</span><br/><b style='color: #888;'>Source:</b> <span style='color: #ccc;'>{{source}}</span></div>",
    "style": {"backgroundColor": "#1E293B", "border": f"1px solid {accent_blue}", "color": "#F8FAFC", "borderRadius": "8px", "boxShadow": "0 10px 15px -3px rgba(0, 0, 0, 0.5)"}
}

r = pdk.Deck(layers=layers, initial_view_state=view_state, map_style=map_style, tooltip=custom_tooltip)
st.pydeck_chart(r, use_container_width=True)

# ---------------------------------------------------------
# 8. TERMINALS: RADIO & GENAI CHAT
# ---------------------------------------------------------
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("### 📡 EXECUTIVE BRIEFING FEED")
    st.markdown(f"<div class='terminal'>{radio_text}</div>", unsafe_allow_html=True)
with col_b:
    st.markdown("### 🧭 GENAI ROUTING ENGINE")
    if st.button("Generate Voyage Plan Override"):
        with st.status("GenAI correlating live weather with decadal baseline..."):
            try:
                routing_prompt = f"You are a strategic marine logistics AI. The sector is {sector_mode}. A weather hazard with wave heights > 6.1m is detected. Generate a brief, highly technical 3-step voyage rerouting plan to minimize drag. Estimate bunker fuel saved. Use bullet points."
                route_response = model.generate_content(routing_prompt)
                st.success("Routing Plan Generated")
                st.markdown(f"<div class='terminal'>{route_response.text}</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error("Comms failure with GenAI Engine.")
