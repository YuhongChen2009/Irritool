import json
import math
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

REGIONAL_ET0 = {
    "North America":  [22,  28,  48,  78,  115, 140, 150, 135, 105, 68,  38,  22],
    "South America":  [160, 145, 130, 95,  65,  42,  38,  50,  75,  105, 135, 155],
    "Europe":         [18,  22,  42,  70,  105, 120, 130, 120, 88,  58,  28,  18],
    "Africa":         [95,  100, 105, 110, 105, 85,  80,  90,  100, 100, 95,  90],
    "Asia & Oceania": [55,  62,  85,  110, 140, 150, 148, 138, 115, 90,  65,  52],
    "Global Baseline":[65,  72,  90,  105, 125, 130, 132, 125, 108, 90,  70,  62],
}

REGIONAL_CROP_DATABASE = {
    "North America":  ["Field Corn (Zea mays)", "Soybeans", "Wheat", "Potatoes", "Tomatoes"],
    "South America":  ["Sugarcane", "Soybeans", "Field Corn (Zea mays)", "Rice", "Cassava"],
    "Asia & Oceania": ["Rice", "Wheat", "Sugarcane", "Potatoes", "Field Corn (Zea mays)"],
    "Europe":         ["Wheat", "Barley", "Potatoes", "Sugar Beets", "Tomatoes"],
    "Africa":         ["Cassava", "Yams", "Field Corn (Zea mays)", "Sorghum", "Rice"],
    "Global Baseline":["Field Corn (Zea mays)", "Rice", "Wheat", "Soybeans", "Potatoes"],
}

TILE_OPTIONS = {
    "Voyager":       ("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", "CartoDB", "abcd"),
    "Light":         ("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",           "CartoDB", "abcd"),
    "Dark Mode":     ("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",            "CartoDB", "abcd"),
    "Satellite":     ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", "Esri", ""),
    "OpenStreetMap": ("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",                       "OSM",     "abc"),
}

DEFAULT_LAT = 43.5400
DEFAULT_LON = -80.2500


_MONTH_KEYS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
_DAYS       = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_DOY        = [15, 45, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349]


def _ra(lat_deg, month_idx):
    """Extraterrestrial radiation (MJ/m²/day) via FAO-56 procedure."""
    lat = math.radians(lat_deg)
    dr    = 1 + 0.033 * math.cos(2 * math.pi / 365 * _DOY[month_idx])
    delta = 0.409 * math.sin(2 * math.pi / 365 * _DOY[month_idx] - 1.39)
    ws    = math.acos(max(-1.0, min(1.0, -math.tan(lat) * math.tan(delta))))
    return (24 * 60 / math.pi) * 0.0820 * dr * (
        ws * math.sin(lat) * math.sin(delta) +
        math.cos(lat) * math.cos(delta) * math.sin(ws)
    )


# Maps FAOSTAT item names → internal crop names
_FAOSTAT_TO_CROP = {
    "Maize (corn)":   "Field Corn (Zea mays)",
    "Soybeans":       "Soybeans",
    "Wheat":          "Wheat",
    "Potatoes":       "Potatoes",
    "Tomatoes":       "Tomatoes",
    "Rice":           "Rice",
    "Sugar cane":     "Sugarcane",
    "Cassava, fresh": "Cassava",
    "Yams":           "Yams",
    "Sorghum":        "Sorghum",
    "Sugar beet":     "Sugar Beets",
    "Barley":         "Barley",
}

# Module-level cache so the country list is only fetched once per process
_faostat_area_cache: dict[str, str] = {}


def _reverse_geocode(lat, lon):
    resp = requests.get(
        "https://nominatim.openstreetmap.org/reverse",
        params={"lat": lat, "lon": lon, "format": "json"},
        headers={"User-Agent": "IrriTool/1.0 (irrigation scheduling app)"},
        timeout=10,
    )
    resp.raise_for_status()
    addr = resp.json()["address"]
    return addr["country_code"].upper(), addr.get("country", "")


def _iso2_to_faostat(iso2):  # iso2 is the first element returned by _reverse_geocode
    if not _faostat_area_cache:
        resp = requests.get(
            "https://fenixservices.fao.org/faostat/api/v1/en/definitions/domain/QCL/area",
            params={"output_type": "objects"},
            timeout=15,
        )
        resp.raise_for_status()
        for item in resp.json().get("data", []):
            code = item.get("ISO2_Code", "").upper()
            if code:
                _faostat_area_cache[code] = item["Code"]
    return _faostat_area_cache.get(iso2)


def fetch_top_crops(lat, lon):
    """Returns (country_name, crops) where crops is up to 5 items ranked by
    FAOSTAT production volume. Falls back to regional defaults on any error."""
    try:
        iso2, country_name = _reverse_geocode(lat, lon)
        fao_code = _iso2_to_faostat(iso2)
        if not fao_code:
            raise ValueError(f"No FAOSTAT code for {iso2}")

        resp = requests.get(
            "https://fenixservices.fao.org/faostat/api/v1/en/data/QCL",
            params={"area": fao_code, "element": "5510", "year": "2022", "format": "json"},
            timeout=15,
        )
        resp.raise_for_status()

        rows = sorted(
            resp.json().get("data", []),
            key=lambda x: float(x.get("Value") or 0),
            reverse=True,
        )

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

        return country_name, crops

    except Exception:
        region = determine_region(lat, lon)
        return region, REGIONAL_CROP_DATABASE[region]


def fetch_climate(lat, lon):
    """Fetch long-term monthly climate normals from NASA POWER for a coordinate.
    Returns (precip_mm, et0_mm) as 12-element lists.
    Falls back to regional hardcoded values if the API is unreachable."""
    try:
        resp = requests.get(
            "https://power.larc.nasa.gov/api/temporal/climatology/point",
            params={
                "parameters": "PRECTOTCORR,T2M_MAX,T2M_MIN",
                "community":  "AG",
                "longitude":  round(lon, 4),
                "latitude":   round(lat, 4),
                "format":     "JSON",
            },
            timeout=15,
        )
        resp.raise_for_status()
        param = resp.json()["properties"]["parameter"]

        prec_d = [param["PRECTOTCORR"][k] for k in _MONTH_KEYS]
        tmax   = [param["T2M_MAX"][k]     for k in _MONTH_KEYS]
        tmin   = [param["T2M_MIN"][k]     for k in _MONTH_KEYS]

        precip_mm = [round(prec_d[m] * _DAYS[m], 1) for m in range(12)]
        et0_mm = []
        for m in range(12):
            tmean     = (tmax[m] + tmin[m]) / 2
            td        = max(0.0, tmax[m] - tmin[m])
            et0_daily = 0.0023 * _ra(lat, m) * (tmean + 17.8) * td ** 0.5
            et0_mm.append(round(et0_daily * _DAYS[m], 1))

        return precip_mm, et0_mm

    except Exception:
        region = determine_region(lat, lon)
        return list(REGIONAL_PRECIP[region]), list(REGIONAL_ET0[region])


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
