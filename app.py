import streamlit as st
import pydeck as pdk
import pandas as pd
import json
import ee
from google.oauth2 import service_account

st.set_page_config(layout="wide", page_title="Maritime Operations Command")

# ---------------------------------------------------------
# 1. INITIALIZE EARTH ENGINE SECURELY
# ---------------------------------------------------------
try:
    # Read the hidden JSON token from Streamlit Secrets
    key_dict = json.loads(st.secrets["EARTHENGINE_TOKEN"])
    
    # Convert it into official Google Credentials WITH THE REQUIRED SCOPE
    creds = service_account.Credentials.from_service_account_info(key_dict).with_scopes(['https://www.googleapis.com/auth/earthengine'])
    
    # Initialize Earth Engine with the robot user
    ee.Initialize(credentials=creds, project=key_dict.get("project_id"))
    st.sidebar.success("✅ Earth Engine Connected")
except Exception as e:
    st.sidebar.error(f"Earth Engine Error: {e}")

# ---------------------------------------------------------
# 2. DASHBOARD UI
# ---------------------------------------------------------
st.sidebar.title("🚨 Tactical Incident Command")
st.sidebar.markdown("**Sector Status:** Condition ALPHA")

with st.sidebar.expander("CRITICAL: Dark Vessel Detected", expanded=True):
    st.error("Target: MMSI 413000000 | Incursion Risk")
    st.write("**Last Position:** 34.012° N, 120.341° W")
    if st.sidebar.button("Dispatch Coast Guard Cutter"):
        st.sidebar.success("Interception vector transmitted.")

# Layer 1: Vessel Telemetry (Yellow Dots)
vessels_df = pd.DataFrame([{"lat": 34.12, "lon": -119.85, "mmsi": "368123450", "sog": 12.4, "name": "PACIFIC TITAN"}])
vessel_layer = pdk.Layer("ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", get_color="[255, 204, 0, 220]", get_radius=2500, pickable=True)

# Layer 2: Kelp Restoration Pins (Green Targets)
kelp_df = pd.DataFrame([{"lat": 34.02, "lon": -119.55, "site": "Sector K-1", "depth": "14m"}])
kelp_layer = pdk.Layer("ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", get_color="[0, 255, 128, 220]", get_radius=3000, pickable=True)

# Layer 3: Safe Passage Route (Green Trackline)
route_data = [{"path": [[-119.2, 33.7], [-119.6, 33.8], [-120.2, 34.1]]}]
route_layer = pdk.Layer("PathLayer", data=route_data, get_path="path", get_color="[0, 255, 0, 200]", width_min_pixels=3)

# ---------------------------------------------------------
# 3. RENDER THE MAP 
# ---------------------------------------------------------
r = pdk.Deck(
    layers=[vessel_layer, kelp_layer, route_layer], 
    initial_view_state=pdk.ViewState(latitude=34.0, longitude=-119.8, zoom=8, pitch=30), 
    map_style="dark"  
)
st.pydeck_chart(r)
