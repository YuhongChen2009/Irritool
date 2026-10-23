import {
  DEFAULT_LAT,
  DEFAULT_LON,
  L_PER_MM_PER_ACRE,
  STEPS,
  MONTH_KEYS,
  MONTHS_SHORT,
  DAYS_IN_MONTH,
  DOY_MID_MONTH,
  TILE_URLS,
  CROP_PARAMS,
  CROP_SCIENTIFIC,
  REGIONAL_PRECIP,
  REGIONAL_CROP_DATABASE,
  FAOSTAT_TO_CROP,
  FAOSTAT_COUNTRY_CROPS,
  SOIL_PRESETS,
  SOIL_REFERENCE_TABLE,
} from "./data.js";

// ── Firebase Configuration ───────────────────────────────────────────────────

export const firebaseConfig = {
  apiKey: "AIzaSyA80u1LG9I47zgD5HPi8QpQ7MlT3Wtyayo",
  authDomain: "irritool.firebaseapp.com",
  projectId: "irritool",
  storageBucket: "irritool.firebasestorage.app",
  messagingSenderId: "331674114003",
  appId: "1:331674114003:web:b6369a770e377344564126",
  measurementId: "G-XPS9KC46WZ",
};

if (typeof window !== "undefined") {
  Promise.all([import("firebase/app"), import("firebase/analytics")])
    .then(([{ initializeApp }, { getAnalytics, isSupported }]) => {
      const app = initializeApp(firebaseConfig);
      isSupported().then((supported) => {
        if (supported) getAnalytics(app);
      });
    })
    .catch((err) => console.warn("[Firebase] SDK init skipped:", err));
}

// ── Application State ────────────────────────────────────────────────────────

const state = {
  page: 0,
  maxPage: 0,
  coordLat: null,
  coordLon: null,
  hasMarker: false,
  selectedCountry: "",
  selectedIso2: "",
  isWater: false,
  mapTileChoice: "Default (local languages)",
  selectedCrop: null,
  plantingDate: "2026-05-01",
  faostatKey: null,
  faostatCrops: null,
  faostatDataYear: null,
  countryName: "",
  soilType: "Loam",
  soilFc: 31.0,
  soilPwp: 14.0,
  climateKey: null,
  climateData: null,
  climateSource: "Unknown",
  bfResultKey: null,
  bfResult: null,
};

// Caches (equivalent to module-level caches in core/data_fetcher.py)
const faostatAreaCache = {};
const cropCache = {};
const geocodeCache = {};

// ── Math & Regional Helpers (ported from core/data_fetcher.py) ───────────────

function round1(val) {
  return Math.round(val * 10) / 10;
}

function round4(val) {
  return Math.round(val * 10000) / 10000;
}

function normalizeLon(lon) {
  return ((((lon + 180) % 360) + 360) % 360) - 180;
}

export function determineRegion(lat, lon) {
  if (lat > 10 && lon >= -170 && lon <= -50) return "North America";
  if (lat <= 10 && lon >= -90 && lon <= -30) return "South America";
  if (lat > 35 && lon >= -10 && lon <= 40) return "Europe";
  if (lat >= -35 && lat <= 35 && lon >= -20 && lon <= 55) return "Africa";
  if (lat >= -45 && lat <= 75 && lon >= 55 && lon <= 180) return "Asia & Oceania";
  return "Global Baseline";
}

function calcRa(latDeg, monthIdx) {
  const lat = (latDeg * Math.PI) / 180.0;
  const doy = DOY_MID_MONTH[monthIdx];
  const dr = 1 + 0.033 * Math.cos(((2 * Math.PI) / 365) * doy);
  const delta = 0.409 * Math.sin(((2 * Math.PI) / 365) * doy - 1.39);
  const tanProd = -Math.tan(lat) * Math.tan(delta);
  const ws = Math.acos(Math.max(-1.0, Math.min(1.0, tanProd)));
  return (
    ((24 * 60) / Math.PI) *
    0.0820 *
    dr *
    (ws * Math.sin(lat) * Math.sin(delta) + Math.cos(lat) * Math.cos(delta) * Math.sin(ws))
  );
}

function calcRaEt0(lat) {
  const annMean = Math.max(-10.0, 30.0 - 0.55 * Math.abs(lat));
  const amplitude = Math.abs(lat) * 0.38;
  const trange = 8.0 + Math.abs(lat) * 0.12;
  const peakM = lat >= 0 ? 6 : 0;

  const et0 = [];
  for (let m = 0; m < 12; m++) {
    const tmean = annMean + amplitude * Math.cos((2 * Math.PI * (m - peakM)) / 12);
    const rs = 0.5 * calcRa(lat, m);
    const et0Daily = Math.max(0.0, 0.0023 * rs * (tmean + 17.8) * Math.sqrt(trange));
    et0.push(round1(et0Daily * DAYS_IN_MONTH[m]));
  }
  return et0;
}

// ── Data Fetching (Nominatim, FAOSTAT, NASA POWER) ───────────────────────────

function formatCountry(local, english) {
  if (english && english.toLowerCase() !== (local || "").toLowerCase()) {
    return local ? `${local} (${english})` : english;
  }
  return local || english || "";
}

