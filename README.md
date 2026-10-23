# IrriTool — Localized Dynamic Precision Irrigation Scheduler

A static web application built for **Firebase Hosting** that computes localized precision irrigation schedules using FAO-56 crop water balance modeling, NASA POWER climatological normals, OpenStreetMap Nominatim reverse geocoding, and FAOSTAT QCL crop production rankings.

## Project Structure

- `firebase.json` — Firebase Hosting configuration serving the `public/` directory.
- `public/index.html` — Single-page 4-step wizard (`Select Location`, `Choose Crop`, `Choose Soil`, `Irrigation Schedule`).
- `public/styles.css` — Responsive UI styles, metrics, data tables, and chart styling.
- `public/data.js` — Crop parameters, FAO-56 Kc values, soil presets/reference tables, and regional/FAOSTAT crop rankings.
- `public/app.js` — Client-side hydrological grid-search simulation, Leaflet map controller, and API integrations (Nominatim, FAOSTAT, NASA POWER).

## Local Preview

Serve the `public/` folder with any static file server or the Firebase CLI:

```bash
# Option 1: Firebase Local Emulator
firebase emulators:start --only hosting

# Option 2: Python built-in HTTP server
python -m http.server 8000 --directory public
```

## Deploy to Firebase Hosting

1. Authenticate with Firebase (if not already logged in):
   ```bash
   firebase login
   ```
2. Associate this repository with your Firebase project:
   ```bash
   firebase use --add
   ```
3. Deploy to Firebase Hosting:
   ```bash
   firebase deploy --only hosting
   ```

