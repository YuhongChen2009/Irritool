import numpy as np
from .data_fetcher import CROP_PARAMS

L_PER_MM_PER_ACRE = 4047.0
TRAD_EVENTS_YR = 28
TRAD_DOSE_MM = 25


def _effective_precip(precip):
    """FAO/USDA SCS effective rainfall: reduces monthly totals for runoff and deep percolation.
    Pe = 0.6P - 10  (P ≤ 70 mm);  Pe = 0.8P - 24  (P > 70 mm), floored at 0.
    """
    result = []
    for p in precip:
        pe = 0.6 * p - 10.0 if p <= 70.0 else 0.8 * p - 24.0
        result.append(max(0.0, pe))
    return result


def _simulate(p, precip, et0, trigger, season_start):
    dose_vwc = p["dose_mm"] / p["root_mm"] * 100
    vwc = p["fc"]
    events = 0
    stress = 0
    for i in range(len(p["kc"])):
        m = (season_start - 1 + i) % 12
        etc_vwc = et0[m] * p["kc"][i] / p["root_mm"] * 100
        prec_vwc = precip[m] / p["root_mm"] * 100
        vwc = vwc + prec_vwc - etc_vwc
        while vwc < trigger:
            vwc += dose_vwc
            events += 1
        vwc = min(vwc, p["fc"])
        if vwc < p["stress_buffer"]:
            stress += 1
    return events, stress


def _compute_phases(p, precip, et0, trigger, season_start, raw_precip=None):
    # precip: effective rainfall used in water balance
    # raw_precip: actual monthly totals shown in the phase table
    if raw_precip is None:
        raw_precip = precip
    n = len(p["kc"])
    third = n // 3
    dose_vwc = p["dose_mm"] / p["root_mm"] * 100
    vwc = p["fc"]
    phases = []

    slices = [range(0, third), range(third, 2 * third), range(2 * third, n)]
    names  = ["Initial (Emergence)", "Mid-Season (Peak)", "Late (Maturity)"]

    for ph_range, ph_name in zip(slices, names):
        ph_events = 0
        ph_precip = 0
        for i in ph_range:
            m = (season_start - 1 + i) % 12
            etc_vwc = et0[m] * p["kc"][i] / p["root_mm"] * 100
            prec_vwc = precip[m] / p["root_mm"] * 100
            ph_precip += raw_precip[m]
            vwc = vwc + prec_vwc - etc_vwc
            while vwc < trigger:
                vwc += dose_vwc
                ph_events += 1
            vwc = min(vwc, p["fc"])

        bf_mm = ph_events * p["dose_mm"]
        trad_mm = len(list(ph_range)) / n * TRAD_EVENTS_YR * TRAD_DOSE_MM
        saved_pct = round((1 - bf_mm / trad_mm) * 100, 1) if trad_mm > 0 else 100.0
        phases.append({
            "Phase":            ph_name,
            "Phase Precip (mm)": int(ph_precip),
            "Traditional (mm)": int(trad_mm),
            "ByteForce (mm)":   bf_mm,
            "Water Saved (%)":  f"{saved_pct}%",
        })

    return phases


def run_calc(crop_name, precip, et0, planting_date, soil_fc=None, soil_pwp=None):
    p = dict(CROP_PARAMS.get(crop_name) or {})
    if not p:
        return None

    if soil_fc is not None or soil_pwp is not None:
        orig_fc  = p["fc"]
        orig_pwp = p["pwp"]
        if soil_fc  is not None: p["fc"]  = soil_fc
        if soil_pwp is not None: p["pwp"] = soil_pwp
        if orig_fc > orig_pwp:
            ratio = (p["stress_buffer"] - orig_pwp) / (orig_fc - orig_pwp)
            p["stress_buffer"] = round(
                max(p["pwp"] + 0.5, min(p["fc"] - 1.0,
                    p["pwp"] + ratio * (p["fc"] - p["pwp"]))), 1)

    season_start = planting_date.month
    eff_precip = _effective_precip(precip)

    best_trigger, best_events, best_stress = None, 9999, 9999
    for t in np.arange(p["pwp"] + 2.0, p["fc"] - 1.0, 0.5):
        ev, sx = _simulate(p, eff_precip, et0, t, season_start)
        if sx < best_stress or (sx == best_stress and ev < best_events):
            best_trigger, best_events, best_stress = float(t), ev, sx

    # np.arange is empty when fc - pwp <= 3.0; no valid trigger exists.
    if best_trigger is None:
        return None

    print(f"[Sim] {crop_name} | trigger={best_trigger} events={best_events} stress={best_stress} "
          f"fc={p['fc']} pwp={p['pwp']} buf={p['stress_buffer']}")

    trad_water = TRAD_EVENTS_YR * TRAD_DOSE_MM * L_PER_MM_PER_ACRE
    bf_water   = best_events * p["dose_mm"] * L_PER_MM_PER_ACRE
    saved      = max(0, trad_water - bf_water)
    reduction  = round(max(0.0, (1 - best_events / TRAD_EVENTS_YR) * 100), 1)

    return dict(
        trigger=round(best_trigger, 1),
        bf_events_yr=best_events,
        trad_events_yr=TRAD_EVENTS_YR,
        reduction_pct=reduction,
        bf_water_L=int(bf_water),
        trad_water_L=int(trad_water),
        saved_L=int(saved),
        phases=_compute_phases(p, eff_precip, et0, best_trigger, season_start, raw_precip=precip),
        kc=p["kc"],
        fc=p["fc"], pwp=p["pwp"],
        stress_buffer=p["stress_buffer"],
        dose_mm=p["dose_mm"],
        root_mm=p["root_mm"],
        paper_validated=p.get("paper_validated", False),
        paper_trigger=p.get("paper_trigger"),
    )
