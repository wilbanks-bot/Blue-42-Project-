import streamlit as st
import pydeck as pdk
import pandas as pd
import json
import ee
from google.oauth2 import service_account
import google.generativeai as genai

# ---------------------------------------------------------
# 1. PAGE SETUP & THEME TOGGLE
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 Command", page_icon="⚓", initial_sidebar_state="expanded")

night_vision = st.sidebar.toggle("🌙 Tactical Night Vision Mode", value=False)

if night_vision:
    bg_color = "#0a0a0a"; card_bg = "#121212"; text_color = "#ff4d4d"; border_color = "#8b0000"; map_style = "dark"
    term_color = "#ff0000"; term_bg = "#220000"
    css = f"""<style>.stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 6px; border-left: 4px solid {border_color}; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(255,0,0,0.1); font-family: -apple-system, sans-serif;}}
    .alert-card {{ border: 1px solid #ef4444; box-shadow: 0 0 15px rgba(239, 68, 68, 0.5), inset 0 0 20px rgba(239, 68, 68, 0.2); animation: pulse-red 2s infinite; }}
    h2, h3, h4 {{ color: {text_color}; font-family: 'Trebuchet MS', sans-serif; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 5px rgba(255,255,255,0.3); margin-top: 0; }}
    .kpi-value {{ font-size: 2.5rem; color: {text_color}; font-weight: bold; text-shadow: 0 0 10px {text_color}; margin: 0; line-height: 1.2; }}
    .kpi-alert {{ color: #ef4444; text-shadow: 0 0 10px #ef4444; }}
    .hud-text {{ color: #94a3b8; font-size: 0.85rem; letter-spacing: 1px; }}
    @keyframes pulse-red {{ 0% {{ box-shadow: 0 0 15px rgba(239, 68, 68, 0.5); }} 50% {{ box-shadow: 0 0 25px rgba(239, 68, 68, 0.8); }} 100% {{ box-shadow: 0 0 15px rgba(239, 68, 68, 0.5); }} }}
    .terminal {{ background-color: {term_bg}; padding: 15px; border: 1px solid {term_color}; border-radius: 3px; color: {term_color}; font-size: 0.8rem; box-shadow: inset 0 0 10px rgba(255, 0, 0, 0.2); white-space: pre-wrap; }}
    .streamlit-expanderHeader {{ color: {text_color} !important; font-family: 'Courier New', monospace; font-weight: bold; background: rgba(14, 165, 233, 0.1); border: 1px solid #0ea5e9; }}
    </style>"""
else:
    bg_color = "#f8fafc"; card_bg = "#ffffff"; text_color = "#0f172a"; accent_blue = "#003366"; accent_red = "#cc0000"; map_style = "light"
    term_color = "#22c55e"; term_bg = "#000000"
    css = f"""<style>.stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 6px; border-left: 4px solid {accent_blue}; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); font-family: -apple-system, sans-serif;}}
    .protection-card {{ border-left: 4px solid {accent_red}; }}
    .alert-card {{ border: 1px solid #ef4444; box-shadow: 0 0 15px rgba(239, 68, 68, 0.5), inset 0 0 20px rgba(239, 68, 68, 0.2); animation: pulse-red 2s infinite; }}
    h4 {{ margin-top: 0px; color: #64748b; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
    h2 {{ margin-bottom: 0px; color: {accent_blue}; font-size: 2rem; font-weight: 700; }}
    p {{ margin-bottom: 0px; color: #475569; font-size: 0.85rem; }}
    @keyframes pulse-red {{ 0% {{ box-shadow: 0 0 15px rgba(239, 68, 68, 0.5); }} 50% {{ box-shadow: 0 0 25px rgba(239, 68, 68, 0.8); }} 100% {{ box-shadow: 0 0 15px rgba(239, 68, 68, 0.5); }} }}
    .terminal {{ background-color: {term_bg}; padding: 15px; border: 1px solid {term_color}; border-radius: 3px; color: {term_color}; font-size: 0.8rem; box-shadow: inset 0 0 10px rgba(34, 197, 94, 0.2); white-space: pre-wrap; }}
    .streamlit-expanderHeader {{ color: {accent_blue} !important; font-family: 'Courier New', monospace; font-weight: bold; background: rgba(14, 165, 233, 0.1); border: 1px solid #0ea5e9; }}
    </style>"""
