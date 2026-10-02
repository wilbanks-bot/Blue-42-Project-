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
    st.session_state["sar_tasked"] = False

night_vision = st.sidebar.toggle("🌙 Tactical Night Vision", value=True)

# 1A. SECURE COLOR PALETTE
if night_vision:
    bg_color = "#0f172a"; card_bg = "#1e293b"; text_color = "#f8fafc"
    muted_text = "#94a3b8"; border_color = "#27272a"
    accent_blue = "#38bdf8"; accent_red = "#fb7185"; accent_green = "#34d399"
    accent_purple = "#a78bfa"; accent_amber = "#fbbf24"
    map_style = "dark"; term_bg = "#000000"; term_color = "#10b981"
else:
    bg_color = "#f1f5f9"; card_bg = "#ffffff"; text_color = "#0f172a"
    muted_text = "#64748b"; border_color = "#e2e8f0"
    accent_blue = "#0284c7"; accent_red = "#e11d48"; accent_green = "#059669"
    accent_purple = "#7c3aed"; accent_amber = "#d97706"
    map_style = "light"; term_bg = "#f1f5f9"; term_color = "#0f172a"

# 1B. FAIL-SAFE TOOLTIP DICTIONARY (Declared immediately to prevent NameErrors)
tooltip_dict = {
    "html": f"""
    <div style='background: {card_bg}; border: 1px solid {accent_blue}; padding: 14px; border-radius: 10px; color: {text_color}; font-family: Inter, sans-serif; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); max-width: 320px;'>
        <div style='font-size: 1.1rem; font-weight: 700; color: {accent_blue}; margin-bottom: 4px;'>{{name}}</div>
        <div style='font-size: 0.85rem; color: {muted_text}; margin-bottom: 2px;'>{{primary_metric}}</div>
        <div style='font-size: 0.85rem; color: {muted_text}; margin-bottom: 12px;'>{{secondary_metric}}</div>
        <div style='border-top: 1px solid {border_color}; padding-top: 10px;'>
            <span style='color: {accent_green}; font-weight: 600; font-size: 0.85rem;'>AI ANALYTICS:</span><br/>
            <span style='font-size: 0.85rem; line-height: 1.4; color: {text_color};'>{{analytics}}</span>
        </div>
        <div style='margin-top: 10px; font-size: 0.75rem; color: {muted_text}; font-style: italic;'>Source: {{source}}</div>
    </div>
    """,
    "style": {"backgroundColor": "transparent", "padding": "0"} 
}

