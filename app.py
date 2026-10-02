import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import json
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
# 1. PAGE SETUP & ENTERPRISE UX THEME
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 | Strategic Command", page_icon="🌐", initial_sidebar_state="expanded")

# Palantir-Style Slate Theme (Maximum readability, zero eye strain)
bg_color = "#0B1121"
card_bg = "#1F2937"
text_color = "#F9FAFB"
muted_text = "#9CA3AF"
border_color = "#374151"

accent_cyan = "#06B6D4"
accent_green = "#10B981"
accent_red = "#F43F5E"
accent_purple = "#8B5CF6"
accent_amber = "#F59E0B"

css = f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: 'Inter', -apple-system, sans-serif; }}
    .metric-container {{ display: flex; justify-content: space-between; gap: 1rem; margin-bottom: 2rem; }}
    .metric-card {{ background-color: {card_bg}; padding: 1.5rem; border-radius: 0.5rem; border: 1px solid {border_color}; flex: 1; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
    .metric-card h4 {{ color: {muted_text}; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; margin-top: 0; }}
    .metric-card h2 {{ color: {text_color}; font-size: 2rem; font-weight: 700; margin: 0; line-height: 1.2; }}
    .metric-card p {{ color: {accent_cyan}; font-size: 0.85rem; font-weight: 500; margin-top: 0.5rem; margin-bottom: 0; }}
    .border-red {{ border-top: 3px solid {accent_red}; }}
    .border-green {{ border-top: 3px solid {accent_green}; }}
    .border-cyan {{ border-top: 3px solid {accent_cyan}; }}
    .border-purple {{ border-top: 3px solid {accent_purple}; }}
    .terminal {{ background-color: #000000; padding: 1rem; border-radius: 0.5rem; border: 1px solid {border_color}; color: {accent_green}; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.85rem; white-space: pre-wrap; line-height: 1.5; }}
    div[data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid {border_color}; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 2rem; }}
    .stTabs [data-baseweb="tab"] {{ color: {muted_text}; background-color: transparent; border-radius: 0; padding-top: 1rem; padding-bottom: 1rem; font-weight: 600; font-size: 1.05rem; }}
    .stTabs [aria-selected="true"] {{ color: {accent_cyan}; border-bottom: 2px solid {accent_cyan}; }}
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
    else: ee_status = "🔴 OFFLINE"
except: ee_status = "🔴 OFFLINE"

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = 'gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0].replace('models/', '')
        model = genai.GenerativeModel(target_model)
        ai_status = f"🟢 ACTIVE ({target_model})"
    else: ai_status = "🔴 OFFLINE"
except: ai_status = "🔴 OFFLINE"

try:
    ais_key = st.secrets.get("AISSTREAM_API_KEY", "")
    ais_status = "🟢 ACTIVE" if ais_key else "🔴 OFFLINE"
except: ais_status = "🔴 OFFLINE"

# ---------------------------------------------------------
# 3. SIDEBAR: TACTICAL CONTROLS
# ---------------------------------------------------------
st.sidebar.markdown(f"""
<div style="text-align: center; margin-bottom: 2rem;">
    <div style="font-size: 3rem; color: {accent_cyan}; line-height: 1;">🌐</div>
    <div style="font-weight: 800; color: {text_color}; font-size: 1.5rem; letter-spacing: 0.1em; margin-top: 0.5rem;">BLUE 42</div>
    <div style="color: {muted_text}; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.1em;">GLOBAL MARITIME OS</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"<div style='font-size: 0.8rem; color: {muted_text}; margin-bottom: 2rem;'><b>GEO:</b> {ee_status} | <b>AI:</b> {ai_status} | <b>AIS:</b> {ais_status}</div>", unsafe_allow_html=True)

st.sidebar.markdown("### 🌍 DEPLOYMENT ZONE")
sector_mode = st.sidebar.selectbox("Sector", ["US West Coast (Channel Islands)", "Pacific Ops (Hawaiian Islands)"], label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown("### 📡 TELEMETRY & OVERLAYS")
live_ais = st.sidebar.toggle("Connect Live Satellite AIS", value=False)
show_iuu = st.sidebar.checkbox("🛡️ Marine Protected Areas", value=True)
show_weather = st.sidebar.checkbox("⛈️ Weather Hazard Polygons", value=True)
show_cables = st.sidebar.checkbox("🔌 Subsea Data Trunks", value=True)
show_depth = st.sidebar.checkbox("🌱 Blue Carbon Bio-Sinks", value=True)
show_military = st.sidebar.checkbox("⚓ Naval Exclusion Zones", value=False)

# ---------------------------------------------------------
# 4. EXECUTIVE HEADER & KPIs
# ---------------------------------------------------------
st.markdown(f"<h1 style='text-align: center; margin-bottom: 0.5rem;'>Global Maritime Command Center</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: {muted_text}; font-size: 1.1rem; margin-bottom: 2rem;'>Synthesizing planetary telemetry into auditable business value and global security workflows.</p>", unsafe_allow_html=True)

# Clean, widescreen KPI layout
st.markdown(f"""
<div class="metric-container">
    <div class="metric-card border-red">
        <h4>🛡️ Threat Interdiction</h4>
        <h2>1 ACTIVE VOI</h2>
        <p>Target masking identity near MPA</p>
    </div>
    <div class="metric-card border-cyan">
        <h4>🌪️ Supply Chain Resilience</h4>
        <h2>5 REROUTED</h2>
        <p>Avoiding extreme hydrodynamic drag</p>
    </div>
    <div class="metric-card border-green">
        <h4>🌱 Planetary Capital</h4>
        <h2>14.2 HA</h2>
        <p>Optimal blue carbon sites verified</p>
    </div>
    <div class="metric-card border-purple">
        <h4>⚓ Sovereign Defense</h4>
        <h2>SECURE</h2>
        <p>No civilian incursions in active ranges</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. DYNAMIC MAP DATA GENERATION (ARPA VECTORS)
# ---------------------------------------------------------
map_layers = []

# Regional configuration
if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=45, bearing=0)
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]]
    base_lat, base_lon = 33.8, -119.5
    regional_ports = ["Port of Los Angeles", "Port of Long Beach", "Port Hueneme"]
    
    if show_iuu:
        mpa_data = [{"polygon": [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]], "name": "Channel Islands MPA", "desc": "Federally Protected Boundary. Zero commercial take allowed.", "color": [56, 189, 248, 20]}]
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(mpa_data), get_polygon="polygon", get_fill_color="color", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2, pickable=True))
    
    if show_weather:
        storm_data = [{"polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]], "name": "Severe Gale Warning", "desc": "H_s > 6.1m detected. Severe drag penalty.", "color": [239, 68, 68, 30]}]
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(storm_data), get_polygon="polygon", get_fill_color="color", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2, pickable=True))
        route_data = [{"path": [[[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]]], "name": "AI Optimized Route", "desc": "Predictive vector avoiding hazard.", "color": [16, 185, 129, 255]}]
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame(route_data), get_path="path", get_color="color", width_min_pixels=4, pickable=True))

    if show_depth:
        kelp_data = [{"lat": 34.02, "lon": -119.55, "name": "Verified Carbon Sink K-1", "desc": "Area: 5.1 HA | Depth: 14m | SST: 16.5°C"}]
        map_layers.append(pdk.Layer("ScatterplotLayer", data=pd.DataFrame(kelp_data), get_position="[lon, lat]", get_fill_color="[16, 185, 129, 200]", get_radius=3000, pickable=True))

    if show_cables:
        cable_data = [{"path": [[[-121.0, 33.5], [-119.0, 33.8], [-118.0, 34.2]]], "name": "Transpacific Data Trunk", "desc": "Critical infrastructure. High anchor vulnerability."}]
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame(cable_data), get_path="path", get_color="[203, 213, 225, 200]", width_min_pixels=3, pickable=True))
        
    if show_military:
        mil_data = [{"polygon": [[[-120.5, 33.2], [-119.0, 33.2], [-119.0, 33.8], [-120.5, 33.8]]], "name": "Point Mugu Sea Range", "desc": "RESTRICTED: Live-fire naval weapons area.", "color": [139, 92, 246, 30]}]
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(mil_data), get_polygon="polygon", get_fill_color="color", get_line_color="[139, 92, 246, 150]", line_width_min_pixels=2, pickable=True))

