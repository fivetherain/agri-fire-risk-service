from fastapi import FastAPI
from sqlalchemy import text

from app.db.session import engine
from app.models.base import Base
from app.models.land_plot import LandPlot
from app.models.fire_perimeter import FirePerimeter

app = FastAPI(title='Agri Fire Risk Service', version='0.1.0')

@app.on_event('startup')
def startup():
    Base.metadata.create_all(bind=engine)

@app.get('/health')
def health():
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    return {'status': 'ok'}
