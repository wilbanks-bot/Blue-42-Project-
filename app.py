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

night_vision = st.sidebar.toggle("🌙 Tactical Night Vision", value=True)

if night_vision:
    bg_color = "#0f172a"; card_bg = "#1e293b"; text_color = "#f8fafc"
    accent_blue = "#38bdf8"; accent_red = "#fb7185"; accent_green = "#34d399"; accent_purple = "#a78bfa"; accent_amber = "#fbbf24"
    map_style = "mapbox://styles/mapbox/dark-v11"
else:
    bg_color = "#f1f5f9"; card_bg = "#ffffff"; text_color = "#0f172a"
    accent_blue = "#0284c7"; accent_red = "#e11d48"; accent_green = "#059669"; accent_purple = "#7c3aed"; accent_amber = "#d97706"
    map_style = "mapbox://styles/mapbox/light-v11"

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
        model = genai.GenerativeModel('gemini-3.5-flash')
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

st.sidebar.markdown("### 📊 MULTI-DOMAIN OVERLAYS")
show_iuu = st.sidebar.checkbox("🛡️ Marine Protected Areas (IUU)", value=True)
show_whales = st.sidebar.checkbox("🐋 Dynamic Marine Mammal Zones", value=True)
show_weather = st.sidebar.checkbox("⛈️ Weather Hazards (Waves/Wind)", value=True)
show_currents = st.sidebar.checkbox("🌊 Microcurrents (Fuel Surfing)", value=True)
show_spill = st.sidebar.checkbox("🛢️ Oil Spill Trajectory (Crisis)", value=False)
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

if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=45, bearing=-10)
    base_lat, base_lon = 33.8, -119.5
    
    if show_iuu:
        poly_data = [{"polygon": [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]], "name": "Channel Islands Marine Sanctuary", "primary_metric": "Protection Level: FULL", "secondary_metric": "Jurisdiction: Federal MPA", "analytics": "Zero-take zone. Continuous AI surveillance active to detect 'dark fleet' incursions.", "source": "UNEP-WCMC WDPA", "color": [52, 211, 153, 30]}]
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(poly_data), get_polygon="polygon", get_fill_color="color", get_line_color="[52, 211, 153, 180]", line_width_min_pixels=2, pickable=True))
        
    if show_whales:
        poly_data = [{"polygon": [[[-120.0, 33.5], [-119.5, 33.5], [-119.3, 34.0], [-119.8, 34.0]]], "name": "Dynamic Whale Pod Migration", "primary_metric": "Status: 10-Knot Speed Limit Active", "secondary_metric": "Species: Blue Whale (Endangered)", "analytics": "DeepMind SDM indicates high probability of plankton bloom. Dynamic speed reduction enforced to mitigate strike risk.", "source": "Google DeepMind", "color": [167, 139, 250, 40]}]
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(poly_data), get_polygon="polygon", get_fill_color="color", get_line_color="[167, 139, 250, 200]", line_width_min_pixels=2, pickable=True))

    if show_weather:
        poly_data = [{"polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]], "name": "Severe Gale Warning", "primary_metric": "Intensity: H_s > 6.1m (20ft)", "secondary_metric": "Wind: Sustained 45 knots", "analytics": "Extreme hydrodynamic drag detected. Routing through this zone increases fuel consumption by 12%.", "source": "WeatherNext 3", "color": [251, 113, 133, 40]}]
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(poly_data), get_polygon="polygon", get_fill_color="color", get_line_color="[251, 113, 133, 180]", line_width_min_pixels=2, pickable=True))

    if show_currents:
        path_data = [{"path": [[-120.5, 34.5], [-119.8, 33.8], [-119.2, 33.0]], "name": "California Microcurrent Stream", "primary_metric": "Velocity: 1.2 kts Southbound", "secondary_metric": "Status: Favorable Surf Zone", "analytics": "Surfing this current allows a 10% reduction in engine RPM while maintaining SOG, generating massive fuel savings.", "source": "Copernicus Ocean Physics", "color": [56, 189, 248, 200]}]
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame(path_data), get_path="path", get_color="color", width_min_pixels=6, pickable=True))

    if show_spill:
        poly_data = [{"polygon": [[[-119.8, 33.9], [-119.6, 33.8], [-119.5, 33.9], [-119.7, 34.0]]], "name": "72-Hour Spill Trajectory", "primary_metric": "Contaminant: Heavy Fuel Oil", "secondary_metric": "Impact Risk: Critical", "analytics": "AlphaEarth leeway models project slick impacting Santa Cruz Island in 48 hours. Deploy containment booms immediately.", "source": "AlphaEarth & Sentinel-1 SAR", "color": [245, 158, 11, 70]}]
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(poly_data), get_polygon="polygon", get_fill_color="color", get_line_color="[245, 158, 11, 200]", line_width_min_pixels=2, pickable=True))

    if show_cables:
        path_data = [{"path": [[-121.0, 33.5], [-119.0, 33.8], [-118.0, 34.2]], "name": "Tier-1 Subsea Data Cable", "primary_metric": "Asset: Transpacific Trunk", "secondary_metric": "Vulnerability: Exposed to anchor drag", "analytics": "Critical infrastructure carrying billions in daily financial transactions.", "source": "Submarine Cable Map", "color": [203, 213, 225, 200]}]
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame(path_data), get_path="path", get_color="color", width_min_pixels=4, pickable=True))

