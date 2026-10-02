import streamlit as st
import pydeck as pdk
import pandas as pd
import json
import ee
from google.oauth2 import service_account
import google.generativeai as genai

# ---------------------------------------------------------
# 1. PAGE SETUP & FUTURISTIC HUD CSS
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 Command", page_icon="⚓", initial_sidebar_state="expanded")

# Cyberpunk / Global Intelligence HUD CSS with glowing animations
css = """
<style>
    /* Main Background */
    .stApp { background-color: #020617; color: #38bdf8; font-family: 'Courier New', monospace; }
    
    /* Glowing Cyber Cards */
    .cyber-card { 
        background: rgba(2, 6, 23, 0.8); 
        border: 1px solid #0ea5e9; 
        padding: 20px; 
        border-radius: 4px; 
        box-shadow: 0 0 15px rgba(14, 165, 233, 0.3), inset 0 0 20px rgba(14, 165, 233, 0.1);
        margin-bottom: 15px;
    }
    .alert-card {
        border: 1px solid #ef4444;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.5), inset 0 0 20px rgba(239, 68, 68, 0.2);
        animation: pulse-red 2s infinite;
    }
    
    /* Typography */
    h2, h3, h4 { color: #f8fafc; font-family: 'Trebuchet MS', sans-serif; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 5px rgba(255,255,255,0.3); margin-top: 0; }
    .kpi-value { font-size: 2.5rem; color: #38bdf8; font-weight: bold; text-shadow: 0 0 10px #38bdf8; margin: 0; line-height: 1.2; }
    .kpi-alert { color: #ef4444; text-shadow: 0 0 10px #ef4444; }
    .hud-text { color: #94a3b8; font-size: 0.85rem; letter-spacing: 1px; }
    
    /* Pulse Animation for Critical Threats */
    @keyframes pulse-red {
        0% { box-shadow: 0 0 15px rgba(239, 68, 68, 0.5); }
        50% { box-shadow: 0 0 25px rgba(239, 68, 68, 0.8); }
        100% { box-shadow: 0 0 15px rgba(239, 68, 68, 0.5); }
    }
    
    /* Terminal Box */
    .terminal { background-color: #000000; padding: 15px; border: 1px solid #22c55e; border-radius: 3px; color: #22c55e; font-size: 0.8rem; box-shadow: inset 0 0 10px rgba(34, 197, 94, 0.2); }
    
    /* Expanders */
    .streamlit-expanderHeader { color: #38bdf8 !important; font-family: 'Courier New', monospace; font-weight: bold; background: rgba(14, 165, 233, 0.1); border: 1px solid #0ea5e9; }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. SECURE API INITIALIZATION
# ---------------------------------------------------------
try:
    key_dict = json.loads(st.secrets["EARTHENGINE_TOKEN"])
    creds = service_account.Credentials.from_service_account_info(key_dict).with_scopes(['https://www.googleapis.com/auth/earthengine'])
    ee.Initialize(credentials=creds, project=key_dict.get("project_id"))
    ee_status = "🟢 UPLINK SECURE"
except:
    ee_status = "🔴 UPLINK SEVERED"

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
    ai_status = "🟢 CORE ACTIVE"
except:
    ai_status = "🔴 CORE OFFLINE"

# ---------------------------------------------------------
# 3. SIDEBAR: HUD LOGO, MISSION SELECTOR & SIGINT
# ---------------------------------------------------------
st.sidebar.markdown("""
<div style="text-align: center; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #0ea5e9;">
    <div style="font-size: 65px; color: #38bdf8; text-shadow: 0 0 20px #38bdf8; line-height: 1;">⚓</div>
    <div style="font-family: 'Trebuchet MS', sans-serif; font-weight: bold; color: #f8fafc; font-size: 1.5rem; letter-spacing: 4px; margin-top: 5px; text-shadow: 0 0 10px rgba(255,255,255,0.5);">BLUE 42</div>
    <div style="font-family: 'Courier New', monospace; color: #22c55e; font-size: 0.8rem; letter-spacing: 2px;">GLOBAL MARITIME COMMAND</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"<div class='hud-text'><b>SATCOM:</b> {ee_status}<br><b>NEURAL NET:</b> {ai_status}</div><hr>", unsafe_allow_html=True)

st.sidebar.markdown("### 🌐 OVERRIDE PARAMETERS")
mission_mode = st.sidebar.radio("TARGET OVERLAY:", 
    ["Ecological Protection (IUU / Kelp)", 
     "Economic Security (Subsea Cables)", 
     "Humanitarian (Search & Rescue)"]
)
st.sidebar.markdown("---")

st.sidebar.markdown("### 📻 SIGINT TERMINAL")
if mission_mode == "Ecological Protection (IUU / Kelp)":
    radio_feed = "[14:02Z VHF-16] 'MARITIME COMM, this is F/V Horizon. Trawler running dark, hauling nets 3nm off Santa Cruz Is.'\n> ACOUSTIC MATCH: MMSI 413000000."
    risk_score = "RED (High Risk)"
    ai_summary = "Target masking identity in protected biosphere. Matrix indicates High Severity to marine biomass, High Probability of ecocide. Recommend immediate intercept."
elif mission_mode == "Economic Security (Subsea Cables)":
    radio_feed = "[14:15Z NAVTEX] 'SECURITE. UNIDENTIFIED VESSEL LOITERING IN RESTRICTED CABLE CORRIDOR. HYDROPHONE DETECTS ANCHOR DROP.'\n> MATCH: Transpacific Trunk."
    risk_score = "RED (Critical Risk)"
    ai_summary = "Vessel anchoring over Tier-1 fiber optic trunk. Critical Severity (Global Economic Disruption). Exposure: High. Dispatching interdiction assets."
else:
    radio_feed = "[14:22Z VHF-16] 'MAYDAY MAYDAY. S/V Orion. Taking water. Engines dead. Lat 33.7, Lon -119.8. 4 POB.'\n> MATCH: Generating SAR Drift Grid."
    risk_score = "AMBER (Elevated Risk)"
    ai_summary = "Vessel adrift. WeatherNext indicates deteriorating sea state. Amber status: Time-sensitive exposure for 4 souls on board. Drift vector initialized."

st.sidebar.markdown(f
