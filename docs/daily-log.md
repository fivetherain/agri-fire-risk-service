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