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

# Night Vision Toggle in the sidebar
night_vision = st.sidebar.toggle("🌙 Tactical Night Vision Mode", value=False)

if night_vision:
    bg_color = "#0a0a0a"
    card_bg = "#121212"
    text_color = "#ff4d4d"
    border_color = "#8b0000"
    map_style = "dark"
    css = f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 6px; border-left: 4px solid {border_color}; margin-bottom: 5px; box-shadow: 0 1px 3px rgba(255,0,0,0.1); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;}}
    h4 {{ margin-top: 0px; color: {text_color}; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
    h2 {{ margin-bottom: 0px; color: {text_color}; font-size: 2rem; font-weight: 700; }}
    p {{ margin-bottom: 0px; color: #b30000; font-size: 0.85rem; }}
    .streamlit-expanderHeader {{ color: {text_color} !important; font-size: 0.9rem; }}
    </style>
    """
else:
    bg_color = "#f8fafc"
    card_bg = "#ffffff"
    text_color = "#0f172a"
    accent_blue = "#003366" 
    accent_red = "#cc0000"
    map_style = "light"
    css = f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 6px; border-left: 4px solid {accent_blue}; margin-bottom: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;}}
    .protection-card {{ border-left: 4px solid {accent_red}; }}
    h4 {{ margin-top: 0px; color: #64748b; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
    h2 {{ margin-bottom: 0px; color: {accent_blue}; font-size: 2rem; font-weight: 700; }}
    p {{ margin-bottom: 0px; color: #475569; font-size: 0.85rem; }}
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
    ee_status = "🟢 ON-LINE"
except Exception as e:
    ee_status = f"🔴 OFF-LINE"

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
    ai_status = "🟢 ON-LINE"
except Exception as e:
    ai_status = "🔴 OFF-LINE"

# ---------------------------------------------------------
# 3. SIDEBAR: TACTICAL WATCHSTANDER & LIVE AI CHAT
# ---------------------------------------------------------
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1c/Seal_of_the_United_States_Coast_Guard.svg/200px-Seal_of_the_United_States_Coast_Guard.svg.png", width=60)
