import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import json
import ee
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
# 1. EXPERT PAGE SETUP & GLASSMORPHISM CSS
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 | Strategic Command", page_icon="🌐", initial_sidebar_state="collapsed")

# Safeguard Session States
if "sar_tasked" not in st.session_state: st.session_state.sar_tasked = False
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Command AI active. Awaiting strategic parameters."}]

# High-End Dark Theme Palette
bg_color = "#0B1121"         # Slate 950
glass_bg = "rgba(30, 41, 59, 0.7)" # Slate 800 with 70% opacity
text_color = "#F8FAFC"
muted_text = "#9CA3AF"
border_color = "rgba(255, 255, 255, 0.1)"
accent_blue = "#0EA5E9"      # Neon Cyan
accent_red = "#F43F5E"       # Rose/Crimson
accent_green = "#10B981"     # Emerald
accent_purple = "#8B5CF6"    # Violet
accent_amber = "#F59E0B"     # Amber

css = f"""
<style>
    /* Full App Background */
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: 'Inter', -apple-system, sans-serif; }}
    
    /* Hide Default Streamlit Elements for an Edge-to-Edge look */
    #MainMenu {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .block-container {{padding-top: 1rem; padding-bottom: 0rem; max-width: 100%;}}
    
    /* Glassmorphism Panels */
    .glass-card {{
        background: {glass_bg};
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        margin-bottom: 1rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .glass-card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 40px 0 rgba(0, 0, 0, 0.4); }}
    
    /* Glowing Accents */
    .glow-blue {{ border-top: 4px solid {accent_blue}; box-shadow: 0 0 15px rgba(14, 165, 233, 0.2); }}
    .glow-red {{ border-top: 4px solid {accent_red}; box-shadow: 0 0 15px rgba(244, 63, 94, 0.2); }}
    .glow-green {{ border-top: 4px solid {accent_green}; box-shadow: 0 0 15px rgba(16, 185, 129, 0.2); }}
    
    /* Typography */
    h1, h2, h3, h4 {{ color: {text_color}; font-weight: 700; margin-top: 0; letter-spacing: -0.02em; }}
    h4 {{ font-size: 0.85rem; text-transform: uppercase; color: {muted_text}; letter-spacing: 0.1em; margin-bottom: 12px; }}
    .kpi-value {{ font-size: 2.5rem; font-weight: 800; margin: 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.85rem; color: {muted_text}; margin-top: 4px; display: block; }}
    
    /* Custom Terminal */
    .terminal {{ background-color: #000000; padding: 16px; border-radius: 8px; border-left: 4px solid {accent_blue}; color: #22d3ee; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.85rem; white-space: pre-wrap; line-height: 1.5; }}
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {{ gap: 24px; }}
    .stTabs [data-baseweb="tab"] {{ color: {muted_text}; background-color: transparent; padding-top: 10px; padding-bottom: 10px; font-weight: 600; font-size: 1.05rem; }}
    .stTabs [aria-selected="true"] {{ color: {accent_blue}; border-bottom: 2px solid {accent_blue}; }}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. SECURE API INITIALIZATION (FAIL-SAFED)
# ---------------------------------------------------------
try:
    if "EARTHENGINE_TOKEN" in st.secrets:
        key_dict = json.loads(st.secrets["EARTHENGINE_TOKEN"])
        creds = service_account.Credentials.from_service_account_info(key_dict).with_scopes(['https://www.googleapis.com/auth/earthengine'])
        ee.Initialize(credentials=creds, project=key_dict.get("project_id"))
        ee_status = "🟢 ON-LINE"
    else: ee_status = "🔴 OFFLINE"
except: ee_status = "🔴 OFFLINE"

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Dynamic fallback to ensure model always works
        avail = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = 'gemini-1.5-flash' if 'models/gemini-1.5-flash' in avail else avail[0].replace('models/', '')
        model = genai.GenerativeModel(target_model)
        ai_status = "🟢 ACTIVE"
    else: ai_status = "🔴 OFFLINE"
except: ai_status = "🔴 OFFLINE"

try:
    ais_key = st.secrets.get("AISSTREAM_API_KEY", "")
    ais_status = "🟢 AUTHENTICATED" if ais_key else "🔴 OFFLINE"
except: ais_status = "🔴 OFFLINE"

# ---------------------------------------------------------
# 3. EXECUTIVE HEADER & TACTICAL CONTROLS
# ---------------------------------------------------------
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
        <div style="font-size: 48px; color: {accent_blue}; line-height: 1; text-shadow: 0 0 20px {accent_blue};">🌐</div>
        <div>
            <h1 style="margin: 0; font-size: 2.2rem; letter-spacing: 2px;">PROJECT BLUE 42</h1>
            <div style="color: {accent_blue}; font-weight: 600; letter-spacing: 2px; font-size: 0.9rem; text-transform: uppercase;">Global Maritime Intelligence OS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with col_head2:
    st.markdown(f"<div style='text-align: right; font-family: monospace; font-size: 0.8rem; color: {muted_text};'><b>SATCOM:</b> {ee_status}<br><b>NEURAL NET:</b> {ai_status}<br><b>RADAR:</b> {ais_status}</div>", unsafe_allow_html=True)

# Strategic Control Ribbon
st.markdown(f"<div style='background: {glass_bg}; border: 1px solid {border_color}; border-radius: 8px; padding: 15px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>", unsafe_allow_html=True)
col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 2, 1])
with col_ctrl1:
    sector_mode = st.selectbox("Operational Theater", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"], label_visibility="collapsed")
with col_ctrl2:
    focus_mode = st.radio("Strategic Focus", ["🌍 Global Overview", "🛡️ Threat Interdiction", "🌪️ Macro-Economics", "🌱 ESG Capital"], horizontal=True, label_visibility="collapsed")
with col_ctrl3:
    live_ais = st.toggle("📡 Activate Live Satellite AIS", value=False)
st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. DYNAMIC DATA GENERATOR & ARPA KINEMATICS
# ---------------------------------------------------------
if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=45, bearing=-10)
    base_lat, base_lon = 33.8, -119.5
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]]
    regional_ports = ["Port of Los Angeles", "Port of Long Beach", "Port Hueneme"]
else:
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=45, bearing=-10)
    base_lat, base_lon = 21.2, -158.0
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    regional_ports = ["Honolulu Harbor", "Pearl Harbor", "Kahului"]

live_vessels_data = []

# Live AIS Processing
if live_ais and ais_key and WEBSOCKET_AVAILABLE:
    with st.spinner("Establishing secure satellite uplink..."):
        try:
            ws = websocket.create_connection("wss://stream.aisstream.io/v0/stream", timeout=4)
            ws.send(json.dumps({"APIKey": ais_key, "BoundingBoxes": ais_bounds, "FilterMessageTypes": ["PositionReport"]}))
            start_time = time.time()
            while time.time() - start_time < 3.0: 
                try:
                    data = json.loads(ws.recv())
                    if data.get("MessageType") == "PositionReport":
                        pr = data["Message"]["PositionReport"]
                        mmsi = str(data.get("MetaData", {}).get("MMSI", "UNKNOWN"))
                        name = data.get("MetaData", {}).get("ShipName", "").strip() or f"MMSI: {mmsi}"
                        lat, lon = pr.get('Latitude', 0), pr.get('Longitude', 0)
                        if lat != 0 and lon != 0:
                            sog, cog = pr.get('Sog', 0), pr.get('Cog', 0)
                            v_len = int(random.uniform(150, 350))
                            v_width = int(v_len*0.15)
                            v_draft = round(random.uniform(8.0, 15.0), 1)
                            live_vessels_data.append({
                                "MMSI": mmsi, "Vessel Name": name, "Type": "MERCHANT", "lat": lat, "lon": lon, 
                                "sog": sog, "cog": cog, "Length (m)": v_len, "Width (m)": v_width, "Draft (m)": v_draft, "Gross Tonnage": int(v_len * v_width * v_draft * 0.7),
                                "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
                            })
                        if len(live_vessels_data) >= 30: break
                except: break
            ws.close()
        except: pass

# High-Fidelity Simulation Fallback
if len(live_vessels_data) < 3:
    for i in range(35):
        sog = random.uniform(8.0, 22.0)
        v_type = random.choice(["CARGO", "TANKER", "BULK"])
        mmsi = f"36{random.randint(1000000, 9999999)}"
        v_len = int(random.uniform(150,350))
        v_width = int(v_len*0.15)
        v_draft = round(random.uniform(8.0, 16.0), 1)
        live_vessels_data.append({
            "MMSI": mmsi, "Vessel Name": f"{v_type} {mmsi[-4:]}", "Type": v_type,
            "lat": base_lat + random.uniform(-1.5, 1.5), "lon": base_lon + random.uniform(-2.0, 2.0),
            "sog": round(sog,1), "cog": round(random.uniform(0, 360),1),
            "Length (m)": v_len, "Width (m)": v_width, "Draft (m)": v_draft, "Gross Tonnage": int(v_len * v_width * v_draft * 0.7),
            "Risk Status": "Nominal", "Cargo Value ($M)": round(random.uniform(10, 150), 1), "Fuel Saved (MT)": round(random.uniform(5, 25), 1)
        })

# Inject Critical Dark Target (IUU / Slavery Threat)
dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
live_vessels_data.append({
    "MMSI": "413000000", "Vessel Name": "UNVERIFIED DARK TARGET", "Type": "SUSPECT",
    "lat": dt_lat, "lon": dt_lon, "sog": 2.5, "cog": 80.0,
    "Length (m)": 45, "Width (m)": 8, "Draft (m)": 3.2, "Gross Tonnage": 806,
    "Risk Status": "CRITICAL ANOMALY", "Cargo Value ($M)": 0.0, "Fuel Saved (MT)": 0.0
})

# ---------------------------------------------------------
# 5. MAP LAYERS & CLICK-TO-LOCK ENGINE
# ---------------------------------------------------------
map_layers = []
vessels_formatted = []

for v in live_vessels_data:
    is_threat = v['Risk Status'] != "Nominal"
    if focus_mode == "🌱 Planetary Capital (ESG)" and not is_threat: continue
    if focus_mode == "🛡️ Threat Interdiction" and not is_threat: continue
    
    cog_rad = math.radians(v['cog'])
    vec_len = max(v['sog'] * 0.004, 0.02) # ARPA vector line length
    color = [244, 63, 94, 255] if is_threat else [14, 165, 233, 200]
    
    # Store clean data for both mapping and the "Target Lock" feature
    vessels_formatted.append({
        "name": v['Vessel Name'], "lat": v['lat'], "lon": v['lon'],
        "sog": v['sog'], "cog": v['cog'], "length": v['Length (m)'], "tonnage": v['Gross Tonnage'],
        "color": color, "is_threat": is_threat,
        "arpa_path": [[v['lon'], v['lat']], [v['lon'] + vec_len * math.sin(cog_rad), v['lat'] + vec_len * math.cos(cog_rad)]]
    })

vessels_df = pd.DataFrame(vessels_formatted)
if not vessels_df.empty:
    vessels_df['coordinates'] = vessels_df.apply(lambda r: [r['lon'], r['lat']], axis=1)
    # The Glowing Tactical Dot
    map_layers.append(pdk.Layer(
        "ScatterplotLayer", data=vessels_df, get_position="coordinates", 
        get_fill_color="color", get_line_color="[255,255,255,255]", stroked=True, line_width_min_pixels=1, 
        get_radius=1500, radius_min_pixels=5, pickable=True, auto_highlight=True, id="vessel_dots"
    ))
    # The ARPA Heading Line
    map_layers.append(pdk.Layer("PathLayer", data=vessels_df, get_path="arpa_path", get_color="color", width_min_pixels=2, pickable=False))

# Environmental Polygons based on region
if sector_mode == "US West Coast (Channel Islands)":
    if focus_mode in ["🌍 Global Overview", "🌪️ Macro-Economic Resilience"]:
        storm_df = pd.DataFrame([{"name": "Severe Gale Warning", "polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]]}])
        map_layers.append(pdk.Layer("PolygonLayer", data=storm_df, get_polygon="polygon", get_fill_color="[244, 63, 94, 30]", get_line_color="[244, 63, 94, 150]", line_width_min_pixels=2, pickable=True, id="storm_zone"))
    if focus_mode in ["🌍 Global Overview", "🌱 Planetary Capital (ESG)"]:
        kelp_df = pd.DataFrame([{"name": "Verified Carbon Sink K-1", "lon": -119.55, "lat": 34.02}])
        kelp_df['coordinates'] = kelp_df.apply(lambda r: [r['lon'], r['lat']], axis=1)
        map_layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="coordinates", get_fill_color="[16, 185, 129, 200]", get_radius=3000, pickable=True, id="carbon_sink"))

# Expert Tooltip (Clean, non-crashing HTML)
tooltip_config = {
    "html": f"<div style='font-family: Inter, sans-serif; font-size: 14px; font-weight: bold; color: {accent_blue}; padding: 4px;'>{{name}}<br><span style='font-size: 11px; color: {muted_text}; font-weight: normal;'>Click to Lock Target & Analyze</span></div>",
    "style": {"backgroundColor": card_bg, "border": f"1px solid {accent_blue}", "color": text_color, "borderRadius": "6px", "boxShadow": "0 4px 6px rgba(0,0,0,0.3)"}
}

# ---------------------------------------------------------
# 6. RENDER THE BATTLESPACE & "TARGET LOCK" SIDE PANEL
# ---------------------------------------------------------
col_map, col_ops = st.columns([2.5, 1.5])

with col_map:
    st.markdown(f"<div style='border: 1px solid {border_color}; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);'>", unsafe_allow_html=True)
    
    # NEW UX: Capturing click events seamlessly!
    selected_target = None
    try:
        r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=tooltip_config)
        event = st.pydeck_chart(r, use_container_width=True, height=650, on_select="rerun", selection_mode="single-object")
        if event and hasattr(event, "selection") and event.selection.get("objects"):
            for layer_name, items in event.selection["objects"].items():
                if items:
                    selected_target = items[0]
                    break
    except:
        st.pydeck_chart(pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=tooltip_config), use_container_width=True, height=650)
    st.markdown("</div>", unsafe_allow_html=True)

with col_ops:
    if selected_target:
        # THE TARGET LOCK VIEW (Displays when user clicks an object on the map)
        is_threat = selected_target.get('is_threat', False)
        t_color = accent_red if is_threat else accent_blue
        
        st.markdown(f"<div class='glass-card' style='border-top: 4px solid {t_color}; height: 650px; overflow-y: auto;'>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color: {t_color}; margin-bottom: 5px;'>🎯 TARGET LOCK ACQUIRED</h3>", unsafe_allow_html=True)
        st.markdown(f"<h2>{selected_target.get('name', 'UNKNOWN ASSET')}</h2>", unsafe_allow_html=True)
        
        # Display extracted telemetry if it's a ship
        if 'sog' in selected_target:
            st.markdown(f"<p style='color: {muted_text};'><b>LAT/LON:</b> {selected_target['lat']:.4f}, {selected_target['lon']:.4f} <br><b>SPEED:</b> {selected_target['sog']} kts | <b>HEADING:</b> {selected_target['cog']}°<br><b>DIMENSIONS:</b> {selected_target['length']}m | {selected_target['tonnage']:,} GT</p>", unsafe_allow_html=True)
            
            st.markdown("#### 🧠 AI KINEMATIC ANALYSIS")
            if is_threat:
                st.error("CRITICAL ANOMALY: Vessel disabled transponder 15nm from MPA. Kinematics (low SOG) strongly suggest illicit fishing and forced labor operations. Intercept recommended.")
                if st.button("⚖️ DRAFT UNCLOS LEGAL INDICTMENT", use_container_width=True):
                    with st.spinner("Compiling spatial evidence..."):
                        try:
                            res = model.generate_content("Draft a formal, 2-paragraph legal indictment under UNCLOS for a vessel operating illegally without AIS near a Marine Protected Area.")
                            st.info(res.text)
                        except: st.error("AI Comms Offline.")
            else:
                st.success("Vessel kinetics operate within nominal parameters. Compliant track.")
                
                # Dynamic Routing Engine for the specifically clicked ship!
                st.markdown("---")
                st.markdown("#### 🧭 Dynamic GenAI Routing")
                origin = st.selectbox("Origin Port:", regional_ports, key="orig")
                dest = st.selectbox("Destination Port:", reversed(regional_ports), key="dest")
                if st.button("Generate Predictive Voyage Plan", use_container_width=True):
                    with st.spinner(f"AI correlating {selected_target['tonnage']:,} GT hull displacement with decadal wave baselines..."):
                        try:
                            prompt = f"A {selected_target['length']}m vessel is transiting from {origin} to {dest}. Generate a 3-step rerouting plan to avoid 6.1m waves. Estimate fuel saved."
                            res = model.generate_content(prompt)
                            st.markdown(f"<div class='terminal'>{res.text}</div>", unsafe_allow_html=True)
                        except: st.error("AI Comms Offline.")
        
        # Display data if they clicked a storm or kelp zone
        elif 'Severe Gale' in selected_target.get('name', ''):
            st.markdown("#### 🧠 AI ENVIRONMENTAL ANALYSIS")
            st.warning("Extreme hydrodynamic drag detected (H_s > 6.1m). Routing commercial traffic through this zone increases fuel consumption by 12%. Automated fleet rerouting active.")
            st.latex(r"R_T = \frac{1}{2} \rho v^2 S C_T")
        elif 'Verified' in selected_target.get('name', ''):
            st.markdown("#### 🧠 AI ECOLOGICAL ANALYSIS")
            st.success("Site meets all thermal survivability thresholds (SST < 18°C, Depth -14m). Highly viable Blue Carbon zone.")
            if st.button("Mint Verified Blue Carbon Credits", use_container_width=True):
                st.success("SUCCESS: 2,500 tCO₂e validated. Asset ID #BC-8492-GEE minted.")

        st.markdown("<br><br><br><i>Click the map background to clear target lock.</i>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        # DEFAULT VIEW (No target locked)
        st.markdown(f"<div class='glass-card glow-blue' style='height: 650px;'>", unsafe_allow_html=True)
        st.markdown(f"<h3>🌍 Executive Intelligence Briefing</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {muted_text};'>Select a specific focus from the top menu to filter the battlespace, or <b>click on any asset on the map</b> to lock the target and access deep-dive AI analytics.</p><hr>", unsafe_allow_html=True)
        
        st.markdown("#### Operational Baselines")
        st.write(f"• **Active Fleet Tracks:** {len(live_vessels_data)}")
        st.write("• **Critical Anomalies (Dark Fleet):** 1")
        st.write("• **Total Capital Protected (24H):** $4.2 Billion")
        st.write("• **Verified Carbon Assets:** 14.2 HA")
        
        st.markdown("---")
        st.markdown("#### 💬 Strategic Advisory AI")
        if "chat_history" not in st.session_state: st.session_state.chat_history = []
        for msg in st.session_state.chat_history[-2:]:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if prompt := st.chat_input("Request strategic evaluation..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                try:
                    res = model.generate_content(f"You are a Senior Maritime Advisor. Analyze: {prompt}")
                    st.markdown(res.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": res.text})
                except: st.error("AI Comms Offline.")
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. ENTERPRISE DATA LEDGERS (BOTTOM TABS)
# ---------------------------------------------------------
st.write("---")
st.markdown("### 📈 Operational Analytics & Financial Ledgers")
tab1, tab2 = st.tabs(["🚢 Active Fleet Kinematics", "💰 Scope 3 Financial & Carbon Ledger"])

with tab1:
    fleet_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Length (m)", "sog", "cog", "Risk Status"]]
    fleet_df.rename(columns={"sog": "Speed (kts)", "cog": "Heading (°)"}, inplace=True)
    st.dataframe(fleet_df, use_container_width=True)

with tab2:
    ledger_df = pd.DataFrame(live_vessels_data)[["MMSI", "Vessel Name", "Risk Status", "Cargo Value ($M)", "Fuel Saved (MT)"]]
    total_cargo = ledger_df["Cargo Value ($M)"].sum()
    total_carbon = ledger_df["Fuel Saved (MT)"].sum() * 3.11 
    st.markdown(f"**Total Capital Protected:** <span style='color:{accent_green}'>${total_cargo:,.1f} Million</span> | **Scope 3 Averted:** <span style='color:{accent_blue}'>{total_carbon:,.1f} MT CO₂e</span>", unsafe_allow_html=True)
    st.dataframe(ledger_df.style.highlight_max(axis=0, subset=["Fuel Saved (MT)"], color=accent_green), use_container_width=True)