async function reverseGeocode(lat, lon) {
  const cacheKey = `${round4(lat)},${round4(lon)}`;
  if (geocodeCache[cacheKey]) {
    const cached = geocodeCache[cacheKey];
    if (cached.isWater) throw new Error("WATER");
    return cached;
  }

  const url = new URL("https://nominatim.openstreetmap.org/reverse");
  url.searchParams.set("lat", String(lat));
  url.searchParams.set("lon", String(lon));
  url.searchParams.set("format", "json");
  url.searchParams.set("zoom", "3");
  url.searchParams.set("namedetails", "1");

  const resp = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
  });
  if (!resp.ok) {
    throw new Error(`Nominatim HTTP ${resp.status}`);
  }
  const data = await resp.json();
  if (!data || !data.address || !data.address.country_code) {
    geocodeCache[cacheKey] = { isWater: true };
    throw new Error("WATER");
  }

  const addr = data.address;
  const iso2 = addr.country_code.toUpperCase();
  const nd = data.namedetails || {};
  const localName = nd.name || addr.country || "";
  const englishName = nd["name:en"] || "";
  const result = { iso2, localName, englishName, isWater: false };
  geocodeCache[cacheKey] = result;
  return result;
}

async function fetchCountryInfo(lat, lon) {
  try {
    const { iso2, localName, englishName } = await reverseGeocode(lat, lon);
    return { country: formatCountry(localName, englishName), iso2, isWater: false };
  } catch (err) {
    if (err && err.message === "WATER") {
      return { country: "Water", iso2: "", isWater: true };
    }
    return { country: null, iso2: "", isWater: false };
  }
}

async function iso2ToFaostat(iso2) {
  if (Object.keys(faostatAreaCache).length === 0) {
    const resp = await fetch(
      "https://faostatservices.fao.org/api/v1/en/definitions/domain/QCL/area?output_type=objects"
    );
    if (!resp.ok) throw new Error("FAOSTAT area definition request failed");
    const body = await resp.json();
    for (const item of body.data || []) {
      const code = (item["ISO2 Code"] || "").toUpperCase();
      if (code) {
        faostatAreaCache[code] = item["Country Code"];
      }
    }
  }
  return faostatAreaCache[iso2];
}

function padCropsWithRegional(crops, lat, lon) {
  const regional = REGIONAL_CROP_DATABASE[determineRegion(lat, lon)];
  const result = [...crops];
  for (const c of regional) {
    if (result.length >= 5) break;
    if (!result.includes(c)) result.push(c);
  }
  return result.slice(0, 5);
}

async function fetchTopCrops(lat, lon) {
  let iso2 = state.selectedIso2;
  let countryName = state.selectedCountry;

  try {
    const geo = await reverseGeocode(lat, lon);
    iso2 = geo.iso2;
    countryName = formatCountry(geo.localName, geo.englishName);
    if (cropCache[iso2]) {
      return cropCache[iso2];
    }

    // Attempt live FAOSTAT API first
    try {
      const faoCode = await iso2ToFaostat(iso2);
      if (faoCode) {
        let rows = [];
        let dataYear = null;
        for (const year of [2025, 2024, 2023, 2022]) {
          try {
            const url = new URL("https://faostatservices.fao.org/api/v1/en/data/QCL");
            url.searchParams.set("area", faoCode);
            url.searchParams.set("element", "2510");
            url.searchParams.set("item", "QC>");
            url.searchParams.set("year", String(year));
            url.searchParams.set("output_type", "objects");

            const resp = await fetch(url.toString());
            if (!resp.ok) continue;
            const body = await resp.json();
            const candidateRows = body.data || [];
            if (candidateRows.length > 0) {
              rows = candidateRows;
              dataYear = year;
              break;
            }
          } catch (_) {
            continue;
          }
        }

        if (rows.length > 0) {
          const aggSuffixes = [" primary", " total", "n.e.c.", ", total", ", primary"];
          const isAggregate = (name) => {
            const n = (name || "").toLowerCase();
            return aggSuffixes.some((s) => n.endsWith(s));
          };

          const filtered = rows
            .filter((r) => !isAggregate(r.Item || ""))
            .sort((a, b) => ( parseFloat(b.Value) || 0 ) - ( parseFloat(a.Value) || 0 ));

          const crops = [];
          for (const row of filtered) {
            const internal = FAOSTAT_TO_CROP[row.Item];
            if (internal && !crops.includes(internal)) {
              crops.push(internal);
            }
            if (crops.length === 5) break;
          }

          const finalCrops = padCropsWithRegional(crops, lat, lon);
          cropCache[iso2] = { countryName, crops: finalCrops, dataYear };
          return cropCache[iso2];
        }
      }
    } catch (_) {
      // Fall through to pre-indexed FAOSTAT dataset or regional defaults
    }

    // Check pre-indexed FAOSTAT QCL country dataset
    if (iso2 && FAOSTAT_COUNTRY_CROPS[iso2]) {
      const entry = FAOSTAT_COUNTRY_CROPS[iso2];
      const finalCrops = padCropsWithRegional(entry.crops, lat, lon);
      cropCache[iso2] = { countryName, crops: finalCrops, dataYear: entry.year };
      return cropCache[iso2];
    }

    const region = determineRegion(lat, lon);
    const fallback = {
      countryName: countryName || region,
      crops: [...REGIONAL_CROP_DATABASE[region]],
      dataYear: null,
    };
    if (iso2) cropCache[iso2] = fallback;
    return fallback;
  } catch (_) {
    const region = determineRegion(lat, lon);
    return {
      countryName: countryName && countryName !== "Water" ? countryName : region,
      crops: [...REGIONAL_CROP_DATABASE[region]],
      dataYear: null,
    };
  }
}

