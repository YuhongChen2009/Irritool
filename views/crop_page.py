import streamlit as st
from core.data_fetcher import fetch_top_crops


def render(active_region, suggested_crops):
    lat, lon = st.session_state["map_center"]
    faostat_key = (round(lat, 2), round(lon, 2))

    if st.session_state.get("faostat_key") != faostat_key:
        with st.spinner("Fetching crop data from FAOSTAT..."):
            country_name, crops = fetch_top_crops(lat, lon)
            st.session_state["faostat_key"]   = faostat_key
            st.session_state["faostat_crops"] = crops
            st.session_state["country_name"]  = country_name
    else:
        crops        = st.session_state["faostat_crops"]
        country_name = st.session_state.get("country_name") or active_region

    if st.session_state["selected_crop"] not in crops:
        st.session_state["selected_crop"] = crops[0]

    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown("### Your Selected Location")
        ma, mb = st.columns(2)
        ma.metric("Country", country_name)
        mb.metric("Coordinates", f"{lat:.4f}°N, {lon:.4f}°E")

        st.divider()
        st.markdown("### Configure Your Crop")
        st.selectbox(
            "💡 Top Crops for This Country (FAOSTAT-ranked):",
            options=crops,
            index=crops.index(st.session_state["selected_crop"]),
            key="selected_crop",
        )
        st.date_input(
            "Expected Planting Date",
            value=st.session_state["planting_date"],
            key="planting_date",
        )

    st.divider()
    col_back, _, col_next = st.columns([1, 4, 1])
    if col_back.button("← Back", use_container_width=True):
        st.session_state["page"] = 0
        st.rerun()
    if col_next.button("Next →", type="primary", use_container_width=True):
        st.session_state["page"] = 2
        st.rerun()
