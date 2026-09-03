def test_exposure_for_plot(client, exposure_seed):
    plot, fire = exposure_seed

    response = client.get(f"/v1/exposure/plots/{plot.id}")

    assert response.status_code == 200

    data = response.json()

    assert data["plot_id"] == plot.id
    assert data["plot_area_m2"] > 0
    assert data["fire_count"] >= 1
    assert len(data["items"]) >= 1

    first_item = data["items"][0]

    assert first_item["fire_id"] == fire.id
    assert first_item["intersection_area_m2"] > 0
    assert first_item["intersection_pct"] > 0

def test_exposure_geojson(client, exposure_seed):
    plot, fire = exposure_seed
    response = client.get(
        f"/v1/exposure/plots/{plot.id}/geojson"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["type"] == "FeatureCollection"
    assert data["plot_id"] == plot.id
    assert data["plot_area_m2"] > 0
    assert data["fire_count"] >= 1

    feature = next(
        item
        for item in data["feature"]
        if item["id"] == fire.id
    )

    assert feature["geometry"] is not None
    assert feature["properties"]["fire_id"] == fire.id
    assert feature["properties"]["intersection_area_m2"] > 0
    assert feature["properties"]["intersection_pct"] > 0