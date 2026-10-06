import streamlit as st
import pydeck as pdk
import pandas as pd
import math
import json
import time
import random
from datetime import datetime
import google.generativeai as genai

try:
    from fpdf import FPDF
except ImportError:
    st.error("Please install fpdf: pip install fpdf")

# =========================================================
# 1. APP CONFIGURATION & CUSTOM CSS (EXPERT UI/UX)
# =========================================================
st.set_page_config(layout="wide", page_title="Blue 42 Command", page_icon="🌊", initial_sidebar_state="expanded")

# Custom CSS for a sleek, Palantir-style Dark Mode Enterprise look
custom_css = """
<style>
    /* Clean up the header space */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    
    /* Style the Metric Cards for the KPI row */
    div[data-testid="metric-container"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* Make buttons look tactile and professional */
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2);
    }
    
    /* Clean up expanders */
    .streamlit-expanderHeader { font-weight: 600; color: #38BDF8; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Initialize Session States
if "library" not in st.session_state: st.session_state.library = []
if "sentinel_logs" not in st.session_state: st.session_state.sentinel_logs = []
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Blue 42 Watchstander AI initialized. How can I assist with your sector today?"}]

# =========================================================
# 2. BACKEND LOGIC: CACHING & ORCHESTRATION
# =========================================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_weather_hazard_polygons():
    """Simulates Earth Engine weather vectorization."""
    return [{"polygon": [[-121.0, 34.5], [-119.0, 34.5], [-119.0, 33.5], [-121.0, 33.5]]}]

@st.cache_resource(ttl=60)
def get_live_vessels():
    """Vessel Telemetry (with fallback snapshot for demo stability)."""
    data = [
        {"lat": 34.12, "lon": -119.85, "mmsi": 362728551, "sog": 12.4, "cog": 180, "length": 288, "width": 40, "name": "BULK 8551", "risk": "Nominal", "cargo_val": 25.6, "fuel_saved": 19.3},
        {"lat": 33.95, "lon": -120.15, "mmsi": 413000000, "sog": 3.1,  "cog": 45,  "length": 35,  "width": 8,  "name": "DARK TARGET", "risk": "CRITICAL", "cargo_val": 0.0, "fuel_saved": 0.0},
        {"lat": 34.05, "lon": -119.60, "mmsi": 362125848, "sog": 8.5,  "cog": 90,  "length": 190, "width": 25, "name": "CARGO 5848", "risk": "Nominal", "cargo_val": 102.9, "fuel_saved": 24.4}
    ]
    return pd.DataFrame(data)

def filter_kelp_sites(proposed_sites, live_vessels, safe_distance_km=2.0):
    """Deconflicts kelp zones from active shipping lanes."""
    safe_sites = []
    R = 6371 
    for site in proposed_sites:
        conflict = False
        for _, ship in live_vessels.iterrows():
            dlat = math.radians(ship['lat'] - site['lat'])
            dlon = math.radians(ship['lon'] - site['lon'])
            a = math.sin(dlat/2)**2 + math.cos(math.radians(site['lat'])) * math.cos(math.radians(ship['lat'])) * math.sin(dlon/2)**2
            dist = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))
            if dist < safe_distance_km:
                conflict = True
                break
        if not conflict: safe_sites.append(site)
    return safe_sites

def create_pdf_brief(incident: dict) -> bytes:
    """Generates immutable PDF report for dispatch."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "BLUE 42 - TACTICAL INTERDICTION BRIEF", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 10, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", ln=True)
    pdf.cell(0, 10, f"Target MMSI: {incident.get('mmsi', 'UNKNOWN')}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "AI Reasoning Trace:", ln=True)
    pdf.set_font("Arial", size=10)
    text = incident.get('trace', 'N/A').encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, text)
    return pdf.output(dest="S").encode("latin-1")

