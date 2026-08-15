from types import SimpleNamespace

from services.optimization import evaluate_appliance


def make_appliance(
    id="test",
    name="Test Appliance",
    kw=1.5,
    interruptible=True,
    priority="low",
):
    return SimpleNamespace(
        id=id,
        name=name,
        kw=kw,
        interruptible=interruptible,
        priority=priority,
    )


def make_grid(tier="on_peak", rate=0.297868):
    return {"tier": tier, "rate": rate}


def test_high_power_flexible_load_pauses_on_peak():
    result = evaluate_appliance(
        make_appliance(
            id="ev_charger",
            name="EV Charger",
            kw=7.2,
            interruptible=True,
            priority="low",
        ),
        make_grid(),
    )

    assert result["decision"] == "pause"
    assert result["status"] == "paused"
    assert result["optimization_score"] >= 50
    assert result["savings_per_hour"] > 0


def test_non_interruptible_never_pauses():
    result = evaluate_appliance(
        make_appliance(kw=7.2, interruptible=False, priority="low"),
        make_grid(),
    )

    assert result["decision"] == "keep_running"
    assert result["status"] == "running"
    assert result["can_pause"] is False


def test_critical_never_pauses():
    result = evaluate_appliance(
        make_appliance(kw=7.2, interruptible=True, priority="critical"),
        make_grid(),
    )

    assert result["decision"] == "keep_running"
    assert result["status"] == "running"
    assert result["can_pause"] is False


def test_super_off_peak_keeps_medium_load_running():
    result = evaluate_appliance(
        make_appliance(kw=1.5, interruptible=True, priority="medium"),
        make_grid("super_off_peak", 0.021859),
    )

    assert result["decision"] == "keep_running"
    assert result["status"] == "running"


def test_rising_grid_adds_ten_points():
    baseline = evaluate_appliance(
        make_appliance(kw=1.5, interruptible=True, priority="medium"),
        make_grid("off_peak", 0.101676),
    )

    rising = evaluate_appliance(
        make_appliance(kw=1.5, interruptible=True, priority="medium"),
        make_grid("off_peak", 0.101676),
        live_grid={"condition": "rising"},
    )

    assert rising["optimization_score"] == baseline["optimization_score"] + 10


def test_lower_carbon_mix_subtracts_ten_points():
    baseline = evaluate_appliance(
        make_appliance(kw=1.5, interruptible=True, priority="medium"),
        make_grid("off_peak", 0.101676),
    )

    lower_carbon = evaluate_appliance(
        make_appliance(kw=1.5, interruptible=True, priority="medium"),
        make_grid("off_peak", 0.101676),
        carbon_signal={"signal": "lower_carbon_mix"},
    )

    assert lower_carbon["optimization_score"] == baseline["optimization_score"] - 10
