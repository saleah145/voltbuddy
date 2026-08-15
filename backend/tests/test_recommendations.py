from services.recommendations import generate_recommendations


def test_pause_decision_creates_high_priority_recommendation():
    results = [
        {
            "id": "ev_charger",
            "name": "EV Charger",
            "decision": "pause",
            "optimization_score": 80,
            "savings_per_hour": 2.14,
        }
    ]

    recommendations = generate_recommendations(
        results,
        {"tier": "on_peak"},
    )

    assert recommendations[0]["type"] == "pause_now"
    assert recommendations[0]["priority"] == "high"


def test_super_off_peak_creates_good_time_to_run_recommendation():
    recommendations = generate_recommendations(
        [],
        {"tier": "super_off_peak"},
    )

    assert any(
        item["type"] == "good_time_to_run"
        for item in recommendations
    )


def test_fossil_heavy_mix_creates_carbon_recommendation():
    recommendations = generate_recommendations(
        [],
        {"tier": "off_peak"},
        carbon_signal={"signal": "fossil_heavy_mix"},
    )

    assert any(
        item["type"] == "carbon_context"
        and item["priority"] == "medium"
        for item in recommendations
    )
