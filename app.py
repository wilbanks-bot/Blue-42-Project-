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
    bg_color = "#0a0a0a"
    card_bg = "#121212"
    text_color = "#ff4d4d"
    border_color = "#8b0000"
    map_style = "dark"
    term_color = "#ff0000"
    term_bg = "#220000"
    css = f"""<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .metric-card {{ background-color: {card_bg}; padding: 20px; border-radius: 6px; border-left: 4px solid {border_color}; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(255,0,0,0.1); font-family: -apple-system, sans-serif;}}
    .alert-card {{ border: 1px solid #ef4444; box-shadow: 0 0 15px rgba(239, 68, 68, 0.5), inset 0 0 20px rgba(239, 68, 68, 0.2); animation: pulse-red 2s infinite; }}
    h2, h3, h4 {{ color: {text_color}; font-family: 'Trebuchet MS', sans-serif; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 5px rgba(255,255,255,0.3); margin-top: 0
