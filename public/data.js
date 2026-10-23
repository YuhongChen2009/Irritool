// IrriTool Static Datasets & Constants (ported from core/data_fetcher.py, assets/crop_data.json, views/soil_page.py)

export const DEFAULT_LAT = 43.5400;
export const DEFAULT_LON = -80.2500;
export const L_PER_MM_PER_ACRE = 4047.0;

export const STEPS = [
  "Select Location",
  "Choose Crop",
  "Choose Soil",
  "Irrigation Schedule",
];

export const MONTH_KEYS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
export const MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
export const DOY_MID_MONTH = [15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349];

export const TILE_URLS = {
  "Default (local languages)": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  "English": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
};

export const CROP_PARAMS = {
  "Field Corn (Zea mays)": {
    fc: 30.0, pwp: 12.0, stress_buffer: 15.0, root_mm: 600, dose_mm: 25,
    kc: [0.30, 0.75, 1.20, 1.20, 0.90, 0.60],
    paper_trigger: 17.0, paper_validated: true,
  },
  "Soybeans": {
    fc: 28.0, pwp: 11.0, stress_buffer: 14.0, root_mm: 550, dose_mm: 25,
    kc: [0.40, 0.70, 1.15, 1.15, 0.75, 0.50],
    paper_trigger: null, paper_validated: false,
  },
  "Wheat": {
    fc: 32.0, pwp: 10.0, stress_buffer: 13.0, root_mm: 900, dose_mm: 25,
    kc: [0.30, 0.70, 1.15, 1.10, 0.60, 0.25],
    paper_trigger: null, paper_validated: false,
  },
  "Potatoes": {
    fc: 28.0, pwp: 12.0, stress_buffer: 16.0, root_mm: 400, dose_mm: 25,
    kc: [0.50, 0.80, 1.15, 1.15, 0.85, 0.75],
    paper_trigger: null, paper_validated: false,
  },
  "Tomatoes": {
    fc: 30.0, pwp: 13.0, stress_buffer: 17.0, root_mm: 500, dose_mm: 25,
    kc: [0.60, 0.80, 1.15, 1.20, 1.00, 0.80],
    paper_trigger: null, paper_validated: false,
  },
  "Rice": {
    fc: 35.0, pwp: 18.0, stress_buffer: 22.0, root_mm: 500, dose_mm: 30,
    kc: [1.05, 1.10, 1.20, 1.20, 1.05, 0.95],
    paper_trigger: null, paper_validated: false,
  },
  "Sugarcane": {
    fc: 32.0, pwp: 13.0, stress_buffer: 17.0, root_mm: 1200, dose_mm: 30,
    kc: [0.55, 0.75, 1.00, 1.25, 1.25, 0.70],
    paper_trigger: null, paper_validated: false,
  },
  "Cassava": {
    fc: 28.0, pwp: 10.0, stress_buffer: 14.0, root_mm: 800, dose_mm: 25,
    kc: [0.30, 0.60, 0.80, 0.90, 1.00, 0.80],
    paper_trigger: null, paper_validated: false,
  },
  "Yams": {
    fc: 28.0, pwp: 11.0, stress_buffer: 14.0, root_mm: 600, dose_mm: 25,
    kc: [0.50, 0.80, 1.05, 1.05, 0.90, 0.70],
    paper_trigger: null, paper_validated: false,
  },
  "Sorghum": {
    fc: 27.0, pwp: 10.0, stress_buffer: 13.0, root_mm: 1000, dose_mm: 25,
    kc: [0.35, 0.65, 1.00, 1.10, 0.90, 0.55],
    paper_trigger: null, paper_validated: false,
  },
  "Sugar Beets": {
    fc: 30.0, pwp: 11.0, stress_buffer: 15.0, root_mm: 700, dose_mm: 25,
    kc: [0.35, 0.75, 1.20, 1.20, 0.90, 0.70],
    paper_trigger: null, paper_validated: false,
  },
  "Barley": {
    fc: 30.0, pwp: 10.0, stress_buffer: 13.0, root_mm: 800, dose_mm: 25,
    kc: [0.30, 0.60, 1.15, 1.15, 0.55, 0.25],
    paper_trigger: null, paper_validated: false,
  },
};