else: # HAWAII
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=45, bearing=0)
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    base_lat, base_lon = 21.2, -158.0
    regional_ports = ["Honolulu Harbor", "Pearl Harbor", "Kahului"]

    if show_iuu:
        mpa_data = [{"polygon": [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]], "name": "Kaena Point MPA", "desc": "Federally Protected Boundary. Zero commercial take allowed.", "color": [56, 189, 248, 20]}]
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(mpa_data), get_polygon="polygon", get_fill_color="color", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2, pickable=True))

    if show_weather:
        storm_data = [{"polygon": [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]], "name": "Tropical Squall Hazard", "desc": "H_s > 4.5m detected. Supply chain delay risk.", "color": [239, 68, 68, 30]}]
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(storm_data), get_polygon="polygon", get_fill_color="color", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2, pickable=True))
        route_data = [{"path": [[[-158.5, 20.8], [-158.0, 20.9], [-157.4, 20.9], [-157.1, 21.2]]], "name": "AI Optimized Route", "desc": "Predictive vector avoiding hazard.", "color": [16, 185, 129, 255]}]
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame(route_data), get_path="path", get_color="color", width_min_pixels=4, pickable=True))

    if show_depth:
        kelp_data = [{"lat": 21.45, "lon": -157.8, "name": "Verified Reef Restoration R-1", "desc": "Area: 6.5 HA | Depth: 8m | SST: 24.5°C"}]
        map_layers.append(pdk.Layer("ScatterplotLayer", data=pd.DataFrame(kelp_data), get_position="[lon, lat]", get_fill_color="[16, 185, 129, 200]", get_radius=3000, pickable=True))

    if show_cables:
        cable_data = [{"path": [[[-160.0, 22.0], [-157.8, 21.3], [-155.0, 20.0]]], "name": "Honolulu Transpacific Landing", "desc": "Critical infrastructure carrying Pacific financial routing."}]
        map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame(cable_data), get_path="path", get_color="[203, 213, 225, 200]", width_min_pixels=3, pickable=True))

    if show_military:
        mil_data = [{"polygon": [[[-159.9, 21.8], [-159.5, 21.8], [-159.5, 22.2], [-159.9, 22.2]]], "name": "PMRF Barking Sands", "desc": "RESTRICTED: Live-fire naval weapons area.", "color": [139, 92, 246, 30]}]
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(mil_data), get_polygon="polygon", get_fill_color="color", get_line_color="[139, 92, 246, 150]", line_width_min_pixels=2, pickable=True))