async function fetchClimate(lat, lon) {
  const tdEst = Math.max(6.0, 15.0 - 0.1 * Math.abs(lat));

  try {
    const url = new URL("https://power.larc.nasa.gov/api/temporal/climatology/point");
    url.searchParams.set("parameters", "PRECTOTCORR,T2M,ALLSKY_SFC_SW_DWN");
    url.searchParams.set("community", "AG");
    url.searchParams.set("longitude", String(round4(lon)));
    url.searchParams.set("latitude", String(round4(lat)));
    url.searchParams.set("format", "JSON");

    const resp = await fetch(url.toString());
    if (!resp.ok) throw new Error(`NASA POWER HTTP ${resp.status}`);
    const body = await resp.json();
    const param = body.properties.parameter;

    const annMean = Math.max(-10.0, 30.0 - 0.55 * Math.abs(lat));
    const amplitude = Math.abs(lat) * 0.38;
    const peakM = lat >= 0 ? 6 : 0;

    const rawPrec = MONTH_KEYS.map((k) => param.PRECTOTCORR[k]);
    const rawTmean = MONTH_KEYS.map((k) => param.T2M[k]);
    const srad = MONTH_KEYS.map((k) => param.ALLSKY_SFC_SW_DWN[k]);

    const precD = rawPrec.map((v) => Math.max(0.0, v));
    const tmean = rawTmean.map((v, m) =>
      v > -100 ? v : annMean + amplitude * Math.cos((2 * Math.PI * (m - peakM)) / 12)
    );

    const precipMm = precD.map((d, m) => round1(d * DAYS_IN_MONTH[m]));
    const et0Mm = [];
    for (let m = 0; m < 12; m++) {
      const rs = srad[m] >= 0 ? srad[m] : 0.5 * calcRa(lat, m);
      const et0Daily = Math.max(0.0, 0.0023 * rs * (tmean[m] + 17.8) * Math.sqrt(tdEst));
      et0Mm.push(round1(et0Daily * DAYS_IN_MONTH[m]));
    }

    return { precip: precipMm, et0: et0Mm, source: "NASA POWER" };
  } catch (err) {
    console.warn("[NASA POWER] fetch failed, using Ra fallback:", err);
    const region = determineRegion(lat, lon);
    return {
      precip: [...REGIONAL_PRECIP[region]],
      et0: calcRaEt0(lat),
      source: "Ra Estimate (offline)",
    };
  }
}

// ── Hydrological Simulator (ported from core/simulator.py) ───────────────────

function effectivePrecip(precip) {
  return precip.map((p) => {
    const pe = p <= 70.0 ? 0.6 * p - 10.0 : 0.8 * p - 24.0;
    return Math.max(0.0, pe);
  });
}

function simulate(p, precip, et0, trigger, seasonStart) {
  const doseVwc = (p.dose_mm / p.root_mm) * 100.0;
  let vwc = p.fc;
  let events = 0;
  let stress = 0;

  for (let i = 0; i < p.kc.length; i++) {
    const m = (seasonStart - 1 + i) % 12;
    const etcVwc = ((et0[m] * p.kc[i]) / p.root_mm) * 100.0;
    const precVwc = (precip[m] / p.root_mm) * 100.0;
    vwc = vwc + precVwc - etcVwc;
    while (vwc < trigger) {
      vwc += doseVwc;
      events += 1;
    }
    vwc = Math.min(vwc, p.fc);
    if (vwc < p.stress_buffer) {
      stress += 1;
    }
  }
  return { events, stress };
}

function computePhases(p, precip, et0, trigger, seasonStart, tradEvents, rawPrecip) {
  const actualRaw = rawPrecip || precip;
  const n = p.kc.length;
  const third = Math.floor(n / 3);
  const doseVwc = (p.dose_mm / p.root_mm) * 100.0;
  let vwc = p.fc;

  const ranges = [
    [0, third],
    [third, 2 * third],
    [2 * third, n],
  ];
  const names = ["Initial (Emergence)", "Mid-Season (Peak)", "Late (Maturity)"];
  const phases = [];

  for (let rIdx = 0; rIdx < ranges.length; rIdx++) {
    const [startIdx, endIdx] = ranges[rIdx];
    const phName = names[rIdx];
    let phEvents = 0;
    let phPrecip = 0;

    for (let i = startIdx; i < endIdx; i++) {
      const m = (seasonStart - 1 + i) % 12;
      const etcVwc = ((et0[m] * p.kc[i]) / p.root_mm) * 100.0;
      const precVwc = (precip[m] / p.root_mm) * 100.0;
      phPrecip += actualRaw[m];
      vwc = vwc + precVwc - etcVwc;
      while (vwc < trigger) {
        vwc += doseVwc;
        phEvents += 1;
      }
      vwc = Math.min(vwc, p.fc);
    }

    const bfMm = phEvents * p.dose_mm;
    const tradMm = ((endIdx - startIdx) / n) * tradEvents * p.dose_mm;
    const savedPct = tradMm > 0 ? round1((1 - bfMm / tradMm) * 100) : 100.0;

    phases.push({
      phase: phName,
      phasePrecipMm: Math.trunc(phPrecip),
      tradMm: Math.trunc(tradMm),
      bfMm: bfMm,
      waterSavedPct: `${savedPct.toFixed(1)}%`,
    });
  }

  return phases;
}

