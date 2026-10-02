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

# Night Vision Toggle in the sidebar
night_vision = st.sidebar.toggle("🌙 Tactical Night Vision Mode", value=False)

if night_vision:
    bg_color = "#0a0a0a"
    card_bg = "#121212"
    text_color = "#ff4d4d"
    border_color = "#8b0000"
    map_style = "dark"
    css = f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 6px; border-left: 4px solid {border_color}; margin-bottom: 5px; box-shadow: 0 1px 3px rgba(255,0,0,0.1); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;}}
    h4 {{ margin-top: 0px; color: {text_color}; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
    h2 {{ margin-bottom: 0px; color: {text_color}; font-size: 2rem; font-weight: 700; }}
    p {{ margin-bottom: 0px; color: #b30000; font-size: 0.85rem; }}
    .streamlit-expanderHeader {{ color: {text_color} !important; font-size: 0.9rem; }}
    </style>
    """
else:
    bg_color = "#f8fafc"
    card_bg = "#ffffff"
    text_color = "#0f172a"
    accent_blue = "#003366" 
    accent_red = "#cc0000"
    map_style = "light"
    css = f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 6px; border-left: 4px solid {accent_blue}; margin-bottom: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;}}
    .protection-card {{ border-left: 4px solid {accent_red}; }}
    h4 {{ margin-top: 0px; color: #64748b; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
    h2 {{ margin-bottom: 0px; color: {accent_blue}; font-size: 2rem; font-weight: 700; }}
    p {{ margin-bottom: 0px; color: #475569; font-size: 0.85rem; }}
    </style>
    """

st.markdown(css, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. SECURE API INITIALIZATION
# ---------------------------------------------------------
try:
    key_dict = json.loads(st.secrets["EARTHENGINE_TOKEN"])
    creds = service_account.Credentials.from_service_account_info(key_dict).with_scopes(['https://www.googleapis.com/auth/earthengine'])
    ee.Initialize(credentials=creds, project=key_dict.get("project_id"))
    ee_status = "🟢 ON-LINE"
except Exception as e:
    ee_status = f"🔴 OFF-LINE"

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
    ai_status = "🟢 ON-LINE"
except Exception as e:
    ai_status = "🔴 OFF-LINE"

# ---------------------------------------------------------
# 3. SIDEBAR: TACTICAL WATCHSTANDER & LIVE AI CHAT
# ---------------------------------------------------------
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Seal_of_the_United_States_Coast_Guard.svg/200px-Seal_of_the_United_States_Coast_Guard.svg.png", width=60)
st.sidebar.title("Sector Command")
st.sidebar.markdown(f"**Satellite Telemetry:** {ee_status}  \n**Gemini Neural Net:** {ai_status}")
st.sidebar.markdown("---")

with st.sidebar.expander("🚨 CRITICAL: Dark Vessel Detected", expanded=True):
    st.error("**Target:** MMSI 413000000")
    st.write("**Location:** 34.012° N, 120.341° W")
    st.write("**Status:** AIS transponder disabled for 74 mins.")
    if st.sidebar.button("AUTHORIZE INTERCEPT"):
        st.sidebar.success("Vector transmitted to USCG Cutter.")

st.sidebar.markdown("### 🧠 Live Threat Analysis")
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Watchstander AI active. Awaiting analytical queries."}]

for message in st.session_state.messages:
    with st.sidebar.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.sidebar.chat_input("Ask Gemini for tactical analysis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.sidebar.chat_message("user"):
        st.markdown(prompt)
    with st.sidebar.chat_message("assistant"):
        try:
            tactical_prompt = f"You are a US Coast Guard AI Watchstander. Keep your answer brief, tactical, and highly professional. The user asks: {prompt}"
            response = model.generate_content(tactical_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error("Comms failure with Gemini.")

# ---------------------------------------------------------
# 4. MAIN DASHBOARD HEADER & M.A.P. METRICS (With Deep Dives)
# ---------------------------------------------------------
st.title("⚓ Project Blue 42: Planetary Command")
st.markdown("**Automated Maritime Domain Awareness & Climate Intervention**")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div class="metric-card protection-card"><h4>🛡️ Protection</h4><h2>1 Active Threat</h2><p>10M Hectares Under AI Surveillance</p></div>', unsafe_allow_html=True)
    with st.expander("📊 Analytical Breakdown & Data Lineage"):
        st.markdown("""
        **Data Source:** [UNEP World Database on Protected Areas (WDPA)](https://www.protectedplanet.net/)
        
        **Analytics:** The Watchstander AI correlates vessel Speed Over Ground (SOG) with transponder blackout events near designated marine sanctuaries.
        *   **Algorithm:** `Distance_to_MPA < 15nm` AND `SOG > 3kts` AND `Signal_Loss > 60m` = `HIGH THREAT`.
        *   **Validation:** [Global Fishing Watch Methodologies](https://globalfishingwatch.org/)
        """)

with col2:
    st.markdown('<div class="metric-card"><h4>🌪️ Adaptation</h4><h2>5 Ships Rerouted</h2><p>54 MT Fuel Saved (Weather Avoidance)</p></div>', unsafe_allow_html=True)
    with st.expander("📊 Analytical Breakdown & Data Lineage"):
        st.markdown("""
        **Data Source:** [Copernicus Marine Wave Data (CMEMS)](https://marine.copernicus.eu/) & WeatherNext 3
        
        **Analytics:** Routing vectors are optimized to avoid extreme sea states that cause hydrodynamic drag.
        *   **Algorithm:** Hazard polygons generated where Significant Wave Height ($H_s$) $\ge 6.1$m or Sustained Wind $\ge 22.35$m/s.
        *   **Impact:** Skirting $H_s \ge 6.1$m reduces engine load, cutting bunker fuel consumption by an estimated 5-12% per transit.
        *   **Validation:** [ECMWF ERA5 Reanalysis](https://cds.climate.copernicus.eu/)
        """)

with col3:
    st.markdown('<div class="metric-card"><h4>🌱 Mitigation</h4><h2>14 Hectares</h2><p>Optimal Blue Carbon Zones Verified</p></div>', unsafe_allow_html=True)
    with st.expander("📊 Analytical Breakdown & Data Lineage"):
        st.markdown("""
        **Data Source:** [Copernicus Static Bathymetry](https://marine.copernicus.eu/) & GDM Species Distribution Models
        
        **Analytics:** Suitability masking for *Macrocystis pyrifera* (Giant Kelp) utilizing Google Earth Engine.
        *   **Algorithm:** `Depth between -5m and -30m` AND `SST < 18°C`.
        *   **Impact:** Verifying coordinates programmatically unlocks institutional ESG capital by proving spatial viability before physical planting.
        *   **Validation:** [The Blue Carbon Initiative](https://www.thebluecarboninitiative.org/)
        """)

st.write("") # Spacer

# ---------------------------------------------------------
# 5. DATA LAYERS & 3D MAP
# ---------------------------------------------------------
vessels_df = pd.DataFrame([
    {"lat": 34.12, "lon": -119.85, "mmsi": "368123450", "sog": 12.4, "name": "PACIFIC TITAN (Cargo)", "color": [255, 165, 0, 200]},
    {"lat": 33.95, "lon": -120.15, "mmsi": "413000000", "sog": 9.1, "name": "DARK TARGET (Suspect)", "color": [204, 0, 0, 255]},
    {"lat": 33.80, "lon": -119.60, "mmsi": "219000000", "sog": 15.2, "name": "MAERSK SEALAND", "color": [255, 165, 0, 200]}
])

kelp_df = pd.DataFrame([
    {"lat": 34.02, "lon": -119.55, "site": "Sector K-1 (High Viability)", "depth": "14m"},
    {"lat": 33.88, "lon": -119.72, "site": "Sector K-2 (Medium Viability)", "depth": "22m"},
    {"lat": 34.05, "lon": -120.00, "site": "Sector K-3 (High Viability)", "depth": "11m"}
])

storm_data = pd.DataFrame([{"polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]], "name": "Severe Gale Warning"}])
route_data = pd.DataFrame([{"path": [[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]], "name": "Optimized Safe Route"}])

vessel_layer = pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_color="color", get_radius=3000, pickable=True)
kelp_layer = pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_color="[0, 153, 76, 255]", get_radius=2000, pickable=True)
storm_layer = pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[204, 0, 0, 40]", get_line_color="[204, 0, 0, 150]", line_width_min_pixels=2, pickable=True)
route_layer = pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[0, 102, 204, 255]" if not night_vision else "[255, 50, 50, 200]", width_min_pixels=4, pickable=True)

view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=45)
r = pdk.Deck(layers=[storm_layer, route_layer, kelp_layer, vessel_layer], initial_view_state=view_state, map_style=map_style, tooltip={"html": "<b>{name}</b><br/>{site}<br/>Speed: {sog} kts<br/>Depth: {depth}"})

st.pydeck_chart(r, use_container_width=True)
