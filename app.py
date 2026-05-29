import streamlit as st
import datetime

# Page Configuration
st.set_page_config(
    page_title="IrriTool | Precision Irrigation Engine",
    page_icon="💧",
    layout="centered"
)

# Main Branding Header
st.title("💧 IrriTool")
st.subheader("Data-Driven Optimization Engine for Precision Irrigation")
st.markdown("""
Powered by the **ByteForce** heuristic grid-search optimization framework. 
IrriTool simulates localized soil-water dynamics to maximize natural rainfall retention 
and eliminate crop stress globally.
""")

# Simulation Parameters Input Layout
st.header("📋 Simulation Parameters")
col1, col2 = st.columns(2)

with col1:
    crop_type = st.selectbox(
        "Select Crop Type",
        ["Field Corn (Zea mays)", "Soybeans", "Wheat"]
    )
    planting_date = st.date_input(
        "Planting Date",
        datetime.date(2026, 5, 1)
    )

with col2:
    lat = st.number_input("Location Latitude", min_value=-90.0, max_value=90.0, value=43.5400, format="%.4f")
    lon = st.number_input("Location Longitude", min_value=-180.0, max_value=180.0, value=-80.2500, format="%.4f")

st.markdown("### Ready to Optimize?")
if st.button("🚀 Run IrriTool Engine", type="primary"):
    with st.spinner("Fetching climate datasets and executing grid-search iterations..."):
        # Temporary verification readout
        st.success("Analysis Complete!")
        st.metric(label="Optimal VWC Trigger", value="17.0%", delta="-70.6% Irrigation Events")
        st.info("Branding updated successfully! Let's wire up the assets next.")