export function runCalc(cropName, precip, et0, plantingDateStr, soilFc = null, soilPwp = null) {
  const baseParams = CROP_PARAMS[cropName];
  if (!baseParams) return null;
  const p = { ...baseParams, kc: [...baseParams.kc] };

  if (soilFc !== null || soilPwp !== null) {
    const origFc = p.fc;
    const origPwp = p.pwp;
    if (soilFc !== null) p.fc = soilFc;
    if (soilPwp !== null) p.pwp = soilPwp;
    if (origFc > origPwp) {
      const ratio = (p.stress_buffer - origPwp) / (origFc - origPwp);
      p.stress_buffer = round1(
        Math.max(p.pwp + 0.5, Math.min(p.fc - 1.0, p.pwp + ratio * (p.fc - p.pwp)))
      );
    }
  }

  // Extract month (1-12) from YYYY-MM-DD
  const parts = (plantingDateStr || "2026-05-01").split("-");
  const seasonStart = parseInt(parts[1], 10) || 5;
  const effPrecip = effectivePrecip(precip);

  let seasonalEtc = 0;
  for (let i = 0; i < p.kc.length; i++) {
    seasonalEtc += et0[(seasonStart - 1 + i) % 12] * p.kc[i];
  }
  const tradEvents = Math.max(1, Math.round(seasonalEtc / p.dose_mm));

  let bestTrigger = null;
  let bestEvents = 9999;
  let bestStress = 9999;

  const startT = p.pwp + 2.0;
  const stopT = p.fc - 1.0;
  for (let step = 0; ; step++) {
    const t = Math.round((startT + step * 0.5) * 1000) / 1000;
    if (t >= stopT - 1e-9) break;
    const { events: ev, stress: sx } = simulate(p, effPrecip, et0, t, seasonStart);
    if (sx < bestStress || (sx === bestStress && ev < bestEvents)) {
      bestTrigger = t;
      bestEvents = ev;
      bestStress = sx;
    }
  }

  if (bestTrigger === null) return null;

  const tradWater = tradEvents * p.dose_mm * L_PER_MM_PER_ACRE;
  const bfWater = bestEvents * p.dose_mm * L_PER_MM_PER_ACRE;
  const saved = Math.trunc(tradWater - bfWater);
  const reduction = round1((1 - bestEvents / tradEvents) * 100);

  return {
    trigger: round1(bestTrigger),
    bf_events_yr: bestEvents,
    trad_events_yr: tradEvents,
    reduction_pct: reduction,
    bf_water_L: Math.trunc(bfWater),
    trad_water_L: Math.trunc(tradWater),
    saved_L: saved,
    phases: computePhases(p, effPrecip, et0, bestTrigger, seasonStart, tradEvents, precip),
    kc: p.kc,
    fc: p.fc,
    pwp: p.pwp,
    stress_buffer: p.stress_buffer,
    dose_mm: p.dose_mm,
    root_mm: p.root_mm,
    paper_validated: Boolean(p.paper_validated),
    paper_trigger: p.paper_trigger,
  };
}

// ── UI Helpers (Toast, Step Bar, SVG Bar Charts) ─────────────────────────────

function showToast(message, icon = "") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = icon ? `${icon} ${message}` : message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3500);
}

function renderSteps() {
  const nav = document.getElementById("step-indicator");
  nav.innerHTML = "";

  if (state.page > state.maxPage) {
    state.maxPage = state.page;
  }

  STEPS.forEach((label, i) => {
    if (i === state.page) {
      const div = document.createElement("div");
      div.className = "step-pill active";
      div.textContent = `● ${label}`;
      nav.appendChild(div);
    } else if (i <= state.maxPage) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "step-pill reachable";
      btn.textContent = label;
      btn.addEventListener("click", () => navigateToPage(i));
      nav.appendChild(btn);
    } else {
      const div = document.createElement("div");
      div.className = "step-pill disabled";
      div.textContent = label;
      nav.appendChild(div);
    }
  });
}

function renderBarChart(containerId, months, values, color, yLabel = "mm") {
  const container = document.getElementById(containerId);
  const width = 560;
  const height = 260;
  const padLeft = 48;
  const padRight = 16;
  const padTop = 20;
  const padBottom = 42;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const maxVal = Math.max(10, ...values) * 1.12;
  const ticks = 4;

  let svg = `<svg class="bar-chart-svg" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">`;

  // Horizontal grid lines & Y-axis labels
  for (let t = 0; t <= ticks; t++) {
    const val = (maxVal / ticks) * t;
    const y = padTop + plotH - (val / maxVal) * plotH;
    svg += `<line x1="${padLeft}" y1="${y.toFixed(1)}" x2="${width - padRight}" y2="${y.toFixed(1)}" stroke="#e5e7eb" stroke-width="1" />`;
    svg += `<text x="${padLeft - 8}" y="${(y + 4).toFixed(1)}" text-anchor="end" font-size="11" fill="#6b7280">${Math.round(val)}</text>`;
  }

  // Y-axis title
  svg += `<text x="14" y="${padTop + plotH / 2}" text-anchor="middle" font-size="11" fill="#6b7280" transform="rotate(-90, 14, ${padTop + plotH / 2})">${yLabel}</text>`;

  // Bars & X-axis labels
  const slotW = plotW / months.length;
  const barW = slotW * 0.64;

  months.forEach((m, idx) => {
    const v = values[idx] || 0;
    const barH = Math.max(0, (v / maxVal) * plotH);
    const x = padLeft + idx * slotW + (slotW - barW) / 2;
    const y = padTop + plotH - barH;
    const cx = padLeft + idx * slotW + slotW / 2;

    svg += `<rect class="bar-rect" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${barH.toFixed(1)}" fill="${color}" rx="3">
      <title>${m}: ${v.toFixed(1)} ${yLabel}</title>
    </rect>`;
    svg += `<text x="${cx.toFixed(1)}" y="${padTop + plotH + 18}" text-anchor="middle" font-size="11" fill="#374151">${m}</text>`;
  });

  // X-axis title
  svg += `<text x="${padLeft + plotW / 2}" y="${height - 4}" text-anchor="middle" font-size="11" fill="#6b7280">Month</text>`;
  svg += `</svg>`;

  container.innerHTML = svg;
}

