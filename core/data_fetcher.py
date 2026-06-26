import base64
import json
import math
import time
import requests
from pathlib import Path

with open(Path(__file__).parent.parent / "assets" / "crop_data.json") as _f:
    CROP_PARAMS = json.load(_f)

REGIONAL_PRECIP = {
    "North America":  [55,  48,  60,  75,  90,  92,  88,  82,  78,  68,  62,  58],
    "South America":  [155, 140, 115, 75,  45,  25,  20,  25,  50,  90,  125, 150],
    "Europe":         [47,  42,  52,  57,  68,  67,  63,  67,  62,  62,  57,  52],
    "Africa":         [32,  28,  48,  82,  105, 82,  52,  62,  82,  78,  42,  32],
    "Asia & Oceania": [52,  57,  82,  105, 135, 158, 162, 142, 112, 82,  62,  52],
    "Global Baseline":[65,  60,  70,  80,  90,  90,  85,  85,  80,  75,  65,  65],
}

REGIONAL_CROP_DATABASE = {
    "North America":  ["Field Corn (Zea mays)", "Soybeans", "Wheat", "Potatoes", "Tomatoes"],
    "South America":  ["Sugarcane", "Soybeans", "Field Corn (Zea mays)", "Rice", "Cassava"],
    "Asia & Oceania": ["Rice", "Wheat", "Sugarcane", "Potatoes", "Field Corn (Zea mays)"],
    "Europe":         ["Wheat", "Barley", "Potatoes", "Sugar Beets", "Tomatoes"],
    "Africa":         ["Cassava", "Yams", "Field Corn (Zea mays)", "Sorghum", "Rice"],
    "Global Baseline":["Field Corn (Zea mays)", "Rice", "Wheat", "Soybeans", "Potatoes"],
}

DEFAULT_LAT = 43.5400
DEFAULT_LON = -80.2500


_MONTH_KEYS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
_DAYS       = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_DOY        = [15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349]


def _ra(lat_deg, month_idx):
    """Extraterrestrial radiation (MJ/m²/day) via FAO-56 for any latitude."""
    lat = math.radians(lat_deg)
    dr    = 1 + 0.033 * math.cos(2 * math.pi / 365 * _DOY[month_idx])
    delta = 0.409 * math.sin(2 * math.pi / 365 * _DOY[month_idx] - 1.39)
    ws    = math.acos(max(-1.0, min(1.0, -math.tan(lat) * math.tan(delta))))
    return (24 * 60 / math.pi) * 0.0820 * dr * (
        ws * math.sin(lat) * math.sin(delta) +
        math.cos(lat) * math.cos(delta) * math.sin(ws)
    )


def _ra_et0(lat):
    """Estimate monthly ET0 (mm) from extraterrestrial radiation and latitude-based
    temperature normals. Used as a fallback when NASA POWER is unavailable.

    Temperature model (Tmean, Trange) derived from latitude only:
      - Annual mean ≈ 30 − 0.55·|lat|  (global lapse-rate approximation)
      - Seasonal amplitude ≈ 0.38·|lat| (larger swings at higher latitudes)
      - Peaks in July (N hemisphere) / January (S hemisphere)
      - Daily range ≈ 8 + 0.12·|lat|   (more continental away from tropics)
    """
    ann_mean  = max(-10.0, 30.0 - 0.55 * abs(lat))
    amplitude = abs(lat) * 0.38
    trange    = 8.0 + abs(lat) * 0.12
    peak_m    = 6 if lat >= 0 else 0   # July (index 6) for N, January (0) for S

    et0 = []
    for m in range(12):
        tmean     = ann_mean + amplitude * math.cos(2 * math.pi * (m - peak_m) / 12)
        # Rs ≈ 0.5 * Ra: Angström formula at ~50% average sunshine fraction.
        # Using raw Ra here inflates ET0 by ~2.5× in humid/temperate climates.
        rs        = 0.5 * _ra(lat, m)
        et0_daily = max(0.0, 0.0023 * rs * (tmean + 17.8) * trange ** 0.5)
        et0.append(round(et0_daily * _DAYS[m], 1))
    return et0


