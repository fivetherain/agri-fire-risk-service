import pytest
from fastapi.testclient import TestClient
from geoalchemy2.elements import WKTElement

from app.db.session import SessionLocal
from app.main import app
from app.models.fire_perimeter import FirePerimeter
from app.models.land_plot import LandPlot

@pytest.fixture()
def client():
    return TestClient(app)

@pytest.fixture()
def db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

@pytest.fixture()
def exposure_seed(db):
    db.query(FirePerimeter).filter(
        FirePerimeter.event_id.like("TEST_DAY6_%")
    ).delete(synchronize_session=False)

    db.query(LandPlot).filter(
        LandPlot.plot_id.like("TEST_DAY6_%")
    ).delete(synchronize_session=False)

    db.commit()

    plot = LandPlot(
        plot_id="TEST_DAY6_PLOT_001",
        crop_type="wheat",
        area_ha=10.0,
        geom=WKTElement(
           "POLYGON((0 0, 0.02 0, 0.02 0.02, 0 0.02, 0 0))",
            srid=4326,
        )
    )

    fire = FirePerimeter(
        source="test",
        event_id="TEST_DAY6_FIRE_001",
        name="Day6 Test Fire",
        geom=WKTElement(
            "POLYGON((0.01 0.01, 0.03 0.01, 0.03 0.03, 0.01 0.03, 0.01 0.01))",
            srid=4326,
        ),
    )

    db.add(plot)   
    db.add(fire)
    db.commit()

    db.refresh(plot)
    db.refresh(fire)

    yield plot, fire

    db.query(FirePerimeter).filter(FirePerimeter.id == fire.id).delete()
    db.query(LandPlot).filter(LandPlot.id == plot.id).delete()
    db.commit()