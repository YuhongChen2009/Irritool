from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from core.data_fetcher import REGIONAL_CROP_DATABASE, determine_region, fetch_country_name

_leaflet = components.declare_component(
    "leaflet_map",
    path=str(Path(__file__).parent.parent / "components" / "leaflet_map"),
)

_TILE_URLS = {
    "Default (local languages)": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    "English":                   "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
}


def render(active_region, suggested_crops):
    # coord_lat/lon are widget-keyed and get cleared when the map page unmounts.
    # _coord_*_saved are plain user state that survive page navigation.
    # Both default to None — no location is selected until the user clicks or types.
    if st.session_state.get("coord_lat") is None:
        st.session_state["coord_lat"] = st.session_state.get("_coord_lat_saved")
    if st.session_state.get("coord_lon") is None:
        st.session_state["coord_lon"] = st.session_state.get("_coord_lon_saved")
    if "last_click_ts" not in st.session_state:
        st.session_state["last_click_ts"] = 0
    if "has_marker" not in st.session_state:
        st.session_state["has_marker"] = False
    if "map_tile_choice" not in st.session_state:
        st.session_state["map_tile_choice"] = "Default (local languages)"

    coord_lat = st.session_state["coord_lat"]
    coord_lon = st.session_state["coord_lon"]
    has_location = coord_lat is not None and coord_lon is not None

    if has_location:
        active_region = determine_region(coord_lat, coord_lon)
        suggested_crops = REGIONAL_CROP_DATABASE[active_region]
        if st.session_state["selected_crop"] not in suggested_crops:
            st.session_state["selected_crop"] = suggested_crops[0]

    # Visual center for the map when no location is selected yet
    map_lat = coord_lat if has_location else 25.0
    map_lon = coord_lon if has_location else 0.0

    col_map, col_panel = st.columns([3.5, 1])

    tile_url = _TILE_URLS[st.session_state["map_tile_choice"]]

    with col_map:
        result = _leaflet(
            lat=map_lat,
            lon=map_lon,
            height=1000,
            init_zoom=3,
            has_marker=st.session_state["has_marker"],
            tile_url=tile_url,
            default=None,
            key="leaflet_map",
        )

    # Timestamp guard: only process genuinely new clicks, not stale values from old reruns
    if result and result.get("ts", 0) > st.session_state["last_click_ts"]:
        st.session_state["last_click_ts"] = result["ts"]
        new_lat = round(float(result["lat"]), 4)
        new_lon = round(float(result["lon"]), 4)
        if not has_location or [new_lat, new_lon] != [coord_lat, coord_lon]:
            country = fetch_country_name(new_lat, new_lon)
            st.session_state["coord_lat"] = new_lat
            st.session_state["coord_lon"] = new_lon
            st.session_state["has_marker"] = True
            st.session_state["selected_country"] = country
            st.session_state["is_water"] = (country == "Water")
            if country != "Water":
                region = determine_region(new_lat, new_lon)
                crops = REGIONAL_CROP_DATABASE[region]
                if st.session_state["selected_crop"] not in crops:
                    st.session_state["selected_crop"] = crops[0]
            st.rerun()

    is_water = st.session_state.get("is_water", False)

    with col_panel:
        st.markdown("### Selected Location")

        if has_location:
            prev_lat, prev_lon = coord_lat, coord_lon
            st.number_input("Latitude",  min_value=-90.0,  max_value=90.0,
                            step=0.0001, format="%.4f", key="coord_lat")
            st.number_input("Longitude", min_value=-180.0, max_value=180.0,
                            step=0.0001, format="%.4f", key="coord_lon")
            if (st.session_state["coord_lat"] != prev_lat or
                    st.session_state["coord_lon"] != prev_lon):
                st.session_state["has_marker"] = True
            if is_water:
                st.warning("🌊 **Water** — please select a land area.")
            else:
                location_label = st.session_state.get("selected_country") or active_region
                st.info(f"Location: **{location_label}**")
        else:
            st.info("📍 Click on the map to select a location.")

        _choices = list(_TILE_URLS.keys())
        _selected = st.selectbox("Map labels", _choices,
                                 index=_choices.index(st.session_state["map_tile_choice"]))
        st.session_state["map_tile_choice"] = _selected
        st.divider()
        if st.button("Next →", type="primary", use_container_width=True):
            if not has_location:
                st.toast("Please select a location first.", icon="⚠️")
            elif is_water:
                st.toast("Please select a land area, not water.", icon="🌊")
            else:
                st.session_state["_coord_lat_saved"] = coord_lat
                st.session_state["_coord_lon_saved"] = coord_lon
                st.session_state["page"] = 1
                st.rerun()