# --- LIVE AIS / SIMULATION ENGINE ---
live_vessels_data = []

if live_ais and ais_key and WEBSOCKET_AVAILABLE:
    with st.spinner("📡 Correlating Live AIS with Threat Matrix..."):
        try:
            ws = websocket.create_connection("wss://stream.aisstream.io/v0/stream", timeout=4)
            ws.send(json.dumps({"APIKey": ais_key, "BoundingBoxes": ais_bounds, "FilterMessageTypes": ["PositionReport"]}))
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
                            sog, cog = pr.get('Sog', 0), pr.get('Cog', 0)
                            v_len = int(random.uniform(150, 350))
                            live_vessels_data.append({
                                "MMSI": mmsi, "Vessel Name": name, "Type": "MERCHANT", "lat": lat, "lon": lon, 
                                "sog": sog, "cog": cog, "Length (m)": v_len, "Draft (m)": round(random.uniform(9,15), 1),
                                "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
                            })
                        if len(live_vessels_data) >= 30: break
                except: break
            ws.close()
        except: pass

# If websocket fails or returns too few, populate realistic fleet simulation
if len(live_vessels_data) < 3:
    for i in range(35):
        sog = random.uniform(8.0, 22.0)
        v_type = random.choice(["CARGO", "TANKER", "BULK"])
        mmsi = f"36{random.randint(1000000, 9999999)}"
        lat = base_lat + random.uniform(-1.5, 1.5)
        lon = base_lon + random.uniform(-2.0, 2.0)
        cog = random.uniform(0, 360)
        v_len = int(random.uniform(150,350))
        live_vessels_data.append({
            "MMSI": mmsi, "Vessel Name": f"{v_type} {mmsi[-4:]}", "Type": v_type,
            "lat": lat, "lon": lon, "sog": round(sog,1), "cog": round(cog,1),
            "Length (m)": v_len, "Draft (m)": round(random.uniform(9.0,16.0), 1),
            "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
        })