st.markdown(css, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. SECURE API INITIALIZATION
# ---------------------------------------------------------
try:
    key_dict = json.loads(st.secrets["EARTHENGINE_TOKEN"])
    creds = service_account.Credentials.from_service_account_info(key_dict).with_scopes(['https://www.googleapis.com/auth/earthengine'])
    ee.Initialize(credentials=creds, project=key_dict.get("project_id"))
    ee_status = "🟢 UPLINK SECURE"
except:
    ee_status = "🔴 UPLINK SEVERED"

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
    ai_status = "🟢 CORE ACTIVE"
except:
    ai_status = "🔴 CORE OFFLINE"

# ---------------------------------------------------------
# 3. SIDEBAR: HUD LOGO, REGION & MULTI-SELECT OVERLAYS
# ---------------------------------------------------------
st.sidebar.markdown("""
<div style="text-align: center; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #0ea5e9;">
    <div style="font-size: 65px; color: #38bdf8; text-shadow: 0 0 20px #38bdf8; line-height: 1;">⚓</div>
    <div style="font-family: 'Trebuchet MS', sans-serif; font-weight: bold; color: #f8fafc; font-size: 1.5rem; letter-spacing: 4px; margin-top: 5px; text-shadow: 0 0 10px rgba(255,255,255,0.5);">BLUE 42</div>
    <div style="font-family: 'Courier New', monospace; color: #22c55e; font-size: 0.8rem; letter-spacing: 2px;">GLOBAL MARITIME COMMAND</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"<div class='hud-text'><b>SATCOM:</b> {ee_status}<br><b>NEURAL NET:</b> {ai_status}</div><hr>", unsafe_allow_html=True)

st.sidebar.markdown("### 🌍 REGIONAL COMMAND")
sector_mode = st.sidebar.selectbox("OPERATIONAL SECTOR:", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"])
st.sidebar.markdown("---")

st.sidebar.markdown("### 🌐 MULTI-DOMAIN OVERLAYS")
st.sidebar.write("Toggle active intelligence layers:")
show_weather = st.sidebar.checkbox("⛈️ Weather Shield (Storm Hazards)", value=True)
show_iuu = st.sidebar.checkbox("🐟 Ecological Protection (IUU / Kelp)", value=True)
show_cables = st.sidebar.checkbox("🔌 Economic Security (Subsea Cables)", value=False)
show_sar = st.sidebar.checkbox("🚁 Humanitarian (Search & Rescue)", value=False)
st.sidebar.markdown("---")

# ---------------------------------------------------------
# 4. REGIONAL DATA & LAYER AGGREGATION
# ---------------------------------------------------------
layers = []
radio_feeds = []
active_alerts = []
risk_level = "GREEN (Routine Transit)"

if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=50, bearing=-15)
    vessels_data = [
        {"lat": 34.12, "lon": -119.85, "name": "CARGO (MMSI: 368123450)", "color": [14, 165, 233, 200], "analytics": "Vector normal.", "source": "Live AIS"},
        {"lat": 33.95, "lon": -120.15, "name": "DARK TARGET (MMSI: 413000000)", "color": [239, 68, 68, 255], "analytics": "ANOMALY: Transponder disabled.", "source": "AISStream + WDPA"}
    ]
    
    if show_weather:
        storm_data = pd.DataFrame([{"polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]], "name": "Severe Gale Warning", "analytics": "H_s > 6.1m detected.", "source": "WeatherNext 3"}])
        layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[204, 0, 0, 40]", get_line_color="[204, 0, 0, 150]", line_width_min_pixels=2, pickable=True))
        route_data = pd.DataFrame([{"path": [[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]], "name": "AI Optimized Safe Route", "analytics": "Fuel savings vector.", "source": "AlphaEarth"}])
        layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[0, 255, 0, 255]", width_min_pixels=4, pickable=True))
        active_alerts.append("Weather system detected. Rerouting protocols active.")

    if show_iuu:
        radio_feeds.append("[14:02Z VHF-16] 'MARITIME COMM, this is F/V Horizon. Trawler running dark, hauling nets 3nm off Santa Cruz Is.'\n> ACOUSTIC MATCH: MMSI 413000000.")
        kelp_df = pd.DataFrame([{"lat": 34.02, "lon": -119.55, "name": "Kelp Restoration (K-1)", "analytics": "Depth 14m, SST 16.5°C.", "source": "Copernicus/GDM", "color": [34, 197, 94, 255]}])
        layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_color="color", get_radius=4000, pickable=True))
        active_alerts.append("Target masking identity near MPA. Recommend immediate intercept.")
        risk_level = "RED (High Risk)"
        
    if show_cables:
        radio_feeds.append("[14:15Z NAVTEX] 'SECURITE. UNIDENTIFIED VESSEL LOITERING IN RESTRICTED CABLE CORRIDOR. HYDROPHONE DETECTS ANCHOR DROP.'\n> MATCH: Transpacific Trunk.")
        cable_data = pd.DataFrame([{"path": [[-121.0, 33.5], [-119.0, 33.8], [-118.0, 34.2]], "name": "Transpacific Data Trunk", "analytics": "Critical infrastructure.", "source": "Submarine Cable Map", "color": [14, 165, 233, 255]}])
        layers.append(pdk.Layer("PathLayer", data=cable_data, get_path="path", get_color="color", width_min_pixels=5, pickable=True))
        active_alerts.append("Vessel anchoring over Tier-1 fiber optic trunk. Dispatching assets.")
        risk_level = "RED (Critical Risk)"
        
    if show_sar:
        radio_feeds.append("[14:22Z VHF-16] 'MAYDAY MAYDAY. S/V Orion. Taking water. Engines dead. Lat 33.7, Lon -119.8. 4 POB.'\n> MATCH: SAR Drift Grid.")
        sar_data = pd.DataFrame([{"polygon": [[[-120.5, 33.7], [-119.8, 33.7], [-119.6, 34.2], [-120.3, 34.2]]], "name": "Predictive Drift Zone", "analytics": "AlphaEarth leeway grid based on 22kt winds.", "source": "WeatherNext 3"}])
        layers.append(pdk.Layer("PolygonLayer", data=sar_data, get_polygon="polygon", get_fill_color="[249, 115, 22, 80]", get_line_color="[249, 115, 22, 255]", line_width_min_pixels=3, pickable=True))
        active_alerts.append("Vessel adrift. Time-sensitive exposure for 4 POB. Drift vector initialized.")
        if risk_level == "GREEN (Routine Transit)": risk_level = "AMBER (Elevated Risk)"

else:
    # PACIFIC (HAWAII) REGION
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=50, bearing=-15)
    vessels_data = [
        {"lat": 21.1, "lon": -157.9, "name": "PACIFIC TRADER (MMSI: 366111000)", "color": [14, 165, 233, 200], "analytics": "Vector normal.", "source": "Live AIS"},
        {"lat": 21.6, "lon": -158.3, "name": "UNKNOWN TARGET (MMSI: 412999000)", "color": [239, 68, 68, 255], "analytics": "ANOMALY: Transponder disabled.", "source": "AISStream + WDPA"}
    ]
    
    if show_weather:
        storm_data = pd.DataFrame([{"polygon": [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]], "name": "Tropical Squall Zone", "analytics": "H_s > 4.5m detected.", "source": "WeatherNext 3"}])
        layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[204, 0, 0, 40]", get_line_color="[204, 0, 0, 150]", line_width_min_pixels=2, pickable=True))
        route_data = pd.DataFrame([{"path": [[-158.5, 20.8], [-158.0, 20.9], [-157.4, 20.9], [-157.1, 21.2]], "name": "AI Optimized Safe Route", "analytics": "Fuel savings vector.", "source": "AlphaEarth"}])
        layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[0, 255, 0, 255]", width_min_pixels=4, pickable=True))
        active_alerts.append("Weather squall detected. Rerouting protocols active.")

    if show_iuu:
        radio_feeds.append("[08:15W VHF-16] 'MARITIME COMM, this is S/V Moana. Unidentified vessel deploying gear off Kaena Point MPA.'\n> ACOUSTIC MATCH: MMSI 412999000.")
        overlay_df = pd.DataFrame([{"lat": 21.45, "lon": -157.8, "name": "Coral/Limu Restoration (Kaneohe Bay)", "analytics": "Depth 8m, SST 24.5°C.", "source": "Copernicus/GDM", "color": [34, 197, 94, 255]}])
        layers.append(pdk.Layer("ScatterplotLayer", data=overlay_df, get_position="[lon, lat]", get_color="color", get_radius=4000, pickable=True))
        active_alerts.append("Target masking identity near protected reef. Recommend intercept.")
        risk_level = "RED (High Risk)"
        
    if show_cables:
        radio_feeds.append("[08:30W NAVTEX] 'SECURITE. UNIDENTIFIED VESSEL LOITERING IN HONOLULU LANDING CORRIDOR.'\n> MATCH: Pacific Fiber Trunk.")
        overlay_data = pd.DataFrame([{"path": [[-160.0, 22.0], [-157.8, 21.3], [-155.0, 20.0]], "name": "Transpacific Data Trunk", "analytics": "Critical infrastructure.", "source": "Submarine Cable Map", "color": [14, 165, 233, 255]}])
        layers.append(pdk.Layer("PathLayer", data=overlay_data, get_path="path", get_color="color", width_min_pixels=5, pickable=True))
        active_alerts.append("Vessel anchoring over Honolulu landing trunk. Exposure: High.")
        risk_level = "RED (Critical Risk)"
        
    if show_sar:
        radio_feeds.append("[08:45W VHF-16] 'MAYDAY MAYDAY. F/V Makai. Engine fire. Lat 21.6, Lon -158.2 in Kauai Channel.'\n> MATCH: SAR Drift Grid.")
        sar_data = pd.DataFrame([{"polygon": [[[-158.5, 21.5], [-158.0, 21.5], [-158.0, 21.8], [-158.5, 21.8]]], "name": "Predictive Drift Zone", "analytics": "AlphaEarth leeway grid.", "source": "WeatherNext 3"}])
        layers.append(pdk.Layer("PolygonLayer", data=sar_data, get_polygon="polygon", get_fill_color="[249, 115, 22, 80]", get_line_color="[249, 115, 22, 255]", line_width_min_pixels=3, pickable=True))
        active_alerts.append("Vessel adrift in Kauai Channel. Drift vector initialized.")
        if risk_level == "GREEN (Routine Transit)": risk_level = "AMBER (Elevated Risk)"

# Always add vessels last so they sit on top
layers.append(pdk.Layer("ScatterplotLayer", data=pd.DataFrame(vessels_data), get_position="[lon, lat]", get_color="color", get_radius=3000, pickable=True))

if not radio_feeds:
    radio_feeds.append("[14:30Z] Sector Comm channel clear. Normal operations.")
if not active_alerts:
    active_alerts.append("All sectors operating within normal parameters. No active threats.")

radio_text = "\n\n".join(radio_feeds)
ai_summary_text = " | ".join(active_alerts)

# ---------------------------------------------------------
# 5. RENDER SIGINT TERMINAL
# ---------------------------------------------------------
st.sidebar.markdown("### 📻 SIGINT TERMINAL")
st.sidebar.markdown(f"<div class='terminal'>{radio_text}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. MAIN DASHBOARD: THE HUD & METRICS
# ---------------------------------------------------------
st.markdown("<h2>⚓ PROJECT BLUE 42: PLANETARY COMMAND</h2>", unsafe_allow_html=True)
st.markdown("<p class='hud-text'>AUTOMATED MARITIME DOMAIN AWARENESS & INTELLIGENCE</p>", unsafe_allow_html=True)
st.write("")

alert_class = "alert-card" if "RED" in risk_level else ""
st.markdown(f"""
<div class='cyber-card {alert_class}' style='margin-bottom: 25px;'>
    <h4>⚠️ GENAI TACTICAL RISK ASSESSMENT</h4>
    <p style='color: #f8fafc; font-size: 1

