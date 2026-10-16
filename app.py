import streamlit as st
import pydeck as pdk

# 1. Setup for Immersive UI
st.set_page_config(page_title="Blue 42 OS", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for Glassmorphism & removing Streamlit top padding
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    .glass-card {
        background: rgba(15, 23, 42, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Main Title Layout
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("## BLUE 42 | Planetary Capital OS 🌿")
    st.caption("Planetary-scale biogeochemical operating system fusing frontier AI and Earth telemetry.")

# 3. Hero Section: 3D Map + Floating Metrics
st.markdown("### 🌊 3D Spatial Deconfliction & Bathymetry")

# Top row metrics (Styled as a dashboard)
m1, m2, m3, m4 = st.columns(4)
m1.metric(label="Net Viable Kelp Area", value="35.4 HA", delta="Mathematically Deconflicted")
m2.metric(label="Harvestable Yield", value="602.5 MT", delta="-8% Thermal Stress", delta_color="inverse")
m3.metric(label="Averted Infrastructure Damage", value="$197.7M", delta="Wave Attenuation Active")
m4.metric(label="Ecological Capital ROI", value="$295k / Yr", delta="Stacked Value")

# 3D PyDeck Map replacing 2D Carto Map
# (You would feed your actual bathymetry/kelp data here)
st.pydeck_chart(pdk.Deck(
    map_style='mapbox://styles/mapbox/dark-v10',
    initial_view_state=pdk.ViewState(
        latitude=34.05, # Example California coast
        longitude=-120.0,
        zoom=10,
        pitch=50, # Tilts the map for 3D viewing
    ),
    layers=[
        pdk.Layer(
            'ColumnLayer', # Great for showing Kelp biomass vertically
            data=[], # Insert your GeoJSON / Dataframe
            get_position='[lon, lat]',
            get_elevation='biomass_yield',
            elevation_scale=100,
            radius=200,
            get_fill_color='[34, 139, 34, 150]', # Kelp Green
            pickable=True,
            auto_highlight=True,
        ),
    ],
))

# 4. Scrollytelling Panels instead of hidden tabs
st.markdown("---")
st.markdown("### 🎛️ Step 1: Stress-Test Simulation")
# Add your time sliders, marine heatwave toggles, and strain matchers here...