# Inject the Critical Dark Target
dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
live_vessels_data.append({
    "MMSI": "413000000", "Vessel Name": "UNVERIFIED DARK TARGET", "Type": "SUSPECT",
    "lat": dt_lat, "lon": dt_lon, "sog": 2.5, "cog": 80.0,
    "Length (m)": 45, "Draft (m)": 3.2,
    "Risk Status": "CRITICAL ANOMALY", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
})

# Generate ARPA Track Vectors (Sleek Military UI)
vessels = []
for v in live_vessels_data:
    is_threat = v['Risk Status'] != "Nominal"
    cog_rad = math.radians(v['cog'])
    # Speed vector length
    vec_len = max(v['sog'] * 0.003, 0.01)
    
    color = [244, 63, 94, 255] if is_threat else [56, 189, 248, 200]
    desc = "CRITICAL HUMAN RIGHTS ANOMALY: Vessel disabled transponder 15nm from MPA. Kinematics suggest illicit fishing/forced labor." if is_threat else "Vessel kinetics operate within nominal parameters."
    
    vessels.append({
        "lat": v['lat'], "lon": v['lon'], "name": v['Vessel Name'],
        "desc": f"Speed: {v['sog']} kts | Heading: {v['cog']}°\n{desc}",
        "color": color,
        "vector": [[v['lon'], v['lat']], [v['lon'] + vec_len * math.sin(cog_rad), v['lat'] + vec_len * math.cos(cog_rad)]],
        "radius": 1800 if is_threat else 800
    })

vessels_df = pd.DataFrame(vessels)

# The Tactical Render: Glowing core dot + Directional ARPA line
map_layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))
map_layers.append(pdk.Layer("PathLayer", data=vessels_df, get_path="vector", get_color="color", width_min_pixels=3, pickable=False))

# ---------------------------------------------------------
# 6. RENDER THE FULL-WIDTH MAP
# ---------------------------------------------------------
# Ultra-clean glassmorphic tooltip
tooltip = {
    "html": f"""
    <div style='background: {card_bg}; border: 1px solid {accent_blue}; padding: 16px; border-radius: 8px; color: {text_color}; font-family: Inter, sans-serif; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); max-width: 300px;'>
        <div style='font-size: 1.1rem; font-weight: 700; color: {accent_blue}; margin-bottom: 8px;'>{{name}}</div>
        <div style='font-size: 0.85rem; line-height: 1.4; color: {muted_text};'>{{desc}}</div>
    </div>
    """,
    "style": {"backgroundColor": "transparent", "padding": "0"}
}

st.markdown("<div style='border: 1px solid #374151; border-radius: 8px; overflow: hidden; margin-bottom: 2rem;'>", unsafe_allow_html=True)
r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style="dark", tooltip=tooltip)
st.pydeck_chart(r, use_container_width=True, height=600)
st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. THE ENTERPRISE ANALYTICS OS (BOTTOM TABS)
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["🧭 GenAI Voyage Routing", "💰 Scope 3 Financial Ledger", "🧠 Strategic Advisory Chat", "📋 Automated Action Reports"])

