import datetime
import streamlit as st
from core.simulator import run_calc
from core.data_fetcher import fetch_climate

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def render(active_region):
    crop = st.session_state.get("selected_crop") or st.session_state.get("_selected_crop_saved")
    planting_date = st.session_state.get("planting_date") or st.session_state.get("_planting_date_saved")
    lat = st.session_state.get("_coord_lat_saved") or 0.0
    lon = st.session_state.get("_coord_lon_saved") or 0.0

    # Version tag forces re-fetch when the ET0 calculation method changes.
    _CACHE_VER = "v3-T2M"
    climate_key = (round(lat, 2), round(lon, 2), _CACHE_VER)
    if st.session_state.get("climate_key") != climate_key:
        with st.spinner("Fetching climate data from NASA POWER..."):
            precip, et0, climate_source = fetch_climate(lat, lon)
            st.session_state["climate_key"]    = climate_key
            st.session_state["climate_data"]   = (precip, et0)
            st.session_state["climate_source"] = climate_source
    else:
        precip, et0 = st.session_state["climate_data"]
        climate_source = st.session_state.get("climate_source", "Unknown")

    soil_fc  = st.session_state.get("soil_fc",  31.0)
    soil_pwp = st.session_state.get("soil_pwp", 14.0)
    result_key = (crop, climate_key, str(planting_date), soil_fc, soil_pwp)
    if st.session_state["bf_result_key"] != result_key:
        with st.spinner("Running hydrological grid search..."):
            st.session_state["bf_result"]     = run_calc(crop, precip, et0, planting_date, soil_fc, soil_pwp)
            st.session_state["bf_result_key"] = result_key

    result = st.session_state["bf_result"]

    if result is None:
        st.error("No parameters found for this crop.")
    else:
        st.markdown(f"## Calculated Results — {crop}")
        location = st.session_state.get("country_name") or active_region
        st.caption(f"{location} · Planting: {planting_date.strftime('%B %d, %Y')}")

        if result["paper_validated"]:
            st.success(
                f"**Paper-validated.** Originally validated on 11 years (2014–2024) of "
                f"Ontario climate data. Paper-reported VWC trigger: **{result['paper_trigger']}%** — "
                f"output below uses your location's climatological norms."
            )

        if result["bf_events_yr"] == 0:
            st.info(
                "**0 irrigation events calculated.** Monthly average rainfall during this crop's "
                "growing season appears sufficient to meet water demand at this location. "
                "Note: this model uses monthly climate averages and cannot capture within-month "
                "dry spells — actual field irrigation may still be needed. "
                "If this is a dry-season crop, try changing the planting month. "
                "If ET₀ in the charts below appears near zero, there may be a data issue with this coordinate."
            )

        above_baseline = result["bf_events_yr"] > result["trad_events_yr"]
        if above_baseline:
            awc = round(result["fc"] - result["pwp"], 1)
            st.warning(
                f"**More events than the traditional baseline ({result['trad_events_yr']}).** "
                f"The selected soil has an AWC of only {awc}% ({awc * result['root_mm'] / 100:.0f} mm in a "
                f"{result['root_mm']} mm root zone) — too small to buffer this crop's water demand between "
                f"irrigations at this location. Go back and select a soil with higher AWC (e.g. Loam or Silt Loam), "
                f"or verify that the soil type matches the actual field conditions."
            )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Optimal VWC Trigger", f"{result['trigger']}%")
        c2.metric("Calculated Events / Yr", result["bf_events_yr"],
                  delta=result["bf_events_yr"] - result["trad_events_yr"],
                  delta_color="inverse")
        if above_baseline:
            c3.metric("Frequency Increase", f"{abs(result['reduction_pct'])}%")
            c4.metric("Extra Water Needed", f"{abs(result['saved_L']):,} L/acre")
        else:
            c3.metric("Frequency Reduction", f"{result['reduction_pct']}%")
            c4.metric("Annual Water Saved",  f"{result['saved_L']:,} L/acre")

        st.divider()
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### Phase-Specific Water Allocation")
            st.caption(f"Irrigation depth (mm) vs. traditional baseline ({result['trad_events_yr']} events/season, no rain credit).")
            st.dataframe(result["phases"], width='stretch', hide_index=True)

            if above_baseline:
                events_note = f"{abs(result['reduction_pct'])}% more"
                water_note  = f"{abs(result['saved_L']):,} L extra"
            else:
                events_note = f"{result['reduction_pct']}% fewer"
                water_note  = f"{result['saved_L']:,} L saved"

            st.markdown("#### Calculated vs. Traditional Baseline")
            st.dataframe([
                {"Metric": "Events / Year",         "Traditional": str(result["trad_events_yr"]),
                 "Irritool": str(result["bf_events_yr"]),
                 "Improvement": events_note},
                {"Metric": "Water / Year (L/acre)", "Traditional": f"{result['trad_water_L']:,}",
                 "Irritool": f"{result['bf_water_L']:,}",
                 "Improvement": water_note},
            ], width='stretch', hide_index=True)

        with col_b:
            st.markdown("#### Crop Coefficients (Kc) — FAO-56")
            month_names = [
                datetime.date(2000, ((planting_date.month - 1 + i) % 12) + 1, 1).strftime("%b")
                for i in range(len(result["kc"]))
            ]
            st.dataframe(
                [{"Month": mn, "Kc": kc} for mn, kc in zip(month_names, result["kc"])],
                width='stretch', hide_index=True,
            )

            st.markdown("#### Soil-Water Parameters")
            st.dataframe([
                {"Parameter": "Field Capacity (FC)",     "Value": f"{result['fc']}%"},
                {"Parameter": "Permanent Wilting Point", "Value": f"{result['pwp']}%"},
                {"Parameter": "Stress Safety Buffer",    "Value": f"{result['stress_buffer']}%"},
                {"Parameter": "Root Zone Depth",         "Value": f"{result['root_mm']} mm"},
                {"Parameter": "Irrigation Dose",         "Value": f"{result['dose_mm']} mm/event"},
                {"Parameter": "VWC Trigger (optimised)", "Value": f"{result['trigger']}%"},
            ], width='stretch', hide_index=True)

        # ── Climate data section ──────────────────────────────────────────────
        st.divider()
        if climate_source == "NASA POWER":
            st.success(f"**Climate data: {climate_source}** · 20-year climatological normals (2001–2020) · "
                       f"{lat:.2f}°N, {lon:.2f}°E · FAO effective rainfall applied in simulation")
        else:
            st.warning(f"**Climate data: {climate_source}** · NASA POWER unavailable — "
                       f"ET₀ estimated from extraterrestrial radiation at {lat:.2f}°N. "
                       f"Precipitation uses regional defaults. Results will be less accurate. "
                       f"FAO effective rainfall applied in simulation.")

        chart_data = {
            "Month":             _MONTHS,
            "Precipitation (mm)": precip,
            "ET₀ (mm)":          et0,
        }
        cl, cr = st.columns(2)
        with cl:
            st.markdown("#### Monthly Precipitation")
            st.bar_chart(
                data={m: p for m, p in zip(_MONTHS, precip)},
                x_label="Month", y_label="mm",
                color="#4a90d9",
            )
        with cr:
            st.markdown("#### Monthly Reference ET₀")
            st.bar_chart(
                data={m: e for m, e in zip(_MONTHS, et0)},
                x_label="Month", y_label="mm",
                color="#e8734a",
            )

        with st.expander("Monthly climate data table"):
            st.dataframe(
                [{"Month": m, "Precipitation (mm)": p, "ET₀ (mm)": e}
                 for m, p, e in zip(_MONTHS, precip, et0)],
                hide_index=True, width='stretch',
            )

    st.divider()
    col_back, _ = st.columns([1, 5])
    if col_back.button("← Back", width='stretch'):
        st.session_state["page"] = 2
        st.rerun()
