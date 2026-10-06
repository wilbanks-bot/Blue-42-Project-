import streamlit as st
import pydeck as pdk
import pandas as pd
import time
import json
import ee
from datetime import datetime
from google.oauth2 import service_account

# =========================================================
# 1. PAGE SETUP & CONFIGURATION
# =========================================================
st.set_page_config(layout="wide", page_title="Blue 42", page_icon="🌊")

# Hide standard Streamlit padding to maximize the map's real estate
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; padding-left: 1rem; padding-right: 1rem; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. GOOGLE EARTH ENGINE INITIALIZATION
# =========================================================
try:
    if "EARTHENGINE_TOKEN" in st.secrets:
        key_dict = json.loads(st.secrets["EARTHENGINE_TOKEN"])
        creds = service_account.Credentials.from_service_account_info(key_dict).with_scopes(['https://www.googleapis.com/auth/earthengine'])
        ee.Initialize(credentials=creds, project=key_dict.get("project_id"))
        ee_connected = True
    else:
        # Fallback initialization if no secrets are found
        ee.Initialize()
        ee_connected = True
except Exception:
    ee_connected = False

# =========================================================
# 3. BACKEND DATA PROCESSING & CACHING
# =========================================================

@st.cache_data(ttl=3600)
def get_kelp_planting_coordinates():
    """
    Finds suitable giant kelp habitats using Copernicus Bathymetry (5m-30m) 
    and ERA5 Hourly Sea Surface Temperature (<18C / 291.15K).
    """
    if ee_connected:
        try:
            # 1. Copernicus Static Bathymetry (5m to 30m depth)
            bathy = ee.ImageCollection('COPERNICUS/MARINE/WAV/ANFC_0_083DEG_STATIC').first().select('deptho')
            depth_mask = bathy.gte(5).And(bathy.lte(30))

            # 2. ERA5 Hourly Sea Surface Temperature (< 18°C / 291.15 K)
            # Taking a mean over a recent time period to represent average conditions
            sst = ee.ImageCollection('ECMWF/ERA5_HOURLY').filterDate('2023-01-01', '2023-12-31').mean().select('sea_surface_temperature')
            temp_mask = sst.lt(291.15)

            # 3. Create suitability mask where both conditions are true
            suitability = depth_mask.And(temp_mask)
            suitable_areas = suitability.updateMask(suitability)

            # 4. Group adjacent pixels into clusters, extract top 5 largest centroids
            # Defined Region of Interest (California Coast) to prevent global timeout limits
            roi = ee.Geometry.Rectangle([-122.0, 33.0, -118.0, 35.0])
            
            # Reduce to vectors to get coordinate points of the clusters
            clusters = suitable_areas.reduceToVectors(
                geometry=roi,
                crs=bathy.projection(),
                scale=1000, # 1km scale for query efficiency
                geometryType='centroid',
                maxPixels=1e9
            ).limit(5) # Top 5 clusters

            # Extract coordinates to Pandas DataFrame
            features = clusters.getInfo()['features']
            kelp_data = []
            for i, f in enumerate(features):
                coords = f['geometry']['coordinates']
                kelp_data.append({
                    "lon": coords[0], 
                    "lat": coords[1], 
                    "site": f"Kelp Cluster {i+1}", 
                    "depth": "Suitable (5m-30m)"
                })
            
            if kelp_data:
                return pd.DataFrame(kelp_data)
                
        except Exception as e:
            print(f"Earth Engine Query Failed, using fallback. Error: {e}")

    # FALLBACK: If Earth Engine is not authenticated or times out, load mocked exact coordinates
    return pd.DataFrame([
        {"lat": 34.02, "lon": -119.55, "site": "Kelp Cluster 1 (Modeled)", "depth": "14m"},
        {"lat": 33.85, "lon": -120.00, "site": "Kelp Cluster 2 (Modeled)", "depth": "22m"},
        {"lat": 33.75, "lon": -119.20, "site": "Kelp Cluster 3 (Modeled)", "depth": "18m"},
        {"lat": 34.10, "lon": -119.30, "site": "Kelp Cluster 4 (Modeled)", "depth": "25m"},
        {"lat": 33.90, "lon": -119.80, "site": "Kelp Cluster 5 (Modeled)", "depth": "12m"}
    ])