CROP_SCIENTIFIC = {
    "Field Corn (Zea mays)": "Field Corn (Zea mays)",
    "Soybeans":              "Soybeans (Glycine max)",
    "Wheat":                 "Wheat (Triticum aestivum)",
    "Potatoes":              "Potatoes (Solanum tuberosum)",
    "Tomatoes":              "Tomatoes (Solanum lycopersicum)",
    "Rice":                  "Rice (Oryza sativa)",
    "Sugarcane":             "Sugarcane (Saccharum officinarum)",
    "Cassava":               "Cassava (Manihot esculenta)",
    "Yams":                  "Yams (Dioscorea spp.)",
    "Sorghum":               "Sorghum (Sorghum bicolor)",
    "Sugar Beets":           "Sugar Beets (Beta vulgaris)",
    "Barley":                "Barley (Hordeum vulgare)",
}

# Maps FAOSTAT item names → internal crop names (covers old and new API name variants)
_FAOSTAT_TO_CROP = {
    "Maize (corn)":        "Field Corn (Zea mays)",
    "Maize":               "Field Corn (Zea mays)",
    "Corn":                "Field Corn (Zea mays)",
    "Soybeans":            "Soybeans",
    "Soya beans":          "Soybeans",
    "Soybean":             "Soybeans",
    "Wheat":               "Wheat",
    "Potatoes":            "Potatoes",
    "Potato":              "Potatoes",
    "Tomatoes":            "Tomatoes",
    "Tomato":              "Tomatoes",
    "Rice":                "Rice",
    "Rice, paddy":         "Rice",
    "Sugar cane":          "Sugarcane",
    "Sugar Cane":          "Sugarcane",
    "Sugarcane":           "Sugarcane",
    "Cassava, fresh":      "Cassava",
    "Cassava":             "Cassava",
    "Yams":                "Yams",
    "Yam":                 "Yams",
    "Sorghum":             "Sorghum",
    "Sugar beet":          "Sugar Beets",
    "Sugar beets":         "Sugar Beets",
    "Sugar Beet":          "Sugar Beets",
    "Barley":              "Barley",
}

# Module-level caches: country list fetched once, crop results cached per country
_faostat_area_cache: dict[str, str] = {}
_crop_cache: dict[str, tuple[str, list]] = {}


