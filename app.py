import datetime
import streamlit as st
from core.data_fetcher import DEFAULT_LAT, DEFAULT_LON, REGIONAL_CROP_DATABASE, determine_region
from views.map_page import render as render_map
from views.crop_page import render as render_crop
from views.soil_page import render as render_soil
from views.schedule_page import render as render_schedule

st.set_page_config(page_title="IrriTool | Regional Precision Irrigation", layout="wide")
st.title("IrriTool")
st.subheader("Localized Dynamic Precision Irrigation Scheduler")


# ── Session state ─────────────────────────────────────────────────────────────

_DEFAULTS = {
    "page":          0,
    "max_page":      0,
    "map_center":    [DEFAULT_LAT, DEFAULT_LON],
    "selected_crop": None,
    "planting_date": datetime.date(2026, 5, 1),
    "bf_result":     None,
    "bf_result_key": None,
    "climate_data":  None,
    "climate_key":   None,
    "faostat_crops": None,
    "faostat_key":   None,
    "country_name":  "",
    "soil_type":     "Loam",
    "soil_fc":       31.0,
    "soil_pwp":      14.0,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

_lat_raw = st.session_state.get("coord_lat")
_lon_raw = st.session_state.get("coord_lon")
_lat = _lat_raw if _lat_raw is not None else DEFAULT_LAT
_lon = _lon_raw if _lon_raw is not None else DEFAULT_LON
active_region = determine_region(_lat, _lon)
suggested_crops = REGIONAL_CROP_DATABASE[active_region]

if not st.session_state.get("selected_crop"):
    st.session_state["selected_crop"] = suggested_crops[0]


# ── Step indicator ────────────────────────────────────────────────────────────

STEPS = ["Select Location", "Choose Crop", "Choose Soil", "Irrigation Schedule"]
page = st.session_state["page"]
if page > st.session_state["max_page"]:
    st.session_state["max_page"] = page
max_reached = st.session_state["max_page"]


def _render_steps(current, max_reached):
    for i, (col, label) in enumerate(zip(st.columns(4), STEPS)):
        if i == current:
            col.markdown(
                f"<div style='text-align:center;padding:6px 8px;background:#e8f0fe;"
                f"color:#0055cc;font-weight:700;border-radius:6px'>● {label}</div>",
                unsafe_allow_html=True,
            )
        elif i <= max_reached:
            if col.button(label, key=f"tab_{i}", width='stretch'):
                st.session_state["_coord_lat_saved"]     = st.session_state.get("coord_lat") or st.session_state.get("_coord_lat_saved")
                st.session_state["_coord_lon_saved"]     = st.session_state.get("coord_lon") or st.session_state.get("_coord_lon_saved")
                st.session_state["_selected_crop_saved"] = st.session_state.get("selected_crop") or st.session_state.get("_selected_crop_saved")
                st.session_state["_planting_date_saved"] = st.session_state.get("planting_date") or st.session_state.get("_planting_date_saved")
                st.session_state["_soil_type_saved"]     = st.session_state.get("soil_type") or st.session_state.get("_soil_type_saved")
                st.session_state["_soil_fc_saved"]       = st.session_state.get("soil_fc") or st.session_state.get("_soil_fc_saved")
                st.session_state["_soil_pwp_saved"]      = st.session_state.get("soil_pwp") or st.session_state.get("_soil_pwp_saved")
                st.session_state["page"] = i
                st.rerun()
        else:
            col.markdown(
                f"<div style='text-align:center;padding:6px 8px;color:#aaa'>{label}</div>",
                unsafe_allow_html=True,
            )

_render_steps(page, max_reached)
st.divider()

# ── Routing ───────────────────────────────────────────────────────────────────

if page == 0:
    render_map(active_region, suggested_crops)
elif page == 1:
    render_crop(active_region, suggested_crops)
elif page == 2:
    render_soil(active_region)
elif page == 3:
    render_schedule(active_region)