def get_battleship_polygon(lat, lon, cog, length_m, width_m):
    """Creates a directed 3D polygon for ships on PyDeck."""
    cog_rad = math.radians(cog)
    scale = 3.5 
    L, W = length_m * scale, width_m * scale
    lat_deg_per_m = 1.0 / 111111.0
    lon_deg_per_m = 1.0 / (111111.0 * math.cos(math.radians(lat)))
    pts = [(-W/2, -L/2), (W/2, -L/2), (W/2, L/4), (0, L/2), (-W/2, L/4)]
    poly = []
    for dx, dy in pts:
        x_rot = dx * math.cos(cog_rad) + dy * math.sin(cog_rad)
        y_rot = -dx * math.sin(cog_rad) + dy * math.cos(cog_rad)
        poly.append([lon + x_rot * lon_deg_per_m, lat + y_rot * lat_deg_per_m])
    return [poly]

# =========================================================
# 3. UI: SIDEBAR NAVIGATION
# =========================================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/e/e4/Globe_icon.svg", width=50) # Placeholder logo
    st.title("Blue 42 Command")
    st.caption("Global Blue Economy OS")
    
    st.markdown("---")
    operator_role = st.selectbox("Operator Profile", ["Watchstander", "Command", "ESG Auditor"])
    sector_mode = st.selectbox("Sector", ["US West Coast", "Hawaiian Islands"])
    
    with st.expander("🟢 System Status", expanded=True):
        st.write("🌐 **GEO:** SECURE UPLINK")
        st.write("🧠 **AI:** CORE ACTIVE")
        st.write("📡 **AIS:** RADAR AUTHENTICATED")
        
    with st.expander("📊 Map Overlays", expanded=False):
        show_iuu = st.checkbox("🛡️ Marine Protected Areas", value=True)
        show_weather = st.checkbox("⛈️ Weather Hazards", value=True)
        show_depth = st.checkbox("🌱 Blue Carbon Sites", value=True)

# =========================================================
# 4. UI: MAIN HEADER & KPI METRICS
# =========================================================
st.markdown("### 🌍 Global Maritime Command Center")
st.caption("Synthesizing planetary telemetry into predictive intelligence and actionable workflows.")

# Clean, styled KPI row
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric(label="⚠️ Supply Value at Risk", value="$4.2B", delta="-2.1% (Weather)")
kpi2.metric(label="✅ Scope 3 Averted", value="1,245 MT", delta="Optimal Routing")
kpi3.metric(label="🌱 Verified Blue Carbon", value="$12.4M", delta="+1.2 HA")
kpi4.metric(label="🚨 Active IUU Threats", value="2", delta="1 Critical")
kpi5.metric(label="🐋 Mammal Strikes Avoided", value="14", delta="Speed Limits Enforced")
st.write("") # Spacer

# =========================================================
# 5. UI: SPLIT LAYOUT (MAP vs. OPERATIONS)
# =========================================================
# The 70/30 split makes it look like a real software dashboard
col_map, col_ops = st.columns([7, 3], gap="large")