export const CROP_SCIENTIFIC = {
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
};

export const REGIONAL_PRECIP = {
  "North America":   [55,  48,  60,  75,  90,  92,  88,  82,  78,  68,  62,  58],
  "South America":   [155, 140, 115, 75,  45,  25,  20,  25,  50,  90,  125, 150],
  "Europe":          [47,  42,  52,  57,  68,  67,  63,  67,  62,  62,  57,  52],
  "Africa":          [32,  28,  48,  82,  105, 82,  52,  62,  82,  78,  42,  32],
  "Asia & Oceania":  [52,  57,  82,  105, 135, 158, 162, 142, 112, 82,  62,  52],
  "Global Baseline": [65,  60,  70,  80,  90,  90,  85,  85,  80,  75,  65,  65],
};

export const REGIONAL_CROP_DATABASE = {
  "North America":   ["Field Corn (Zea mays)", "Soybeans", "Wheat", "Potatoes", "Tomatoes"],
  "South America":   ["Sugarcane", "Soybeans", "Field Corn (Zea mays)", "Rice", "Cassava"],
  "Asia & Oceania":  ["Rice", "Wheat", "Sugarcane", "Potatoes", "Field Corn (Zea mays)"],
  "Europe":          ["Wheat", "Barley", "Potatoes", "Sugar Beets", "Tomatoes"],
  "Africa":          ["Cassava", "Yams", "Field Corn (Zea mays)", "Sorghum", "Rice"],
  "Global Baseline": ["Field Corn (Zea mays)", "Rice", "Wheat", "Soybeans", "Potatoes"],
};

export const FAOSTAT_TO_CROP = {
  "Maize (corn)":   "Field Corn (Zea mays)",
  "Maize":          "Field Corn (Zea mays)",
  "Corn":           "Field Corn (Zea mays)",
  "Soybeans":       "Soybeans",
  "Soya beans":     "Soybeans",
  "Soybean":        "Soybeans",
  "Wheat":          "Wheat",
  "Potatoes":       "Potatoes",
  "Potato":         "Potatoes",
  "Tomatoes":       "Tomatoes",
  "Tomato":         "Tomatoes",
  "Rice":           "Rice",
  "Rice, paddy":    "Rice",
  "Sugar cane":     "Sugarcane",
  "Sugar Cane":     "Sugarcane",
  "Sugarcane":      "Sugarcane",
  "Cassava, fresh": "Cassava",
  "Cassava":        "Cassava",
  "Yams":           "Yams",
  "Yam":            "Yams",
  "Sorghum":        "Sorghum",
  "Sugar beet":     "Sugar Beets",
  "Sugar beets":    "Sugar Beets",
  "Sugar Beet":     "Sugar Beets",
  "Barley":         "Barley",
};

