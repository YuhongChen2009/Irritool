import datetime
import streamlit as st
from core.data_fetcher import fetch_top_crops, fetch_country_name, REGIONAL_CROP_DATABASE, CROP_SCIENTIFIC


def render(active_region, suggested_crops):
    # Use saved coords — coord_lat/lon are map-page widget keys, None when map is inactive
    lat = st.session_state.get("_coord_lat_saved") or 0.0
    lon = st.session_state.get("_coord_lon_saved") or 0.0
    faostat_key = (round(lat, 2), round(lon, 2))

    if st.session_state.get("faostat_key") != faostat_key:
        with st.spinner("Fetching crop data from FAOSTAT..."):
            country_name, crops, data_year = fetch_top_crops(lat, lon)
            if country_name in REGIONAL_CROP_DATABASE:
                country_name = (fetch_country_name(lat, lon)
                                or st.session_state.get("selected_country")
                                or country_name)
            st.session_state["faostat_key"]       = faostat_key
            st.session_state["faostat_crops"]     = crops
            st.session_state["country_name"]      = country_name
            st.session_state["faostat_data_year"] = data_year
            st.session_state["selected_crop"]     = crops[0]
    else:
        crops      = st.session_state["faostat_crops"]
        _fao_name  = st.session_state.get("country_name", "")
        _is_region = _fao_name in REGIONAL_CROP_DATABASE
        country_name = (st.session_state.get("selected_country")
                        if _is_region or not _fao_name
                        else _fao_name) or active_region
        data_year = st.session_state.get("faostat_data_year")

    current_crop = st.session_state.get("selected_crop")
    if current_crop not in crops:
        current_crop = crops[0]

    planting_date = st.session_state.get("planting_date") or datetime.date(2026, 5, 1)

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

        selected_crop = st.selectbox(
            "💡 Top Crops for This Country:",
            options=crops,
            format_func=lambda c: f"{crops.index(c) + 1}. {CROP_SCIENTIFIC.get(c, c)}",
            index=crops.index(current_crop) if current_crop in crops else 0,
        )
        # Write back immediately — no key= so session state is never cleared by Streamlit
        st.session_state["selected_crop"] = selected_crop

        st.caption("Ranked by annual production volume (tonnes) · Source: FAOSTAT QCL")

        new_date = st.date_input("Expected Planting Date", value=planting_date)
        st.session_state["planting_date"] = new_date

    st.divider()
    col_back, _, col_next = st.columns([1, 4, 1])
    if col_back.button("← Back", width='stretch'):
        st.session_state["page"] = 0
        st.rerun()
    if col_next.button("Next →", type="primary", width='stretch'):
        st.session_state["page"] = 2
        st.rerun()