// ── Step 0: Leaflet Map & Location Selection ─────────────────────────────────

let leafletMap = null;
let leafletMarker = null;
let leafletTileLayer = null;
let locationReqId = 0;

const MARKER_OPTS = {
  radius: 8,
  color: "white",
  weight: 2,
  fillColor: "#e84040",
  fillOpacity: 1.0,
};

function initMapPage() {
  const initLat = state.coordLat !== null ? state.coordLat : 25.0;
  const initLon = state.coordLon !== null ? state.coordLon : 0.0;

  leafletMap = L.map("map", {
    center: [initLat, initLon],
    zoom: 3,
    minZoom: 2,
    doubleClickZoom: false,
    maxBounds: [
      [-90, -180],
      [90, 180],
    ],
    maxBoundsViscosity: 1.0,
    attributionControl: false,
  });

  setMapTileUrl(TILE_URLS[state.mapTileChoice]);

  leafletMap.on("click", (e) => {
    const clickLat = round4(e.latlng.lat);
    const clickLon = round4(normalizeLon(e.latlng.lng));
    selectCoordinates(clickLat, clickLon, false);
  });

  // Wire up manual coordinate inputs
  const inputLat = document.getElementById("input-lat");
  const inputLon = document.getElementById("input-lon");

  const onManualCoordChange = () => {
    const parsedLat = parseFloat(inputLat.value);
    const parsedLon = parseFloat(inputLon.value);
    if (Number.isNaN(parsedLat) || Number.isNaN(parsedLon)) return;
    const clampedLat = round4(Math.max(-90, Math.min(90, parsedLat)));
    const clampedLon = round4(Math.max(-180, Math.min(180, parsedLon)));
    selectCoordinates(clampedLat, clampedLon, true);
  };

  inputLat.addEventListener("change", onManualCoordChange);
  inputLon.addEventListener("change", onManualCoordChange);

  // Wire up map tile selector
  const selectTile = document.getElementById("select-map-tile");
  selectTile.addEventListener("change", () => {
    state.mapTileChoice = selectTile.value;
    setMapTileUrl(TILE_URLS[state.mapTileChoice]);
  });

  // Next button
  document.getElementById("btn-map-next").addEventListener("click", () => {
    if (state.coordLat === null || state.coordLon === null) {
      showToast("Please select a location first.", "⚠️");
    } else if (state.isWater) {
      showToast("Please select a land area, not water.", "🌊");
    } else {
      navigateToPage(1);
    }
  });
}

function setMapTileUrl(url) {
  if (!leafletMap) return;
  if (leafletTileLayer) {
    leafletMap.removeLayer(leafletTileLayer);
  }
  leafletTileLayer = L.tileLayer(url, { noWrap: false }).addTo(leafletMap);
}

function syncMapMarker(lat, lon) {
  if (!leafletMap) return;
  if (!leafletMarker) {
    leafletMarker = L.circleMarker([lat, lon], MARKER_OPTS).addTo(leafletMap);
  } else {
    leafletMarker.setLatLng([lat, lon]);
  }
}

async function selectCoordinates(lat, lon, fromInput = false) {
  state.coordLat = lat;
  state.coordLon = lon;
  state.hasMarker = true;

  syncMapMarker(lat, lon);
  if (fromInput && leafletMap) {
    leafletMap.panTo([lat, lon]);
  }

  const coordsGroup = document.getElementById("location-coords-group");
  coordsGroup.classList.remove("hidden");

  const inputLat = document.getElementById("input-lat");
  const inputLon = document.getElementById("input-lon");
  inputLat.value = lat.toFixed(4);
  inputLon.value = lon.toFixed(4);

  const statusBox = document.getElementById("location-status-box");
  statusBox.className = "alert alert-info";
  statusBox.innerHTML = "Resolving location...";

  const reqId = ++locationReqId;
  const { country, iso2, isWater } = await fetchCountryInfo(lat, lon);
  if (reqId !== locationReqId) return;

  state.selectedCountry = country;
  state.selectedIso2 = iso2;
  state.isWater = isWater;

  const region = determineRegion(lat, lon);
  if (isWater) {
    statusBox.className = "alert alert-warning";
    statusBox.innerHTML = "🌊 <strong>Water</strong> — please select a land area.";
  } else {
    const label = country || region;
    statusBox.className = "alert alert-info";
    statusBox.innerHTML = `Location: <strong>${escapeHtml(label)}</strong>`;
    const crops = REGIONAL_CROP_DATABASE[region];
    if (!crops.includes(state.selectedCrop)) {
      state.selectedCrop = crops[0];
    }
  }
}

// ── Step 1: Choose Crop ──────────────────────────────────────────────────────

function initCropPageEvents() {
  const selectCrop = document.getElementById("select-crop");
  selectCrop.addEventListener("change", () => {
    state.selectedCrop = selectCrop.value;
  });

  const inputDate = document.getElementById("input-planting-date");
  inputDate.addEventListener("change", () => {
    if (inputDate.value) {
      state.plantingDate = inputDate.value;
    }
  });

  document.getElementById("btn-crop-back").addEventListener("click", () => navigateToPage(0));
  document.getElementById("btn-crop-next").addEventListener("click", () => navigateToPage(2));
}