// Pre-indexed FAOSTAT QCL production volume rankings by ISO2 country code (fallback when live FAOSTAT API requires auth)
export const FAOSTAT_COUNTRY_CROPS = {
  US: { year: 2024, crops: ["Field Corn (Zea mays)", "Soybeans", "Wheat", "Sugar Beets", "Potatoes"] },
  CA: { year: 2024, crops: ["Wheat", "Field Corn (Zea mays)", "Barley", "Soybeans", "Potatoes"] },
  MX: { year: 2024, crops: ["Sugarcane", "Field Corn (Zea mays)", "Sorghum", "Tomatoes", "Wheat"] },
  BR: { year: 2024, crops: ["Sugarcane", "Soybeans", "Field Corn (Zea mays)", "Cassava", "Rice"] },
  AR: { year: 2024, crops: ["Field Corn (Zea mays)", "Soybeans", "Wheat", "Sugarcane", "Barley"] },
  CO: { year: 2024, crops: ["Sugarcane", "Rice", "Potatoes", "Cassava", "Field Corn (Zea mays)"] },
  PE: { year: 2024, crops: ["Sugarcane", "Potatoes", "Rice", "Field Corn (Zea mays)", "Cassava"] },
  CL: { year: 2024, crops: ["Wheat", "Field Corn (Zea mays)", "Potatoes", "Sugar Beets", "Tomatoes"] },
  GB: { year: 2024, crops: ["Wheat", "Barley", "Sugar Beets", "Potatoes", "Tomatoes"] },
  FR: { year: 2024, crops: ["Wheat", "Sugar Beets", "Field Corn (Zea mays)", "Barley", "Potatoes"] },
  DE: { year: 2024, crops: ["Sugar Beets", "Wheat", "Barley", "Potatoes", "Field Corn (Zea mays)"] },
  ES: { year: 2024, crops: ["Barley", "Wheat", "Tomatoes", "Field Corn (Zea mays)", "Sugar Beets"] },
  IT: { year: 2024, crops: ["Wheat", "Tomatoes", "Field Corn (Zea mays)", "Sugar Beets", "Rice"] },
  PL: { year: 2024, crops: ["Sugar Beets", "Wheat", "Field Corn (Zea mays)", "Potatoes", "Barley"] },
  UA: { year: 2024, crops: ["Field Corn (Zea mays)", "Wheat", "Potatoes", "Sugar Beets", "Barley"] },
  RU: { year: 2024, crops: ["Wheat", "Sugar Beets", "Potatoes", "Barley", "Field Corn (Zea mays)"] },
  TR: { year: 2024, crops: ["Wheat", "Sugar Beets", "Tomatoes", "Field Corn (Zea mays)", "Barley"] },
  NL: { year: 2024, crops: ["Sugar Beets", "Potatoes", "Wheat", "Tomatoes", "Barley"] },
  CN: { year: 2024, crops: ["Field Corn (Zea mays)", "Rice", "Wheat", "Sugarcane", "Potatoes"] },
  IN: { year: 2024, crops: ["Sugarcane", "Rice", "Wheat", "Potatoes", "Field Corn (Zea mays)"] },
  ID: { year: 2024, crops: ["Rice", "Sugarcane", "Field Corn (Zea mays)", "Cassava", "Potatoes"] },
  TH: { year: 2024, crops: ["Sugarcane", "Rice", "Cassava", "Field Corn (Zea mays)", "Soybeans"] },
  VN: { year: 2024, crops: ["Rice", "Sugarcane", "Cassava", "Field Corn (Zea mays)", "Potatoes"] },
  PH: { year: 2024, crops: ["Sugarcane", "Rice", "Field Corn (Zea mays)", "Cassava", "Potatoes"] },
  PK: { year: 2024, crops: ["Sugarcane", "Wheat", "Rice", "Field Corn (Zea mays)", "Potatoes"] },
  BD: { year: 2024, crops: ["Rice", "Potatoes", "Sugarcane", "Field Corn (Zea mays)", "Wheat"] },
  JP: { year: 2024, crops: ["Rice", "Sugar Beets", "Potatoes", "Sugarcane", "Wheat"] },
  KR: { year: 2024, crops: ["Rice", "Potatoes", "Tomatoes", "Soybeans", "Barley"] },
  AU: { year: 2024, crops: ["Sugarcane", "Wheat", "Barley", "Sorghum", "Potatoes"] },
  NZ: { year: 2024, crops: ["Potatoes", "Wheat", "Barley", "Field Corn (Zea mays)", "Tomatoes"] },
  NG: { year: 2024, crops: ["Cassava", "Yams", "Field Corn (Zea mays)", "Rice", "Sorghum"] },
  EG: { year: 2024, crops: ["Sugar Beets", "Sugarcane", "Wheat", "Field Corn (Zea mays)", "Tomatoes"] },
  ZA: { year: 2024, crops: ["Sugarcane", "Field Corn (Zea mays)", "Potatoes", "Wheat", "Soybeans"] },
  ET: { year: 2024, crops: ["Field Corn (Zea mays)", "Wheat", "Sorghum", "Barley", "Sugarcane"] },
  KE: { year: 2024, crops: ["Sugarcane", "Field Corn (Zea mays)", "Potatoes", "Cassava", "Wheat"] },
  GH: { year: 2024, crops: ["Cassava", "Yams", "Field Corn (Zea mays)", "Rice", "Sorghum"] },
  TZ: { year: 2024, crops: ["Cassava", "Field Corn (Zea mays)", "Rice", "Sugarcane", "Potatoes"] },
  MA: { year: 2024, crops: ["Wheat", "Sugar Beets", "Potatoes", "Tomatoes", "Barley"] },
};

