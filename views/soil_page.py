import streamlit as st

SOIL_PRESETS = {
    "Sand":            {"fc": 10.0, "pwp": 4.0},
    "Loamy Sand":      {"fc": 14.0, "pwp": 6.0},
    "Sandy Loam":      {"fc": 20.0, "pwp": 9.0},
    "Loam":            {"fc": 31.0, "pwp": 14.0},
    "Silt Loam":       {"fc": 33.0, "pwp": 13.0},
    "Silt":            {"fc": 33.0, "pwp": 8.0},
    "Sandy Clay Loam": {"fc": 27.0, "pwp": 17.0},
    "Clay Loam":       {"fc": 36.0, "pwp": 20.0},
    "Silty Clay Loam": {"fc": 38.0, "pwp": 22.0},
    "Sandy Clay":      {"fc": 35.0, "pwp": 22.0},
    "Silty Clay":      {"fc": 41.0, "pwp": 27.0},
    "Clay":            {"fc": 45.0, "pwp": 30.0},
    "Custom":          None,
}

_REFERENCE_TABLE = [
    {"Soil Type": "Sand",            "Field Capacity (%)": 10, "Wilting Point (%)": 4,  "AWC (mm/m)": 60,  "Common Regions": "Sahara, Arabian Peninsula, Australian Outback"},
    {"Soil Type": "Loamy Sand",      "Field Capacity (%)": 14, "Wilting Point (%)": 6,  "AWC (mm/m)": 80,  "Common Regions": "Coastal dunes, semi-arid grasslands"},
    {"Soil Type": "Sandy Loam",      "Field Capacity (%)": 20, "Wilting Point (%)": 9,  "AWC (mm/m)": 110, "Common Regions": "US Midwest, Mediterranean, South Africa"},
    {"Soil Type": "Loam",            "Field Capacity (%)": 31, "Wilting Point (%)": 14, "AWC (mm/m)": 170, "Common Regions": "US Corn Belt, Northern Europe, Argentina Pampas"},
    {"Soil Type": "Silt Loam",       "Field Capacity (%)": 33, "Wilting Point (%)": 13, "AWC (mm/m)": 200, "Common Regions": "Mississippi Valley, Central China, Ukraine"},
    {"Soil Type": "Silt",            "Field Capacity (%)": 33, "Wilting Point (%)": 8,  "AWC (mm/m)": 250, "Common Regions": "River deltas, floodplains (Ganges, Nile, Mekong)"},
    {"Soil Type": "Sandy Clay Loam", "Field Capacity (%)": 27, "Wilting Point (%)": 17, "AWC (mm/m)": 100, "Common Regions": "Sub-Saharan Africa, SE Asia uplands"},
    {"Soil Type": "Clay Loam",       "Field Capacity (%)": 36, "Wilting Point (%)": 20, "AWC (mm/m)": 160, "Common Regions": "Ontario, UK, Northern India"},
    {"Soil Type": "Silty Clay Loam", "Field Capacity (%)": 38, "Wilting Point (%)": 22, "AWC (mm/m)": 160, "Common Regions": "Pacific Northwest, Central Europe, Korea"},
    {"Soil Type": "Sandy Clay",      "Field Capacity (%)": 35, "Wilting Point (%)": 22, "AWC (mm/m)": 130, "Common Regions": "Parts of Australia, Southern Africa"},
    {"Soil Type": "Silty Clay",      "Field Capacity (%)": 41, "Wilting Point (%)": 27, "AWC (mm/m)": 140, "Common Regions": "Southeast Asia rice paddies, Nile Delta"},
    {"Soil Type": "Clay",            "Field Capacity (%)": 45, "Wilting Point (%)": 30, "AWC (mm/m)": 150, "Common Regions": "Tropical Africa, South Asia, Vertisol regions"},
]

_CHOICES = list(SOIL_PRESETS.keys())


def render(active_region):
    # Read stable session state values (never cleared since no key= is used)
    current_type = st.session_state.get("soil_type") or "Loam"
    current_fc   = st.session_state.get("soil_fc")   or 31.0
    current_pwp  = st.session_state.get("soil_pwp")  or 14.0

    if current_type not in _CHOICES:
        current_type = "Loam"

    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown("### Choose Soil Type")

        selected_type = st.selectbox(
            "Soil texture class",
            options=_CHOICES,
            index=_CHOICES.index(current_type),
        )

        # Apply preset when the type changes; preserve custom values otherwise
        if selected_type != current_type and selected_type != "Custom":
            preset = SOIL_PRESETS[selected_type]
            current_fc  = preset["fc"]
            current_pwp = preset["pwp"]

        fc = st.number_input(
            "Field Capacity — FC (%)",
            min_value=1.0, max_value=70.0, step=0.5, format="%.1f",
            value=current_fc,
            help="Volumetric water content after gravity drainage (24–48 h).",
        )
        pwp = st.number_input(
            "Permanent Wilting Point — PWP (%)",
            min_value=1.0, max_value=50.0, step=0.5, format="%.1f",
            value=current_pwp,
            help="Minimum VWC at which plants can extract water.",
        )

        # Write back immediately — no key= so values persist across navigation
        st.session_state["soil_type"] = selected_type
        st.session_state["soil_fc"]   = fc
        st.session_state["soil_pwp"]  = pwp

        awc = round(fc - pwp, 1)
        if awc <= 3.0:
            st.error("Field Capacity must exceed Wilting Point by more than 3%. "
                     "Increase FC or decrease PWP.")
        else:
            st.info(f"Available Water Capacity: **{awc}%** ({awc * 10:.0f} mm/m root zone)")

    st.divider()
    st.markdown("#### Reference: Common Soil Types")
    st.caption("Source: FAO Irrigation & Drainage Paper 56 · USDA NRCS texture classes")
    st.dataframe(_REFERENCE_TABLE, hide_index=True, width='stretch')

    st.divider()
    col_back, _, col_next = st.columns([1, 4, 1])
    if col_back.button("← Back", width='stretch'):
        st.session_state["page"] = 1
        st.rerun()
    if col_next.button("Next →", type="primary", width='stretch'):
        if awc <= 3.0:
            st.toast("FC must exceed PWP by more than 3% before continuing.", icon="⚠️")
        else:
            st.session_state["page"] = 3
            st.rerun()