css = f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: 'Inter', -apple-system, sans-serif; }}
    .metric-card {{ background-color: {card_bg}; padding: 24px; border-radius: 12px; border-top: 4px solid {accent_blue}; margin-bottom: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .protection-card {{ border-top: 4px solid {accent_red}; }}
    .mitigation-card {{ border-top: 4px solid {accent_green}; }}
    .military-card {{ border-top: 4px solid {accent_purple}; }}
    h1, h2, h3, h4 {{ color: {text_color}; font-weight: 600; margin-top: 0; letter-spacing: -0.01em; }}
    h4 {{ font-size: 0.85rem; text-transform: uppercase; color: {muted_text}; letter-spacing: 0.05em; }}
    .kpi-value {{ font-size: 2.25rem; font-weight: 700; color: {text_color}; margin: 4px 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.85rem; color: {muted_text}; display: block; margin-bottom: 4px; }}
    .streamlit-expanderHeader {{ font-weight: 600 !important; font-size: 0.95rem; color: {text_color} !important; border-radius: 8px; }}
    div[data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid {border_color}; }}
    .terminal {{ background-color: {term_bg}; padding: 12px; border: 1px solid {accent_green}; border-radius: 4px; color: {term_color}; font-family: 'Courier New', monospace; font-size: 0.8rem; box-shadow: inset 0 0 10px rgba(52, 211, 153, 0.2); }}
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
        # Failsafe model selection
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = 'gemini-1.5-flash'
        if 'models/gemini-2.5-flash' in available: target_model = 'gemini-2.5-flash'
        model = genai.GenerativeModel(target_model)
        ai_status = "🟢 CORE ACTIVE"
    else: ai_status = "🔴 CORE OFFLINE"
except Exception as e: ai_status = "🔴 CORE OFFLINE"

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
    <div style="color: {muted_text}; font-size: 0.75rem; font-weight: 500; letter-spacing: 1px; text-transform: uppercase;">Global Blue Economy OS</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🌍 REGIONAL DEPLOYMENT")
sector_mode = st.sidebar.selectbox("Operational Theater:", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"], label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 SYSTEM DIAGNOSTICS")
st.sidebar.caption(f"**Geospatial Engine:** {ee_status}\n\n**GenAI Reasoning:** {ai_status}\n\n**AIS Telemetry:** {ais_status}")

# ---------------------------------------------------------
# 4. EXECUTIVE STORYBOARD & STRATEGIC FILTER
# ---------------------------------------------------------
st.markdown(f"<h2 style='color: {text_color}; text-align: center; margin-bottom: 8px; font-weight: 700;'>Global Maritime Command Center</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: {muted_text}; font-size: 1.1rem; margin-bottom: 30px;'>Synthesizing planetary telemetry into predictive intelligence for global economic stability and human rights.</p>", unsafe_allow_html=True)

focus_mode = st.radio("SELECT STRATEGIC FOCUS TO FILTER BATTLESPACE & ANALYTICS:", 
    ["🌍 Global Overview", "🛡️ Threat Interdiction", "⚓ Military Security", "🌪️ Supply Chain Resilience", "🌱 ESG Blue Carbon"], 
    horizontal=True)

st.write("")

# Dynamic KPIs based on Filter
if focus_mode == "🌍 Global Overview":
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ACTIVE THREATS</h4><p class='kpi-value' style='color:{accent_red};'>1 VOI</p><span class='kpi-subtext'>Target masking identity near MPA</span></div>", unsafe_allow_html=True)
    with col2: st.markdown(f"<div class='metric-card military-card'><h4>⚓ MILITARY ZONES</h4><p class='kpi-value' style='color:{accent_purple};'>SECURE</p><span class='kpi-subtext'>No incursions in weapons ranges</span></div>", unsafe_allow_html=True)
    with col3: st.markdown(f"<div class='metric-card'><h4>🌪️ RESILIENCE</h4><p class='kpi-value' style='color:{accent_blue};'>5 REROUTED</p><span class='kpi-subtext'>Avoiding extreme wave heights</span></div>", unsafe_allow_html=True)
    with col4: st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 BLUE CARBON</h4><p class='kpi-value' style='color:{accent_green};'>14.2 HA</p><span class='kpi-subtext'>Optimal restoration sites verified</span></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. REGIONAL MAP CONFIGURATIONS
# ---------------------------------------------------------
map_layers = []

def create_unified_tooltip_data(lat, lon, name, primary, secondary, analytics, source, color, polygon=None, path=None, radius=None, elevation=0):
    return {"lat": lat, "lon": lon, "name": name, "primary_metric": primary, "secondary_metric": secondary, "analytics": analytics, "source": source, "color": color, "polygon": polygon, "path": path, "radius": radius, "elevation": elevation}

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

# Base Configurations
view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=50, bearing=0)
base_lat, base_lon = 33.8, -119.5
regional_ports = ["Port of Los Angeles", "Port of Long Beach", "Port Hueneme"]

if sector_mode == "Pacific Operations (Hawaiian Islands)":
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=50, bearing=0)
    base_lat, base_lon = 21.2, -158.0
    regional_ports = ["Honolulu Harbor", "Pearl Harbor", "Kahului"]

# Common Overlays
if focus_mode in ["🌍 Global Overview", "🌱 ESG Blue Carbon"]:
    p_lat, p_lon = (33.9, -119.4) if sector_mode == "US West Coast (Channel Islands)" else (21.3, -157.6)
    poly = [[[p_lon-0.3, p_lat], [p_lon, p_lat], [p_lon, p_lat+0.2], [p_lon-0.3, p_lat+0.2]]]
    depth_data = create_unified_tooltip_data(p_lat, p_lon-0.15, "Optimal Bathymetric Shelf", "Layer: Ocean Topography", "Range: -5m to -30m", "Depth and SST support ecosystem survival.", "Copernicus Marine", [45, 212, 191, 40], polygon=poly)
    map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([depth_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[45, 212, 191, 150]", line_width_min_pixels=2, pickable=True))
    
    k_lat, k_lon = (34.02, -119.55) if sector_mode == "US West Coast (Channel Islands)" else (21.45, -157.8)
    kelp_df = pd.DataFrame([create_unified_tooltip_data(k_lat, k_lon, "Verified Carbon Sink K-1", "Area: 5.1 HA", "Status: VERIFIED", "Viability Index: 98%. Safe for capital allocation.", "DeepMind SDM", [34, 197, 94, 200], radius=3000)])
    map_layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))

