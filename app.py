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
# 1. PAGE SETUP & SESSION STATE (MUSE PERSISTENCE)
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 | Maritime Command", page_icon="🌐", initial_sidebar_state="expanded")

# MUSE Feature: Persistent Library and Side Chats Initialization
if "library" not in st.session_state:
    st.session_state.library = []
if "chats" not in st.session_state:
    st.session_state.chats = {"General OPCON": [], "Threat Interdiction": [], "Logistics Routing": []}
if "sentinel_logs" not in st.session_state:
    st.session_state.sentinel_logs = []

# ---------------------------------------------------------
# 2. ENTERPRISE UX THEME (MATTE DARK)
# ---------------------------------------------------------
night_vision = st.sidebar.toggle("🌙 Tactical Night Vision", value=True)

if night_vision:
    bg_color = "#09090b"; card_bg = "#18181b"; text_color = "#f4f4f5"; muted_text = "#a1a1aa"; border_color = "#27272a"
    accent_blue = "#0ea5e9"; accent_red = "#ef4444"; accent_green = "#22c55e"; accent_purple = "#8b5cf6"; accent_amber = "#f59e0b"
    map_style = "dark"; term_bg = "#000000"; term_color = "#10b981"
else:
    bg_color = "#f8fafc"; card_bg = "#ffffff"; text_color = "#0f172a"; muted_text = "#64748b"; border_color = "#e2e8f0"
    accent_blue = "#0284c7"; accent_red = "#e11d48"; accent_green = "#059669"; accent_purple = "#7c3aed"; accent_amber = "#d97706"
    map_style = "satellite"; term_bg = "#f1f5f9"; term_color = "#0f172a"

css = f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: 'Inter', -apple-system, sans-serif; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 6px; border: 1px solid {border_color}; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    .protection-card {{ border-left: 4px solid {accent_red}; }}
    .mitigation-card {{ border-left: 4px solid {accent_green}; }}
    .military-card {{ border-left: 4px solid {accent_purple}; }}
    h1, h2, h3, h4 {{ color: {text_color}; font-weight: 600; margin-top: 0; letter-spacing: -0.02em; }}
    h4 {{ font-size: 0.8rem; text-transform: uppercase; color: {muted_text}; letter-spacing: 0.05em; margin-bottom: 8px; }}
    .kpi-value {{ font-size: 2rem; font-weight: 700; color: {text_color}; margin: 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.85rem; color: {muted_text}; display: block; margin-top: 4px; }}
    div[data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid {border_color}; }}
    .terminal {{ background-color: {term_bg}; padding: 12px; border-radius: 4px; border: 1px solid {border_color}; color: {term_color}; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.8rem; white-space: pre-wrap; line-height: 1.5; }}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. SECURE API INITIALIZATION
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
# 4. SIDEBAR: ALIGNMENT SYNTHESIS & NAVIGATION
# ---------------------------------------------------------
st.sidebar.markdown(f"""
<div style="margin-bottom: 20px; text-align: center;">
    <div style="font-size: 36px; color: {accent_blue}; line-height: 1;">🌐</div>
    <div style="font-weight: 700; color: {text_color}; font-size: 1.25rem; letter-spacing: 1.5px; margin-top: 8px;">BLUE 42 COMMAND</div>
    <div style="color: {muted_text}; font-size: 0.75rem; font-weight: 500; letter-spacing: 1px; text-transform: uppercase; margin-top: 2px;">Agentic Operating System</div>
</div>
""", unsafe_allow_html=True)

# MUSE Feature: Alignment Synthesis (Role-based personalization)
st.sidebar.markdown("### 👤 OPERATOR ALIGNMENT SYNTHESIS")
operator_role = st.sidebar.selectbox("Active Profile:", ["USCG Watch Commander", "ESG Financial Auditor", "Logistics Fleet Director"])
if operator_role == "USCG Watch Commander":
    alignment_prompt = "You are a Coast Guard AI. Prioritize kinetic threats, intercept geometry, and maritime law enforcement."
elif operator_role == "ESG Financial Auditor":
    alignment_prompt = "You are an ESG AI. Prioritize institutional capital risk, carbon registry validation, and compliance metrics."
else:
    alignment_prompt = "You are a Logistics AI. Prioritize hydrodynamic drag, fuel optimization, and supply chain continuity."

