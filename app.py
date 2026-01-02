import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from src.database import get_connection

st.set_page_config(layout="wide", page_title="Regional Grantmaker PoC")

# --- 0. STATE MANAGEMENT ---
if "selected_tract" not in st.session_state:
    st.session_state.selected_tract = None

# --- 1. DATA LOADING ---
try:
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM vw_tract_profile", conn)
    conn.close()
    # Parse GeoJSON strings into Dicts for PyDeck
    df['geometry'] = df['geometry'].apply(json.loads)
except Exception as e:
    st.error("Database not found. Run 'src/etl.py' locally first!")
    st.stop()

# --- 2. SIDEBAR ---
st.sidebar.title("🎯 Tug Hill Grant Strategy")
st.sidebar.markdown("### 🕵️ Data Debug")
st.sidebar.info(f"Total Tracts Loaded: {len(df)}")
#st.sidebar.caption(f"Visible Tracts (filtered): {len(filtered_df)}")
if st.sidebar.checkbox("Show Raw Data Table"):
    st.dataframe(df[['name', 'overall_svi', 'context_tag']])
svi_threshold = st.sidebar.slider("Minimum SVI (Need)", 0.0, 1.0, 0.3)
show_deserts = st.sidebar.checkbox("Highlight Urgent Deserts", value=True)

with st.sidebar.expander("⚖️ Legal / Disclaimer", expanded=False):
    st.caption("**Personal Project:** This project was made as a personal project in my personal time. It is not affiliated with any employer nor does it nessecarily represent their opinions. Further, this experiemntal project is not the grounds for any decisions and is not derived from any confidential or legally protected source. The data contained within is soley either publically available or simulated for demo purposes.")

# --- 3. MAP LOGIC ---
st.title("Regional Opportunity Map")

display_df = df.copy() # <-- NEW

def get_color(row):
    # 1. CHECK THE SLIDER (The "Dimming" Logic)
    if row['overall_svi'] < svi_threshold:
        # Return a very transparent grey (Ghost Mode)
        # [R, G, B, Alpha] -> Alpha 20 is barely visible
        return [200, 200, 200, 20] 
        
    # 2. STANDARD LOGIC (For visible tracts)
    if row['context_tag'] == 'Urgent Desert' and show_deserts:
        return [200, 30, 30, 200]  # Red
    elif row['context_tag'] == 'High-Capacity Hub':
        return [30, 200, 30, 160]  # Green
    else:
        return [30, 100, 200, 140] # Blue (The standard "Visible" color)

display_df['fill_color'] = display_df.apply(get_color, axis=1)

# Define Layer
layer = pdk.Layer(
    "GeoJsonLayer", 
    display_df,      # Use the full dataset
    id="geojson", 
    get_polygon="geometry", 
    get_fill_color="fill_color",
    # Dynamic Line Color: Hide lines for "Ghost" tracts to reduce clutter
    get_line_color="[255, 255, 255, 80]", 
    pickable=True, 
    auto_highlight=True, 
    opacity=0.8,
    stroked=True,
    get_line_width=20
)

# UPDATED ZOOM: Centered to show Jefferson, Lewis, and St. Lawrence
view_state = pdk.ViewState(latitude=44.2, longitude=-75.4, zoom=7.5)

# RENDER MAP & CAPTURE CLICK
event = st.pydeck_chart(
    pdk.Deck(
        layers=[layer], 
        initial_view_state=view_state, 
        tooltip={"html": "<b>{name}</b><br/>Status: {context_tag}<br/>SVI: {overall_svi}"}
    ),
    on_select="rerun",           # Rerun app on click
    selection_mode="single-object"
)

# HANDLE CLICK EVENT
if event.selection:
    # PyDeck returns: {'geojson': [ {row_data...} ]}
    clicked_objects = event.selection.get("objects", {}).get("geojson", [])
    if clicked_objects:
        # Update Session State with the name of the clicked tract
        st.session_state.selected_tract = clicked_objects[0]['name']

# --- 4. DRILL DOWN ---
st.divider()
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Priority Zones")
    display_cols = ['name', 'context_tag', 'overall_svi', 'count_assets']
    st.dataframe(
        display_df[display_cols].sort_values('overall_svi', ascending=False), 
        hide_index=True, 
        use_container_width=True
    )

with col2:
    st.subheader("🔍 Tract Inspector")
    
    # Get list of valid names for the dropdown
    available_names = list(display_df['name'].unique())
    
    # LOGIC: Sync Dropdown with Map Click
    # If the clicked tract is in the current filtered list, set it as default.
    try:
        if st.session_state.selected_tract in available_names:
            index = available_names.index(st.session_state.selected_tract)
        else:
            index = 0
    except:
        index = 0
    
    if available_names:
        
        # The Selectbox
        selected_name = st.selectbox("Select Tract:", available_names, index=index)
        
        # Update Session State (in case user uses dropdown instead of map)
        st.session_state.selected_tract = selected_name
        
        # --- RENDER DETAILS ---
        # Safe Row Fetch
        match = display_df[display_df['name'] == selected_name]
        if match.empty:
            st.warning("Selection not available in current filter.")
            st.stop()
            
        row = match.iloc[0]

        # --- NEW: TABBED INTERFACE ---
        tab_overview, tab_social, tab_capacity = st.tabs(["📊 Overview", "👥 Demographics", "🛠️ Capacity"])
        
        # Parse JSON once
        try:
            d = json.loads(row['demographics_json'])
        except:
            d = {}

        with tab_overview:
            st.markdown(f"### {row['name']}")
            
            # Key KPI Row
            k1, k2 = st.columns(2)
            k1.metric("SVI Score", f"{row['overall_svi']:.2f}", 
                      delta="High Vulnerability" if row['overall_svi'] > 0.75 else "Stable",
                      delta_color="inverse")
            k2.metric("Population", f"{d.get('total_pop', 'N/A'):,}")
            
            # Extra Metrics from ETL
            k3, k4 = st.columns(2)
            k3.metric("Broadband Access", f"{d.get('pct_broadband', 0)}%")
            k4.metric("Uninsured", f"{d.get('pct_uninsured', 0)}%")

            # Status Banner
            if "Desert" in row['context_tag']:
                st.error(f"🚨 **{row['context_tag']}**\n\nHigh Need + Low Assets. Priority for Capacity Building.")
            elif "Hub" in row['context_tag']:
                st.success(f"✅ **{row['context_tag']}**\n\nStrong infrastructure available for new programs.")
            else:
                st.info(f"ℹ️ **{row['context_tag']}**")

        with tab_social:
            if d:
                st.caption("Census DP05 Data")
                st.markdown("**Age Structure**")
                st.progress(d['pct_senior']/100, f"Seniors: {d['pct_senior']}%")
                st.progress(d['pct_under_18']/100, f"Youth: {d['pct_under_18']}%")
                
                st.markdown("**Race & Ethnicity**")
                # Simple bar chart for race
                race_data = pd.DataFrame({
                    'Group': ['White', 'Black', 'Hispanic'],
                    'Pct': [d['pct_white'], d['pct_black'], d['pct_hispanic']]
                })
                st.bar_chart(race_data.set_index('Group'), horizontal=True)
            else:
                st.warning("No demographic data linked.")

        with tab_capacity:
            st.markdown(f"**Asset Count:** {row['count_assets']}")
            st.caption("Estimated count based on regional infrastructure density.")
            # In a real app, query the 'raw_assets' table here
        
    else:
        st.warning("No tracts found. Try lowering the SVI threshold.")