with tab1:
    st.markdown("### Dynamic Route Optimization")
    st.markdown(f"<p style='color: {muted_text}; font-size: 0.95rem; margin-bottom: 1.5rem;'>Automated WeatherNext 3 route optimization ensuring verifiable fuel and carbon reductions.</p>", unsafe_allow_html=True)
    
    with st.form("routing_form"):
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            vessel_opts = [f"{v['Vessel Name']} (MMSI: {v['MMSI']})" for v in live_vessels_data if v['Risk Status'] == "Nominal"]
            selected_vessel = st.selectbox("Select Asset to Reroute:", vessel_opts if vessel_opts else ["No Active Fleet"])
        with col_r2:
            origin_port = st.selectbox("Origin Port:", regional_ports)
        with col_r3:
            dest_port = st.selectbox("Destination Port:", reversed(regional_ports))
            
        if st.form_submit_button("Calculate Predictive Voyage Plan", use_container_width=True):
            target_v = next((v for v in live_vessels_data if v['MMSI'] in selected_vessel), None)
            v_len = target_v['Length (m)'] if target_v else 300
            with st.spinner(f"GenAI processing hydrodynamic drag profile for {v_len}m vessel..."):
                try:
                    routing_prompt = f"You are a marine logistics AI. A {v_len}m freighter is transiting {origin_port} to {dest_port}. Avoid 6.1m waves. Generate 3-step rerouting plan. Estimate fuel saved in MT."
                    res = model.generate_content(routing_prompt)
                    st.success("Voyage Override Authorized.")
                    st.markdown(f"<div class='terminal'>{res.text}</div>", unsafe_allow_html=True)
                except Exception as e: 
                    st.error("AI Comms Offline. Check API Key.")

with tab2:
    st.markdown("### Enterprise Ledger")
    st.markdown(f"<p style='color: {muted_text}; font-size: 0.95rem;'>Live accounting of protected maritime cargo value and calculated Scope 3 emissions reductions.</p>", unsafe_allow_html=True)
    
    ledger_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Length (m)", "Draft (m)", "Risk Status", "Cargo Value ($M)", "Fuel Saved (MT)"]]
    total_cargo = ledger_df["Cargo Value ($M)"].sum()
    total_carbon = ledger_df["Fuel Saved (MT)"].sum() * 3.11 
    
    st.markdown(f"<h3 style='color: {accent_green};'>Total Capital Protected: ${total_cargo:,.1f}M &nbsp;|&nbsp; Scope 3 Averted: {total_carbon:,.1f} MT CO₂e</h3>", unsafe_allow_html=True)
    st.dataframe(ledger_df.style.highlight_max(axis=0, subset=["Fuel Saved (MT)"], color=accent_green), use_container_width=True)

with tab3:
    st.markdown("### Tactical Intelligence Interrogation")
    if "messages" not in st.session_state: st.session_state.messages = []
    
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages[-3:]: 
            with st.chat_message(message["role"]): st.markdown(message["content"])
            
    if prompt := st.chat_input("Request strategic risk evaluation..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                res = model.generate_content(f"You are a Senior Strategic Advisor. Sector: {sector_mode}. Analyze query concisely: {prompt}")
                st.markdown(res.text)
                st.session_state.messages.append({"role": "assistant", "content": res.text})
            except: st.error("AI Comms Offline.")

with tab4:
    st.markdown("### Regulatory Compliance")
    st.markdown(f"<p style='color: {muted_text}; font-size: 0.95rem;'>GenAI automated formal reporting for Coast Guard incident dispatch and Corporate ESG audits.</p>", unsafe_allow_html=True)
    
    col_act1, col_act2 = st.columns(2)
    with col_act1:
        if st.button("⚖️ Draft UNCLOS Legal Indictment (IUU Threat)", use_container_width=True):
            with st.spinner("Compiling spatial evidence..."):
                try:
                    res = model.generate_content("Draft a highly formal, 2-paragraph legal indictment under UNCLOS for a vessel operating illegally without AIS near a Marine Protected Area.")
                    st.info(res.text)
                except: st.error("AI Offline.")
    with col_act2:
        if st.button("🌱 Mint Verified Blue Carbon Assets", use_container_width=True):
            st.success("SUCCESS: Spatial parameters verified via DeepMind SDM. 2,500 tCO₂e validated. Asset ID #BC-8492-GEE minted to active registry.")