with col_map:
    st.markdown("#### Live Geospatial Battlespace")
    
    # Process Map Data
    vessels_df = get_live_vessels()
    raw_kelp = [{"lat": 34.02, "lon": -119.55, "site": "K-1"}, {"lat": 33.95, "lon": -120.15, "site": "K-2"}]
    safe_kelp = filter_kelp_sites(raw_kelp, vessels_df, safe_distance_km=1.5)
    kelp_df = pd.DataFrame(safe_kelp)

    # Prepare 3D Polygons for Vessels
    vessels_df['polygon'] = vessels_df.apply(lambda r: get_battleship_polygon(r['lat'], r['lon'], r['cog'], r['length'], r['width']), axis=1)
    vessels_df['color'] = vessels_df['risk'].apply(lambda x: [239, 68, 68, 255] if x == "CRITICAL" else [56, 189, 248, 180])
    vessels_df['elevation'] = vessels_df.apply(lambda r: 150 if r['risk'] == "CRITICAL" else r['length']/4, axis=1)

    # PyDeck Layers
    layers = []
    layers.append(pdk.Layer(
        "PolygonLayer", data=vessels_df, get_polygon="polygon", get_fill_color="color", 
        extruded=True, get_elevation="elevation", pickable=True, auto_highlight=True
    ))
    if show_weather:
        layers.append(pdk.Layer(
            "PolygonLayer", data=get_weather_hazard_polygons(), get_polygon="polygon", 
            get_fill_color="[239, 68, 68, 60]", get_line_color="[239, 68, 68, 200]"
        ))
    if not kelp_df.empty and show_depth:
        layers.append(pdk.Layer(
            "ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", 
            get_color="[16, 185, 129, 200]", get_radius=3000, pickable=True
        ))

    view_state = pdk.ViewState(latitude=34.0, longitude=-119.8, zoom=8, pitch=45)
    r = pdk.Deck(
        layers=layers, initial_view_state=view_state, 
        tooltip={"text": "{name}\nSpeed: {sog} kts\nRisk: {risk}"}, 
        map_style="mapbox://styles/mapbox/dark-v11"
    )
    st.pydeck_chart(r, use_container_width=True, height=550)