st.sidebar.markdown("---")
st.sidebar.markdown("### 🌍 REGIONAL DEPLOYMENT")
sector_mode = st.sidebar.selectbox("Theater:", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"])

st.sidebar.markdown("### 📡 LIVE TELEMETRY")
live_ais = st.sidebar.toggle("Connect Live Satellite AIS Feed", value=False)

st.sidebar.markdown("### 📊 TACTICAL DATA OVERLAYS")
show_iuu = st.sidebar.checkbox("🛡️ Marine Protected Areas", value=True)
show_weather = st.sidebar.checkbox("⛈️ Weather Shield", value=True)
show_depth = st.sidebar.checkbox("🌱 Blue Carbon Bathymetry", value=True)

# ---------------------------------------------------------
# 5. DATA LOGIC & WEBSOCKET INGESTION
# ---------------------------------------------------------
map_layers = []
radio_feeds = []

if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=45, bearing=0)
    ais_bounds = [[[33.0, -121.0], [35.0, -118.0]]]
    base_lat, base_lon = 33.8, -119.5
    if show_iuu:
        radio_feeds.append("[14:02Z VHF-16] 'USCG, this is F/V Horizon. Trawler running dark, hauling nets 3nm off Santa Cruz Is.'\n> SIGINT MATCH: MMSI 413000000.")
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([{"polygon": [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]], "name": "Channel Islands MPA"}]), get_polygon="polygon", get_fill_color="[56, 189, 248, 20]", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2))
    if show_weather:
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([{"polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]], "name": "Gale Warning"}]), get_polygon="polygon", get_fill_color="[239, 68, 68, 30]", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2))
    if show_depth:
        map_layers.append(pdk.Layer("ScatterplotLayer", data=pd.DataFrame([{"lat": 34.02, "lon": -119.55}]), get_position="[lon, lat]", get_fill_color="[34, 197, 94, 200]", get_radius=3000))
else:
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=45, bearing=0)
    ais_bounds = [[[19.0, -161.0], [23.0, -154.0]]]
    base_lat, base_lon = 21.2, -158.0
    if show_iuu:
        radio_feeds.append("[08:15W VHF-16] 'MARITIME COMM, unidentified vessel deploying gear off Kaena Point.'\n> SIGINT MATCH: MMSI 412999000.")
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([{"polygon": [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]]}]), get_polygon="polygon", get_fill_color="[56, 189, 248, 20]", get_line_color="[56, 189, 248, 150]", line_width_min_pixels=2))
    if show_weather:
        map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame([{"polygon": [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]]}]), get_polygon="polygon", get_fill_color="[239, 68, 68, 30]", get_line_color="[239, 68, 68, 150]", line_width_min_pixels=2))
    if show_depth:
        map_layers.append(pdk.Layer("ScatterplotLayer", data=pd.DataFrame([{"lat": 21.45, "lon": -157.8}]), get_position="[lon, lat]", get_fill_color="[34, 197, 94, 200]", get_radius=3000))

# Fetch Ships (Live or Sim)
vessels = []
if live_ais and ais_key and WEBSOCKET_AVAILABLE:
    try:
        ws = websocket.create_connection("wss://stream.aisstream.io/v0/stream", timeout=4)
        ws.send(json.dumps({"APIKey": ais_key, "BoundingBoxes": ais_bounds, "FilterMessageTypes": ["PositionReport"]}))
        start_time = time.time()
        while time.time() - start_time < 3.0: 
            try:
                data = json.loads(ws.recv())
                if data.get("MessageType") == "PositionReport":
                    pr = data["Message"]["PositionReport"]
                    lat, lon = pr.get('Latitude', 0), pr.get('Longitude', 0)
                    if lat != 0: vessels.append({"lat": lat, "lon": lon, "color": [148, 163, 184, 150], "radius": 1000})
            except: break
        ws.close()
    except: pass

if len(vessels) < 3:
    for i in range(25): vessels.append({"lat": base_lat + random.uniform(-1.5, 1.5), "lon": base_lon + random.uniform(-2.0, 2.0), "color": [148, 163, 184, 150], "radius": 1000})

vessels.append({"lat": base_lat + 0.15, "lon": base_lon - 0.65, "color": [239, 68, 68, 255], "radius": 2500}) # Dark Target

map_layers.append(pdk.Layer("ScatterplotLayer", data=pd.DataFrame(vessels), get_position="[lon, lat]", get_fill_color="color", get_radius="radius"))

# ---------------------------------------------------------
# 6. MAIN DASHBOARD: EXECUTIVE HUD & SIGINT
# ---------------------------------------------------------
st.markdown(f"<h2 style='color: {text_color}; margin-bottom: 5px;'>Blue 42: Agentic Operations Center</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='color: {muted_text}; font-size: 1.0rem; margin-bottom: 20px;'>{operator_role} Authentication Confirmed. Alignment parameters active.</p>", unsafe_allow_html=True)

# SIGINT Intercepts (Public Comms)
if radio_feeds:
    st.markdown("#### 📻 OSINT / SIGINT Intercepts")
    st.markdown(f"<div class='terminal'>{chr(10).join(radio_feeds)}</div>", unsafe_allow_html=True)
    st.write("")

