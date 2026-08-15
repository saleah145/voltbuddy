def test_get_appliances(client):
    response = client.get("/appliances")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4
    assert any(item["id"] == "ev_charger" for item in data)


def test_create_appliance(client):
    response = client.post(
        "/appliances",
        json={
            "name": "Dish Washer",
            "kw": 1.2,
            "interruptible": True,
            "priority": "low",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "dish_washer"


def test_duplicate_appliance_rejected(client):
    response = client.post(
        "/appliances",
        json={
            "name": "EV Charger",
            "kw": 7.2,
            "interruptible": True,
            "priority": "low",
        },
    )

    assert response.status_code == 400


def test_create_and_fetch_home(client):
    response = client.post(
        "/homes",
        json={
            "name": "Apartment",
            "appliances": ["ev_charger", "refrigerator"],
        },
    )

    assert response.status_code == 200
    home_id = response.json()["id"]

    fetch = client.get(f"/homes/{home_id}")

    assert fetch.status_code == 200
    data = fetch.json()
    assert data["name"] == "Apartment"

    appliance_ids = {item["id"] for item in data["appliances"]}
    assert appliance_ids == {"ev_charger", "refrigerator"}


def test_home_rejects_unknown_appliance(client):
    response = client.post(
        "/homes",
        json={
            "name": "Bad Home",
            "appliances": ["does_not_exist"],
        },
    )

    assert response.status_code == 400


def test_simulate_on_peak_pauses_ev_charger(client, monkeypatch):
    import routers.simulations as simulation_router

    monkeypatch.setattr(
        simulation_router,
        "get_live_grid_data",
        lambda: None,
    )
    monkeypatch.setattr(
        simulation_router,
        "get_live_carbon_signal",
        lambda: None,
    )

    response = client.post(
        "/simulate",
        json={
            "hour": 16,
            "month": 8,
            "weekday": 2,
            "appliances": ["ev_charger", "refrigerator"],
        },
    )

    assert response.status_code == 200
    data = response.json()

    by_id = {item["id"]: item for item in data["appliances"]}

    assert data["grid"]["tier"] == "on_peak"
    assert by_id["ev_charger"]["decision"] == "pause"
    assert by_id["refrigerator"]["decision"] == "keep_running"
    assert data["total_savings_per_hour"] > 0


def test_simulation_history_records_simulation(client, monkeypatch):
    import routers.simulations as simulation_router

    monkeypatch.setattr(
        simulation_router,
        "get_live_grid_data",
        lambda: None,
    )
    monkeypatch.setattr(
        simulation_router,
        "get_live_carbon_signal",
        lambda: None,
    )

    simulate = client.post(
        "/simulate",
        json={
            "hour": 10,
            "month": 8,
            "weekday": 2,
            "appliances": ["gaming_pc"],
        },
    )

    assert simulate.status_code == 200

    history = client.get("/simulations")
    assert history.status_code == 200

    data = history.json()
    assert len(data) == 1
    assert data[0]["hour"] == 10


def test_grid_live_unavailable_without_api_key(client):
    response = client.get("/grid/live")

    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False


def test_grid_carbon_unavailable_without_api_key(client):
    response = client.get("/grid/carbon")

    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False


def test_invalid_simulation_request_rejected(client):
    response = client.post(
        "/simulate",
        json={
            "hour": 25,
            "month": 8,
            "weekday": 2,
            "appliances": ["ev_charger"],
        },
    )

    assert response.status_code == 422

def test_delete_custom_appliance(client):
    created = client.post(
        "/appliances",
        json={
            "name": "Portable Fan",
            "kw": 0.08,
            "interruptible": True,
            "priority": "low",
        },
    )
    assert created.status_code == 200
    appliance_id = created.json()["id"]

    response = client.delete(f"/appliances/{appliance_id}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True

    appliances = client.get("/appliances").json()
    assert all(item["id"] != appliance_id for item in appliances)


def test_builtin_appliance_cannot_be_deleted(client):
    response = client.delete("/appliances/ev_charger")

    assert response.status_code == 400
    assert "cannot be deleted" in response.json()["detail"]


def test_delete_saved_home(client):
    created = client.post(
        "/homes",
        json={
            "name": "Temporary Home",
            "appliances": ["gaming_pc"],
        },
    )
    assert created.status_code == 200
    home_id = created.json()["id"]

    response = client.delete(f"/homes/{home_id}")
    assert response.status_code == 200

    fetch = client.get(f"/homes/{home_id}")
    assert fetch.status_code == 404


def test_clear_simulation_history(client, monkeypatch):
    import routers.simulations as simulation_router

    monkeypatch.setattr(
        simulation_router,
        "get_live_grid_data",
        lambda: None,
    )
    monkeypatch.setattr(
        simulation_router,
        "get_live_carbon_signal",
        lambda: None,
    )

    response = client.post(
        "/simulate",
        json={
            "hour": 10,
            "month": 8,
            "weekday": 2,
            "appliances": ["gaming_pc"],
        },
    )
    assert response.status_code == 200
    assert len(client.get("/simulations").json()) == 1

    clear = client.delete("/simulations")
    assert clear.status_code == 200
    assert clear.json()["deleted"] is True
    assert len(client.get("/simulations").json()) == 0