def _reverse_geocode(lat, lon):
    resp = requests.get(
        "https://nominatim.openstreetmap.org/reverse",
        params={"lat": lat, "lon": lon, "format": "json", "zoom": 3, "namedetails": 1},
        headers={"User-Agent": "IrriTool/1.0 (irrigation scheduling app)"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if "address" not in data:
        raise ValueError(f"No land address for ({lat}, {lon}) — ocean or unmapped area")
    addr = data["address"]
    iso2 = addr["country_code"].upper()
    nd = data.get("namedetails", {})
    local_name = nd.get("name") or addr.get("country", "")
    english_name = nd.get("name:en", "")
    return iso2, local_name, english_name


def _format_country(local, english):
    if english and english.lower() != local.lower():
        return f"{local} ({english})"
    return local or english


def fetch_country_name(lat, lon):
    """Returns the country name, or 'Water' for ocean/unmapped areas, or None on error."""
    try:
        _, local_name, english_name = _reverse_geocode(lat, lon)
        return _format_country(local_name, english_name)
    except ValueError:
        return "Water"
    except Exception:
        return None


_faostat_token: str = ""
_faostat_token_expiry: float = 0.0


def _jwt_expiry(token: str) -> float:
    """Decode the exp claim from a JWT without verifying the signature."""
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        return float(json.loads(base64.urlsafe_b64decode(payload_b64)).get("exp", 0))
    except Exception:
        return 0.0


def _faostat_login() -> str:
    try:
        import os, tomllib
        username, password = "", ""
        secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
        try:
            with open(secrets_path, "rb") as f:
                s = tomllib.load(f)
            username = s.get("FAOSTAT_USERNAME", "")
            password = s.get("FAOSTAT_PASSWORD", "")
        except FileNotFoundError:
            pass
        if not username:
            username = os.environ.get("FAOSTAT_USERNAME", "")
        if not password:
            password = os.environ.get("FAOSTAT_PASSWORD", "")
        if not username or not password:
            return ""
        resp = requests.post(
            "https://faostatservices.fao.org/api/v1/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        token = (data.get("AuthenticationResult") or {}).get("AccessToken") \
             or data.get("access_token") or data.get("AccessToken") or data.get("token", "")
        return token
    except Exception as e:
        print(f"[FAOSTAT] login failed: {e}")
        return ""


def _faostat_headers() -> dict:
    global _faostat_token, _faostat_token_expiry
    # Refresh if missing or expiring within 60 seconds
    if not _faostat_token or time.time() > _faostat_token_expiry - 60:
        _faostat_token = _faostat_login()
        _faostat_token_expiry = _jwt_expiry(_faostat_token) if _faostat_token else 0.0
    if _faostat_token:
        return {"Authorization": f"Bearer {_faostat_token}"}
    return {}


def _iso2_to_faostat(iso2):  # iso2 is the first element returned by _reverse_geocode
    if not _faostat_area_cache:
        resp = requests.get(
            "https://faostatservices.fao.org/api/v1/en/definitions/domain/QCL/area",
            params={"output_type": "objects"},
            headers=_faostat_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        for item in resp.json().get("data", []):
            code = item.get("ISO2 Code", "").upper()
            if code:
                _faostat_area_cache[code] = item["Country Code"]
    return _faostat_area_cache.get(iso2)


def fetch_top_crops(lat, lon):
    """Returns (country_name, crops, data_year) ranked by FAOSTAT production volume.
    data_year is None when falling back to regional defaults."""
    try:
        iso2, local_name, english_name = _reverse_geocode(lat, lon)
        country_name = _format_country(local_name, english_name)
        if iso2 in _crop_cache:
            return _crop_cache[iso2]

        fao_code = _iso2_to_faostat(iso2)
        if not fao_code:
            raise ValueError(f"No FAOSTAT code for {iso2}")

        rows = []
        data_year = None
        for year in (2025, 2024, 2023, 2022):
            try:
                resp = requests.get(
                    "https://faostatservices.fao.org/api/v1/en/data/QCL",
                    params={"area": fao_code, "element": "2510", "item": "QC>", "year": str(year), "output_type": "objects"},
                    headers=_faostat_headers(),
                    timeout=15,
                )
                resp.raise_for_status()
                body = resp.json()
                rows = body.get("data", [])
                if rows:
                    data_year = year
                    break
            except Exception:
                continue

        _AGG_SUFFIXES = (" primary", " total", "n.e.c.", ", total", ", primary")

        def _is_aggregate(name: str) -> bool:
            n = name.lower()
            return any(n.endswith(s) for s in _AGG_SUFFIXES)

        rows = [r for r in rows if not _is_aggregate(r.get("Item", ""))]
        rows = sorted(rows, key=lambda x: float(x.get("Value") or 0), reverse=True)

        print(f"\n[FAOSTAT] {iso2} ({country_name}) — year={data_year}, {len(rows)} rows (after aggregate filter)")
        for r in rows[:20]:
            print(f"  {r.get('Value'):>12}  {r.get('Item')}")

        crops = []
        for row in rows:
            internal = _FAOSTAT_TO_CROP.get(row["Item"])
            if internal and internal not in crops:
                crops.append(internal)
            if len(crops) == 5:
                break

        # Pad to 5 with regional defaults if FAOSTAT didn't cover enough
        for c in REGIONAL_CROP_DATABASE[determine_region(lat, lon)]:
            if len(crops) == 5:
                break
            if c not in crops:
                crops.append(c)

        _crop_cache[iso2] = (country_name, crops, data_year)
        return _crop_cache[iso2]

    except Exception:
        region = determine_region(lat, lon)
        return region, REGIONAL_CROP_DATABASE[region], None


def fetch_climate(lat, lon):
    """Fetch long-term monthly climate normals from NASA POWER for a coordinate.
    Returns (precip_mm, et0_mm, source).

    Two important unit / data corrections vs naive usage:
      1. ALLSKY_SFC_SW_DWN is in MJ/m²/day — do NOT multiply by 3.6.
      2. T2M_MAX/T2M_MIN in the climatology endpoint are all-time monthly extremes,
         not averages of daily max/min. Using them for td inflates ET0 ~2×.
         Instead fetch T2M (monthly mean) and estimate diurnal range from latitude.
    """
    # Typical daily temperature range estimated from latitude:
    # lower in humid tropics/coasts, higher in continental mid-latitudes.
    td_est = max(6.0, 15.0 - 0.1 * abs(lat))

    try:
        resp = requests.get(
            "https://power.larc.nasa.gov/api/temporal/climatology/point",
            params={
                "parameters": "PRECTOTCORR,T2M,ALLSKY_SFC_SW_DWN",
                "community":  "AG",
                "longitude":  round(lon, 4),
                "latitude":   round(lat, 4),
                "format":     "JSON",
            },
            timeout=15,
        )
        resp.raise_for_status()
        param = resp.json()["properties"]["parameter"]

        # NASA POWER uses -999 as a fill value for missing/invalid data.
        # Guard all three parameters so a flagged month doesn't silently corrupt results:
        #   PRECTOTCORR: clamp to 0 (negative rain is physically impossible)
        #   T2M:         substitute latitude-based temperature estimate
        #   ALLSKY_SFC_SW_DWN: substitute Ra × 0.5 (Angström estimate)
        _ann_mean  = max(-10.0, 30.0 - 0.55 * abs(lat))
        _amplitude = abs(lat) * 0.38
        _peak_m    = 6 if lat >= 0 else 0

        raw_prec  = [param["PRECTOTCORR"][k]       for k in _MONTH_KEYS]
        raw_tmean = [param["T2M"][k]               for k in _MONTH_KEYS]
        srad      = [param["ALLSKY_SFC_SW_DWN"][k] for k in _MONTH_KEYS]

        prec_d = [max(0.0, v) for v in raw_prec]
        tmean  = [v if v > -100 else _ann_mean + _amplitude * math.cos(2 * math.pi * (m - _peak_m) / 12)
                  for m, v in enumerate(raw_tmean)]

        precip_mm = [round(prec_d[m] * _DAYS[m], 1) for m in range(12)]
        et0_mm = []
        for m in range(12):
            rs        = srad[m] if srad[m] >= 0 else 0.5 * _ra(lat, m)
            et0_daily = max(0.0, 0.0023 * rs * (tmean[m] + 17.8) * td_est ** 0.5)
            et0_mm.append(round(et0_daily * _DAYS[m], 1))

        months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        print(f"\n[NASA POWER] {lat:.2f}°N {lon:.2f}°E  td_est={td_est:.1f}°C")
        print(f"  {'Mo':<4} {'Precip':>8} {'ET0':>8} {'Tmean':>7} {'Rs':>7}")
        for m in range(12):
            print(f"  {months[m]:<4} {precip_mm[m]:>8.1f} {et0_mm[m]:>8.1f} {tmean[m]:>7.1f} {srad[m]:>7.2f}")

        return precip_mm, et0_mm, "NASA POWER"

    except Exception as e:
        print(f"[NASA POWER] fetch failed ({e}), using Ra fallback for {lat:.2f}°N")
        region = determine_region(lat, lon)
        return list(REGIONAL_PRECIP[region]), _ra_et0(lat), "Ra Estimate (offline)"


def determine_region(lat, lon):
    if lat > 10 and -170 <= lon <= -50:
        return "North America"
    if lat <= 10 and -90 <= lon <= -30:
        return "South America"
    if lat > 35 and -10 <= lon <= 40:
        return "Europe"
    if -35 <= lat <= 35 and -20 <= lon <= 55:
        return "Africa"
    if -45 <= lat <= 75 and 55 <= lon <= 180:
        return "Asia & Oceania"
    return "Global Baseline"
