# The main entry point for the Agri Fire Risk Service.
from fastapi import FastAPI
from sqlalchemy import text
from app.db.session import engine
from app.models.base import Base
from app.models.land_plot import LandPlot
from app.models.fire_perimeter import FirePerimeter
import time
import logging
from fastapi import Request
from app.routers import land_plots
from app.routers.fire_perimeters import router as fire_router
from app.routers.exposure import router as exposure_router
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from fastapi.staticfiles import StaticFiles

setup_logging()

app = FastAPI(title='Agri Fire Risk Service', version='0.1.0')

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)

app.include_router(land_plots.router, prefix="/v1/land_plots")
app.include_router(fire_router, prefix="/v1/fire_perimeters")
app.include_router(exposure_router, prefix="/v1/exposure")

@app.on_event('startup')
def startup():
    Base.metadata.create_all(bind=engine)

@app.get('/health')
def health():
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    return {'status': 'ok'}

    # logging middleware
logging.basicConfig(level=logging.INFO)

@app.middleware('http')
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    cost_ms = (time.time() - start) * 1000
    logging.info("%s %s -> %s (%.1fms)", request.method, request.url, response.status_code, cost_ms)
    return response