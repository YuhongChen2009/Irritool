import streamlit as st
from core.data_fetcher import fetch_top_crops, fetch_country_name, REGIONAL_CROP_DATABASE


def render(active_region, suggested_crops):
    _lat_raw = st.session_state.get("coord_lat")
    _lon_raw = st.session_state.get("coord_lon")
    lat = _lat_raw if _lat_raw is not None else 0.0
    lon = _lon_raw if _lon_raw is not None else 0.0
    faostat_key = (round(lat, 2), round(lon, 2))

    if st.session_state.get("faostat_key") != faostat_key:
        with st.spinner("Fetching crop data from FAOSTAT..."):
            country_name, crops, data_year = fetch_top_crops(lat, lon)
            # If FAOSTAT fell back to a region name, get the real country from Nominatim
            if country_name in REGIONAL_CROP_DATABASE:
                country_name = (fetch_country_name(lat, lon)
                                or st.session_state.get("selected_country")
                                or country_name)
            st.session_state["faostat_key"]       = faostat_key
            st.session_state["faostat_crops"]     = crops
            st.session_state["country_name"]      = country_name
            st.session_state["faostat_data_year"] = data_year
            # Always default to the #1 ranked crop on a new fetch
            st.session_state["selected_crop"] = crops[0]
    else:
        crops        = st.session_state["faostat_crops"]
        _fao_name = st.session_state.get("country_name", "")
        _is_region = _fao_name in REGIONAL_CROP_DATABASE
        country_name = (st.session_state.get("selected_country")
                        if _is_region or not _fao_name
                        else _fao_name) or active_region
        data_year    = st.session_state.get("faostat_data_year")

    if st.session_state["selected_crop"] not in crops:
        st.session_state["selected_crop"] = crops[0]

    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown("### Your Selected Location")
        ma, mb = st.columns(2)
        ma.metric("Country", country_name)
        mb.metric("Coordinates", f"{lat:.4f}°N, {lon:.4f}°E")
        mc, md = st.columns(2)
        mc.metric("Data Source", "FAOSTAT")
        md.metric("Data Year", str(data_year) if data_year else "Regional defaults")

        st.divider()
        st.markdown("### Configure Your Crop")
        current = st.session_state["selected_crop"]
        st.selectbox(
            "💡 Top Crops for This Country (FAOSTAT-ranked):",
            options=crops,
            format_func=lambda c: f"{crops.index(c) + 1}. {c}",
            index=crops.index(current) if current in crops else 0,
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
