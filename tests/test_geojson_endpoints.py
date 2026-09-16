def find_feature(data: dict, feature_id: int):
    return next(
        (
            feature
            for feature in data["features"]
            if feature["id"]  == feature_id
        ),
        None,
    )

def test_land_plots_geojson(client, exposure_seed):
    plot, _ = exposure_seed

    response = client.get("/v1/land_plots/geojson")

    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"

    feature = find_feature(data, plot.id)

    assert feature is not None
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["properties"]["id"] == plot.id
    assert feature["properties"]["plot_id"] == plot.plot_id

def test_fire_perimeters_geojson(client, exposure_seed):
    _, fire = exposure_seed

    response = client.get("/v1/fire_perimeters/geojson")

    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"

    feature = find_feature(data, fire.id)

    assert feature is not None
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["properties"]["id"] == fire.id
    assert feature["properties"]["event_id"] == fire.event_id

def test_leaflet_demo_page(client):
    response = client.get("/static/index.html")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="map"' in response.text
    assert "/v1/land_plots/geojson" in response.text
    assert "/v1/fire_perimeters/geojson" in response.text
    assert "/v1/exposure/plots/" in response.text
    assert 'id="exposure-panel"' in response.text
    assert "loadExposure" in response.text
    assert 'aria-live="polite"' in response.text
    assert "renderExposurePanel" in response.text
    assert "data.features" in response.text
    assert "feature.properties" in response.text
    assert "collapsed: false" in response.text
    assert 'id=""exposure-panel' not in response.text
    assert "/v1/exposure/plot/${" not in response.text
    assert "data.feature.length" not in response.text
    assert "async function fetchJson" in response.text
    assert "response.ok" in response.text
    assert "body?.error?.message" in response.text
    assert "await fetchJson" in response.text
    assert 'id="map-status"' in response.text
    assert "renderExposurePanel(data)" in response.text
    assert "headers:" in response.text

def test_delete_fire_perimeter(client, exposure_seed):
    _, fire = exposure_seed

    response = client.delete(
        f"/v1/fire_perimeters/{fire.id}"
    )

    assert response.status_code == 200
    assert response.json() == {
        "deleted": True,
        "id": fire.id,
    }