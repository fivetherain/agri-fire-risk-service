from geoalchemy2.elements import WKTElement

from app.models.land_plot import LandPlot

def test_create_land_plot_in_database(db):
    plot = LandPlot(
        plot_id="TEST_DAY6_CREATE_001",
        crop_type="canola",
        area_ha=20.0,
        geom=WKTElement(
            "POLYGON((1 1, 1.01 1, 1.01 1.01, 1 1.01, 1 1))",
            srid=4326,
        ),
    )

    db.add(plot)
    db.commit()
    db.refresh(plot)

    assert plot.id is not None
    assert plot.plot_id == "TEST_DAY6_CREATE_001"
    assert plot.crop_type == "canola"

    db.query(LandPlot).filter(LandPlot.id == plot.id).delete()
    db.commit()