else: # HAWAII
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=45, bearing=-10)
    base_lat, base_lon = 21.2, -158.0
    
    if show_iuu:
        poly_data = [{"polygon": [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]], "name": "Kaena Point MPA Expansion", "primary_metric": "Protection Level: FULL", "secondary_metric": "Jurisdiction: State/Federal", "analytics": "High-value target for illicit commercial harvesting. AI monitoring active.", "source": "UNEP-WCMC WDPA", "color": [52, 211, 153, 30]}]
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(poly_data), get_polygon="polygon", get_fill_color="color", get_line_color="[52, 211, 153, 180]", line_width_min_pixels=2, pickable=True))

    if show_whales:
        poly_data = [{"polygon": [[[-157.5, 20.5], [-156.8, 20.8], [-156.5, 21.2], [-157.2, 20.8]]], "name": "Humpback Winter Breeding Grounds", "primary_metric": "Status: 10-Knot Speed Limit Active", "secondary_metric": "Species: Humpback Whale", "analytics": "High density calving area detected. Automatic ESG compliance alerts routing to encroaching vessels.", "source": "Google DeepMind", "color": [167, 139, 250, 40]}]
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(poly_data), get_polygon="polygon", get_fill_color="color", get_line_color="[167, 139, 250, 200]", line_width_min_pixels=2, pickable=True))

    if show_weather:
        poly_data = [{"polygon": [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]], "name": "Tropical Squall Hazard Zone", "primary_metric": "Intensity: H_s > 4.5m", "secondary_metric": "Wind: Gusts to 35 knots", "analytics": "Localized squall creating supply chain delays for Honolulu port approaches.", "source": "WeatherNext 3", "color": [251, 113, 133, 40]}]
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(poly_data), get_polygon="polygon", get_fill_color="color", get_line_color="[251, 113, 133, 180]", line_width_min_pixels=2, pickable=True))

    if show_currents:
        path_data = [{"path": [[-156.0, 22.0], [-157.0, 21.5], [-158.5, 21.0]], "name": "North Equatorial Current", "primary_metric": "Velocity: 1.5 kts Westbound", "secondary_metric": "Status: Favorable Surf Zone", "analytics": "Surfing this current allows ships bound for Asia to throttle down, saving Scope 3 emissions.", "source": "Copernicus Ocean Physics", "color": [56, 189, 248, 200]}]
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame(path_data), get_path="path", get_color="color", width_min_pixels=6, pickable=True))

vessels = []
for i in range(35):
    sog = random.uniform(8.0, 22.0)
    v_type = random.choice(["CARGO", "TANKER", "BULK"])
    mmsi = f"36{random.randint(1000000, 9999999)}"
    lat = base_lat + random.uniform(-1.5, 1.5)
    lon = base_lon + random.uniform(-2.0, 2.0)
    cog = random.uniform(0, 360)
    
    cog_rad = math.radians(cog)
    vec_len = max(sog * 0.003, 0.01)
    heading_path = [[lon, lat], [lon + vec_len * math.sin(cog_rad), lat + vec_len * math.cos(cog_rad)]]
    
    vessels.append({
        "lat": lat, "lon": lon, "name": f"{v_type} (MMSI: {mmsi})", 
        "primary_metric": f"Speed: {sog:.1f} kts | Heading: {cog:.1f}°", 
        "secondary_metric": f"Length: {random.randint(150,350)}m | Draft: {random.uniform(9,15):.1f}m", 
        "analytics": "Vessel kinetics operate within nominal parameters. Compliant track.", 
        "source": "Verified AIS Telemetry", 
        "color": [56, 189, 248, 200], "path": heading_path, "radius": 1200
    })

dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
vessels.append({
    "lat": dt_lat, "lon": dt_lon, "name": "UNVERIFIED DARK TARGET", 
    "primary_metric": "Speed: 2.5 kts (Loitering) | Heading: 80.0°", 
    "secondary_metric": "Estimated Length: 45m | Draft: 3.2m", 
    "analytics": "CRITICAL ANOMALY: Vessel disabled transponder 15nm from MPA. Kinematics strongly suggest illicit fishing deployment.", 
    "source": "AISStream / Spatial DeepMind Analysis", 
    "color": [251, 113, 133, 255], 
    "path": [[dt_lon, dt_lat], [dt_lon + 0.01, dt_lat + 0.005]], "radius": 2000
})

vessels_df = pd.DataFrame(vessels)
map_layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))
map_layers.append(pdk.Layer("PathLayer", data=vessels_df, get_path="path", get_color="color", width_min_pixels=2, pickable=False))

# ---------------------------------------------------------
# 5. MAIN DASHBOARD: THE EXECUTIVE STORYBOARD
# ---------------------------------------------------------
st.markdown(f"<h2 style='color: {text_color};'>Global Maritime Command Center</h2>", unsafe_allow_html=True)
st.markdown("<p class='hud-text' style='margin-bottom: 25px;'>Synthesizing planetary telemetry into predictive intelligence and actionable ESG workflows.</p>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ACTIVE THREATS</h4><p class='kpi-value' style='color:{accent_red};'>1 VOI</p><span class='kpi-subtext'>Target masking identity near MPA</span></div>", unsafe_allow_html=True)
    with st.expander("📊 View Analytics & Recommendations"):
        st.markdown("**📡 Data Analytics:**\nKinematic anomaly detected. Vessel MMSI 413000000 dropped AIS transmission 15nm from the MPA boundary. Speed reduced from 12 kts to 2.5 kts (loitering profile).\n\n**🧠 GenAI Recommendation:**\nDeploy autonomous surface vehicle (ASV) or nearest Coast Guard cutter for visual identification. Initiate satellite Synthetic Aperture Radar (SAR) tasking to verify physical presence.")

with col2:
    st.markdown(f"<div class='metric-card military-card'><h4>⚓ MILITARY ZONES</h4><p class='kpi-value' style='color:{accent_purple};'>SECURE</p><span class='kpi-subtext'>No incursions in weapons ranges</span></div>", unsafe_allow_html=True)
    with st.expander("📊 View Analytics & Recommendations"):
        st.markdown("**📡 Data Analytics:**\nGeospatial perimeter of active testing range remains clear of civilian AIS tracks. No kinetic intersection anomalies detected in the last 24 hours.\n\n**🧠 GenAI Recommendation:**\nMaintain current geofence monitoring. Routine baseline established. No immediate action required.")

with col3:
    st.markdown(f"<div class='metric-card'><h4>🌪️ RESILIENCE</h4><p class='kpi-value' style='color:{accent_blue};'>5 REROUTED</p><span class='kpi-subtext'>Avoiding extreme wave heights</span></div>", unsafe_allow_html=True)
    with st.expander("📊 View Analytics & Recommendations"):
        st.markdown("**📡 Data Analytics:**\n5 commercial vessels successfully diverted from severe gale polygon ($H_s \ge 6.1$m). Hydrodynamic drag coefficient reduced by 42% on average across the fleet.\n\n**🧠 GenAI Recommendation:**\nLog 54 MT of Scope 3 Fuel Savings in the financial ledger. Alert port authorities of revised Estimated Time of Arrival (ETA) to manage Just-In-Time (JIT) anchorage and prevent port congestion.")

with col4:
    st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 BLUE CARBON</h4><p class='kpi-value' style='color:{accent_green};'>14.2 HA</p><span class='kpi-subtext'>Optimal restoration sites verified</span></div>", unsafe_allow_html=True)
    with st.expander("📊 View Analytics & Recommendations"):
        st.markdown("**📡 Data Analytics:**\nBathymetric depth (-5m to -30m) and Sea Surface Temperature (< 18°C) criteria met. 92% survival probability for *Macrocystis pyrifera* (Giant Kelp) against decadal heatwave trends.\n\n**🧠 GenAI Recommendation:**\nProceed with spatial asset minting. Package coordinates and telemetry data for Verra/Gold Standard registry validation to instantly unlock $187,500 in ESG capital financing.")

# ---------------------------------------------------------
# 6. RENDER 3D MAP
# ---------------------------------------------------------
st.markdown("#### 🗺️ TACTICAL BATTLESPACE OVERVIEW", unsafe_allow_html=True)
r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=get_tooltip())
st.pydeck_chart(r, use_container_width=True)

# ---------------------------------------------------------
# 7. ANALYTICS & GENAI DEEP DIVES
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
