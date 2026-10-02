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

# ---------------------------------------------------------
# 1. PAGE SETUP & TACTICAL THEME CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 Strategic Command", page_icon="🌐", initial_sidebar_state="expanded")

night_vision = st.sidebar.toggle("🌙 Tactical Night Vision", value=True)

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
    h4 {{ font-size: 0.875rem; text-transform: uppercase; color: #64748B; letter-spacing: 0.1em; }}
    .kpi-value {{ font-size: 2.25rem; font-weight: 700; color: {text_color}; margin: 8px 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.875rem; color: #64748B; display: block; }}
    .kpi-impact {{ font-size: 0.875rem; color: {accent_green}; font-weight: 600; margin-top: 4px; display: block; }}
    .hud-text {{ color: #64748B; font-size: 0.875rem; line-height: 1.5; }}
    .terminal {{ background-color: {term_bg}; padding: 16px; border-radius: 6px; border-left: 4px solid {accent_blue}; color: {term_color}; font-family: 'Courier New', monospace; font-size: 0.85rem; white-space: pre-wrap; }}
    @keyframes pulse-border {{ 0% {{ box-shadow: 0 0 0 0 rgba(225, 29, 72, 0.4); }} 70% {{ box-shadow: 0 0 0 10px rgba(225, 29, 72, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(225, 29, 72, 0); }} }}
    .stTabs [data-baseweb="tab"] {{ height: 50px; background-color: transparent; border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px; }}
    .stTabs [aria-selected="true"] {{ background-color: {card_bg}; border-bottom: 2px solid {accent_blue}; color: {accent_blue}; }}
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
except Exception as e: ee_status = "🔴 UPLINK SEVERED"

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Fallback handling just in case of version 404s
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
        except:
            model = genai.GenerativeModel('gemini-1.0-pro')
        ai_status = "🟢 CORE ACTIVE"
    else: ai_status = "🔴 CORE OFFLINE"
except Exception as e: ai_status = "🔴 CORE OFFLINE"

try:
    ais_key = st.secrets.get("AISSTREAM_API_KEY", "")
    ais_status = "🟢 RADAR AUTHENTICATED" if ais_key else "🔴 RADAR OFFLINE"
except: ais_status = "🔴 RADAR OFFLINE"

# ---------------------------------------------------------
# 3. SIDEBAR: STRATEGIC OVERLAYS & OPCON
# ---------------------------------------------------------
st.sidebar.markdown(f"""
<div style="margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid {accent_blue};">
    <div style="font-size: 48px; color: {accent_blue}; line-height: 1;">🌐</div>
    <div style="font-weight: 800; color: {text_color}; font-size: 1.5rem; letter-spacing: 2px; margin-top: 5px;">BLUE 42 INTELLIGENCE</div>
    <div style="color: #64748B; font-size: 0.8rem; font-weight: 600; letter-spacing: 1px;">COMMON OPERATING PICTURE (COP)</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"<div class='hud-text'><b>Geospatial Engine:</b> {ee_status}<br><b>GenAI Reasoning:</b> {ai_status}<br><b>AIS Telemetry:</b> {ais_status}</div><hr>", unsafe_allow_html=True)

st.sidebar.markdown("### 🌍 SECTOR COMMAND")
sector_mode = st.sidebar.selectbox("Select Area of Responsibility (AOR):", ["Sector LA/LB (Channel Islands)", "Sector Honolulu (Hawaiian Islands)"])
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 LIVE TELEMETRY")
live_ais = st.sidebar.toggle("Initialize Live Satellite AIS", value=False)
st.sidebar.markdown("---")

st.sidebar.markdown("### 📊 TACTICAL OVERLAYS")
show_depth = st.sidebar.checkbox("🌊 Bathymetric Contours", value=True)
show_iuu = st.sidebar.checkbox("🐟 Marine Protected Areas (MPA)", value=True)
show_weather = st.sidebar.checkbox("⛈️ Extreme Weather Matrix", value=True)
show_cables = st.sidebar.checkbox("🔌 Subsea Infrastructure", value=False)
show_sar = st.sidebar.checkbox("🚁 Predictive SAR Drift", value=False)
st.sidebar.markdown("---")

# ---------------------------------------------------------
# 4. REGIONAL DATA & TACTICAL LOGIC
# ---------------------------------------------------------
layers = []
active_alerts = []
risk_level = "GREEN (Nominal)"

if sector_mode == "Sector LA/LB (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=50, bearing=-15)
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]]
    base_lat, base_lon = 33.8, -119.5
    regional_ports = ["Port of Los Angeles", "Port of Long Beach", "Port Hueneme", "San Diego"]
    friendly_cutter = {"lat": 33.75, "lon": -119.20, "name": "USCGC BLACKTIP (WPB-87326)", "type": "BLUE FORCE", "color": [56, 189, 248, 255], "sog": 18.5, "cog": 270, "analytics": "Patrol status nominal. Ready for intercept tasking.", "source": "Blue Force Tracker"}
    
    if show_depth:
        depth_data = pd.DataFrame([{"polygon": [[[-119.7, 33.9], [-119.4, 33.9], [-119.4, 34.1], [-119.7, 34.1]]], "name": "Optimal Bathymetric Shelf (-5m to -30m)", "analytics": "Viable Carbon Sink Depth", "source": "Copernicus Marine"}])
        layers.append(pdk.Layer("PolygonLayer", data=depth_data, get_polygon="polygon", get_fill_color="[45, 212, 191, 50]", get_line_color="[45, 212, 191, 200]", line_width_min_pixels=2, pickable=True))
        
    if show_iuu:
        mpa_data = pd.DataFrame([{"polygon": [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]], "name": "Channel Islands National Marine Sanctuary", "analytics": "Federally Protected Boundary", "source": "UNEP-WCMC"}])
        layers.append(pdk.Layer("PolygonLayer", data=mpa_data, get_polygon="polygon", get_fill_color="[16, 185, 129, 20]", get_line_color="[16, 185, 129, 200]", line_width_min_pixels=3, pickable=True))
        kelp_df = pd.DataFrame([{"lat": 34.02, "lon": -119.55, "name": "Verified Carbon Sink", "analytics": "High-yield Blue Carbon potential.", "source": "GDM", "color": [16, 185, 129, 255]}])
        layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_fill_color="color", get_radius=4000, pickable=True))
        risk_level = "RED (Active Threat)"

    if show_weather:
        storm_data = pd.DataFrame([{"polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]], "name": "Severe Gale Warning", "analytics": "H_s > 6.1m detected. High drag coefficient.", "source": "WeatherNext 3"}])
        layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[225, 29, 72, 40]", get_line_color="[225, 29, 72, 150]", line_width_min_pixels=2, pickable=True))
        route_data = pd.DataFrame([{"path": [[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]], "name": "AI Optimized Logistics Route", "analytics": "Fuel optimization vector.", "source": "AlphaEarth"}])
        layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[16, 185, 129, 255]", width_min_pixels=4, pickable=True))

    if show_cables:
        cable_data = pd.DataFrame([{"path": [[-121.0, 33.5], [-119.0, 33.8], [-118.0, 34.2]], "name": "Tier-1 Transpacific Data Trunk", "analytics": "Critical infrastructure carrying financial data.", "source": "Submarine Cable Map"}])
        layers.append(pdk.Layer("PathLayer", data=cable_data, get_path="path", get_color="[56, 189, 248, 255]", width_min_pixels=5, pickable=True))

    if show_sar:
        sar_data = pd.DataFrame([{"polygon": [[[-120.5, 33.7], [-119.8, 33.7], [-119.6, 34.2], [-120.3, 34.2]]], "name": "Predictive Drift Zone", "analytics": "AlphaEarth leeway grid based on 22kt winds.", "source": "WeatherNext 3"}])
        layers.append(pdk.Layer("PolygonLayer", data=sar_data, get_polygon="polygon", get_fill_color="[245, 158, 11, 80]", get_line_color="[245, 158, 11, 255]", line_width_min_pixels=3, pickable=True))
        if risk_level == "GREEN (Nominal)": risk_level = "AMBER (SAR Active)"

else:
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=50, bearing=-15)
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    base_lat, base_lon = 21.2, -158.0
    regional_ports = ["Honolulu Harbor", "Pearl Harbor", "Kahului", "Hilo Harbor", "Nawiliwili"]
    friendly_cutter = {"lat": 21.25, "lon": -157.85, "name": "USCGC OLIVER BERRY (WPC-1124)", "type": "BLUE FORCE", "color": [56, 189, 248, 255], "sog": 24.0, "cog": 300, "analytics": "Fast Response Cutter. On patrol.", "source": "Blue Force Tracker"}
    
    if show_depth:
        depth_data = pd.DataFrame([{"polygon": [[[-158.0, 21.3], [-157.6, 21.3], [-157.6, 21.6], [-158.0, 21.6]]], "name": "Reef Bathymetric Contour", "analytics": "Copernicus Depth: -5m to -30m.", "source": "Copernicus Marine Bathymetry"}])
        layers.append(pdk.Layer("PolygonLayer", data=depth_data, get_polygon="polygon", get_fill_color="[45, 212, 191, 50]", get_line_color="[45, 212, 191, 200]", line_width_min_pixels=2, pickable=True))

    if show_iuu:
        mpa_data = pd.DataFrame([{"polygon": [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]], "name": "Kaena Point MPA", "analytics": "Federally Protected Boundary.", "source": "UNEP-WCMC"}])
        layers.append(pdk.Layer("PolygonLayer", data=mpa_data, get_polygon="polygon", get_fill_color="[16, 185, 129, 20]", get_line_color="[16, 185, 129, 200]", line_width_min_pixels=3, pickable=True))
        overlay_df = pd.DataFrame([{"lat": 21.45, "lon": -157.8, "name": "Verified Reef Restoration Zone", "analytics": "Optimal ESG rehabilitation zone.", "source": "GDM", "color": [16, 185, 129, 255]}])
        layers.append(pdk.Layer("ScatterplotLayer", data=overlay_df, get_position="[lon, lat]", get_fill_color="color", get_radius=4000, pickable=True))
        risk_level = "RED (Active Threat)"

    if show_weather:
        storm_data = pd.DataFrame([{"polygon": [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]], "name": "Tropical Squall Hazard Zone", "analytics": "H_s > 4.5m detected.", "source": "WeatherNext 3"}])
        layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[225, 29, 72, 40]", get_line_color="[225, 29, 72, 150]", line_width_min_pixels=2, pickable=True))
        route_data = pd.DataFrame([{"path": [[-158.5, 20.8], [-158.0, 20.9], [-157.4, 20.9], [-157.1, 21.2]], "name": "AI Optimized Logistics Route", "analytics": "Fuel optimization vector.", "source": "AlphaEarth Optimization"}])
        layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[16, 185, 129, 255]", width_min_pixels=4, pickable=True))
        
    if show_cables:
        overlay_data = pd.DataFrame([{"path": [[-160.0, 22.0], [-157.8, 21.3], [-155.0, 20.0]], "name": "Honolulu Transpacific Landing", "analytics": "Critical infrastructure.", "source": "Submarine Cable Map"}])
        layers.append(pdk.Layer("PathLayer", data=overlay_data, get_path="path", get_color="[56, 189, 248, 255]", width_min_pixels=5, pickable=True))
        
    if show_sar:
        sar_data = pd.DataFrame([{"polygon": [[[-158.5, 21.5], [-158.0, 21.5], [-158.0, 21.8], [-158.5, 21.8]]], "name": "Predictive Drift Zone", "analytics": "Leeway grid based on 25kt Trade Winds.", "source": "WeatherNext 3"}])
        layers.append(pdk.Layer("PolygonLayer", data=sar_data, get_polygon="polygon", get_fill_color="[245, 158, 11, 80]", get_line_color="[245, 158, 11, 255]", line_width_min_pixels=3, pickable=True))
        if risk_level == "GREEN (Nominal)": risk_level = "AMBER (SAR Active)"

# ---------------------------------------------------------
# 5. DYNAMIC VESSEL SIMULATION & BLUE FORCE TRACKING
# ---------------------------------------------------------
live_vessels_data = []

if live_ais and ais_key:
    with st.sidebar.status("📡 Correlating AIS with Threat Matrix...", expanded=True) as status:
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
                        sog = pr.get('Sog', 0)
                        
                        if lat != 0 and lon != 0:
                            length = int(random.uniform(80, 350))
                            width = int(length * 0.15)
                            draft = round(random.uniform(5.5, 18.0), 1)
                            tonnage = int(length * width * draft * 0.7)
                            
                            live_vessels_data.append({
                                "MMSI": mmsi, "Vessel Name": name, "Type": "MERCHANT", "lat": lat, "lon": lon, 
                                "sog": sog, "cog": pr.get('Cog', 0),
                                "length": length, "width": width, "draft": draft, "gross_tonnage": tonnage,
                                "Risk Status": "COMMERCIAL TRACK", "Cargo Value ($M)": round(random.uniform(10, 150), 1),
                                "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
                            })
                        if len(live_vessels_data) >= 40: break
                except websocket.WebSocketTimeoutException:
                    break
            ws.close()
            if live_vessels_data:
                status.update(label=f"Tracking {len(live_vessels_data)} verified vessels.", state="complete")
            else:
                status.update(label="Uplink silent. Initializing tactical simulation.", state="error")
        except Exception as e:
            status.update(label=f"Uplink failed: {e}", state="error")

if len(live_vessels_data) < 5:
    for i in range(45):
        sog = random.uniform(5.0, 24.0)
        mmsi = f"36{random.randint(1000000, 9999999)}"
        length = int(random.uniform(100, 400))
        width = int(length * 0.15)
        draft = round(random.uniform(8.0, 20.0), 1)
        tonnage = int(length * width * draft * 0.7)
        
        live_vessels_data.append({
            "MMSI": mmsi, "Vessel Name": f"MERCHANT (MMSI: {mmsi[-4:]})", "Type": "MERCHANT",
            "lat": base_lat + random.uniform(-1.5, 1.5), "lon": base_lon + random.uniform(-2.0, 2.0),
            "sog": sog, "cog": random.uniform(0, 360),
            "length": length, "width": width, "draft": draft, "gross_tonnage": tonnage,
            "Risk Status": "COMMERCIAL TRACK", "Cargo Value ($M)": round(random.uniform(10, 150), 1),
            "Fuel Saved (MT)": round(random.uniform(5, 25), 1) if show_weather else 0.0
        })
    
    # Adding Kinematic Threat Profiling (Vessel of Interest)
    live_vessels_data.append({
        "MMSI": "413000000", "Vessel Name": "VOI (DARK TARGET)", "Type": "SUSPECT",
        "lat": base_lat + 0.15, "lon": base_lon - 0.65,
        "sog": 2.5, "cog": 80.0, # Slow speed = loitering/fishing
        "length": 45, "width": 8, "draft": 3.2, "gross_tonnage": 806,
        "Risk Status": "HOSTILE TRACK: Loitering kinematics detected.", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
    })

# Inject Blue Force Asset
live_vessels_data.append({
    "MMSI": "N/A", "Vessel Name": friendly_cutter["name"], "Type": friendly_cutter["type"],
    "lat": friendly_cutter["lat"], "lon": friendly_cutter["lon"],
    "sog": friendly_cutter["sog"], "cog": friendly_cutter["cog"],
    "length": 47, "width": 7, "draft": 2.6, "gross_tonnage": 353,
    "Risk Status": "FRIENDLY ASSET", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
})

map_vessels = []
for v in live_vessels_data:
    cog_rad = math.radians(v['cog'])
    length_vector = max(v['sog'] * 0.003, 0.01)
    
    # Standard Naval Color Coding
    if v['Type'] == "BLUE FORCE": color = [56, 189, 248, 255] # Friendly (Blue)
    elif v['Type'] == "SUSPECT": color = [239, 68, 68, 255] # Hostile (Red)
    else: color = [251, 191, 36, 200] # Commercial (Amber)

    map_vessels.append({
        "lat": v['lat'], "lon": v['lon'], "name": v['Vessel Name'], "MMSI": v['MMSI'],
        "sog": v['sog'], "cog": v['cog'], "Class": v['Type'],
        "v_length": v['length'], "v_width": v['width'], "v_draft": v['draft'], "v_tonnage": f"{v['gross_tonnage']:,}",
        "color": color,
        "heading_path": [[v['lon'], v['lat']], [v['lon'] + length_vector * math.sin(cog_rad), v['lat'] + length_vector * math.cos(cog_rad)]],
        "analytics": v['Risk Status'], "source": "AIS / BFT"
    })

vessels_df = pd.DataFrame(map_vessels)
layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_fill_color="color", get_line_color="[255,255,255,200]", stroked=True, line_width_min_pixels=2, get_radius=1500, pickable=True))
layers.append(pdk.Layer("PathLayer", data=vessels_df, get_path="heading_path", get_color="color", width_min_pixels=3, pickable=False))

# ---------------------------------------------------------
# 6. MAIN DASHBOARD: THE TACTICAL HUD 
# ---------------------------------------------------------
st.markdown(f"<h2 style='color: {accent_blue};'>PROJECT BLUE 42: COP & TACTICAL INTERVENTION</h2>", unsafe_allow_html=True)

alert_class = "alert-card" if "RED" in risk_level else ""
if "RED" in risk_level and show_iuu:
    ai_summary_text = "VOI Kinematics: 2.5 kts (Loitering). Profile matches IUU Trawler. USCG Cutter intercept recommended."
else:
    ai_summary_text = "All assets operating within nominal parameters. Routine COP established."

st.markdown(f"""
<div class='metric-card {alert_class}'>
    <h4>⚠️ TACTICAL THREAT ASSESSMENT</h4>
    <p style='color: {text_color}; font-size: 1.1rem;'><b>BATTLESPACE THREAT LEVEL: <span style='color: {accent_red};'>{risk_level}</span></b></p>
    <p class='hud-text'>{ai_summary_text}</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ DOMAIN AWARENESS</h4><p class='kpi-value' style='color:{accent_red};'>1 VOI</p><span class='kpi-subtext'>Vessel of Interest Tracked</span></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='metric-card'><h4>🌪️ RESILIENCE</h4><p class='kpi-value'>45 TRACKS</p><span class='kpi-subtext'>Dynamic Rerouting Active</span></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 MITIGATION</h4><p class='kpi-value'>14 HA</p><span class='kpi-subtext'>Blue Carbon Sites Verified</span></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. ASSEMBLE MAP & TACTICAL TOOLTIPS
# ---------------------------------------------------------
custom_tooltip = {
    "html": f"""
    <div style='padding: 12px; line-height: 1.5; min-width: 260px;'>
        <b style='color: {accent_blue}; font-size: 1.1em;'>{{name}}</b><br/>
        <span style='color: #F43F5E; font-size: 0.9em; font-weight: bold;'>CLASS: {{Class}}</span><br/>
        <span style='color: #E0E0E0; font-size: 0.9em;'><b>Speed:</b> {{sog}} kts | <b>Heading:</b> {{cog}}&deg;</span><br/>
        <span style='color: #E0E0E0; font-size: 0.9em;'><b>Size:</b> {{v_length}}m x {{v_width}}m | <b>Draft:</b> {{v_draft}}m</span><br/>
        <hr style='border-color: #334155; margin: 8px 0;'/>
        <b style='color: {accent_green};'>Kinematic Profile:</b> <span style='color: #ccc; font-size: 0.9em;'>{{analytics}}</span>
    </div>
    """,
    "style": {"backgroundColor": "#1E293B", "border": f"1px solid {accent_blue}", "color": "#F8FAFC", "borderRadius": "8px"}
}

r = pdk.Deck(layers=layers, initial_view_state=view_state, map_style=map_style, tooltip=custom_tooltip)
st.pydeck_chart(r, use_container_width=True)

# ---------------------------------------------------------
# 8. THE ENTERPRISE ANALYTICS SUITE 
# ---------------------------------------------------------
st.markdown("<h3 style='margin-top: 30px;'>📈 Operational Analytics & Financial Ledger</h3>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["💰 Scope 3 Financial & Carbon Ledger", "🌱 ESG Asset Ledger", "📋 Automated Action Reports"])

with tab1:
    ledger_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "length", "gross_tonnage", "Risk Status", "Cargo Value ($M)", "Fuel Saved (MT)"]]
    ledger_df.rename(columns={"length": "Length (m)", "gross_tonnage": "Tonnage (GT)"}, inplace=True)
    total_cargo = ledger_df["Cargo Value ($M)"].sum(); total_fuel = ledger_df["Fuel Saved (MT)"].sum()
    total_carbon = total_fuel * 3.11; total_carbon_value = total_carbon * 75.00
    st.markdown(f"**Total Capital Protected:** ${total_cargo:,.1f} Million | **Total Scope 3 Averted:** {total_carbon:,.1f} MT CO₂e | **Verified Carbon Value:** ${total_carbon_value:,.2f}")
    st.dataframe(ledger_df.style.highlight_max(axis=0, subset=["Fuel Saved (MT)"], color=accent_green), use_container_width=True)

with tab2:
    bc_col1, bc_col2, bc_col3 = st.columns(3)
    bc_col1.metric("Verified Area", "14.2 Hectares", "Sector K-1, K-2, K-3")
    bc_col2.metric("Projected Drawdown", "2,500 tCO₂e", "+15% YoY Growth")
    bc_col3.metric("ESG Asset Value (@ $75/ton)", "$187,500.00", "Ready for Minting")

with tab3:
    st.markdown("<p class='hud-text'>GenAI automated formal reporting for Coast Guard incident dispatch.</p>", unsafe_allow_html=True)
    if st.button("Generate Official Action Report via Gemini"):
        with st.spinner("Drafting formal tactical brief..."):
            try:
                report_prompt = f"You are a Coast Guard officer. Based on the {sector_mode} sector with threat level {risk_level}, write a highly formal, 3-paragraph tactical incident report covering maritime security, intercept geometry, and environmental impact."
                response = model.generate_content(report_prompt)
                st.info(response.text)
            except Exception as e:
                st.error(f"GenAI Error: {e}")

# ---------------------------------------------------------
# 9. TERMINALS: RADIO & GENAI CHAT
# ---------------------------------------------------------
st.write("---")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("### 💬 STRATEGIC ADVISORY AI")
    if "messages" not in st.session_state: st.session_state.messages = []
    for message in st.session_state.messages[-3:]: 
        with st.chat_message(message["role"]): st.markdown(message["content"])
    
    if prompt := st.chat_input("Request tactical evaluation..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                tactical_prompt = f"You are a USCG Operations Specialist. Sector is {sector_mode}. Analyze the query focusing on tactical intercept, kinematic profiling, and operational continuity: {prompt}"
                response = model.generate_content(tactical_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e: st.error(f"GenAI Chat Error: {e}")

with col_b:
    st.markdown("### 🧭 GENAI ROUTING ENGINE")
    st.markdown("<p class='hud-text'>Automated WeatherNext 3 route optimization.</p>", unsafe_allow_html=True)
    with st.form("routing_form"):
        port_col1, port_col2 = st.columns(2)
        with port_col1: origin_port = st.selectbox("Origin Port:", regional_ports)
        with port_col2: dest_port = st.selectbox("Destination Port:", reversed(regional_ports))
        submit_route = st.form_submit_button("Generate Voyage Plan Override")
        if submit_route:
            with st.spinner("GenAI correlating live weather with decadal baseline..."):
                try:
                    routing_prompt = f"You are a strategic marine logistics AI. A vessel is transiting from {origin_port} to {dest_port}. A weather hazard with significant wave heights (H_s) > 6.1m is detected. Generate a brief, highly technical 3-step voyage rerouting plan to minimize drag. Estimate bunker fuel saved. Use bullet points."
                    route_response = model.generate_content(routing_prompt)
                    st.success("Routing Plan Generated")
                    st.markdown(f"<div class='terminal'>{route_response.text}</div>", unsafe_allow_html=True)
                except Exception as e: st.error(f"GenAI Error: {e}")
