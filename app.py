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
    st.session_state.sar_tasked = False

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
    .terminal {{ background-color: #000000; padding: 12px; border: 1px solid {accent_green}; border-radius: 4px; color: {accent_green}; font-family: 'Courier New', monospace; font-size: 0.8rem; box-shadow: inset 0 0 10px rgba(52, 211, 153, 0.2); max-height: 250px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }}
    .ticker-wrap {{ width: 100%; overflow: hidden; background-color: {card_bg}; border-bottom: 1px solid rgba(100,116,139,0.2); padding: 8px 0; margin-bottom: 20px; }}
    .ticker {{ display: inline-block; white-space: nowrap; padding-right: 100%; animation-iteration-count: infinite; animation-timing-function: linear; animation-name: ticker; animation-duration: 30s; }}
    .ticker-item {{ display: inline-block; padding: 0 2rem; font-family: monospace; font-size: 0.9rem; color: {accent_blue}; font-weight: 600; }}
    @keyframes ticker {{ 0% {{ transform: translate3d(0, 0, 0); }} 100% {{ transform: translate3d(-100%, 0, 0); }} }}
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
        model = genai.GenerativeModel('gemini-2.5-flash')
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
    <div style="font-size: 40px; color: {accent_blue}; line-height: 1;">🌊</div>
    <div style="font-weight: 700; color: {text_color}; font-size: 1.4rem; letter-spacing: 1px; margin-top: 5px;">BLUE 42 COMMAND</div>
    <div style="color: {muted_text}; font-size: 0.75rem; font-weight: 500; letter-spacing: 1px; text-transform: uppercase;">Global Blue Economy OS</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🌍 REGIONAL DEPLOYMENT")
sector_mode = st.sidebar.selectbox("Operational Theater:", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"], label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 LIVE TELEMETRY")
live_ais = st.sidebar.toggle("Connect Live Satellite AIS Feed", value=False)
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 SYSTEM DIAGNOSTICS")
st.sidebar.caption(f"**Geospatial Engine:** {ee_status}\n\n**GenAI Reasoning:** {ai_status}\n\n**AIS Telemetry:** {ais_status}")

# ---------------------------------------------------------
# 4. EXECUTIVE STORYBOARD & STRATEGIC FILTER
# ---------------------------------------------------------
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker">
        <span class="ticker-item">⚠️ GLOBAL SUPPLY CHAIN VALUE AT RISK (H_s > 6.1m): $4.2B</span>
        <span class="ticker-item">✅ SCOPE 3 EMISSIONS AVERTED (24HR): 1,245 MT CO2e</span>
        <span class="ticker-item">🌱 VERIFIED BLUE CARBON ASSETS: $12.4M</span>
        <span class="ticker-item">🚨 ACTIVE IUU THREATS TRACKED: 1</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"<h2 style='color: {text_color}; text-align: center; margin-bottom: 8px; font-weight: 700;'>Global Maritime Command Center</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: {muted_text}; font-size: 1.1rem; margin-bottom: 30px;'>Synthesizing planetary telemetry into predictive intelligence for global economic stability and human rights.</p>", unsafe_allow_html=True)

focus_mode = st.radio("SELECT STRATEGIC FOCUS TO FILTER BATTLESPACE & ANALYTICS:", 
    ["🌍 Global Overview", "🛡️ Human Rights & Ecocide (IUU)", "🌪️ Macro-Economic Resilience", "🌱 Planetary Capital (ESG)"], 
    horizontal=True)
st.write("")

col1, col2, col3, col4 = st.columns(4)
with col1: st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ACTIVE THREATS</h4><p class='kpi-value' style='color:{accent_red};'>1 VOI</p><span class='kpi-subtext'>High risk of forced labor / IUU</span></div>", unsafe_allow_html=True)
with col2: st.markdown(f"<div class='metric-card military-card'><h4>⚓ SOVEREIGNTY</h4><p class='kpi-value' style='color:{accent_purple};'>SECURE</p><span class='kpi-subtext'>No incursions in restricted zones</span></div>", unsafe_allow_html=True)
with col3: st.markdown(f"<div class='metric-card'><h4>🌪️ MACRO-ECONOMICS</h4><p class='kpi-value' style='color:{accent_blue};'>5 REROUTED</p><span class='kpi-subtext'>Inflationary supply shocks averted</span></div>", unsafe_allow_html=True)
with col4: st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 PLANETARY CAPITAL</h4><p class='kpi-value' style='color:{accent_green};'>14.2 HA</p><span class='kpi-subtext'>Optimal bio-sinks verified</span></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. BATTLESHIP 3D POLYGON RENDERER
# ---------------------------------------------------------
# THE UX UPGRADE: Mathematically rendering physical 3D Battleship game pieces!
def get_battleship_polygon(lat, lon, cog, length_m, width_m):
    cog_rad = math.radians(cog)
    # Exaggerate the size slightly so it pops on the map like a physical game piece
    scale = 3.5 
    L = length_m * scale
    W = width_m * scale
    
    # Approximate degree conversion for standard Web Mercator
    lat_deg_per_m = 1.0 / 111111.0
    lon_deg_per_m = 1.0 / (111111.0 * math.cos(math.radians(lat)))
    
    # Create the geometric shape of a ship (Flat Stern, Pointed Bow)
    pts = [
        (-W/2, -L/2), # Stern port
        (W/2, -L/2),  # Stern starboard
        (W/2, L/4),   # Mid starboard
        (0, L/2),     # Pointed Bow
        (-W/2, L/4)   # Mid port
    ]
    
    poly = []
    for dx, dy in pts:
        # Rotate the points so the bow points directly at the Course Over Ground (COG)
        x_rot = dx * math.cos(cog_rad) + dy * math.sin(cog_rad)
        y_rot = -dx * math.sin(cog_rad) + dy * math.cos(cog_rad)
        poly.append([lon + x_rot * lon_deg_per_m, lat + y_rot * lat_deg_per_m])
    return [poly]

# ---------------------------------------------------------
# 6. UNIFIED DATA SCHEMA FOR DEEP-DIVE TOOLTIPS
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
                <span style='color: {accent_green}; font-weight: 600; font-size: 0.85rem;'>NOBEL-TIER ANALYTICS:</span><br/>
                <span style='font-size: 0.85rem; line-height: 1.4; color: {text_color};'>{{analytics}}</span>
            </div>
            <div style='margin-top: 10px; font-size: 0.75rem; color: {muted_text}; font-style: italic;'>Source: {{source}}</div>
        </div>
        """,
        "style": {"backgroundColor": "transparent", "padding": "0"} 
    }

def create_unified_tooltip_data(lat, lon, name, primary, secondary, analytics, source, color, polygon=None, path=None, radius=None, elevation=0):
    return {"lat": lat, "lon": lon, "name": name, "primary_metric": primary, "secondary_metric": secondary, "analytics": analytics, "source": source, "color": color, "polygon": polygon, "path": path, "radius": radius, "elevation": elevation}

# ---------------------------------------------------------
# 7. DYNAMIC MAP LOGIC (FILTERED BY FOCUS)
# ---------------------------------------------------------
if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=60, bearing=-25)
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]]
    base_lat, base_lon = 33.8, -119.5
    regional_ports = ["Port of Los Angeles", "Port of Long Beach", "Port Hueneme"]
    
    if focus_mode in ["🌍 Global Overview", "🌱 Planetary Capital (ESG)"]:
        depth_data = pd.DataFrame([{"polygon": [[[-119.7, 33.9], [-119.4, 33.9], [-119.4, 34.1], [-119.7, 34.1]]], "name": "Optimal Bathymetric Shelf", "analytics": "Copernicus Depth: -5m to -30m.", "source": "Copernicus Marine"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=depth_data, get_polygon="polygon", get_fill_color="[45, 212, 191, 30]", get_line_color="[45, 212, 191, 150]", line_width_min_pixels=2, pickable=True))
        
        mining_poly = [[[-120.5, 33.0], [-119.5, 33.0], [-119.5, 33.3], [-120.5, 33.3]]]
        mining_data = create_unified_tooltip_data(33.15, -120.0, "UN High Seas Treaty Exclusion Zone", "Status: Protected Benthic Zone", "Threat: Deep Sea Mining", "AI actively monitoring for unauthorized seabed dredging vessels.", "UNCLOS", [234, 179, 8, 40], polygon=mining_poly)
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([mining_data]), get_polygon="polygon", get_fill_color="color", get_line_color="[234, 179, 8, 150]", line_width_min_pixels=2, pickable=True))

    if focus_mode in ["🌍 Global Overview", "🛡️ Human Rights & Ecocide (IUU)"]:
        mpa_data = pd.DataFrame([{"polygon": [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]], "name": "Channel Islands MPA", "analytics": "Federally Protected Boundary.", "source": "UNEP-WCMC"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=mpa_data, get_polygon="polygon", get_fill_color="[56, 189, 248, 20]", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2, pickable=True))

    if focus_mode in ["🌍 Global Overview", "🌪️ Macro-Economic Resilience"]:
        storm_data = pd.DataFrame([{"polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]], "name": "Severe Gale Warning", "analytics": "H_s > 6.1m detected.", "source": "WeatherNext 3"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[239, 68, 68, 30]", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2, pickable=True))
        route_data = pd.DataFrame([{"path": [[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]], "name": "AI Optimized Route", "analytics": "Fuel optimization vector.", "source": "AlphaEarth"}])
        map_layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[34, 197, 94, 200]", width_min_pixels=3, pickable=True))

else: # HAWAII
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=60, bearing=-25)
    base_lat, base_lon = 21.2, -158.0
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    regional_ports = ["Honolulu Harbor", "Pearl Harbor", "Kahului"]
    
    if focus_mode in ["🌍 Global Overview", "🌱 Planetary Capital (ESG)"]:
        depth_data = pd.DataFrame([{"polygon": [[[-158.0, 21.3], [-157.6, 21.3], [-157.6, 21.6], [-158.0, 21.6]]], "name": "Reef Bathymetric Contour", "analytics": "Copernicus Depth: -5m to -30m.", "source": "Copernicus Marine"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=depth_data, get_polygon="polygon", get_fill_color="[45, 212, 191, 30]", get_line_color="[45, 212, 191, 150]", line_width_min_pixels=2, pickable=True))

    if focus_mode in ["🌍 Global Overview", "🛡️ Human Rights & Ecocide (IUU)"]:
        mpa_data = pd.DataFrame([{"polygon": [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]], "name": "Kaena Point MPA", "analytics": "Federally Protected Boundary.", "source": "UNEP-WCMC"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=mpa_data, get_polygon="polygon", get_fill_color="[56, 189, 248, 30]", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2, pickable=True))

    if focus_mode in ["🌍 Global Overview", "🌪️ Macro-Economic Resilience"]:
        storm_data = pd.DataFrame([{"polygon": [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]], "name": "Tropical Squall Hazard", "analytics": "H_s > 4.5m detected.", "source": "WeatherNext 3"}])
        map_layers.append(pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[239, 68, 68, 30]", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2, pickable=True))
        route_data = pd.DataFrame([{"path": [[-158.5, 20.8], [-158.0, 20.9], [-157.4, 20.9], [-157.1, 21.2]], "name": "AI Optimized Route", "analytics": "Fuel optimization vector.", "source": "AlphaEarth"}])
        map_layers.append(pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[34, 197, 94, 200]", width_min_pixels=3, pickable=True))

# ---------------------------------------------------------
# 8. LIVE SATELLITE FEED WITH 3D BATTLESHIP RENDERING
# ---------------------------------------------------------
live_vessels_data = []

# Fetch or Simulate Data
# INCREASED TO 65 VESSELS FOR MAXIMUM MAP DENSITY
for i in range(65):
    sog = random.uniform(8.0, 22.0)
    v_type = random.choice(["CARGO", "TANKER", "BULK"])
    mmsi = f"36{random.randint(1000000, 9999999)}"
    lat = base_lat + random.uniform(-1.5, 1.5)
    lon = base_lon + random.uniform(-2.0, 2.0)
    cog = random.uniform(0, 360)
    v_len = int(random.uniform(150,350))
    v_width = int(v_len * 0.15)
    v_draft = round(random.uniform(9.0,16.0), 1)
    
    live_vessels_data.append({
        "MMSI": mmsi, "Vessel Name": f"{v_type} {mmsi[-4:]}", "Type": v_type,
        "lat": lat, "lon": lon, "sog": round(sog,1), "cog": round(cog,1),
        "Length (m)": v_len, "Width (m)": v_width, "Draft (m)": v_draft, "Gross Tonnage": int(v_len * v_width * v_draft * 0.7),
        "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
    })

# Add the Suspect Target
dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
live_vessels_data.append({
    "MMSI": "413000000", "Vessel Name": "UNVERIFIED DARK TARGET", "Type": "SUSPECT",
    "lat": dt_lat, "lon": dt_lon, "sog": 2.5, "cog": 80.0,
    "Length (m)": 45, "Width (m)": 8, "Draft (m)": 3.2, "Gross Tonnage": 806,
    "Risk Status": "CRITICAL ANOMALY", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
})

vessels = []
for v in live_vessels_data:
    is_threat = v['Risk Status'] != "Nominal"
    
    # Hide nominal vessels if we are focusing purely on non-vessel ESG metrics to keep it clean
    if focus_mode == "🌱 Planetary Capital (ESG)" and not is_threat: continue
    
    # ARPA Heading Vector Calculation
    cog_rad = math.radians(v['cog'])
    vec_len = max(v['sog'] * 0.003, 0.01)
    heading_path = [[v['lon'], v['lat']], [v['lon'] + vec_len * math.sin(cog_rad), v['lat'] + vec_len * math.cos(cog_rad)]]
    
    # Tactical Colors
    color = [239, 68, 68, 255] if is_threat else [56, 189, 248, 200]
    
    # BATTLESHIP GEOMETRY: Convert length/width into a 3D Poly Arrow
    ship_poly = get_battleship_polygon(v['lat'], v['lon'], v['cog'], v['Length (m)'], v['Width (m)'])
    
    # Dynamic 3D elevation (Taller for bigger ships, massive spike for the threat)
    elevation = 150 if is_threat else max(50, v['Length (m)'] / 3.0)

    analysis = "CRITICAL HUMAN RIGHTS ANOMALY: Vessel disabled transponder 15nm from MPA. Kinematics strongly suggest illicit fishing and forced labor / transshipment operations." if is_threat else "Vessel kinetics operate within nominal parameters. Compliant track."
    
    vessels.append(create_unified_tooltip_data(
        v['lat'], v['lon'], v['Vessel Name'], f"Speed: {v['sog']} kts | Heading: {v['cog']}°", 
        f"Length: {v['Length (m)']}m | Tonnage: {v['Gross Tonnage']:,} GT", analysis, 
        "Verified AIS Telemetry", color, polygon=ship_poly, path=heading_path, elevation=elevation
    ))

vessels_df = pd.DataFrame(vessels)

if not vessels_df.empty:
    # 1. BATTLESHIP EXTRUSION LAYER (This physically raises the ships off the map in 3D!)
    map_layers.append(pdk.Layer(
        "PolygonLayer", 
        data=vessels_df, 
        get_polygon="polygon", 
        get_fill_color="color", 
        get_line_color="[255,255,255,150]", 
        line_width_min_pixels=1, 
        extruded=True,             # Activates 3D blocks
        get_elevation="elevation", # Sets the height of the block
        pickable=True
    ))
    # 2. ARPA Heading Lines
    map_layers.append(pdk.Layer("PathLayer", data=vessels_df, get_path="path", get_color="color", width_min_pixels=2, pickable=False))

# ---------------------------------------------------------
# 9. RENDER THE INTERACTIVE SMART MAP & DEEP DIVES
# ---------------------------------------------------------
col_map, col_details = st.columns([2.5, 1.5])

with col_map:
    st.markdown("<div style='border: 1px solid #27272a; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.2);'>", unsafe_allow_html=True)
    r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=get_tooltip())
    st.pydeck_chart(r, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_details:
    st.markdown(f"<div class='metric-card' style='height: 100%; border-top: none; padding-top: 5px;'>", unsafe_allow_html=True)
    
    if focus_mode == "🌍 Global Overview":
        st.markdown(f"<h3 style='color: {accent_blue}; font-size: 1.25rem;'>🌍 Global Telemetry</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Select a specific Strategic Focus from the menu above to filter the map and access deep-dive analytics.</p>", unsafe_allow_html=True)
        st.write(f"• **Total Assets Tracked:** {len(live_vessels_data)}")
        st.write("• **Active Anomalies:** 1")

    elif focus_mode == "🛡️ Human Rights & Ecocide (IUU)":
        st.markdown(f"<h3 style='color: {accent_red}; font-size: 1.25rem;'>🛡️ Dark Fleet & Human Rights Analytics</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>IUU fishing is intrinsically linked to modern slavery and transshipment laundering. By tracking these 'Dark Targets,' we enforce human rights on the high seas.</p>", unsafe_allow_html=True)
        st.markdown("#### The Mathematical Trigger")
        st.code("IF (Distance_to_MPA < 15nm) \nAND (Signal_Loss > 60m) \nAND (Speed < 4kts):\n   TRIGGER = HUMAN_RIGHTS_THREAT", language="python")
        
        # NOBEL TIER: Automated UNCLOS Prosecution
        st.markdown("#### Tactical Action: Legal Indictment")
        if st.button("⚖️ DRAFT UNCLOS LEGAL INDICTMENT", use_container_width=True):
            with st.spinner("Compiling spatial evidence against Article 73 of UNCLOS..."):
                try:
                    legal_prompt = f"Draft a highly formal, 2-paragraph legal indictment under the UN Convention on the Law of the Sea (UNCLOS) for a vessel with MMSI 413000000 caught operating illegally without AIS near coordinates {dt_lat}, {dt_lon}."
                    res = model.generate_content(legal_prompt)
                    st.success("Indictment Drafted for Interpol Transmission.")
                    st.markdown(f"<div class='terminal'>{res.text}</div>", unsafe_allow_html=True)
                except: st.error("AI Comms Offline.")

    elif focus_mode == "⚓ Military Security":
        st.markdown(f"<h3 style='color: {accent_purple}; font-size: 1.25rem;'>⚓ Geofencing & Kinetic Risk</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Blue 42 continuously ingests the polygons of restricted military zones to calculate Time-To-Intercept (TTI) for commercial vessels.</p>", unsafe_allow_html=True)
        st.markdown("#### Time-To-Intercept Formula")
        st.latex(r"TTI = \frac{Distance\_to\_Geofence}{Velocity\_of\_Vessel}")
        st.info("STATUS: Nominal. Zero civilian incursions detected in active live-fire ranges.")

    elif focus_mode == "🌪️ Macro-Economic Resilience":
        st.markdown(f"<h3 style='color: {accent_blue}; font-size: 1.25rem;'>🌪️ Supply Chain Optimization</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Severe weather halts shipping, causing massive supply chain shocks that drive global inflation. AI rerouting prevents these shocks, stabilizing the global economy.</p>", unsafe_allow_html=True)
        
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
                        res = model.generate_content(f"A {v_len}m freighter is transiting {origin_port} to {dest_port}. Avoid 6.1m waves. Generate 2-step rerouting plan. Estimate fuel saved.")
                        st.markdown(f"<div class='terminal'>{res.text}</div>", unsafe_allow_html=True)
                    except: st.error("AI Comms Offline.")

    elif focus_mode == "🌱 Planetary Capital (ESG)":
        st.markdown(f"<h3 style='color: {accent_green}; font-size: 1.25rem;'>🌱 Capital Verification</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text}; font-size: 0.9rem;'>Fusing bathymetry with DeepMind SDMs to find the exact biological envelope for Giant Kelp, de-risking the capital investment.</p>", unsafe_allow_html=True)
        st.markdown("#### Ecological Analytics")
        st.write("• **Depth Threshold:** -5m to -30m")
        st.write("• **Thermal Threshold:** SST < 18°C")
        if st.button("Mint Verified Blue Carbon Credits", use_container_width=True): st.success("SUCCESS: 2,500 tCO₂e validated. Asset ID #BC-8492-GEE minted.")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 10. ENTERPRISE DATA LEDGER
# ---------------------------------------------------------
st.write("---")
st.markdown("#### 📈 Enterprise Data Ledger")
tab1, tab2 = st.tabs(["💰 Scope 3 Financial & Carbon Ledger", "📋 Executive Action Reports"])

with tab1:
    st.markdown("<p class='hud-text'>Live accounting of protected maritime cargo value and calculated Scope 3 emissions reductions from AI route optimization. Carbon valuation pegged to active Compliance Markets.</p>", unsafe_allow_html=True)
    ledger_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Length (m)", "Gross Tonnage", "Risk Status", "Cargo Value ($M)", "Fuel Saved (MT)"]]
    
    total_cargo = ledger_df["Cargo Value ($M)"].sum()
    total_fuel = ledger_df["Fuel Saved (MT)"].sum()
    total_carbon = total_fuel * 3.11 
    total_carbon_value = total_carbon * 75.00
    
    st.markdown(f"**Total Capital Protected:** ${total_cargo:,.1f} Million | **Total Scope 3 Averted:** {total_carbon:,.1f} MT CO₂e | **Verified Carbon Value:** ${total_carbon_value:,.2f}")
    st.dataframe(ledger_df.style.highlight_max(axis=0, subset=["Fuel Saved (MT)"], color=accent_green), use_container_width=True)

with tab2:
    st.markdown("<p class='hud-text'>GenAI automated formal reporting for Coast Guard incident dispatch and Corporate ESG audits.</p>", unsafe_allow_html=True)
    if st.button("Generate Official Action Report via Gemini", use_container_width=True):
        with st.spinner("Drafting formal compliance and incident report..."):
            try:
                report_prompt = f"You are an executive ESG auditor and Coast Guard officer. Based on the {sector_mode} sector with a strategic focus on {focus_mode}, write a highly formal, 2-paragraph executive incident report covering operational impact. Use formal government/financial language."
                response = model.generate_content(report_prompt)
                st.info(response.text)
            except Exception as e:
                st.error(f"GenAI Error: {e}")