async function renderCropPage() {
  const lat = state.coordLat ?? DEFAULT_LAT;
  const lon = state.coordLon ?? DEFAULT_LON;
  const faostatKey = `${lat.toFixed(2)},${lon.toFixed(2)}`;

  const loadingEl = document.getElementById("crop-loading");
  const contentEl = document.getElementById("crop-content");

  if (state.faostatKey !== faostatKey) {
    loadingEl.classList.remove("hidden");
    contentEl.classList.add("hidden");

    const { countryName, crops, dataYear } = await fetchTopCrops(lat, lon);
    let resolvedCountry = countryName;
    if (resolvedCountry in REGIONAL_CROP_DATABASE) {
      resolvedCountry = state.selectedCountry || resolvedCountry;
    }

    state.faostatKey = faostatKey;
    state.faostatCrops = crops;
    state.countryName = resolvedCountry;
    state.faostatDataYear = dataYear;
    state.selectedCrop = crops[0];

    loadingEl.classList.add("hidden");
    contentEl.classList.remove("hidden");
  }

  const crops = state.faostatCrops || REGIONAL_CROP_DATABASE[determineRegion(lat, lon)];
  const activeRegion = determineRegion(lat, lon);
  const isRegionName = state.countryName in REGIONAL_CROP_DATABASE;
  const displayCountry =
    (isRegionName || !state.countryName ? state.selectedCountry : state.countryName) ||
    activeRegion;

  if (!crops.includes(state.selectedCrop)) {
    state.selectedCrop = crops[0];
  }

  document.getElementById("metric-country").textContent = displayCountry;
  document.getElementById("metric-coords").textContent = `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`;
  document.getElementById("metric-source").textContent = "FAOSTAT";
  document.getElementById("metric-year").textContent = state.faostatDataYear
    ? String(state.faostatDataYear)
    : "Regional defaults";

  const selectCrop = document.getElementById("select-crop");
  selectCrop.innerHTML = "";
  crops.forEach((c, idx) => {
    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = `${idx + 1}. ${CROP_SCIENTIFIC[c] || c}`;
    if (c === state.selectedCrop) opt.selected = true;
    selectCrop.appendChild(opt);
  });

  document.getElementById("input-planting-date").value = state.plantingDate;
}

// ── Step 2: Choose Soil ──────────────────────────────────────────────────────

function initSoilPage() {
  const selectSoil = document.getElementById("select-soil-type");
  const inputFc = document.getElementById("input-soil-fc");
  const inputPwp = document.getElementById("input-soil-pwp");

  Object.keys(SOIL_PRESETS).forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    if (name === state.soilType) opt.selected = true;
    selectSoil.appendChild(opt);
  });

  // Populate reference table once
  const tbody = document.querySelector("#table-soil-reference tbody");
  tbody.innerHTML = SOIL_REFERENCE_TABLE.map(
    (row) => `
    <tr>
      <td>${escapeHtml(row.soilType)}</td>
      <td>${row.fc}</td>
      <td>${row.pwp}</td>
      <td>${row.awc}</td>
      <td>${escapeHtml(row.regions)}</td>
    </tr>`
  ).join("");

  selectSoil.addEventListener("change", () => {
    const selected = selectSoil.value;
    state.soilType = selected;
    if (selected !== "Custom" && SOIL_PRESETS[selected]) {
      const preset = SOIL_PRESETS[selected];
      state.soilFc = preset.fc;
      state.soilPwp = preset.pwp;
      inputFc.value = preset.fc.toFixed(1);
      inputPwp.value = preset.pwp.toFixed(1);
    }
    updateSoilAwcBanner();
  });

  const onParamInput = () => {
    const fcVal = parseFloat(inputFc.value);
    const pwpVal = parseFloat(inputPwp.value);
    if (!Number.isNaN(fcVal)) state.soilFc = fcVal;
    if (!Number.isNaN(pwpVal)) state.soilPwp = pwpVal;

    const currType = selectSoil.value;
    if (currType !== "Custom" && SOIL_PRESETS[currType]) {
      const preset = SOIL_PRESETS[currType];
      if (state.soilFc !== preset.fc || state.soilPwp !== preset.pwp) {
        state.soilType = "Custom";
        selectSoil.value = "Custom";
      }
    }
    updateSoilAwcBanner();
  };

  inputFc.addEventListener("input", onParamInput);
  inputPwp.addEventListener("input", onParamInput);

  document.getElementById("btn-soil-back").addEventListener("click", () => navigateToPage(1));
  document.getElementById("btn-soil-next").addEventListener("click", () => {
    const awc = round1(state.soilFc - state.soilPwp);
    if (awc <= 3.0) {
      showToast("FC must exceed PWP by more than 3% before continuing.", "⚠️");
    } else {
      navigateToPage(3);
    }
  });

  updateSoilAwcBanner();
}

function updateSoilAwcBanner() {
  const awc = round1(state.soilFc - state.soilPwp);
  const banner = document.getElementById("soil-awc-alert");

  if (awc <= 3.0) {
    banner.className = "alert alert-error";
    banner.innerHTML =
      "Field Capacity must exceed Wilting Point by more than 3%. Increase FC or decrease PWP.";
  } else {
    banner.className = "alert alert-info";
    banner.innerHTML = `Available Water Capacity: <strong>${awc.toFixed(1)}%</strong> (${Math.round(
      awc * 10
    )} mm/m root zone)`;
  }
}