# Map & Side Panel Layout
col_map, col_ops = st.columns([2.5, 1.5])

with col_map:
    st.markdown("<div style='border: 1px solid #27272a; border-radius: 6px; overflow: hidden;'>", unsafe_allow_html=True)
    st.pydeck_chart(pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_ops:
    # MUSE Feature: Tabbed Side Chats & Library
    chat_tab, artifact_tab, sentinel_tab = st.tabs(["💬 Side Chats", "📁 Persistent Library", "🛡️ Sentinel Security"])
    
    with chat_tab:
        active_chat = st.selectbox("Active Channel:", ["General OPCON", "Threat Interdiction", "Logistics Routing"], label_visibility="collapsed")
        
        # Display history for specific channel
        for msg in st.session_state.chats[active_chat][-3:]:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
        if prompt := st.chat_input(f"Message {active_chat}..."):
            st.session_state.chats[active_chat].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                try:
                    full_prompt = f"{alignment_prompt} Context: {active_chat}. Sector: {sector_mode}. Query: {prompt}"
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.chats[active_chat].append({"role": "assistant", "content": response.text})
                except Exception as e: st.error("AI Comms Offline.")

    with artifact_tab:
        st.markdown("<p style='font-size:0.85rem; color:#a1a1aa;'>Generated 'Artifacts' (Action Reports, Memos, Ledgers) are persisted here for operational continuity.</p>", unsafe_allow_html=True)
        
        if st.button("Generate & Save New Artifact: Threat Profile", use_container_width=True):
            with st.spinner("Generating..."):
                try:
                    res = model.generate_content(f"{alignment_prompt} Generate a concise 3-bullet threat artifact for a vessel masking AIS in {sector_mode}.")
                    st.session_state.library.append({"type": "Threat Profile", "content": res.text, "time": pd.Timestamp.now().strftime('%H:%M:%SZ')})
                    st.success("Artifact saved to Library.")
                except: st.error("Failed to generate.")
                
        st.markdown("---")
        for idx, item in enumerate(reversed(st.session_state.library)):
            with st.expander(f"📄 {item['time']} | {item['type']}"):
                st.markdown(item['content'])

    with sentinel_tab:
        # MUSE Feature: Sentinel Architecture (Securing Agentic Action)
        st.markdown("<p style='font-size:0.85rem; color:#a1a1aa;'>The Sentinel Layer isolates the AI from executing raw outbound web actions. Human authorization is required to bypass the Sentinel.</p>", unsafe_allow_html=True)
        
        action_req = "AUTHORIZE KINETIC INTERCEPT" if operator_role == "USCG Watch Commander" else "AUTHORIZE CARBON CREDIT MINTING"
        st.markdown(f"**Pending Agent Action:** `{action_req}`")
        st.markdown("**Sentinel Status:** <span style='color:#ef4444;'>BLOCKED (Awaiting Human-In-The-Loop)</span>", unsafe_allow_html=True)
        
        if st.button(f"🔑 BYPASS SENTINEL & EXECUTE", type="primary", use_container_width=True):
            with st.spinner("Sentinel verifying credentials and network egress..."):
                time.sleep(1.5)
                log_entry = f"[{pd.Timestamp.now().strftime('%H:%M:%SZ')}] SENTINEL CLEARED. Action '{action_req}' executed by {operator_role}."
                st.session_state.sentinel_logs.append(log_entry)
                st.success("Action Executed Successfully.")
                
        st.markdown("---")
        st.markdown("**Sentinel Execution Logs:**")
        for log in reversed(st.session_state.sentinel_logs):
            st.markdown(f"<div style='font-family: monospace; font-size: 0.75rem; color: #22c55e;'>{log}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. FINANCIAL LEDGERS (BOTTOM FULL WIDTH)
# ---------------------------------------------------------
st.write("---")
st.markdown("#### 📈 Enterprise Data Ledger")
ledger_col1, ledger_col2 = st.columns(2)
with ledger_col1:
    st.markdown("**Scope 3 Resilience Ledger (Fuel Avoidance)**")
    st.dataframe(pd.DataFrame([{"Asset": "MMSI 368123", "Fuel Saved": "14.5 MT", "CO2e Averted": "45.1 MT"}, {"Asset": "MMSI 369871", "Fuel Saved": "22.0 MT", "CO2e Averted": "68.4 MT"}]), use_container_width=True)
with ledger_col2:
    st.markdown("**ESG Blue Carbon Asset Ledger**")
    st.dataframe(pd.DataFrame([{"Sector": "K-1", "Area": "5.1 HA", "tCO2e/yr": 898, "Verified Value": "$67,350"}, {"Sector": "K-2", "Area": "4.8 HA", "tCO2e/yr": 845, "Verified Value": "$63,375"}]), use_container_width=True)
