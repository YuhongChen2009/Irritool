import streamlit as st
import folium
from folium import Element
from streamlit_folium import st_folium
from core.data_fetcher import DEFAULT_LAT, DEFAULT_LON, REGIONAL_CROP_DATABASE, determine_region

_SIZE   = 700
_RADIUS = _SIZE // 2  # 350

# All globe visuals live inside the iframe — no unreliable external CSS selectors.
#
# Instead of clip-path (which requires body to have computed height, but Leaflet
# fills the viewport with position:absolute children so body height = 0), we use
# a body::after overlay with a radial-gradient that:
#   • is transparent inside the circle  → map shows through
#   • fades to the dark background outside → corners masked
#   • adds a subtle blue ring at the edge  → atmospheric glow
# pointer-events:none means the overlay never blocks map clicks.
_GLOBE_CSS = f"""
<style>
html, body {{
    height: 100%;
    margin: 0;
    padding: 0;
    background: #0e1f3d;
}}
body::after {{
    content: '';
    position: fixed;
    inset: 0;
    background: radial-gradient(
        circle at {_RADIUS}px {_RADIUS}px,
        transparent           {_RADIUS - 6}px,
        rgba(80,150,255,0.55) {_RADIUS - 4}px,
        rgba(40,100,255,0.20) {_RADIUS + 6}px,
        #0e1f3d               {_RADIUS + 8}px
    );
    pointer-events: none;
    z-index: 10000;
}}
</style>
"""


def _make_map():
    m = folium.Map(
        location=[DEFAULT_LAT, DEFAULT_LON],
        zoom_start=2,
        tiles=None,
        zoom_control=False,
        attributionControl=False,
    )
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        attr="CartoDB",
        subdomains="abcd",
        max_zoom=19,
        control=False,
    ).add_to(m)
    # Inject via .html (not .header) — st_folium passes them as separate args
    # to the component; only .html content ends up in the iframe body.
    m.get_root().html.add_child(Element(_GLOBE_CSS))
    return m


def render(active_region, suggested_crops):
    _, col, _ = st.columns([1, 3, 1])
    with col:
        map_data = st_folium(
            _make_map(),
            width=_SIZE,
            height=_SIZE,
            returned_objects=["last_clicked"],
            center=st.session_state["map_center"],
            key="folium_globe",   # new key — avoids stale state from old Plotly component
        )

    if map_data and map_data.get("last_clicked") is not None:
        lc = map_data["last_clicked"]
        new_lat, new_lon = lc["lat"], lc["lng"]
        if [new_lat, new_lon] != st.session_state["map_center"]:
            st.session_state["map_center"] = [new_lat, new_lon]
            active_region = determine_region(new_lat, new_lon)
            suggested_crops = REGIONAL_CROP_DATABASE[active_region]
            if st.session_state["selected_crop"] not in suggested_crops:
                st.session_state["selected_crop"] = suggested_crops[0]

    col_status, col_nav = st.columns([4, 1])
    with col_status:
        lat, lon = st.session_state["map_center"]
        if map_data and map_data.get("last_clicked"):
            st.success(f"📍 **{active_region}** — {lat:.4f}°N, {lon:.4f}°E")
        else:
            st.info("Click anywhere on the globe to select your field location.")
    with col_nav:
        st.write("")
        if st.button("Next →", type="primary", use_container_width=True):
            st.session_state["page"] = 1
            st.rerun()