// ── Step 3: Irrigation Schedule ──────────────────────────────────────────────

function initSchedulePageEvents() {
  document.getElementById("btn-schedule-back").addEventListener("click", () => navigateToPage(2));
}

function formatPlantingDateLong(dateStr) {
  const [y, m, d] = (dateStr || "2026-05-01").split("-").map((n) => parseInt(n, 10));
  const dateObj = new Date(Date.UTC(y || 2026, (m || 5) - 1, d || 1));
  return dateObj.toLocaleDateString("en-US", {
    month: "long",
    day: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  });
}

async function renderSchedulePage() {
  const lat = state.coordLat ?? DEFAULT_LAT;
  const lon = state.coordLon ?? DEFAULT_LON;
  const activeRegion = determineRegion(lat, lon);
  const crop = state.selectedCrop || REGIONAL_CROP_DATABASE[activeRegion][0];
  const plantingDate = state.plantingDate || "2026-05-01";

  const loadingBox = document.getElementById("schedule-loading");
  const loadingText = document.getElementById("schedule-loading-text");
  const errorBox = document.getElementById("schedule-error");
  const contentBox = document.getElementById("schedule-content");

  const climateKey = `${lat.toFixed(2)},${lon.toFixed(2)},v3-T2M`;
  if (state.climateKey !== climateKey) {
    loadingBox.classList.remove("hidden");
    loadingText.textContent = "Fetching climate data from NASA POWER...";
    contentBox.classList.add("hidden");
    errorBox.classList.add("hidden");

    const { precip, et0, source } = await fetchClimate(lat, lon);
    state.climateKey = climateKey;
    state.climateData = { precip, et0 };
    state.climateSource = source;
  }

  const { precip, et0 } = state.climateData;
  const resultKey = `${crop}|${climateKey}|${plantingDate}|${state.soilFc}|${state.soilPwp}`;

  if (state.bfResultKey !== resultKey) {
    loadingBox.classList.remove("hidden");
    loadingText.textContent = "Running hydrological grid search...";
    state.bfResult = runCalc(crop, precip, et0, plantingDate, state.soilFc, state.soilPwp);
    state.bfResultKey = resultKey;
  }

  loadingBox.classList.add("hidden");
  const result = state.bfResult;

  if (!result) {
    errorBox.classList.remove("hidden");
    contentBox.classList.add("hidden");
    return;
  }

  errorBox.classList.add("hidden");
  contentBox.classList.remove("hidden");

  const location = state.countryName || state.selectedCountry || activeRegion;
  document.getElementById("schedule-title").textContent = `Calculated Results — ${crop}`;
  document.getElementById("schedule-subtitle").textContent = `${location} · Planting: ${formatPlantingDateLong(
    plantingDate
  )}`;

  // Conditional Alerts
  const alertPaper = document.getElementById("alert-paper-validated");
  if (result.paper_validated) {
    alertPaper.classList.remove("hidden");
    alertPaper.innerHTML = `<strong>Paper-validated.</strong> Originally validated on 11 years (2014–2024) of Ontario climate data. Paper-reported VWC trigger: <strong>${result.paper_trigger.toFixed(
      1
    )}%</strong> — output below uses your location's climatological norms.`;
  } else {
    alertPaper.classList.add("hidden");
  }

  const alertZero = document.getElementById("alert-zero-events");
  if (result.bf_events_yr === 0) {
    alertZero.classList.remove("hidden");
  } else {
    alertZero.classList.add("hidden");
  }

  const aboveBaseline = result.bf_events_yr > result.trad_events_yr;
  const alertAbove = document.getElementById("alert-above-baseline");
  if (aboveBaseline) {
    const awc = round1(result.fc - result.pwp);
    const awcMm = Math.round((awc * result.root_mm) / 100);
    alertAbove.classList.remove("hidden");
    alertAbove.innerHTML = `<strong>More events than the traditional baseline (${result.trad_events_yr}).</strong> The selected soil has an AWC of only ${awc.toFixed(
      1
    )}% (${awcMm} mm in a ${result.root_mm} mm root zone) — too small to buffer this crop's water demand between irrigations at this location. Go back and select a soil with higher AWC (e.g. Loam or Silt Loam), or verify that the soil type matches the actual field conditions.`;
  } else {
    alertAbove.classList.add("hidden");
  }

  // Top 4 Metrics
  document.getElementById("res-trigger").textContent = `${result.trigger.toFixed(1)}%`;
  document.getElementById("res-events").textContent = String(result.bf_events_yr);

  const delta = result.bf_events_yr - result.trad_events_yr;
  const deltaEl = document.getElementById("res-events-delta");
  if (delta < 0) {
    deltaEl.className = "metric-delta good";
    deltaEl.textContent = `↓ ${Math.abs(delta)} vs baseline`;
  } else if (delta > 0) {
    deltaEl.className = "metric-delta bad";
    deltaEl.textContent = `↑ +${delta} vs baseline`;
  } else {
    deltaEl.className = "metric-delta neutral";
    deltaEl.textContent = "0 vs baseline";
  }

  const freqLabel = document.getElementById("res-freq-label");
  const freqVal = document.getElementById("res-freq-val");
  const waterLabel = document.getElementById("res-water-label");
  const waterVal = document.getElementById("res-water-val");

  if (aboveBaseline) {
    freqLabel.textContent = "Frequency Increase";
    freqVal.textContent = `${Math.abs(result.reduction_pct).toFixed(1)}%`;
    waterLabel.textContent = "Extra Water Needed";
    waterVal.textContent = `${Math.abs(result.saved_L).toLocaleString()} L/acre`;
  } else {
    freqLabel.textContent = "Frequency Reduction";
    freqVal.textContent = `${result.reduction_pct.toFixed(1)}%`;
    waterLabel.textContent = "Annual Water Saved";
    waterVal.textContent = `${result.saved_L.toLocaleString()} L/acre`;
  }

  // Phase Table
  document.getElementById(
    "phase-caption"
  ).textContent = `Irrigation depth (mm) vs. traditional baseline (${result.trad_events_yr} events/season, no rain credit).`;

  document.querySelector("#table-phases tbody").innerHTML = result.phases
    .map(
      (p) => `
    <tr>
      <td>${escapeHtml(p.phase)}</td>
      <td>${p.phasePrecipMm}</td>
      <td>${p.tradMm}</td>
      <td>${p.bfMm}</td>
      <td>${p.waterSavedPct}</td>
    </tr>`
    )
    .join("");

  // Baseline Comparison Table
  const eventsNote = aboveBaseline
    ? `${Math.abs(result.reduction_pct).toFixed(1)}% more`
    : `${result.reduction_pct.toFixed(1)}% fewer`;
  const waterNote = aboveBaseline
    ? `${Math.abs(result.saved_L).toLocaleString()} L extra`
    : `${result.saved_L.toLocaleString()} L saved`;

  document.querySelector("#table-baseline tbody").innerHTML = `
    <tr>
      <td>Events / Year</td>
      <td>${result.trad_events_yr}</td>
      <td>${result.bf_events_yr}</td>
      <td>${escapeHtml(eventsNote)}</td>
    </tr>
    <tr>
      <td>Water / Year (L/acre)</td>
      <td>${result.trad_water_L.toLocaleString()}</td>
      <td>${result.bf_water_L.toLocaleString()}</td>
      <td>${escapeHtml(waterNote)}</td>
    </tr>
  `;

  // Kc Table
  const startMonthIdx = (parseInt(plantingDate.split("-")[1], 10) || 5) - 1;
  document.querySelector("#table-kc tbody").innerHTML = result.kc
    .map((kc, i) => {
      const mName = MONTHS_SHORT[(startMonthIdx + i) % 12];
      return `
      <tr>
        <td>${mName}</td>
        <td>${kc.toFixed(2)}</td>
      </tr>`;
    })
    .join("");

  // Soil-Water Parameters Table
  const soilParamsRows = [
    ["Field Capacity (FC)", `${result.fc.toFixed(1)}%`],
    ["Permanent Wilting Point", `${result.pwp.toFixed(1)}%`],
    ["Stress Safety Buffer", `${result.stress_buffer.toFixed(1)}%`],
    ["Root Zone Depth", `${result.root_mm} mm`],
    ["Irrigation Dose", `${result.dose_mm} mm/event`],
    ["VWC Trigger (optimised)", `${result.trigger.toFixed(1)}%`],
  ];
  document.querySelector("#table-soil-params tbody").innerHTML = soilParamsRows
    .map(
      ([param, val]) => `
    <tr>
      <td>${escapeHtml(param)}</td>
      <td>${escapeHtml(val)}</td>
    </tr>`
    )
    .join("");

  // Climate Data Section
  const climateAlert = document.getElementById("alert-climate-source");
  if (state.climateSource === "NASA POWER") {
    climateAlert.className = "alert alert-success";
    climateAlert.innerHTML = `<strong>Climate data: ${escapeHtml(
      state.climateSource
    )}</strong> · 20-year climatological normals (2001–2020) · ${lat.toFixed(2)}°N, ${lon.toFixed(
      2
    )}°E · FAO effective rainfall applied in simulation`;
  } else {
    climateAlert.className = "alert alert-warning";
    climateAlert.innerHTML = `<strong>Climate data: ${escapeHtml(
      state.climateSource
    )}</strong> · NASA POWER unavailable — ET₀ estimated from extraterrestrial radiation at ${lat.toFixed(
      2
    )}°N. Precipitation uses regional defaults. Results will be less accurate. FAO effective rainfall applied in simulation.`;
  }

  renderBarChart("chart-precip", MONTHS_SHORT, precip, "#4a90d9", "mm");
  renderBarChart("chart-et0", MONTHS_SHORT, et0, "#e8734a", "mm");

  document.querySelector("#table-climate tbody").innerHTML = MONTHS_SHORT.map(
    (m, idx) => `
    <tr>
      <td>${m}</td>
      <td>${precip[idx].toFixed(1)}</td>
      <td>${et0[idx].toFixed(1)}</td>
    </tr>`
  ).join("");
}

// ── Navigation & Bootstrap ───────────────────────────────────────────────────

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function navigateToPage(targetPage) {
  state.page = targetPage;
  if (targetPage > state.maxPage) {
    state.maxPage = targetPage;
  }

  renderSteps();

  for (let i = 0; i < 4; i++) {
    const sec = document.getElementById(`page-${i}`);
    if (i === targetPage) {
      sec.classList.remove("hidden");
    } else {
      sec.classList.add("hidden");
    }
  }

  if (targetPage === 0 && leafletMap) {
    setTimeout(() => leafletMap.invalidateSize(), 50);
  } else if (targetPage === 1) {
    await renderCropPage();
  } else if (targetPage === 2) {
    updateSoilAwcBanner();
  } else if (targetPage === 3) {
    await renderSchedulePage();
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    renderSteps();
    initMapPage();
    initCropPageEvents();
    initSoilPage();
    initSchedulePageEvents();
  });
}