export const SOIL_PRESETS = {
  "Sand":            { fc: 10.0, pwp: 4.0 },
  "Loamy Sand":      { fc: 14.0, pwp: 6.0 },
  "Sandy Loam":      { fc: 20.0, pwp: 9.0 },
  "Loam":            { fc: 31.0, pwp: 14.0 },
  "Silt Loam":       { fc: 33.0, pwp: 13.0 },
  "Silt":            { fc: 33.0, pwp: 8.0 },
  "Sandy Clay Loam": { fc: 27.0, pwp: 17.0 },
  "Clay Loam":       { fc: 36.0, pwp: 20.0 },
  "Silty Clay Loam": { fc: 38.0, pwp: 22.0 },
  "Sandy Clay":      { fc: 35.0, pwp: 22.0 },
  "Silty Clay":      { fc: 41.0, pwp: 27.0 },
  "Clay":            { fc: 45.0, pwp: 30.0 },
  "Custom":          null,
};

export const SOIL_REFERENCE_TABLE = [
  { soilType: "Sand",            fc: 10, pwp: 4,  awc: 60,  regions: "Sahara, Arabian Peninsula, Australian Outback" },
  { soilType: "Loamy Sand",      fc: 14, pwp: 6,  awc: 80,  regions: "Coastal dunes, semi-arid grasslands" },
  { soilType: "Sandy Loam",      fc: 20, pwp: 9,  awc: 110, regions: "US Midwest, Mediterranean, South Africa" },
  { soilType: "Loam",            fc: 31, pwp: 14, awc: 170, regions: "US Corn Belt, Northern Europe, Argentina Pampas" },
  { soilType: "Silt Loam",       fc: 33, pwp: 13, awc: 200, regions: "Mississippi Valley, Central China, Ukraine" },
  { soilType: "Silt",            fc: 33, pwp: 8,  awc: 250, regions: "River deltas, floodplains (Ganges, Nile, Mekong)" },
  { soilType: "Sandy Clay Loam", fc: 27, pwp: 17, awc: 100, regions: "Sub-Saharan Africa, SE Asia uplands" },
  { soilType: "Clay Loam",       fc: 36, pwp: 20, awc: 160, regions: "Ontario, UK, Northern India" },
  { soilType: "Silty Clay Loam", fc: 38, pwp: 22, awc: 160, regions: "Pacific Northwest, Central Europe, Korea" },
  { soilType: "Sandy Clay",      fc: 35, pwp: 22, awc: 130, regions: "Parts of Australia, Southern Africa" },
  { soilType: "Silty Clay",      fc: 41, pwp: 27, awc: 140, regions: "Southeast Asia rice paddies, Nile Delta" },
  { soilType: "Clay",            fc: 45, pwp: 30, awc: 150, regions: "Tropical Africa, South Asia, Vertisol regions" },
];