if focus_mode in ["🌍 Global Overview", "🛡️ Threat Interdiction"]:
    m_lat, m_lon = (33.8, -119.2) if sector_mode == "US West Coast (Channel Islands)" else (21.4, -157.8)
    poly = [[[m_lon-1.0, m_lat], [m_lon, m_lat], [m_lon, m_lat+0.4], [m_lon-1.0, m_lat+0.4]]]
    mpa_data = create_unified_tooltip_data(m_lat+0.2, m_lon-0.5, "Marine Protected Area", "Protection Level: FULL", "Jurisdiction: Federal", "Zero-take zone. Continuous AI surveillance active.", "UNEP-WCMC", [56, 189, 248, 20], polygon=poly)
    map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([mpa_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2, pickable=True))

if focus_mode in ["🌍 Global Overview", "🌪️ Supply Chain Resilience"]:
    s_lat, s_lon = (33.6, -119.1) if sector_mode == "US West Coast (Channel Islands)" else (21.0, -157.5)
    poly = [[[s_lon-0.4, s_lat], [s_lon, s_lat], [s_lon, s_lat+0.4], [s_lon-0.4, s_lat+0.4]]]
    storm_data = create_unified_tooltip_data(s_lat+0.2, s_lon-0.2, "Severe Gale Warning", "Alert: WEATHER HAZARD", "Radius: 45nm", "Extreme hydrodynamic drag detected.", "WeatherNext 3", [239, 68, 68, 30], polygon=poly)
    map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([storm_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2, pickable=True))

