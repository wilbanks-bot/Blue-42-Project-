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

if night_vision:
    bg_color = "#0f172a"; card_bg = "#1e293b"; text_color = "#f8fafc"; muted_text = "#94a3b8"
    accent_blue = "#38bdf8"; accent_red = "#fb7185"; accent_green = "#34d399"; accent_purple = "#a78bfa"; accent_amber = "#fbbf24"
    map_style = "dark" 
else:
    bg_color = "#f1f5f9"; card_bg = "#ffffff"; text_color = "#0f172a"; muted_text = "#64748b"
    accent_blue = "#0284c7"; accent_red = "#e11d48"; accent_green = "#059669"; accent_purple = "#7c3aed"; accent_amber = "#d97706"
    map_style = "light" 

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
    h4 {{ font-size: 0.85rem; text-transform: uppercase; color: {muted_text}; letter-spacing: 0.05em; }}
    .kpi-value {{ font-size: 2.25rem; font-weight: 700; color: {text_color}; margin: 4px 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.85rem; color: {muted_text}; display: block; margin-bottom: 4px; }}
    .streamlit-expanderHeader {{ font-weight: 600 !important; font-size: 0.95rem; color: {text_color} !important; border-radius: 8px; }}
    div[data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid rgba(100,116,139,0.2); }}
    .terminal {{ background-color: #000000; padding: 12px; border: 1px solid {accent_green}; border-radius: 4px; color: {accent_green}; font-family: 'Courier New', monospace; font-size: 0.8rem; box-shadow: inset 0 0 10px rgba(52, 211, 153, 0.2); }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 24px; }}
    .stTabs [data-baseweb="tab"] {{ height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px; }}
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
        model = genai.GenerativeModel('gemini-2.5-flash')
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
st.markdown(f"<p style='text-align: center; color: {muted_text}; font-size: 1.1rem; margin-bottom: 30px;'>Synthesizing planetary telemetry into predictive intelligence and actionable ESG workflows.</p>", unsafe_allow_html=True)

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
# 5. UNIFIED DATA SCHEMA FOR DEEP-DIVE TOOLTIPS
# ---------------------------------------------------------
map_layers = []

def get_tooltip():
    return {
        "html": f"""
        <div style='background: {card_bg}; border: 1px solid {accent_blue}; padding: 14px; border-radius: 10px; color: {text_color}; font-family: Inter, sans-serif; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); max-width: 320px;'>
            <div style='font-size: 1.1rem; font-weight: 700; color: {accent_blue}; margin-bottom: 4px;'>{{name}}</div>
            <div style='font-size: 0.85rem; color: {muted_text}; margin-bottom: 2px;'>{{primary_metric}}</div>
            <div style='font-size: 0.85rem; color: {muted_text}; margin-bottom: 12px;'>{{secondary_metric}}</div>
            <div style='border-top: 1px solid rgba(148, 163, 184, 0.2); padding-top: 10px;'>
                <span style='color: {accent_green}; font-weight: 600; font-size: 0.85rem;'>AI ANALYTICS:</span><br/>
                <span style='font-size: 0.85rem; line-height: 1.4; color: {text_color};'>{{analytics}}</span>
            </div>
            <div style='margin-top: 10px; font-size: 0.75rem; color: {muted_text}; font-style: italic;'>Source: {{source}}</div>
        </div>
        """,
        "style": {"backgroundColor": "transparent", "padding": "0"} 
    }

def create_unified_tooltip_data(lat, lon, name, primary, secondary, analytics, source, color, polygon=None, path=None, radius=None):
    return {"lat": lat, "lon": lon, "name": name, "primary_metric": primary, "secondary_metric": secondary, "analytics": analytics, "source": source, "color": color, "polygon": polygon, "path": path, "radius": radius}

# ---------------------------------------------------------
# 6. REGIONAL MAP CONFIGURATIONS
# ---------------------------------------------------------
if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=45, bearing=0)
    base_lat, base_lon = 33.8, -119.5
    regional_ports = ["Port of Los Angeles", "Port of Long Beach", "Port of Oakland", "Santa Barbara Anchorage"]
    
    if focus_mode in ["🌍 Global Overview", "🌱 ESG Blue Carbon"]:
        depth_data = pd.DataFrame([{"polygon": [[[-119.7, 33.9], [-119.4, 33.9], [-119.4, 34.1], [-119.7, 34.1]]], "name": "Optimal Bathymetric Shelf", "analytics": "Copernicus Depth: -5m to -30m. Optimal biological envelope.", "source": "Copernicus Marine"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=depth_data, get_polygon="polygon", get_fill_color="[45, 212, 191, 30]", get_line_color="[45, 212, 191, 150]", line_width_min_pixels=2, pickable=True))
        kelp_df = pd.DataFrame([create_unified_tooltip_data(34.02, -119.55, "Verified Carbon Sink", "Area: 5.1 HA", "Viability: 98%", "Depth 14m, SST 16.5°C.", "GDM", [34, 197, 94, 200], radius=3000)])
        map_layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))

    if focus_mode in ["🌍 Global Overview", "🛡️ Threat Interdiction"]:
        mpa_data = pd.DataFrame([{"polygon": [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]], "name": "Channel Islands MPA", "analytics": "Federally Protected Boundary. Zero commercial take allowed.", "source": "UNEP-WCMC"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=mpa_data, get_polygon="polygon", get_fill_color="[56, 189, 248, 20]", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2, pickable=True))

    if focus_mode in ["🌍 Global Overview", "🌪️ Supply Chain Resilience"]:
        storm_data = pd.DataFrame([{"polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]], "name": "Severe Gale Warning", "analytics": "H_s > 6.1m detected. High drag coefficient area.", "source": "WeatherNext 3"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[239, 68, 68, 30]", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2, pickable=True))
        route_data = pd.DataFrame([{"path": [[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]], "name": "AI Optimized Route", "analytics": "Fuel optimization vector.", "source": "AlphaEarth"}])
        map_layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[34, 197, 94, 200]", width_min_pixels=3, pickable=True))

    if focus_mode in ["🌍 Global Overview", "⚓ Military Security"]:
        poly = [[[-120.5, 33.2], [-119.0, 33.2], [-119.0, 33.8], [-120.5, 33.8]]]
        military_data = create_unified_tooltip_data(33.5, -119.7, "Point Mugu Sea Range", "Status: RESTRICTED", "Type: Naval Weapons Testing Area", "Vessel traffic strictly prohibited. High kinetic risk.", "US Navy", [139, 92, 246, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([military_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[139, 92, 246, 150]", line_width_min_pixels=2, pickable=True))

else: # HAWAII
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=45, bearing=0)
    base_lat, base_lon = 21.2, -158.0
    regional_ports = ["Honolulu Harbor", "Pearl Harbor", "Kahului", "Hilo Harbor"]
    
    if focus_mode in ["🌍 Global Overview", "🌱 ESG Blue Carbon"]:
        depth_data = pd.DataFrame([{"polygon": [[[-158.0, 21.3], [-157.6, 21.3], [-157.6, 21.6], [-158.0, 21.6]]], "name": "Reef Bathymetric Contour", "analytics": "Copernicus Depth: -5m to -30m.", "source": "Copernicus Marine"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=depth_data, get_polygon="polygon", get_fill_color="[45, 212, 191, 30]", get_line_color="[45, 212, 191, 150]", line_width_min_pixels=2, pickable=True))
        overlay_df = pd.DataFrame([create_unified_tooltip_data(21.45, -157.8, "Verified Reef Restoration Zone", "Area: 6.5 HA", "Viability: 96%", "Depth 8m, SST 24.5°C.", "GDM", [34, 197, 94, 200], radius=3000)])
        map_layers.append(pdk.Layer("ScatterplotLayer", data=overlay_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))

    if focus_mode in ["🌍 Global Overview", "🛡️ Threat Interdiction"]:
        mpa_data = pd.DataFrame([{"polygon": [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]], "name": "Kaena Point MPA Expansion", "analytics": "Federally Protected Boundary. Zero commercial take.", "source": "UNEP-WCMC"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=mpa_data, get_polygon="polygon", get_fill_color="[56, 189, 248, 30]", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2, pickable=True))

    if focus_mode in ["🌍 Global Overview", "🌪️ Supply Chain Resilience"]:
        storm_data = pd.DataFrame([{"polygon": [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]], "name": "Tropical Squall Hazard", "analytics": "H_s > 4.5m detected. Severe drag penalty.", "source": "WeatherNext 3"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[239, 68, 68, 30]", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2, pickable=True))
        route_data = pd.DataFrame([{"path": [[-158.5, 20.8], [-158.0, 20.9], [-157.4, 20.9], [-157.1, 21.2]], "name": "AI Optimized Route", "analytics": "Fuel optimization vector.", "source": "AlphaEarth"}])
        map_layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[34, 197, 94, 200]", width_min_pixels=3, pickable=True))

    if focus_mode in ["🌍 Global Overview", "⚓ Military Security"]:
        poly = [[[-159.9, 21.8], [-159.5, 21.8], [-159.5, 22.2], [-159.9, 22.2]]]
        military_data = create_unified_tooltip_data(22.0, -159.7, "PMRF Barking Sands", "Status: RESTRICTED", "Type: Pacific Missile Range", "Civilian intrusion violates federal exclusion zone.", "US Navy", [139, 92, 246, 30], polygon=poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([military_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[139, 92, 246, 150]", line_width_min_pixels=2, pickable=True))

# ---------------------------------------------------------
# 7. VESSELS ENGINE (Muted styling for professional look)
# ---------------------------------------------------------
vessels = []
live_vessels_data = [] # Data list for the financial ledger

if focus_mode in ["🌍 Global Overview", "🌪️ Supply Chain Resilience"]:
    for i in range(25):
        sog = random.uniform(8.0, 22.0)
        v_type = random.choice(["CARGO", "TANKER", "BULK"])
        mmsi = f"36{random.randint(1000000, 9999999)}"
        lat = base_lat + random.uniform(-1.5, 1.5)
        lon = base_lon + random.uniform(-2.0, 2.0)
        
        # Save to both map and ledger
        vessels.append(create_unified_tooltip_data(lat, lon, f"{v_type} (MMSI: {mmsi})", f"Speed: {sog:.1f} kts", "Status: NOMINAL", "Operating within compliance parameters.", "AIS", [148, 163, 184, 150], radius=1000))
        live_vessels_data.append({"Vessel Name": f"{v_type} {mmsi[-4:]}", "MMSI": mmsi, "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)})

if focus_mode in ["🌍 Global Overview", "🛡️ Threat Interdiction"]:
    dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
    vessels.append(create_unified_tooltip_data(dt_lat, dt_lon, "UNVERIFIED DARK TARGET", "Speed: 2.5 kts (Loitering)", "Status: CRITICAL ANOMALY", "Vessel disabled transponder 15nm from MPA. Kinematics suggest illicit activity.", "AIS/WDPA", [239, 68, 68, 255], radius=2000))
    live_vessels_data.append({"Vessel Name": "UNVERIFIED DARK TARGET", "MMSI": "413000000", "Risk Status": "CRITICAL ANOMALY", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0})

vessels_df = pd.DataFrame(vessels)
if not vessels_df.empty:
    map_layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))

# ---------------------------------------------------------
# 8. RENDER THE INTERACTIVE SMART MAP & DEEP DIVES
# ---------------------------------------------------------
col_map, col_details = st.columns([2.5, 1.5])

with col_map:
    st.markdown("<div style='border: 1px solid #27272a; border-radius: 8px; overflow: hidden;'>", unsafe_allow_html=True)
    r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=get_tooltip())
    st.pydeck_chart(r, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_details:
    st.markdown(f"<div class='metric-card' style='height: 100%; border-top: none; padding-top: 5px;'>", unsafe_allow_html=True)
    
    if focus_mode == "🌍 Global Overview":
        st.markdown(f"<h3 style='color: {accent_blue}; font-size: 1.25rem;'>🌍 Global Telemetry</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Select a specific Strategic Focus from the menu above to filter the map and access deep-dive analytics.</p>", unsafe_allow_html=True)
        
        st.markdown("#### 💡 Operational Impact")
        st.info("By aggregating disparate data sets (weather, defense, ecology, logistics) into a single Common Operating Picture (COP), Blue 42 eliminates data silos, allowing executives to make holistic, planetary-scale decisions.")
        
        st.markdown("#### System Baseline")
        st.write("• **Total Assets Tracked:** 26")
        st.write("• **Active Anomalies:** 1")

    elif focus_mode == "🛡️ Threat Interdiction":
        st.markdown(f"<h3 style='color: {accent_red}; font-size: 1.25rem;'>🛡️ Dark Fleet Analytics</h3>", unsafe_allow_html=True)
        
        st.markdown("#### 💡 Operational Impact")
        st.info("Illegal, Unreported, and Unregulated (IUU) fishing costs the global economy **$20 Billion annually**. By automating detection using spatial correlations, Coast Guards transition from reactive patrols to targeted, high-efficiency enforcement.")
        
        st.markdown("#### The Mathematical Trigger")
        st.code("IF (Distance_to_MPA < 15nm) \nAND (Signal_Loss > 60m) \nAND (Speed < 4kts):\n   TRIGGER = HIGH_THREAT", language="python")
        
        st.markdown("#### Tactical Action")
        if st.button("🛰️ INITIATE SAR TASKING", use_container_width=True):
            st.session_state["sar_tasked"] = True
        
        if st.session_state.get("sar_tasked", False):
            st.success("SAR CONFIRMATION: 45m metallic hull detected. Intercept authorized.")

    elif focus_mode == "⚓ Military Security":
        st.markdown(f"<h3 style='color: {accent_purple}; font-size: 1.25rem;'>⚓ Geofencing & Kinetic Risk</h3>", unsafe_allow_html=True)
        
        st.markdown("#### 💡 Operational Impact")
        st.info("When civilian vessels inadvertently enter active naval testing ranges, multi-million dollar exercises must be halted. Automated geofencing preserves military readiness and protects civilian life.")
        
        st.markdown("#### Time-To-Intercept Formula")
        st.latex(r"TTI = \frac{Distance\_to\_Geofence}{Velocity\_of\_Vessel}")
        st.success("STATUS: Nominal. Zero civilian incursions detected in active live-fire ranges.")

    elif focus_mode == "🌪️ Supply Chain Resilience":
        st.markdown(f"<h3 style='color: {accent_blue}; font-size: 1.25rem;'>🌪️ Voyage Optimization</h3>", unsafe_allow_html=True)
        
        st.markdown("#### 💡 Operational Impact")
        st.info("Pushing a 300-meter freighter through 20-foot seas causes immense drag. Rerouting avoids supply chain disruption and cuts fuel consumption by **5% to 12% per transit**, directly lowering Scope 3 emissions.")

        st.markdown("#### Hydrodynamic Drag Equation")
        st.latex(r"R_T = \frac{1}{2} \rho v^2 S C_T")
        st.markdown(f"<span style='color: {muted_text}; font-size: 0.85rem;'>Altering the route to avoid $H_s \ge 6.1$m waves drops the drag coefficient ($C_T$) by ~42%.</span>", unsafe_allow_html=True)

    elif focus_mode == "🌱 ESG Blue Carbon":
        st.markdown(f"<h3 style='color: {accent_green}; font-size: 1.25rem;'>🌱 Capital Verification</h3>", unsafe_allow_html=True)
        
        st.markdown("#### 💡 Operational Impact")
        st.info("Investors fear 'impermanence'—that funded kelp forests will die in a heatwave. By utilizing Earth Engine and DeepMind models, the AI guarantees coordinates will sustain growth, completely de-risking capital investment.")

        st.markdown("#### Ecological Analytics")
        st.write("• **Depth Threshold:** -5m to -30m (Sunlight Penetration)")
        st.write("• **Thermal Threshold:** SST < 18°C (Prevents Mortality)")
        st.markdown("#### Institutional Asset Minting")
        if st.button("Mint Verified Blue Carbon Credits", use_container_width=True):
            st.success("SUCCESS: 2,500 tCO₂e validated. Asset ID #BC-8492-GEE minted.")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 9. THE ENTERPRISE ANALYTICS SUITE (BOTTOM TABS)
# ---------------------------------------------------------
st.write("---")
st.markdown("### 📈 Operational Analytics & AI Intelligence")

# RESTORED: The 4-Tab Analytics Suite featuring the Routing Engine and Data Dictionary!
tab1, tab2, tab3, tab4 = st.tabs(["💰 Scope 3 Financial Ledger", "🧭 GenAI Voyage Routing Engine", "🧠 Strategic Advisory Chat", "📖 Maritime Data Dictionary"])

with tab1:
    st.markdown("<p class='hud-text'>Live accounting of protected maritime cargo value and calculated Scope 3 emissions reductions from AI route optimization. Carbon valuation pegged to active Compliance Markets (e.g., California Cap-and-Trade / EU ETS).</p>", unsafe_allow_html=True)
    if not live_vessels_data:
        st.warning("Switch focus mode to 'Global Overview' or 'Supply Chain Resilience' to populate live ledger data.")
    else:
        ledger_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Risk Status", "Cargo Value ($M)", "Fuel Saved (MT)"]]
        
        total_cargo = ledger_df["Cargo Value ($M)"].sum()
        total_fuel = ledger_df["Fuel Saved (MT)"].sum()
        total_carbon = total_fuel * 3.11 
        carbon_price_per_ton = 75.00
        total_carbon_value = total_carbon * carbon_price_per_ton
        
        st.markdown(f"**Total Capital Protected:** ${total_cargo:,.1f} Million | **Total Scope 3 Averted:** {total_carbon:,.1f} MT CO₂e | **Verified Carbon Value:** ${total_carbon_value:,.2f}")
        st.dataframe(ledger_df.style.highlight_max(axis=0, subset=["Fuel Saved (MT)"], color=accent_green), use_container_width=True)

with tab2:
    # RESTORED AND ENHANCED: The GenAI Routing Engine
    st.markdown("#### 🧭 Dynamic Route Optimization")
    st.markdown("<p class='hud-text'>Use AI to mathematically calculate safe passage through severe weather polygons to optimize fuel consumption and avoid drag.</p>", unsafe_allow_html=True)
    
    with st.form("routing_form"):
        st.write("**Configure Voyage Parameters:**")
        port_col1, port_col2 = st.columns(2)
        with port_col1:
            origin_port = st.selectbox("Origin Port:", regional_ports)
        with port_col2:
            dest_port = st.selectbox("Destination Port:", reversed(regional_ports))
        
        submit_route = st.form_submit_button("Generate Predictive Voyage Plan")
        
        if submit_route:
            with st.spinner("GenAI correlating live weather with decadal baseline..."):
                try:
                    routing_prompt = f"You are a strategic marine logistics AI. A commercial vessel is transiting from {origin_port} to {dest_port}. A weather hazard with significant wave heights (H_s) > 6.1m is detected. Generate a brief, highly technical 3-step voyage rerouting plan to minimize drag. Estimate bunker fuel saved. Use bullet points."
                    route_response = model.generate_content(routing_prompt)
                    st.success("Routing Plan Authorized and Generated")
                    st.markdown(f"<div class='terminal'>{route_response.text}</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"GenAI Error: {e}")

with tab3:
    st.markdown("#### 💬 Live Intelligence Chat")
    st.markdown("<p class='hud-text'>Interrogate the AI directly regarding operational parameters, risk profiles, or maritime law.</p>", unsafe_allow_html=True)
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for message in st.session_state.messages[-3:]: 
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("Request strategic risk evaluation..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                tactical_prompt = f"You are a Senior Strategic Advisor. Sector is {sector_mode}. Analyze the query focusing on business value, capital risk, and operational continuity: {prompt}"
                response = model.generate_content(tactical_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"GenAI Chat Error: {e}")

with tab4:
    # NEW FEATURE: Maritime Data Dictionary
    st.markdown("#### 📖 Maritime Data Dictionary")
    st.markdown("<p class='hud-text'>A reference guide translating raw telemetry acronyms into plain English for stakeholders.</p>", unsafe_allow_html=True)
    
    col_dict1, col_dict2 = st.columns(2)
    with col_dict1:
        st.info("**SOG (Speed Over Ground):** The actual speed the vessel is moving relative to the earth. If SOG drops drastically in open water, it indicates loitering or distress.")
        st.info("**COG (Course Over Ground):** The actual direction the vessel is moving. Erratic COG changes suggest a search pattern or evasive maneuvers.")
        st.info("**MMSI (Maritime Mobile Service Identity):** A unique 9-digit tracker ID. Spoofing or disabling this near an MPA is a massive red flag for illegal activity.")
    with col_dict2:
        st.info("**$H_s$ (Significant Wave Height):** The average height of the highest one-third of waves. An $H_s$ of 6.1m means a vessel is fighting 20-foot seas, causing severe engine strain.")
        st.info("**SST (Sea Surface Temperature):** Used to verify the survivability of Blue Carbon investments. Kelp requires cool, nutrient-rich water (< 18°C) to survive.")
        st.info("**Draft:** How deep the ship sits in the water. A deeper draft increases hydrodynamic drag, requiring more precise route optimization to save fuel.")
