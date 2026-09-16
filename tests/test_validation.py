from uuid import uuid4

import pytest

VALID_POLYGON = (
    "POLYGON((-123.10 49.10, -123.00 49.10, "
    "-123.00 49.20, -123.10 49.20, "
    "-123.10 49.10))"
)

def assert_validation_error(response, field: str):
    assert response.status_code == 422

    data = response.json()
    error = data["error"]

    assert error["type"] == "validation_error"
    assert error["message"] == "Request validation failed"
    assert any(
        detail["loc"][-1] == field
        for detail in error["details"]
    )

@pytest.mark.parametrize(
    "geom_wkt",
    [
        "NOT_A_GEOMETRY",
        "POINT(-123.05 49.15)",
        "POLYGON EMPTY",
        (
            "POLYGON((-123.10 49.10, -123.00 49.20, "
            "-123.10 49.20, -123.00 49.10, "
            "-123.10 49.10))"
        ),
        "POLYGON(200 49, 201 49, 201 50, 200 50, 200 49)",
    ],
    ids=[
        "malformed-wkt",
        "wrong-geometry-type",
        "empty-polygon",
        "self-intersection",
        "invalid-longtitude",
    ],
)

def test_land_plot_rejects_invalid_polygon_wkt(client, geom_wkt):
    response = client.post(
        "/v1/land_plots",
        json={
            "plot_id": "TEST_DAYS13_INVALID",
            "crop_type": "wheat",
            "area_ha": 10.0,
            "geom_wkt": geom_wkt,
        },
    )

    assert_validation_error(response, "geom_wkt")

@pytest.mark.parametrize("area_ha", [0, -1])
def test_land_plot_rejects_non_positive_area(client, area_ha):
    response = client.post(
        "/v1/land_plots",
        json={
            "plot_id": "TEST_DAY13_AREA",
            "crop_type": "wheat",
            "area_ha": area_ha,
            "geom_wkt": VALID_POLYGON,
        },
    )

    assert_validation_error(response, "area_ha")

def test_land_plot_update_rejects_point(
    client,
    exposure_seed,
):
    plot, _ =exposure_seed

    response = client.patch(
        f"v1/land_plots/{plot.id}",
        json={"geom_wkt": "POINT(-123.05 49.15)"},
    )

    assert_validation_error(response, "geom_wkt")

def test_land_plot_accepts_valid_polygon(client):
    create_id = None

    try:
        response = client.post(
            "/v1/land_plots",
            json={
                "plot_id": f"TEST_DAY13_{uuid4().hex}",
                "crop_type": "wheat",
                "area_ha": 10.0,
                "geom_wkt": VALID_POLYGON,
            },
        )

        assert response.status_code == 201

        data = response.json()
        create_id = data["id"]

        assert data["geom_geojson"]["type"] == "Polygon"

    finally:
        if create_id is not None:
            client.delete(f"/v1/land_plots/{create_id}")