with col_ops:
    # Action panel replacing the cluttered right column
    st.markdown("#### Operations Center")
    op_tab1, op_tab2, op_tab3 = st.tabs(["🚨 Threats", "💬 AI Watchstander", "🛡️ Sentinel"])
    
    with op_tab1:
        st.error("**CRITICAL: Dark Vessel Detected**")
        st.write("**MMSI:** 413000000")
        st.write("**Position:** 33.95° N, 120.15° W")
        st.write("**Violation:** Intentional AIS Blackout & Loitering.")
        
        with st.expander("🔍 AI Reasoning Trace"):
            st.caption("Speed dropped to 3.1 kts. Heading altered 4 times in past 20 mins. Currently 1.2 NM inside MPA.")
        
        # Auditable PDF Generation
        mock_incident = {"mmsi": "413000000", "trace": "Speed dropped to 3.1 kts. Heading altered 4 times in past 20 mins."}
        pdf_bytes = create_pdf_brief(mock_incident)
        st.download_button("📄 Download PDF Interdiction Brief", data=pdf_bytes, file_name="Target_413000000.pdf", mime="application/pdf", use_container_width=True)

    with op_tab2:
        st.caption(f"Role: {operator_role} Advisor")
        chat_container = st.container(height=300)
        with chat_container:
            for msg in st.session_state.messages:
                st.markdown(f"**{'🤖 AI' if msg['role']=='assistant' else '👤 You'}:** {msg['content']}")
        
        if prompt := st.chat_input("Ask Blue 42..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            # Add Gemini API call here in production
            mock_reply = "I am processing the telemetry and aligning with Coast Guard operational mandates."
            st.session_state.messages.append({"role": "assistant", "content": mock_reply})
            st.rerun()

    with op_tab3:
        st.info("Sentinel Layer: Human-in-the-Loop authorization required for outbound web actions.")
        st.write("**Pending Action:** `AUTHORIZE KINETIC INTERCEPT`")
        if st.button("🔑 BYPASS SENTINEL & TRANSMIT", type="primary", use_container_width=True):
            with st.spinner("Securing connection..."):
                time.sleep(1)
                st.success("Payload Transmitted to Enterprise Ledger.")
                st.json({"event_id": f"evt_{int(time.time())}", "target": "USCG_API", "status": "CLEARED"})

# =========================================================
# 6. UI: BOTTOM ENTERPRISE DATA LEDGER
# =========================================================
st.write("---")
st.markdown("#### 📈 Enterprise Data Ledger & Financial Validation")

ledger_tab, trend_tab = st.tabs(["💰 Fleet Scope 3 Financial Ledger", "📊 Decadal ESG Trends"])

with ledger_tab:
    st.markdown("**Total Capital Protected:** `$3,079.1 Million` | **Total Scope 3 Averted:** `1,600.4 MT CO2e`")
    styled_df = vessels_df[['mmsi', 'name', 'length', 'risk', 'cargo_val', 'fuel_saved']].style.highlight_max(axis=0, subset=["fuel_saved"], color="#10B981")
    st.dataframe(styled_df, use_container_width=True)

with trend_tab:
    c1, c2 = st.columns(2)
    years = pd.date_range("2016", "2026", freq="YE")
    with c1:
        st.markdown("**10-Year Wave Height Extremes (Meters)**")
        st.line_chart(pd.DataFrame({"Max Wave (m)": [5.2, 5.4, 5.1, 5.8, 6.0, 5.9, 6.2, 6.5, 6.4, 6.8]}, index=years), color="#F43F5E")
    with c2:
        st.markdown("**IUU Dark Fleet Incidents**")
        st.bar_chart(pd.DataFrame({"Incidents": [12, 14, 18, 15, 22, 28, 35, 41, 44, 52]}, index=years), color="#38BDF8")
```You are completely right. In my previous streamlined version, I reduced the mock data down to just 3 ships to save code lines, which inadvertently made your map look empty and lifeless! A maritime command center needs to actually **show a bustling fleet of boats** to look impressive to judges.

I have restored and enhanced the **Fleet Generation** logic. The app will now simulate 35+ commercial vessels dynamically scattered across your sector, complete with varying lengths, speeds, and headings, alongside your designated "Dark Target." 

To make sure they are highly visible, the map now renders **both** a glowing `ScatterplotLayer` (so you can see them zoomed out) and the 3D `PolygonLayer` (so you see the boat hulls when zoomed in).

Here is the fully populated, design-expert code:

```python
import streamlit as st
import pydeck as pdk
import pandas as pd
import math
import json
import time
import random
from datetime import datetime
import google.generativeai as genai

try:
    from fpdf import FPDF
except ImportError:
    st.error("Please install fpdf: pip install fpdf")

# =========================================================
# 1. APP CONFIGURATION & CUSTOM CSS (EXPERT UI/UX)
# =========================================================
st.set_page_config(layout="wide", page_title="Blue 42 Command", page_icon="🌊", initial_sidebar_state="expanded")

custom_css = """
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    div[data-testid="metric-container"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .stButton>button { border-radius: 6px; font-weight: 600; transition: all 0.2s ease-in-out; }
    .stButton>button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2); }
    .streamlit-expanderHeader { font-weight: 600; color: #38BDF8; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

if "library" not in st.session_state: st.session_state.library = []
if "sentinel_logs" not in st.session_state: st.session_state.sentinel_logs = []
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Blue 42 Watchstander AI initialized. How can I assist with your sector today?"}]

# =========================================================
# 2. BACKEND LOGIC: CACHING & ORCHESTRATION
# =========================================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_weather_hazard_polygons():
    return [{"polygon": [[-121.0, 34.5], [-119.0, 34.5], [-119.0, 33.5], [-121.0, 33.5]]}]

@st.cache_resource(ttl=60)
def get_live_vessels():
    """Generates a bustling fleet of 35+ vessels to populate the map."""
    data = []
    base_lat, base_lon = 34.0, -119.8
    
    # 1. Generate 35 Nominal Commercial Vessels
    for i in range(35):
        sog = random.uniform(8.0, 22.0)
        v_len = int(random.uniform(150, 350))
        v_type = random.choice(["CARGO", "TANKER", "BULK"])
        data.append({
            "lat": base_lat + random.uniform(-1.5, 1.5),
            "lon": base_lon + random.uniform(-2.0, 2.0),
            "mmsi": f"36{random.randint(1000000, 9999999)}",
            "sog": round(sog, 1),
            "cog": round(random.uniform(0, 360), 1),
            "length": v_len,
            "width": int(v_len * 0.15),
            "name": f"{v_type} {random.randint(100, 999)}",
            "risk": "Nominal",
            "cargo_val": round(random.uniform(10, 150), 1),
            "fuel_saved": round(random.uniform(5, 25), 1)
        })
        
    # 2. Inject Critical Dark Targets
    data.append({
        "lat": 33.95, "lon": -120.15, "mmsi": "413000000", "sog": 3.1, "cog": 45, 
        "length": 45, "width": 8, "name": "DARK TARGET ALPHA", "risk": "CRITICAL", 
        "cargo_val": 0.0, "fuel_saved": 0.0
    })
    data.append({
        "lat": 34.02, "lon": -120.20, "mmsi": "413000001", "sog": 2.5, "cog": 110, 
        "length": 60, "width": 12, "name": "DARK TARGET BRAVO", "risk": "CRITICAL", 
        "cargo_val": 0.0, "fuel_saved": 0.0
    })
    
    return pd.DataFrame(data)

def filter_kelp_sites(proposed_sites, live_vessels, safe_distance_km=2.0):
    safe_sites = []
    R = 6371 
    for site in proposed_sites:
        conflict = False
        for _, ship in live_vessels.iterrows():
            dlat = math.radians(ship['lat'] - site['lat'])
            dlon = math.radians(ship['lon'] - site['lon'])
            a = math.sin(dlat/2)**2 + math.cos(math.radians(site['lat'])) * math.cos(math.radians(ship['lat'])) * math.sin(dlon/2)**2
            dist = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))
            if dist < safe_distance_km:
                conflict = True
                break
        if not conflict: safe_sites.append(site)
    return safe_sites

def create_pdf_brief(incident: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "BLUE 42 - TACTICAL INTERDICTION BRIEF", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 10, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", ln=True)
    pdf.cell(0, 10, f"Target MMSI: {incident.get('mmsi', 'UNKNOWN')}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "AI Reasoning Trace:", ln=True)
    pdf.set_font("Arial", size=10)
    text = incident.get('trace', 'N/A').encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, text)
    return pdf.output(dest="S").encode("latin-1")

def get_battleship_polygon(lat, lon, cog, length_m, width_m):
    cog_rad = math.radians(cog)
    scale = 3.5 
    L, W = length_m * scale, width_m * scale
    lat_deg_per_m = 1.0 / 111111.0
    lon_deg_per_m = 1.0 / (111111.0 * math.cos(math.radians(lat)))
    pts = [(-W/2, -L/2), (W/2, -L/2), (W/2, L/4), (0, L/2), (-W/2, L/4)]
    poly = []
    for dx, dy in pts:
        x_rot = dx * math.cos(cog_rad) + dy * math.sin(cog_rad)
        y_rot = -dx * math.sin(cog_rad) + dy * math.cos(cog_rad)
        poly.append([lon + x_rot * lon_deg_per_m, lat + y_rot * lat_deg_per_m])
    return [poly]

# =========================================================
# 3. UI: SIDEBAR NAVIGATION
# =========================================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/e/e4/Globe_icon.svg", width=50) 
    st.title("Blue 42 Command")
    st.caption("Global Blue Economy OS")
    
    st.markdown("---")
    operator_role = st.selectbox("Operator Profile", ["Watchstander", "Command", "ESG Auditor"])
    sector_mode = st.selectbox("Sector", ["US West Coast", "Hawaiian Islands"])
    
    with st.expander("🟢 System Status", expanded=True):
        st.write("🌐 **GEO:** SECURE UPLINK")
        st.write("🧠 **AI:** CORE ACTIVE")
        st.write("📡 **AIS:** RADAR AUTHENTICATED")
        
    with st.expander("📊 Map Overlays", expanded=False):
        show_iuu = st.checkbox("🛡️ Marine Protected Areas", value=True)
        show_weather = st.checkbox("⛈️ Weather Hazards", value=True)
        show_depth = st.checkbox("🌱 Blue Carbon Sites", value=True)

# =========================================================
# 4. UI: MAIN HEADER & KPI METRICS
# =========================================================
st.markdown("### 🌍 Global Maritime Command Center")
st.caption("Synthesizing planetary telemetry into predictive intelligence and actionable workflows.")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric(label="⚠️ Supply Value at Risk", value="$4.2B", delta="-2.1% (Weather)")
kpi2.metric(label="✅ Scope 3 Averted", value="1,245 MT", delta="Optimal Routing")
kpi3.metric(label="🌱 Verified Blue Carbon", value="$12.4M", delta="+1.2 HA")
kpi4.metric(label="🚨 Active IUU Threats", value="2", delta="Critical Alerts")
kpi5.metric(label="🐋 Mammal Strikes Avoided", value="14", delta="Speed Limits Enforced")
st.write("") 

# =========================================================
# 5. UI: SPLIT LAYOUT (MAP vs. OPERATIONS)
# =========================================================
col_map, col_ops = st.columns([7, 3], gap="large")

with col_map:
    st.markdown("#### Live Geospatial Battlespace")
    
    vessels_df = get_live_vessels()
    raw_kelp = [{"lat": 34.02, "lon": -119.55, "site": "K-1"}, {"lat": 33.85, "lon": -120.00, "site": "K-2"}]
    safe_kelp = filter_kelp_sites(raw_kelp, vessels_df, safe_distance_km=1.5)
    kelp_df = pd.DataFrame(safe_kelp)

    # Visualization styling for boats
    vessels_df['polygon'] = vessels_df.apply(lambda r: get_battleship_polygon(r['lat'], r['lon'], r['cog'], r['length'], r['width']), axis=1)
    vessels_df['color'] = vessels_df['risk'].apply(lambda x: [239, 68, 68, 255] if x == "CRITICAL" else [56, 189, 248, 180])
    vessels_df['dot_color'] = vessels_df['risk'].apply(lambda x: [239, 68, 68, 255] if x == "CRITICAL" else [255, 204, 0, 255])
    vessels_df['elevation'] = vessels_df.apply(lambda r: 150 if r['risk'] == "CRITICAL" else max(20, r['length']/4), axis=1)

    layers = []
    
    # Layer: Glowing Dots for high visibility from afar
    layers.append(pdk.Layer(
        "ScatterplotLayer", data=vessels_df, get_position="[lon, lat]", 
        get_color="dot_color", get_radius=1200, pickable=True
    ))
    
    # Layer: 3D Hull Polygons for zoom-in
    layers.append(pdk.Layer(
        "PolygonLayer", data=vessels_df, get_polygon="polygon", get_fill_color="color", 
        extruded=True, get_elevation="elevation", pickable=False, auto_highlight=True
    ))
    
    if show_weather:
        layers.append(pdk.Layer(
            "PolygonLayer", data=get_weather_hazard_polygons(), get_polygon="polygon", 
            get_fill_color="[239, 68, 68, 50]", get_line_color="[239, 68, 68, 200]"
        ))
        
    if not kelp_df.empty and show_depth:
        layers.append(pdk.Layer(
            "ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", 
            get_color="[16, 185, 129, 200]", get_radius=3000, pickable=True
        ))

    view_state = pdk.ViewState(latitude=34.0, longitude=-119.8, zoom=7.5, pitch=45)
    r = pdk.Deck(
        layers=layers, initial_view_state=view_state, 
        tooltip={"text": "{name}\nSpeed: {sog} kts\nRisk: {risk}"}, 
        map_style="mapbox://styles/mapbox/dark-v11"
    )
    st.pydeck_chart(r, use_container_width=True, height=600)

with col_ops:
    st.markdown("#### Operations Center")
    op_tab1, op_tab2, op_tab3 = st.tabs(["🚨 Threats", "💬 AI Watchstander", "🛡️ Sentinel"])
    
    with op_tab1:
        st.error("**CRITICAL: Dark Vessel Detected**")
        st.write("**MMSI:** 413000000")
        st.write("**Position:** 33.95° N, 120.15° W")
        st.write("**Violation:** Intentional AIS Blackout & Loitering.")
        
        with st.expander("🔍 AI Reasoning Trace"):
            st.caption("Speed dropped to 3.1 kts. Heading altered 4 times in past 20 mins. Currently 1.2 NM inside MPA.")
        
        mock_incident = {"mmsi": "413000000", "trace": "Speed dropped to 3.1 kts. Heading altered 4 times in past 20 mins."}
        pdf_bytes = create_pdf_brief(mock_incident)
        st.download_button("📄 Download PDF Interdiction Brief", data=pdf_bytes, file_name="Target_413000000.pdf", mime="application/pdf", use_container_width=True)

    with op_tab2:
        st.caption(f"Role: {operator_role} Advisor")
        chat_container = st.container(height=350)
        with chat_container:
            for msg in st.session_state.messages:
                st.markdown(f"**{'🤖 AI' if msg['role']=='assistant' else '👤 You'}:** {msg['content']}")
        
        if prompt := st.chat_input("Ask Blue 42..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            mock_reply = "I am processing the telemetry and aligning with Coast Guard operational mandates."
            st.session_state.messages.append({"role": "assistant", "content": mock_reply})
            st.rerun()

    with op_tab3:
        st.info("Sentinel Layer: Human-in-the-Loop authorization required for outbound web actions.")
        st.write("**Pending Action:** `AUTHORIZE KINETIC INTERCEPT`")
        if st.button("🔑 BYPASS SENTINEL & TRANSMIT", type="primary", use_container_width=True):
            with st.spinner("Securing connection..."):
                time.sleep(1)
                st.success("Payload Transmitted to Enterprise Ledger.")
                st.json({"event_id": f"evt_{int(time.time())}", "target": "USCG_API", "status": "CLEARED"})

# =========================================================
# 6. UI: BOTTOM ENTERPRISE DATA LEDGER
# =========================================================
st.write("---")
st.markdown("#### 📈 Enterprise Data Ledger & Financial Validation")

ledger_tab, trend_tab = st.tabs(["💰 Fleet Scope 3 Financial Ledger", "📊 Decadal ESG Trends"])

with ledger_tab:
    total_cargo = vessels_df["cargo_val"].sum()
    total_fuel = vessels_df["fuel_saved"].sum()
    st.markdown(f"**Total Capital Protected:** `${total_cargo:,.1f} Million` | **Total Scope 3 Averted:** `{total_fuel * 3.11:,.1f} MT CO2e`")
    
    styled_df = vessels_df[['mmsi', 'name', 'length', 'risk', 'cargo_val', 'fuel_saved']].style.highlight_max(axis=0, subset=["fuel_saved"], color="#10B981")
    st.dataframe(styled_df, use_container_width=True)

with trend_tab:
    c1, c2 = st.columns(2)
    years = pd.date_range("2016", "2026", freq="YE")
    with c1:
        st.markdown("**10-Year Wave Height Extremes (Meters)**")
        st.line_chart(pd.DataFrame({"Max Wave (m)": [5.2, 5.4, 5.1, 5.8, 6.0, 5.9, 6.2, 6.5, 6.4, 6.8]}, index=years), color="#F43F5E")
    with c2:
        st.markdown("**IUU Dark Fleet Incidents**")
        st.bar_chart(pd.DataFrame({"Incidents": [12, 14, 18, 15, 22, 28, 35, 41, 44, 52]}, index=years), color="#38BDF8")
