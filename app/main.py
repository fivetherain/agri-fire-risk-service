# The main entry point for the Agri Fire Risk Service.
from fastapi import FastAPI
from sqlalchemy import text
from app.db.session import engine
from app.models.base import Base
from app.models.land_plot import LandPlot # noqa: F401
from app.models.fire_perimeter import FirePerimeter # noqa: 401
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
