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
    term_color = "#ff0000"; term_bg = "#220000"
    css = f"""<style>.stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 6px; border-left: 4px solid {border_color}; margin-bottom: 5px; box-shadow: 0 1px 3px rgba(255,0,0,0.1); font-family: -apple-system, sans-serif;}}
    h4 {{ margin-top: 0px; color: {text_color}; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
    h2 {{ margin-bottom: 0px; color: {text_color}; font-size: 2rem; font-weight: 700; }}
    p {{ margin-bottom: 0px; color: #b30000; font-size: 0.85rem; }}
    .streamlit-expanderHeader {{ color: {text_color} !important; font-size: 0.9rem; font-weight: 600; }}</style>"""
else:
    bg_color = "#f8fafc"; card_bg = "#ffffff"; text_color = "#0f172a"; accent_blue = "#003366"; accent_red = "#cc0000"; map_style = "light"
    term_color = "#00ff00"; term_bg = "#000000"
    css = f"""<style>.stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 6px; border-left: 4px solid {accent_blue}; margin-bottom: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); font-family: -apple-system, sans-serif;}}
    .protection-card {{ border-left: 4px solid {accent_red}; }}
    h4 {{ margin-top: 0px; color: #64748b; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
    h2 {{ margin-bottom: 0px; color: {accent_blue}; font-size: 2rem; font-weight: 700; }}
    p {{ margin-bottom: 0px; color: #475569; font-size: 0.85rem; }}
    .streamlit-expanderHeader {{ color: {accent_blue} !important; font-size: 0.9rem; font-weight: 600; }}</style>"""
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
# 3. SIDEBAR: MISSION SELECTOR & RADIO INTERCEPTS
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

# --- NEW SIGINT TERMINAL ---
st.sidebar.subheader("📻 SIGINT & Radio Traffic")

if mission_mode == "Ecological Protection (IUU / Kelp)":
    radio_feed = "[14:02Z VHF CH 16] 'Coast Guard, this is F/V Horizon. We see a trawler running dark, no AIS, hauling nets 3 miles off Santa Cruz Island. Over.'\n\n>> AI SIGINT MATCH: Acoustic profile correlates with MMSI 413000000 blackout."
elif mission_mode == "Economic Security (Subsea Cables)":
    radio_feed = "[14:15Z NAVTEX SAFETY BROADCAST] 'SECURITE SECURITE. UNIDENTIFIED VESSEL LOITERING IN RESTRICTED CABLE CORRIDOR. MILITARY HYDROPHONE ARRAY DETECTS ANCHOR DEPLOYMENT.'\n\n>> AI SIGINT MATCH: Transpacific Trunk Vulnerability."
else:
    radio_feed = "[14:22Z VHF CH 16 DISTRESS] 'MAYDAY MAYDAY. S/V Orion. Taking on water fast. Engines dead. Lat 33.7, Lon -119.8. Four souls on board... [STATIC]'\n\n>> AI SIGINT MATCH: Auto-generating SAR Drift Grid."

st.sidebar.markdown(f"""
<div style='background-color: {term_bg}; padding: 12px; border-radius: 5px; font-family: "Courier New", Courier, monospace; color: {term_color}; font-size: 0.85rem; border: 1px solid #333; margin-bottom: 15px;'>
{radio_feed}
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. SIDEBAR: LIVE AI CHAT
# ---------------------------------------------------------
st.sidebar.markdown("### 🧠 Live Threat Analysis")
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Watchstander AI active. Awaiting tactical queries."}]

for message in st.session_state.messages:
    with st.sidebar.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.sidebar.chat_input("Ask Gemini..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.sidebar.chat_message("user"): st.markdown(prompt)
    with st.sidebar.chat_message("assistant"):
        try:
            tactical_prompt = f"You are a US Coast Guard AI. The mission is {mission_mode}. The latest radio intercept says: {radio_feed}. Respond tactically and analytically to this query: {prompt}"
            response = model.generate_content(tactical_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except:
            st.error("Comms failure with Gemini.")

# ---------------------------------------------------------
# 5. MAIN DASHBOARD HEADER & M.A.P. METRICS WITH EXPANDERS
# ---------------------------------------------------------
st.title("⚓ Project Blue 42: Planetary Command")
st.markdown("**Automated Maritime Domain Awareness & Climate Intervention**")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div class="metric-card protection-card"><h4>🛡️ Protection</h4><h2>Global Defense</h2><p>Monitoring MPAs & Subsea Infrastructure</p></div>', unsafe_allow_html=True)
    with st.expander("📊 Analytics: Threat Interdiction"):
        st.markdown("**Algorithm:** `Distance_to_MPA < 15nm` AND `SOG > 3kts` AND `Signal_Loss > 60m` = `HIGH THREAT`\n\n**Data Source:** UNEP WDPA & AISStream.")

with col2:
    st.markdown('<div class="metric-card"><h4>🌪️ Adaptation</h4><h2>Predictive Rescue</h2><p>Rerouting Fleets & Calculating SAR Drift</p></div>', unsafe_allow_html=True)
    with st.expander("📊 Analytics: Dynamic Routing"):
        st.markdown("**Algorithm:** Hazard polygons generated where `Wave_Height >= 6.1m` or `Wind >= 22.35m/s`.\n\n**Data Source:** Copernicus Marine & WeatherNext 3.")

with col3:
    st.markdown('<div class="metric-card"><h4>🌱 Mitigation</h4><h2>Carbon Target</h2><p>Optimal Blue Carbon & Heatwave Triage</p></div>', unsafe_allow_html=True)
    with st.expander("📊 Analytics: Kelp Suitability"):
        st.markdown("**Algorithm:** Suitability mask applied where `Depth = -5m to -30m` AND `SST < 18°C`.\n\n**Data Source:** DeepMind Species Distribution Models.")
st.write("") 

# ---------------------------------------------------------
# 6. DYNAMIC DATA LAYERS (With Rich Analytics Data Attached)
# ---------------------------------------------------------
layers = []

vessels_df = pd.DataFrame([
    {"lat": 34.12, "lon": -119.85, "name": "CARGO VESSEL (MMSI: 368123450)", "color": [255, 165, 0, 200], "analytics": "Routine transit behavior. Vector normal.", "source": "Live AIS Telemetry"},
    {"lat": 33.95, "lon": -120.15, "name": "DARK TARGET (MMSI: 413000000)", "color": [204, 0, 0, 255], "analytics": "ANOMALY: Transponder disabled < 15nm from MPA.", "source": "AISStream + WDPA Spatial Join"}
])
layers.append(pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_color="color", get_radius=3000, pickable=True))

if mission_mode == "Ecological Protection (IUU / Kelp)":
    kelp_df = pd.DataFrame([{"lat": 34.02, "lon": -119.55, "name": "Kelp Restoration Zone (Sector K-1)", "analytics": "Depth 14
