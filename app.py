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
    css = f"""<style>.stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 6px; border-left: 4px solid {border_color}; margin-bottom: 5px; box-shadow: 0 1px 3px rgba(255,0,0,0.1); font-family: -apple-system, sans-serif;}}
    h4 {{ margin-top: 0px; color: {text_color}; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
    h2 {{ margin-bottom: 0px; color: {text_color}; font-size: 2rem; font-weight: 700; }}
    p {{ margin-bottom: 0px; color: #b30000; font-size: 0.85rem; }}
    .streamlit-expanderHeader {{ color: {text_color} !important; font-size: 0.9rem; }}</style>"""
else:
    bg_color = "#f8fafc"; card_bg = "#ffffff"; text_color = "#0f172a"; accent_blue = "#003366"; accent_red = "#cc0000"; map_style = "light"
    css = f"""<style>.stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 6px; border-left: 4px solid {accent_blue}; margin-bottom: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); font-family: -apple-system, sans-serif;}}
    .protection-card {{ border-left: 4px solid {accent_red}; }}
    h4 {{ margin-top: 0px; color: #64748b; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
    h2 {{ margin-bottom: 0px; color: {accent_blue}; font-size: 2rem; font-weight: 700; }}
    p {{ margin-bottom: 0px; color: #475569; font-size: 0.85rem; }}</style>"""
st.markdown(css, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. SECURE API INITIALIZATION
# ---------------------------------------------------------
try:
    key_dict = json.loads(st.secrets["EARTHENGINE_TOKEN"])
    creds = service_account.Credentials.from_service_account_info(key_dict).with_scopes(['https://www.googleapis.com/auth/earthengine'])
    ee.Initialize(credentials=creds, project=key_dict.get("project_id"))
    ee_status = "🟢 ON-LINE"
except:
    ee_status = f"🔴 OFF-LINE"

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
    ai_status = "🟢 ON-LINE"
except:
    ai_status = "🔴 OFF-LINE"

# ---------------------------------------------------------
# 3. SIDEBAR: MISSION SELECTOR & LIVE AI CHAT
# ---------------------------------------------------------
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Seal_of_the_United_States_Coast_Guard.svg/200px-Seal_of_the_United_States_Coast_Guard.svg.png", width=60)
st.sidebar.title("Sector Command")
st.sidebar.markdown(f"**Telemetry:** {ee_status} | **Gemini AI:** {ai_status}")
st.sidebar.markdown("---")

st.sidebar.subheader("🌍 Global Mission Parameters")
mission_mode = st.sidebar.radio("Select Active Overlay:", 
    ["Ecological Protection (IUU / Kelp)", 
     "Economic Security (Subsea Cables)", 
     "Humanitarian (Search & Rescue)"]
)
st.sidebar.markdown("---")

st.sidebar.markdown("### 🧠 Live Threat Analysis")
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Watchstander AI active. Awaiting tactical queries."}]

for message in st.session_state.messages:
    with st.sidebar.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.sidebar.chat_input("Ask Gemini... (e.g., 'What is the risk to subsea cables?')"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.sidebar.chat_message("user"): st.markdown(prompt)
    with st.sidebar.chat_message("assistant"):
        try:
            tactical_prompt = f"You are a US Coast Guard AI. The current mission is {mission_mode}. Respond tactically: {prompt}"
            response = model.generate_content(tactical_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except:
            st.error("Comms failure with Gemini.")

# ---------------------------------------------------------
# 4. MAIN DASHBOARD HEADER & M.A.P. METRICS
# ---------------------------------------------------------
st.title("⚓ Project Blue 42: Planetary Command")
st.markdown("**Automated Maritime Domain Awareness & Climate Intervention**")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="metric-card protection-card"><h4>🛡️ Protection</h4><h2>Global Defense</h2><p>Monitoring MPAs & Subsea Infrastructure</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="metric-card"><h4>🌪️ Adaptation</h4><h2>Predictive Rescue</h2><p>Rerouting Fleets & Calculating SAR Drift</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-card"><h4>🌱 Mitigation</h4><h2>Carbon Target</h2><p>Optimal Blue Carbon & Heatwave Triage</p></div>', unsafe_allow_html=True)
st.write("") 

# ---------------------------------------------------------
# 5. DYNAMIC DATA LAYERS BASED ON MISSION
# ---------------------------------------------------------
layers = []

# Base Vessels (Always visible)
vessels_df = pd.DataFrame([
    {"lat": 34.12, "lon": -119.85, "name": "CARGO VESSEL", "color": [255, 165, 0, 200]},
    {"lat": 33.95, "lon": -120.15, "name": "DARK TARGET", "color": [204, 0, 0, 255]}
])
layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_color="color", get_radius=3000, pickable=True))

if mission_mode == "Ecological Protection (IUU / Kelp)":
    kelp_df = pd.DataFrame([{"lat": 34.02, "lon": -119.55, "name": "Kelp Restoration Zone"}])
    layers.append(pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_color="[0, 153, 76, 255]", get_radius=4000, pickable=True))
    with st.expander("🚨 ALERT: Dark Vessel near Marine Reserve"):
        st.error("Vessel MMSI 413000000 disabled AIS near Channel Islands. Intercept recommended.")

elif mission_mode == "Economic Security (Subsea Cables)":
    cable_data = pd.DataFrame([{"path": [[-121.0, 33.5], [-119.0, 33.8], [-118.0, 34.2]], "name": "Transpacific Financial Data Trunk"}])
    layers.append(pdk.Layer("PathLayer", data=cable_data, get_path="path", get_color="[0, 255, 255, 255]", width_min_pixels=5, pickable=True))
    with st.expander("🚨 ALERT: Loitering over Subsea Cable"):
        st.error("Dark vessel holding position directly over Transpacific Data Trunk. High risk of anchor sabotage.")

elif mission_mode == "Humanitarian (Search & Rescue)":
    sar_data = pd.DataFrame([{"polygon": [[[-120.5, 33.7], [-119.8, 33.7], [-119.6, 34.2], [-120.3, 34.2]]], "name": "Predictive Drift Zone"}])
    layers.append(pdk.Layer("PolygonLayer", data=sar_data, get_polygon="polygon", get_fill_color="[255, 165, 0, 80]", get_line_color="[255, 165, 0, 255]", line_width_min_pixels=3, pickable=True))
    with st.expander("🚨 ALERT: Distress Signal - Predictive SAR Grid Active"):
        st.warning("Distress signal lost. AlphaEarth wind leeway models have calculated the highest-probability drift sector (Orange Zone).")

# ---------------------------------------------------------
# 6. RENDER THE 3D MAP
# ---------------------------------------------------------
view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=45)
r = pdk.Deck(layers=layers, initial_view_state=view_state, map_style=map_style, tooltip={"html": "<b>{name}</b>"})
st.pydeck_chart(r, use_container_width=True)

