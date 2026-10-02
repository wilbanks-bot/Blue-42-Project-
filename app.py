import streamlit as st
import pydeck as pdk
import pandas as pd
import json
import ee
from google.oauth2 import service_account
import google.generativeai as genai

# ---------------------------------------------------------
# 1. PAGE SETUP & COAST GUARD AESTHETICS
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 Command", page_icon="⚓", initial_sidebar_state="expanded")

# USCG Theme (Navy Blue, Racing Stripe Red, Crisp White)
st.markdown("""
    <style>
    .metric-card { background-color: #002868; padding: 20px; border-radius: 4px; border-left: 6px solid #BF0A30; box-shadow: 0 4px 6px rgba(0,0,0,0.5); font-family: 'Helvetica Neue', sans-serif;}
    .protection-card { border-left: 6px solid #FFD700; } /* Coast Guard Gold for alerts */
    h4 { margin-top: 0px; color: #FFFFFF; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 1.5px; }
    h2 { margin-bottom: 0px; color: #FFFFFF; font-size: 2.2rem; font-weight: bold; }
    p { margin-bottom: 0px; color: #E0E0E0; font-size: 0.9rem; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. SECURE API INITIALIZATION
# ---------------------------------------------------------
# Earth Engine
try:
    key_dict = json.loads(st.secrets["EARTHENGINE_TOKEN"])
    creds = service_account.Credentials.from_service_account_info(key_dict).with_scopes(['https://www.googleapis.com/auth/earthengine'])
    ee.Initialize(credentials=creds, project=key_dict.get("project_id"))
    ee_status = "🟢 ON-LINE"
except Exception as e:
    ee_status = f"🔴 OFF-LINE"

# Gemini AI
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
    ai_status = "🟢 ON-LINE"
except Exception as e:
    ai_status = "🔴 OFF-LINE"

# ---------------------------------------------------------
# 3. SIDEBAR: TACTICAL WATCHSTANDER & LIVE AI CHAT
# ---------------------------------------------------------
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Seal_of_the_United_States_Coast_Guard.svg/200px-Seal_of_the_United_States_Coast_Guard.svg.png", width=80)
st.sidebar.title("Sector Command")
st.sidebar.markdown(f"**Satellite Telemetry:** {ee_status}  \n**Gemini Neural Net:** {ai_status}")
st.sidebar.markdown("---")

with st.sidebar.expander("🚨 CRITICAL: Dark Vessel Detected", expanded=False):
    st.error("**Target:** MMSI 413000000")
    st.write("**Location:** 34.012° N, 120.341° W")
    st.write("**Status:** AIS transponder disabled for 74 mins.")
    if st.sidebar.button("AUTHORIZE INTERCEPT"):
        st.sidebar.success("Vector transmitted to USCG Cutter.")

st.sidebar.markdown("### 🧠 Live Threat Analysis")

# Initialize chat history in memory
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Watchstander AI active. Awaiting operational queries."}
    ]

# Display chat messages from history
for message in st.session_state.messages:
    with st.sidebar.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.sidebar.chat_input("Ask Gemini for tactical analysis..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.sidebar.chat_message("user"):
        st.markdown(prompt)
    # Display AI response
    with st.sidebar.chat_message("assistant"):
        try:
            # We add a tactical prompt wrapper so Gemini answers like a military analyst
            tactical_prompt = f"You are a US Coast Guard AI Watchstander. Keep your answer brief, tactical, and highly professional. The user asks: {prompt}"
            response = model.generate_content(tactical_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error("Comms failure with Gemini.")

# ---------------------------------------------------------
# 4. MAIN DASHBOARD HEADER & M.A.P. METRICS
# ---------------------------------------------------------
st.title("⚓ Project Blue 42: Planetary Command")
st.markdown("**Automated Maritime Domain Awareness & Climate Intervention**")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="metric-card protection-card"><h4>🛡️ Protection</h4><h2>1 Active Threat</h2><p>10M Hectares Under AI Surveillance</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="metric-card"><h4>🌪️ Adaptation</h4><h2>5 Ships Rerouted</h2><p>54 MT Fuel Saved (Weather Avoidance)</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-card"><h4>🌱 Mitigation</h4><h2>14 Hectares</h2><p>Optimal Blue Carbon Zones Verified</p></div>', unsafe_allow_html=True)

st.write("") # Spacer

# ---------------------------------------------------------
# 5. DATA LAYERS (Boats, Kelp, Storms, Routes)
# ---------------------------------------------------------
vessels_df = pd.DataFrame([
    {"lat": 34.12, "lon": -119.85, "mmsi": "368123450", "sog": 12.4, "name": "PACIFIC TITAN (Cargo)", "color": [255, 204, 0, 200]},
    {"lat": 33.95, "lon": -120.15, "mmsi": "413000000", "sog": 9.1, "name": "DARK TARGET (Suspect)", "color": [255, 50, 50, 255]},
    {"lat": 33.80, "lon": -119.60, "mmsi": "219000000", "sog": 15.2, "name": "MAERSK SEALAND", "color": [255, 204, 0, 200]}
])

kelp_df = pd.DataFrame([
    {"lat": 34.02, "lon": -119.55, "site": "Sector K-1 (High Viability)", "depth": "14m"},
    {"lat": 33.88, "lon": -119.72, "site": "Sector K-2 (Medium Viability)", "depth": "22m"},
    {"lat": 34.05, "lon": -120.00, "site": "Sector K-3 (High Viability)", "depth": "11m"}
])

storm_data = pd.DataFrame([{
    "polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]],
    "name": "Severe Gale Warning (H_s > 6.1m)"
}])

route_data = pd.DataFrame([{
    "path": [[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]],
    "name": "AI Optimized Safe Route"
}])

# ---------------------------------------------------------
# 6. RENDER THE 3D MAP
# ---------------------------------------------------------
vessel_layer = pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_color="color", get_radius=3000, pickable=True)
kelp_layer = pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_color="[0, 255, 128, 255]", get_radius=2000, pickable=True)
storm_layer = pdk.Layer("PolygonLayer", data=storm_data, get_polygon="polygon", get_fill_color="[191, 10, 48, 60]", get_line_color="[191, 10, 48, 200]", line_width_min_pixels=2, pickable=True)
route_layer = pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[0, 255, 0, 255]", width_min_pixels=4, pickable=True)

view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=45)

r = pdk.Deck(
    layers=[storm_layer, route_layer, kelp_layer, vessel_layer], 
    initial_view_state=view_state, 
    map_style="dark",
    tooltip={"html": "<b>{name}</b><br/>{site}<br/>Speed: {sog} kts<br/>Depth: {depth}"}
)

st.pydeck_chart(r, use_container_width=True)
