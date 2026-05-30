import json
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from core.data_fetcher import REGIONAL_CROP_DATABASE, determine_region

_COMPONENT_DIR = Path(__file__).parent.parent / "components" / "plotly_globe"
_globe_component = components.declare_component("plotly_globe", path=str(_COMPONENT_DIR))


@st.cache_data
def _grid() -> tuple[list[float], list[float]]:
    lats, lons = [], []
    for lat in range(-85, 86, 5):
        for lon in range(-175, 181, 5):
            lats.append(float(lat))
            lons.append(float(lon))
    return lats, lons


def _make_globe(marker_lat: float, marker_lon: float) -> go.Figure:
    grid_lats, grid_lons = _grid()
    fig = go.Figure()

    # Click surface — nearly invisible markers tile the globe so any click
    # registers as a plotly_click with exact lat/lon on the trace point.
    fig.add_trace(go.Scattergeo(
        lat=grid_lats, lon=grid_lons,
        mode="markers",
        marker=dict(size=20, color="rgba(0,0,0,0.008)", line=dict(width=0)),
        hoverinfo="none",
        showlegend=False,
    ))

    # Visible pin.
    fig.add_trace(go.Scattergeo(
        lat=[marker_lat], lon=[marker_lon],
        mode="markers",
        marker=dict(size=11, color="#e84040", line=dict(color="white", width=2)),
        hoverinfo="none",
        showlegend=False,
    ))

    fig.update_geos(
        projection_type="orthographic",
        showland=True,       landcolor="#4a8f3f",
        showocean=True,      oceancolor="#1a6fa8",
        showcoastlines=True, coastlinecolor="#2d5a27",
        showcountries=True,  countrycolor="#3a7a35",
        showlakes=True,      lakecolor="#1a6fa8",
        showrivers=False,
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
        fitbounds=False,
    )

    fig.update_layout(
        height=700,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def render(active_region, suggested_crops):
    if "coord_lat" not in st.session_state:
        st.session_state["coord_lat"] = float(st.session_state["map_center"][0])
    if "coord_lon" not in st.session_state:
        st.session_state["coord_lon"] = float(st.session_state["map_center"][1])

    coord_lat = st.session_state["coord_lat"]
    coord_lon = st.session_state["coord_lon"]
    if [coord_lat, coord_lon] != st.session_state["map_center"]:
        st.session_state["map_center"] = [coord_lat, coord_lon]
        active_region = determine_region(coord_lat, coord_lon)
        suggested_crops = REGIONAL_CROP_DATABASE[active_region]
        if st.session_state["selected_crop"] not in suggested_crops:
            st.session_state["selected_crop"] = suggested_crops[0]

    lat, lon = st.session_state["map_center"]
    col_globe, col_panel = st.columns([3, 1])
    # to_json() → json.loads() strips numpy types that break component serialization.
    fig_dict = json.loads(_make_globe(lat, lon).to_json())

    with col_globe:
        clicked = _globe_component(
            figure=fig_dict,
            height=950,
            key="globe",
            default=None,
        )

    # Component returns {lat, lon, ts} from Plotly's internal projection invert.
    if clicked:
        new_lat = clicked.get("lat")
        new_lon = clicked.get("lon")
        if new_lat is not None and new_lon is not None:
            new_lat = round(float(new_lat), 4)
            new_lon = round(float(new_lon), 4)
            if [new_lat, new_lon] != [st.session_state["coord_lat"], st.session_state["coord_lon"]]:
                st.session_state["coord_lat"] = new_lat
                st.session_state["coord_lon"] = new_lon
                region = determine_region(new_lat, new_lon)
                crops = REGIONAL_CROP_DATABASE[region]
                if st.session_state["selected_crop"] not in crops:
                    st.session_state["selected_crop"] = crops[0]
                st.rerun()

    with col_panel:
        st.markdown("### Selected Location")
        st.number_input("Latitude",  min_value=-90.0,  max_value=90.0,
                        step=0.0001, format="%.4f", key="coord_lat")
        st.number_input("Longitude", min_value=-180.0, max_value=180.0,
                        step=0.0001, format="%.4f", key="coord_lon")
        st.info(f"Region: **{active_region}**")

        st.divider()
        if st.button("Next →", type="primary", use_container_width=True):
            st.session_state["page"] = 1
            st.rerun()
