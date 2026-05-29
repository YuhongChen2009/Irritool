import datetime
import streamlit as st
from core.simulator import run_calc
from core.data_fetcher import fetch_climate


def render(active_region):
    crop = st.session_state["selected_crop"]
    planting_date = st.session_state["planting_date"]
    lat, lon = st.session_state["map_center"]

    climate_key = (round(lat, 2), round(lon, 2))
    if st.session_state.get("climate_key") != climate_key:
        with st.spinner("Fetching climate data from NASA POWER..."):
            precip, et0 = fetch_climate(lat, lon)
            st.session_state["climate_key"]  = climate_key
            st.session_state["climate_data"] = (precip, et0)
    else:
        precip, et0 = st.session_state["climate_data"]

    result_key = (crop, climate_key, str(planting_date))
    if st.session_state["bf_result_key"] != result_key:
        with st.spinner("Running hydrological grid search..."):
            st.session_state["bf_result"]     = run_calc(crop, precip, et0, planting_date)
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
                f"output below uses your region's climatological norms."
            )
        else:
            st.info(
                "FAO-56 crop coefficients + regional climatological norms. "
                "For maximum accuracy, supply site-specific weather data (e.g. NASA POWER API)."
            )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Optimal VWC Trigger",   f"{result['trigger']}%")
        c2.metric("Calculated Events / Yr", result["bf_events_yr"],
                  delta=f"{result['trad_events_yr'] - result['bf_events_yr']} fewer",
                  delta_color="inverse")
        c3.metric("Frequency Reduction",   f"{result['reduction_pct']}%")
        c4.metric("Annual Water Saved",    f"{result['saved_L']:,} L/acre")

        st.divider()
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### Phase-Specific Water Allocation")
            st.caption("Irrigation depth (mm) vs. OMAFRA fixed-calendar baseline.")
            st.dataframe(result["phases"], use_container_width=True, hide_index=True)

            st.markdown("#### Calculated vs. Traditional Baseline")
            st.dataframe([
                {"Metric": "Events / Year",         "Traditional": result["trad_events_yr"],
                 "Irritool": result["bf_events_yr"],
                 "Improvement": f"{result['reduction_pct']}% fewer"},
                {"Metric": "Water / Year (L/acre)", "Traditional": f"{result['trad_water_L']:,}",
                 "Irritool": f"{result['bf_water_L']:,}",
                 "Improvement": f"{result['saved_L']:,} L saved"},
            ], use_container_width=True, hide_index=True)

        with col_b:
            st.markdown("#### Crop Coefficients (Kc) — FAO-56")
            month_names = [
                datetime.date(2000, ((planting_date.month - 1 + i) % 12) + 1, 1).strftime("%b")
                for i in range(len(result["kc"]))
            ]
            st.dataframe(
                [{"Month": mn, "Kc": kc} for mn, kc in zip(month_names, result["kc"])],
                use_container_width=True, hide_index=True,
            )

            st.markdown("#### Soil-Water Parameters")
            st.dataframe([
                {"Parameter": "Field Capacity (FC)",     "Value": f"{result['fc']}%"},
                {"Parameter": "Permanent Wilting Point", "Value": f"{result['pwp']}%"},
                {"Parameter": "Stress Safety Buffer",    "Value": f"{result['stress_buffer']}%"},
                {"Parameter": "Root Zone Depth",         "Value": f"{result['root_mm']} mm"},
                {"Parameter": "Irrigation Dose",         "Value": f"{result['dose_mm']} mm/event"},
                {"Parameter": "VWC Trigger (optimised)", "Value": f"{result['trigger']}%"},
            ], use_container_width=True, hide_index=True)

    st.divider()
    col_back, _ = st.columns([1, 5])
    if col_back.button("← Back", use_container_width=True):
        st.session_state["page"] = 1
        st.rerun()