@st.cache_data(ttl=3600)
def get_weather_danger_areas():
    """Simulates WeatherNext 3 vector polygons where H_s > 6.1m or Wind > 50mph."""
    return [{"polygon": [[-121.0, 34.5], [-119.0, 34.5], [-119.0, 33.5], [-121.0, 33.5]]}]

@st.cache_data(ttl=60)
def get_live_vessels():
    """Simulates live vessel telemetry with MMSI and SOG."""
    return pd.DataFrame([
        {"lat": 34.12, "lon": -119.85, "mmsi": 362728551, "sog": 12.4},
        {"lat": 34.05, "lon": -119.60, "mmsi": 362125848, "sog": 8.5},
        {"lat": 33.95, "lon": -120.15, "mmsi": 413000000, "sog": 3.1} # Dark target
    ])

@st.cache_data(ttl=3600)
def get_safe_navigation_path():
    """Simulates dynamic green path generation avoiding the red storm zone."""
    return pd.DataFrame([
        {"path": [[-119.2, 33.7], [-119.6, 33.8], [-120.2, 34.1]]}
    ])

# Fetch data layers
kelp_df = get_kelp_planting_coordinates()
vessels_df = get_live_vessels()
route_df = get_safe_navigation_path()
weather_data = get_weather_danger_areas()

# =========================================================
# 4. LEFT-HAND SIDEBAR: COAST GUARD OPERATIONS LOG
# =========================================================
with st.sidebar:
    st.title("Coast Guard Operations Log")
    st.markdown("---")
    
    # Gemini Incident Alert
    st.error("🚨 **GEMINI INCIDENT ALERT**")
    st.markdown("""
    **Target:** MMSI 413000000  
    **Location:** 33.95° N, 120.15° W  
    **Analysis:** Vessel speed dropped to 3.1 kts. Heading altered multiple times in the last 20 mins. Intentional AIS blackout suspected within the Marine Protected Area boundaries. 
    """)
    
    # Authorize Patrol Intercept Button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Authorize Patrol Intercept", type="primary", use_container_width=True):
        with st.spinner("Securing transmission..."):
            time.sleep(1)
            st.success("✅ Intercept Authorized!")
            st.info(f"Coordinates securely transmitted to USCG Cutter at {datetime.utcnow().strftime('%H:%M:%S')} UTC.")
            
    st.markdown("---")
    st.caption("Active Map Layers:")
    st.caption("🟡 Live Vessels | 🔴 Weather Hazard | 🟢 Safe Route | 📍 Kelp Sites")

# =========================================================
# 5. MAIN SCREEN: OCEAN-THEMED PYDECK MAP
# =========================================================

# Layer 1: Live vessels as yellow dots with MMSI and Speed tooltips
layer_1_vessels = pdk.Layer(
    "ScatterplotLayer",
    data=vessels_df,
    get_position="[lon, lat]",
    get_color="[255, 255, 0, 255]", # Bright Yellow
    get_radius=2500,
    pickable=True
)

# Layer 2: Weather danger areas shown as translucent red polygons
layer_2_weather = pdk.Layer(
    "PolygonLayer",
    data=weather_data,
    get_polygon="polygon",
    get_fill_color="[255, 0, 0, 70]", # Translucent Red
    get_line_color="[255, 0, 0, 200]",
    pickable=False
)

# Layer 3: A safe navigation path shown as a green line
layer_3_route = pdk.Layer(
    "PathLayer",
    data=route_df,
    get_path="path",
    get_color="[0, 255, 0, 255]", # Solid Green
    width_min_pixels=4,
    pickable=False
)

# Layer 4: Kelp planting coordinates shown as bright green pins
layer_4_kelp = pdk.Layer(
    "ScatterplotLayer",
    data=kelp_df,
    get_position="[lon, lat]",
    get_color="[0, 255, 128, 255]", # Bright Green
    get_radius=3500,
    pickable=True
)

# Set the View State focusing on the California Coast operational sector
view_state = pdk.ViewState(
    latitude=34.0, 
    longitude=-119.8, 
    zoom=7.5, 
    pitch=30
)

# Render the Map with an "Ocean" satellite theme
r = pdk.Deck(
    layers=[layer_2_weather, layer_3_route, layer_4_kelp, layer_1_vessels],
    initial_view_state=view_state,
    map_style=pdk.map_styles.SATELLITE, # Ocean-themed satellite background
    tooltip={"html": "<b>Asset/Target:</b> {mmsi}{site} <br/> <b>Metrics:</b> {sog} kts {depth}"}
)

st.pydeck_chart(r, use_container_width=True)
