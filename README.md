# IrriTool — Localized Dynamic Precision Irrigation Scheduler

A static web application built for **Firebase Hosting** that computes localized precision irrigation schedules using FAO-56 crop water balance modeling, NASA POWER climatological normals, OpenStreetMap Nominatim reverse geocoding, and FAOSTAT QCL crop production rankings.

## Project Structure

- `firebase.json` — Firebase Hosting configuration serving the `public/` directory.
- `public/index.html` — Single-page 4-step wizard (`Select Location`, `Choose Crop`, `Choose Soil`, `Irrigation Schedule`).
- `public/styles.css` — Responsive UI styles, metrics, data tables, and chart styling.
- `public/data.js` — Crop parameters, FAO-56 Kc values, soil presets/reference tables, and regional/FAOSTAT crop rankings.
- `public/app.js` — Client-side hydrological grid-search simulation, Leaflet map controller, and API integrations (Nominatim, FAOSTAT, NASA POWER).