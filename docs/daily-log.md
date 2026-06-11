#Daily log

##Day1 2026.02.28
-Postgis in Docker running + postgis extension enabled
-FastAPI running (/docs, /health)
-models: LandPlot, FirePerimeter
-Next: Day2 implement LandPlot CRUD and insert sample polygons

##Day3
-implement Fireperimeter CRUD (WKT in, GeoJSON out)
-Added exposure endPoint:St_intersects + ST_Intersection + ST_Area(geography)
_verified in Swagger with 1 plot + 1 perimeter intersecting

## Day 4 - Synthetic Agricultural Land Plot Data
Generated 10,000 synthetic agricultural land plot polygons for Canada Saskatchewan.
Purpose:
- Prepare spatial test data for PostGIS query performance testing
- Simulate agriculture / land management scenarios
- Use WKT + GeoAlchemy2 to insert Polygon geometries into PostGIS
Command:
##bash
###poetry run python -m scripts.generate_land_plots --n 10000 --region canada_sk --reset

##  Day6 - Errors, Logging, and Tests
# - Added centralized logging configuration.
# - Added request logging middleware to record method, path, status code, and duration.
# - Added global exception handlers for HTTP errors, validation errors, and unexpected server errors.
# - Added pytest tests for:
#   - health check
#   - land plot database creation
#   - wildfire exposure endpoint
### Commands
# ```bash
# poetry run pytest -q
# poetry run uvicorn app.main:app --reload

##Day7
### Agri Fire Exposure API
A FastAPI + PostGIS backend service for assessing wildfire exposure of agricultural land plots.
This project models agricultural land plots and wildfire perimeters as spatial polygons, then calculates whether a land plot intersects with wildfire areas and estimates the exposed area.
### Tech Stack

- FastAPI
- PostgreSQL + PostGIS
- SQLAlchemy
- GeoAlchemy2
- Docker Compose
- Pytest

### Features

- Land plot CRUD
- Fire perimeter CRUD
- Spatial intersection query
- Exposure area calculation
- PostGIS GiST index
- EXPLAIN ANALYZE performance comparison
- Request logging middleware
- Unified error responses
- Pytest test cases
- Docker Compose local deployment

### Project Structure

```text
app/
  db/
  models/
  routers/
  schemas/
  middleware/
  exceptions/
scripts/
tests/
docs/
Dockerfile
docker-compose.yml
README.md

## Day8 - GeoJSON API + Leaflet Demo

- Fixed FirePerimeter CRUD route bugs.
- Added GeoJSON FeatureCollection endpoints for land plots and fire perimeters.
- Added a Leaflet demo page served by FastAPI static files.
- Loaded PostGIS polygon data into a browser map.
- Prepared the project for the weekend visual demo.

## Day9 - GeoJSON Demo Stabilization and Tests

### What I built

- Fixed Day8 GeoJSON endpoint bugs.
- Fixed Leaflet demo JavaScript and CSS issues.
- Added tests for land plot GeoJSON output.
- Added tests for fire perimeter GeoJSON output.
- Added a test for the static Leaflet demo page.

### Key technical points

- GeoJSON API should return FeatureCollection.
- PostGIS geometry is converted with ST_AsGeoJSON.
- Leaflet renders polygons with L.geoJSON().
- FastAPI StaticFiles serves the demo page.
- API shape should be protected with pytest.