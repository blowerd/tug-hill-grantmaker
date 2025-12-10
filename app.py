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
    st.error("Database not found. Run 'src/simulation.py' locally first!")
    st.stop()

# --- 2. SIDEBAR ---
st.sidebar.title("🎯 Tug Hill Grant Strategy")
svi_threshold = st.sidebar.slider("Minimum SVI (Need)", 0.0, 1.0, 0.3)
show_deserts = st.sidebar.checkbox("Highlight Urgent Deserts", value=True)

with st.sidebar.expander("⚖️ Legal / Disclaimer", expanded=False):
    st.caption("**Personal Project:** This project was made as a personal project in my personal time. It is not affiliated with any employer nor does it nessecarily represent their opinions. Further, this experiemntal project is not the grounds for any decisions and is not derived from any confidential or legally protected source. The data contained within is soley either publically available or simulated for demo purposes.")

# --- 3. MAP LOGIC ---
st.title("Regional Opportunity Map")

# Filter Data based on Slider
filtered_df = df[df['overall_svi'] >= svi_threshold].copy()

def get_color(row):
    if row['context_tag'] == 'Urgent Desert' and show_deserts:
        return [200, 30, 30, 200]  # Red
    elif row['context_tag'] == 'High-Capacity Hub':
        return [30, 200, 30, 160]  # Green
    else:
        return [100, 100, 100, 100] # Grey

filtered_df['fill_color'] = filtered_df.apply(get_color, axis=1)

# Define Layer with Explicit ID
layer = pdk.Layer(
    "GeoJsonLayer", 
    filtered_df,
    id="geojson", 
    get_polygon="geometry", 
    get_fill_color="fill_color",
    get_line_color=[255, 255, 255], 
    pickable=True, 
    auto_highlight=True, 
    opacity=0.8
)

view_state = pdk.ViewState(latitude=43.98, longitude=-75.8, zoom=9)

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
        filtered_df[display_cols].sort_values('overall_svi', ascending=False), 
        hide_index=True, 
        use_container_width=True
    )

with col2:
    st.subheader("🔍 Tract Inspector")
    
    # Get list of valid names for the dropdown
    available_names = list(filtered_df['name'].unique())
    
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
        match = filtered_df[filtered_df['name'] == selected_name]
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
            # In a real app, query the 'raw_assets' table here for this tract_id
            # conn = get_connection()
            # assets = pd.read_sql(f"SELECT * FROM raw_assets WHERE tract_id = '{match.iloc[0]['tract_id']}'", conn)
            # st.dataframe(assets)
            st.caption("List of known community assets would appear here.")
        
    else:
        st.warning("No tracts found. Try lowering the SVI threshold.")