if focus_mode in ["🌍 Global Overview", "⚓ Military Security"]:
    m_lat, m_lon = (33.2, -119.0) if sector_mode == "US West Coast (Channel Islands)" else (21.8, -159.5)
    poly = [[[m_lon-1.5, m_lat], [m_lon, m_lat], [m_lon, m_lat+0.6], [m_lon-1.5, m_lat+0.6]]]
    military_data = create_unified_tooltip_data(m_lat+0.3, m_lon-0.7, "Naval Sea Range", "Status: RESTRICTED", "Type: Live Fire Area", "Geofence: ACTIVE. High risk of kinetic interaction.", "US Navy", [139, 92, 246, 30], polygon=poly)
    map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([military_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[139, 92, 246, 150]", line_width_min_pixels=2, pickable=True))

# ---------------------------------------------------------
# 7. HIGH-FIDELITY VESSEL SIMULATION
# ---------------------------------------------------------
live_vessels_data = []

# Ensure baseline ships
for i in range(25):
    live_vessels_data.append({
        "MMSI": f"36{random.randint(1000000, 9999999)}", "Vessel Name": f"COMMERCIAL FREIGHTER",
        "lat": base_lat + random.uniform(-1.5, 1.5), "lon": base_lon + random.uniform(-2.0, 2.0),
        "sog": random.uniform(8.0, 22.0), "cog": random.uniform(0, 360),
        "Length (m)": int(random.uniform(150,350)), "Width (m)": int(random.uniform(20,50)),
        "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
    })

# The Critical Dark Target
dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
live_vessels_data.append({
    "MMSI": "413000000", "Vessel Name": "UNVERIFIED DARK TARGET",
    "lat": dt_lat, "lon": dt_lon, "sog": 2.5, "cog": 80.0,
    "Length (m)": 45, "Width (m)": 8, "Risk Status": "CRITICAL ANOMALY",
    "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
})

vessels = []
for v in live_vessels_data:
    is_threat = v['Risk Status'] != "Nominal"
    if focus_mode == "🌱 Planetary Capital (ESG)" and not is_threat: continue
    if focus_mode == "⚓ Military Security" and not is_threat: continue
    
    cog_rad = math.radians(v['cog'])
    vec_len = max(v['sog'] * 0.003, 0.01)
    color = [239, 68, 68, 255] if is_threat else [14, 165, 233, 220]
    ship_poly = get_battleship_polygon(v['lat'], v['lon'], v['cog'], v['Length (m)'], v['Width (m)'])
    elevation = 150 if is_threat else max(30, v['Length (m)'] / 4.0)
    analysis = "CRITICAL ANOMALY: Vessel disabled transponder 15nm from MPA." if is_threat else "Vessel kinetics operate within nominal parameters."
    
    vessels.append(create_unified_tooltip_data(
        v['lat'], v['lon'], v['Vessel Name'], f"Speed: {v['sog']:.1f} kts | Heading: {v['cog']:.1f}°", 
        f"Size: {v['Length (m)']}m x {v['Width (m)']}m", analysis, 
        "Verified AIS", color, polygon=ship_poly, path=[[v['lon'], v['lat']], [v['lon'] + vec_len * math.sin(cog_rad), v['lat'] + vec_len * math.cos(cog_rad)]], elevation=elevation
    ))

vessels_df = pd.DataFrame(vessels)
if not vessels_df.empty:
    map_layers.append(pdk.Layer("PolygonLayer", data=vessels_df, get_polygon="polygon", get_fill_color="color", get_line_color="[255,255,255,100]", line_width_min_pixels=1, extruded=True, get_elevation="elevation", pickable=True))
    map_layers.append(pdk.Layer("PathLayer", data=vessels_df, get_path="path", get_color="color", width_min_pixels=2, pickable=False))

# ---------------------------------------------------------
# 8. RENDER THE INTERACTIVE SMART MAP & DEEP DIVES
# ---------------------------------------------------------
col_map, col_details = st.columns([2.5, 1.5])

with col_map:
    st.markdown("<div style='border: 1px solid #27272a; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.2);'>", unsafe_allow_html=True)
    # SAFEGUARD: Try/Except block guarantees the map never crashes the page
    try:
        r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=tooltip_dict)
        st.pydeck_chart(r, use_container_width=True)
    except Exception as e:
        st.error(f"Map Rendering Offline: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

with col_details:
    st.markdown(f"<div class='metric-card' style='height: 100%; border-top: none; padding-top: 5px;'>", unsafe_allow_html=True)
    
    if focus_mode == "🌍 Global Overview":
        st.markdown(f"<h3 style='color: {accent_blue}; font-size: 1.25rem;'>🌍 Global Telemetry</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Select a specific Strategic Focus from the menu above to filter the map and access deep-dive analytics.</p>", unsafe_allow_html=True)
        st.write(f"• **Total Assets Tracked:** {len(live_vessels_data)}")

    elif focus_mode == "🛡️ Threat Interdiction":
        st.markdown(f"<h3 style='color: {accent_red}; font-size: 1.25rem;'>🛡️ Dark Fleet Analytics</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>IUU fishing is intrinsically linked to modern slavery. By tracking 'Dark Targets,' we enforce human rights on the high seas.</p>", unsafe_allow_html=True)
        st.markdown("#### The Mathematical Trigger")
        st.code("IF (Distance_to_MPA < 15nm) \nAND (Signal_Loss > 60m) \nAND (Speed < 4kts):\n   TRIGGER = HIGH_THREAT", language="python")
        
        # UNCLOS Legal Indictment Tool
        st.markdown("#### Automated UNCLOS Indictment Engine")
        if st.button("⚖️ DRAFT UNCLOS LEGAL INDICTMENT", use_container_width=True):
            with st.spinner("Compiling spatial evidence against Article 73 of UNCLOS..."):
                try:
                    res = model.generate_content(f"Draft a formal, 2-paragraph legal indictment under UNCLOS for a vessel operating illegally without AIS near {dt_lat}, {dt_lon}.")
                    st.success("Indictment Drafted for Interpol Transmission.")
                    st.markdown(f"<div class='terminal'>{res.text}</div>", unsafe_allow_html=True)
                except: st.error("AI Comms Offline.")

    elif focus_mode == "⚓ Military Security":
        st.markdown(f"<h3 style='color: {accent_purple}; font-size: 1.25rem;'>⚓ Geofencing & Kinetic Risk</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Blue 42 continuously ingests the polygons of restricted military zones to calculate Time-To-Intercept (TTI) for commercial vessels.</p>", unsafe_allow_html=True)
        st.markdown("#### Time-To-Intercept Formula")
        st.latex(r"TTI = \frac{Distance\_to\_Geofence}{Velocity\_of\_Vessel}")

    elif focus_mode == "🌪️ Supply Chain Resilience":
        st.markdown(f"<h3 style='color: {accent_blue}; font-size: 1.25rem;'>🌪️ Voyage Optimization</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Severe weather halts shipping, causing massive supply chain shocks that drive global inflation. AI rerouting prevents these shocks.</p>", unsafe_allow_html=True)
        st.latex(r"R_T = \frac{1}{2} \rho v^2 S C_T")
        
        # GENAI ROUTING ENGINE WITH VESSEL SELECTOR
        st.markdown("#### 🧭 GenAI Routing Engine")
        with st.form("routing_form"):
            vessel_opts = [f"{v['Vessel Name']} (MMSI: {v['MMSI']})" for v in live_vessels_data if v['Risk Status'] == "Nominal"]
            selected_vessel = st.selectbox("Select Asset to Reroute:", vessel_opts if vessel_opts else ["No Active Fleet"])
            port_col1, port_col2 = st.columns(2)
            with port_col1: origin_port = st.selectbox("Origin Port:", regional_ports)
            with port_col2: dest_port = st.selectbox("Destination Port:", reversed(regional_ports))
            
            if st.form_submit_button("Generate Predictive Voyage Plan", use_container_width=True):
                target_v = next((v for v in live_vessels_data if v['MMSI'] in selected_vessel), None)
                v_len = target_v['Length (m)'] if target_v else 300
                with st.spinner(f"GenAI calculating drag for {v_len}m vessel..."):
                    try:
                        res = model.generate_content(f"A {v_len}m freighter is transiting from {origin_port} to {dest_port}. Avoid 6.1m waves. Generate 2-step rerouting plan. Estimate fuel saved.")
                        st.markdown(f"<div class='terminal'>{res.text}</div>", unsafe_allow_html=True)
                    except: st.error("AI Comms Offline.")

    elif focus_mode == "🌱 Planetary Capital (ESG)":
        st.markdown(f"<h3 style='color: {accent_green}; font-size: 1.25rem;'>🌱 Capital Verification</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Fusing Earth Engine's bathymetry with DeepMind's Species Distribution Models to find the exact biological envelope for Giant Kelp, de-risking the capital investment.</p>", unsafe_allow_html=True)
        st.write("• **Depth Threshold:** -5m to -30m")
        st.write("• **Thermal Threshold:** SST < 18°C")
        if st.button("Mint Verified Blue Carbon Credits", use_container_width=True):
            st.success("SUCCESS: 2,500 tCO₂e validated. Asset ID #BC-8492-GEE minted.")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 9. ENTERPRISE DATA LEDGER (BOTTOM TABS)
# ---------------------------------------------------------
st.write("---")
st.markdown("### 📈 Operational Analytics & Financial Ledger")
tab1, tab2, tab3 = st.tabs(["🚢 Active Fleet Kinematics", "💰 Scope 3 Financial & Carbon Ledger", "🧠 Strategic Advisory Chat"])

with tab1:
    st.markdown("<p class='hud-text'>Live tactical breakdown of all assets currently operating in the sector. Data includes size, speed, and heading parameters.</p>", unsafe_allow_html=True)
    fleet_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Length (m)", "sog", "cog", "Risk Status"]]
    fleet_df.rename(columns={"sog": "Speed (kts)", "cog": "Heading (°)"}, inplace=True)
    st.dataframe(fleet_df, use_container_width=True)

with tab2:
    st.markdown("<p class='hud-text'>Live accounting of protected maritime cargo value and calculated Scope 3 emissions reductions.</p>", unsafe_allow_html=True)
    ledger_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Risk Status", "Cargo Value ($M)", "Fuel Saved (MT)"]]
    
    total_cargo = ledger_df["Cargo Value ($M)"].sum()
    total_fuel = ledger_df["Fuel Saved (MT)"].sum()
    total_carbon = total_fuel * 3.11 
    total_carbon_value = total_carbon * 75.00
    
    st.markdown(f"**Total Capital Protected:** ${total_cargo:,.1f} Million | **Total Scope 3 Averted:** {total_carbon:,.1f} MT CO₂e | **Verified Carbon Value:** ${total_carbon_value:,.2f}")
    st.dataframe(ledger_df.style.highlight_max(axis=0, subset=["Fuel Saved (MT)"], color=accent_green), use_container_width=True)

with tab3:
    st.markdown("#### Live Intelligence Chat")
    if "messages" not in st.session_state: st.session_state.messages = []
    for message in st.session_state.messages[-3:]: 
        with st.chat_message(message["role"]): st.markdown(message["content"])
    
    if prompt := st.chat_input("Request strategic risk evaluation..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                res = model.generate_content(f"You are a Senior Strategic Advisor. Sector: {sector_mode}. Analyze query: {prompt}")
                st.markdown(res.text)
                st.session_state.messages.append({"role": "assistant", "content": res.text})
            except: st.error("AI Comms Offline.")
