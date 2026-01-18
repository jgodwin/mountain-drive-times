# mountain-drive-times
Simple scraper and web app to measure drive times from Denver (or any origin) to a list of destinations.

## What it does
- Polls the Google Maps Distance Matrix API for current drive time ("duration_in_traffic").
- Stores each snapshot in a local SQLite database (`data/travel_times.sqlite`).
- Builds a static dashboard that shows:
  - a year-at-a-glance calendar heatmap (max daily travel time)
  - a per-day chart of hourly observations
- Works as a Flask app for local use, or as a fully static bundle for S3/Apache/GitHub Pages.

## How it works
- `scripts/scrape.py` fetches travel times and writes rows into SQLite.
- `scripts/build_static_site.py` exports JSON + assets into `webapp/static_site/`.
- `webapp/static/js/app.js` reads either live API endpoints (Flask) or static JSON (Pages/S3).

## Local development quickstart
### 1) Install dependencies
```
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2) Set environment variables
```
export GOOGLE_MAPS_API_KEY="your-key"
export MAPS_SCRAPER_ORIGIN="Golden, CO"
export MAPS_SCRAPER_DESTINATIONS="Frisco, CO;Winter Park, CO"
```

### 3) Scrape a snapshot
```
python scripts/scrape.py --once
```

### 4) Run the local web app
```
python webapp/app.py
```

### 5) Build the static site
```
python scripts/build_static_site.py --clean
```

## Lowest-cost deployment (GitHub Pages + Actions)
This setup runs the scraper every 30 minutes, rebuilds the static site, and deploys to GitHub Pages.

### 1) Add GitHub Actions secrets
Create these repository secrets:
- `GOOGLE_MAPS_API_KEY`
- `MAPS_SCRAPER_ORIGIN` (example: `Golden, CO`)
- `MAPS_SCRAPER_DESTINATIONS` (example: `Frisco, CO;Winter Park, CO`)

### 2) Enable GitHub Pages
In repo settings: Pages → Source → "GitHub Actions".

### 3) Done
The workflow in `.github/workflows/scrape-and-deploy.yml` will:
- run `python scripts/scrape.py --once`
- rebuild `webapp/static_site`
- commit the SQLite DB (`data/travel_times.sqlite`) so data persists between runs
- deploy the static site to Pages

Note: this keeps the DB in the repo history for persistence. It's the cheapest option, but the repo will grow over time.
