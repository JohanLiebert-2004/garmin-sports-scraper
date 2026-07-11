# Garmin Sports Scraper

This service exposes compact live-score data for a Garmin Connect IQ app.

- `GET /health` verifies that the service and score cache are available.
- `GET /scores` returns `matches`, `count`, `updated`, and `source`.

Each match contains `sport`, `home`, `away`, `scoreHome`, `scoreAway`, `phase`, and `event` fields sized for a watch display. The scraper runs through GitHub Actions and writes its latest result to `data/scores.json`.

Deploy on Render as a Python web service using `render.yaml`. The Garmin app should use `https://garmin-sports-scraper.onrender.com/scores`.
