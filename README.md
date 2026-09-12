# agri-fire-risk-service

FastAPI and PostGIS service for assessing wildfire exposure of agricultural land plots in Canadian and Australian scenarios.

## Features
- Land plots CRUD
- Wildfire perimeter CRUD
- PostGIS intersection and exposure-area analysis
- GeoJSON endpoints
- Interactive Leaflet exposure map
- Unified errors and request logging
- Integration tests

## Quick Start

```powershell
docker compose up -d db
poetry install
poetry run uvicorn app.main: app --reload